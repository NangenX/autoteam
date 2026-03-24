"""Review workflow - MVP implementation.

Claude → Judge → Copilot → Judge → stop/continue
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable
from uuid import uuid4

from autoteam.adapters import ClaudeAdapter, CopilotAdapter, AdapterConfig
from autoteam.contracts import WorkerResult, JudgeDecision, RunState, ResultStatus
from autoteam.policy import (
    JudgeAdapter,
    JudgeResult,
    GuardrailConfig,
    ExecutionAction,
)
from autoteam.config.loader import AutoTeamConfig, load_config
from autoteam.storage import TranscriptStore, RunStore


class WorkflowState(Enum):
    """State of a workflow run."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A single step in the workflow."""
    step_number: int
    worker_id: str
    prompt: str
    result: WorkerResult | None = None
    judge_result: JudgeResult | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class WorkflowRun:
    """A complete workflow run."""
    run_id: str
    workflow_name: str
    task: str
    state: WorkflowState = WorkflowState.CREATED
    steps: list[WorkflowStep] = field(default_factory=list)
    current_round: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    final_result: str = ""
    error: str | None = None


class ReviewWorkflow:
    """MVP Review Workflow: Claude → Judge → Copilot → Judge.
    
    This workflow:
    1. Sends task to Claude for analysis
    2. Judge evaluates Claude's output
    3. If continue: Copilot reviews Claude's work
    4. Judge evaluates Copilot's output
    5. Loop until Judge says stop or limits hit
    
    Example:
        workflow = ReviewWorkflow()
        run = await workflow.execute("Review this code: ...")
        print(run.final_result)
    """

    def __init__(
        self,
        config: AutoTeamConfig | None = None,
        claude_adapter: ClaudeAdapter | None = None,
        copilot_adapter: CopilotAdapter | None = None,
        judge: JudgeAdapter | None = None,
        transcript_store: TranscriptStore | None = None,
        run_store: RunStore | None = None,
    ):
        self.config = config or load_config()
        
        # Initialize adapters
        self._claude = claude_adapter or ClaudeAdapter(
            AdapterConfig(
                executable=self.config.workers.get("claude", {}).executable or "claude",
                timeout_seconds=self.config.workers.get("claude", {}).timeout_seconds if "claude" in self.config.workers else 120,
            ),
            worker_id="claude",
        )
        
        self._copilot = copilot_adapter or CopilotAdapter(
            AdapterConfig(
                executable=self.config.workers.get("copilot", {}).executable or "copilot",
                timeout_seconds=self.config.workers.get("copilot", {}).timeout_seconds if "copilot" in self.config.workers else 120,
            ),
            worker_id="copilot",
        )
        
        # Initialize Judge (lazy - only if not provided)
        guardrail_config = GuardrailConfig(
            max_rounds=self.config.guardrails.max_rounds,
            max_retries_per_worker=self.config.guardrails.max_retries_per_worker,
            max_total_runtime_seconds=self.config.guardrails.max_total_runtime_seconds,
            max_cost_usd=self.config.guardrails.max_cost_usd,
        )
        self._judge = judge
        self._guardrail_config = guardrail_config
        self._judge_initialized = judge is not None
        
        # Storage
        self._transcript_store = transcript_store or TranscriptStore()
        self._run_store = run_store or RunStore()
        
        # Callbacks
        self._on_step_complete: Callable[[WorkflowStep], Awaitable[None]] | None = None
        self._on_judge_decision: Callable[[JudgeResult], Awaitable[None]] | None = None

    def on_step_complete(self, callback: Callable[[WorkflowStep], Awaitable[None]]) -> None:
        """Register callback for step completion."""
        self._on_step_complete = callback

    def on_judge_decision(self, callback: Callable[[JudgeResult], Awaitable[None]]) -> None:
        """Register callback for judge decisions."""
        self._on_judge_decision = callback

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        """Execute the review workflow.
        
        Args:
            task: The task/requirement to process
            context: Optional context (files, previous results, etc.)
            
        Returns:
            Completed WorkflowRun with results
        """
        run = WorkflowRun(
            run_id=str(uuid4())[:8],
            workflow_name="review",
            task=task,
            state=WorkflowState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        context = context or {}
        context["original_task"] = task
        context["run_id"] = run.run_id

        try:
            # Main loop
            while run.state == WorkflowState.RUNNING:
                run.current_round += 1
                context["round_number"] = run.current_round

                # Step 1: Claude analysis
                claude_step = await self._execute_worker_step(
                    run=run,
                    worker_id="claude",
                    prompt=self._build_claude_prompt(task, run.steps, context),
                    context=context,
                )

                if claude_step.result and claude_step.result.status == ResultStatus.FAILED:
                    run.state = WorkflowState.FAILED
                    run.error = f"Claude failed: {claude_step.result.summary}"
                    break

                # Judge evaluates Claude
                judge_result = await self._evaluate_with_judge(
                    results=[claude_step.result] if claude_step.result else [],
                    context=context,
                )
                claude_step.judge_result = judge_result

                if self._on_judge_decision:
                    await self._on_judge_decision(judge_result)

                # Check Judge decision
                if judge_result.final_action == "stop":
                    run.state = WorkflowState.COMPLETED
                    run.final_result = self._build_final_result(run.steps)
                    break

                if judge_result.final_action == "escalate":
                    run.state = WorkflowState.PAUSED
                    run.error = f"Escalation needed: {judge_result.reason}"
                    break

                # Step 2: Copilot review (if continuing)
                if judge_result.final_action == "continue":
                    copilot_step = await self._execute_worker_step(
                        run=run,
                        worker_id="copilot",
                        prompt=self._build_copilot_prompt(task, claude_step.result, context),
                        context=context,
                    )

                    # Judge evaluates Copilot
                    all_results = [
                        r for s in run.steps if s.result for r in [s.result]
                    ]
                    judge_result = await self._evaluate_with_judge(
                        results=all_results[-2:],  # Last 2 results
                        context=context,
                    )
                    copilot_step.judge_result = judge_result

                    if self._on_judge_decision:
                        await self._on_judge_decision(judge_result)

                    # Check Judge decision
                    if judge_result.final_action in ("stop", "escalate"):
                        run.state = WorkflowState.COMPLETED if judge_result.final_action == "stop" else WorkflowState.PAUSED
                        run.final_result = self._build_final_result(run.steps)
                        if judge_result.final_action == "escalate":
                            run.error = f"Escalation: {judge_result.reason}"
                        break

                # Safety check
                if run.current_round >= self.config.guardrails.max_rounds:
                    run.state = WorkflowState.COMPLETED
                    run.final_result = self._build_final_result(run.steps)
                    break

        except Exception as e:
            run.state = WorkflowState.FAILED
            run.error = str(e)

        run.completed_at = datetime.now(timezone.utc)

        # Store run
        self._run_store.save_run(run.run_id, self._serialize_run(run))

        return run

    async def _execute_worker_step(
        self,
        run: WorkflowRun,
        worker_id: str,
        prompt: str,
        context: dict[str, Any],
    ) -> WorkflowStep:
        """Execute a single worker step."""
        step = WorkflowStep(
            step_number=len(run.steps) + 1,
            worker_id=worker_id,
            prompt=prompt,
            started_at=datetime.now(timezone.utc),
        )

        # Select adapter
        adapter = self._claude if worker_id == "claude" else self._copilot

        # Execute
        result = await adapter.execute(prompt, context)
        step.result = result
        step.completed_at = datetime.now(timezone.utc)

        # Store transcript
        self._transcript_store.save_transcript(
            run_id=run.run_id,
            worker_id=worker_id,
            content=result.raw_output,
        )

        run.steps.append(step)

        if self._on_step_complete:
            await self._on_step_complete(step)

        return step

    async def _evaluate_with_judge(
        self,
        results: list[WorkerResult],
        context: dict[str, Any],
    ) -> JudgeResult:
        """Evaluate results with Judge."""
        # Lazy initialization of Judge
        if not self._judge_initialized:
            self._judge = JudgeAdapter.create_with_deepseek(
                guardrail_config=self._guardrail_config,
            )
            self._judge_initialized = True
        return await self._judge.evaluate(results, context)

    def _build_claude_prompt(
        self,
        task: str,
        previous_steps: list[WorkflowStep],
        context: dict[str, Any],
    ) -> str:
        """Build prompt for Claude."""
        parts = [f"Task: {task}"]

        if previous_steps:
            parts.append("\nPrevious work:")
            for step in previous_steps[-2:]:  # Last 2 steps
                if step.result:
                    parts.append(f"- {step.worker_id}: {step.result.summary[:200]}")

        parts.append("\nYour role: Analyze and provide detailed insights.")
        return "\n".join(parts)

    def _build_copilot_prompt(
        self,
        task: str,
        claude_result: WorkerResult | None,
        context: dict[str, Any],
    ) -> str:
        """Build prompt for Copilot."""
        parts = [f"Task: {task}"]

        if claude_result:
            parts.append("\nClaude's analysis:")
            parts.append(claude_result.summary[:500])

        parts.append("\nYour role: Review the analysis and provide additional insights or corrections.")
        return "\n".join(parts)

    def _build_final_result(self, steps: list[WorkflowStep]) -> str:
        """Build final result from all steps."""
        parts = ["## Workflow Results\n"]

        for step in steps:
            if step.result:
                parts.append(f"### {step.worker_id.capitalize()} (Step {step.step_number})")
                parts.append(step.result.summary)
                parts.append("")

        return "\n".join(parts)

    def _serialize_run(self, run: WorkflowRun) -> dict[str, Any]:
        """Serialize run for storage."""
        return {
            "run_id": run.run_id,
            "workflow_name": run.workflow_name,
            "task": run.task,
            "state": run.state.value,
            "current_round": run.current_round,
            "steps": [
                {
                    "step_number": s.step_number,
                    "worker_id": s.worker_id,
                    "prompt": s.prompt[:200],
                    "result_summary": s.result.summary[:200] if s.result else None,
                    "result_status": s.result.status.value if s.result else None,
                }
                for s in run.steps
            ],
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "final_result": run.final_result[:1000],
            "error": run.error,
        }


async def run_review_workflow(
    task: str,
    config_path: str | None = None,
) -> WorkflowRun:
    """Convenience function to run review workflow.
    
    Args:
        task: The task to process
        config_path: Optional path to config file
        
    Returns:
        Completed WorkflowRun
    """
    config = load_config(config_path)
    workflow = ReviewWorkflow(config=config)
    return await workflow.execute(task)
