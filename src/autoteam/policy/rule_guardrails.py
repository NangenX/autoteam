"""Rule-based guardrails for safety enforcement.

Provides hard limits that override Judge decisions when necessary.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import hashlib

from autoteam.contracts import JudgeDecision, WorkerResult


class GuardrailAction(Enum):
    """Action to take when guardrail is triggered."""
    ALLOW = "allow"       # Allow the operation
    BLOCK = "block"       # Block and stop
    OVERRIDE = "override" # Override with different action
    WARN = "warn"         # Allow but log warning


@dataclass
class GuardrailResult:
    """Result from guardrail evaluation."""
    action: GuardrailAction
    triggered_rules: list[str]
    modified_decision: JudgeDecision | None = None
    reason: str = ""


@dataclass
class GuardrailConfig:
    """Configuration for guardrails."""
    # Round limits
    max_rounds: int = 5
    max_retries_per_worker: int = 2
    
    # Time limits
    max_total_runtime_seconds: int = 600  # 10 minutes
    max_single_turn_seconds: int = 120
    
    # Content limits
    max_output_size_bytes: int = 100_000  # 100KB
    
    # Duplicate detection
    duplicate_threshold: float = 0.9  # Similarity threshold
    max_duplicate_rounds: int = 2
    
    # Budget limits
    max_api_calls: int = 50
    max_cost_usd: float = 1.0
    
    # Safety
    require_human_approval_on_escalate: bool = True
    block_code_execution: bool = True


class RuleGuardrails:
    """Rule-based safety guardrails.
    
    These rules are evaluated AFTER the Judge decision and can
    override or block actions for safety reasons.
    
    Rules are ordered by priority - first matching rule wins.
    """

    def __init__(self, config: GuardrailConfig | None = None):
        self.config = config or GuardrailConfig()
        self._round_count = 0
        self._retry_counts: dict[str, int] = {}
        self._output_hashes: list[str] = []
        self._total_api_calls = 0
        self._total_cost = 0.0
        self._start_time: float | None = None

    def evaluate(
        self,
        decision: JudgeDecision,
        results: list[WorkerResult] | None = None,
        context: dict[str, Any] | None = None,
    ) -> GuardrailResult:
        """Evaluate guardrails against a Judge decision.
        
        Args:
            decision: The Judge's decision
            results: Recent worker results
            context: Additional context
            
        Returns:
            GuardrailResult with action and any modifications
        """
        context = context or {}
        triggered = []

        # Rule 1: Max rounds
        current_round = context.get("round_number", self._round_count)
        if current_round >= self.config.max_rounds:
            triggered.append("max_rounds_exceeded")
            return GuardrailResult(
                action=GuardrailAction.OVERRIDE,
                triggered_rules=triggered,
                modified_decision=JudgeDecision(
                    action="stop",
                    target_worker=None,
                    reason=f"Maximum rounds ({self.config.max_rounds}) reached",
                    confidence="high",
                    stop_flag=True,
                ),
                reason="Safety limit: maximum rounds exceeded",
            )

        # Rule 2: Max retries per worker
        if decision.action == "retry" and decision.target_worker:
            worker_id = decision.target_worker
            current_retries = self._retry_counts.get(worker_id, 0)
            if current_retries >= self.config.max_retries_per_worker:
                triggered.append("max_retries_exceeded")
                return GuardrailResult(
                    action=GuardrailAction.OVERRIDE,
                    triggered_rules=triggered,
                    modified_decision=JudgeDecision(
                        action="escalate",
                        target_worker=None,
                        reason=f"Worker {worker_id} exceeded retry limit",
                        confidence="high",
                        stop_flag=True,
                    ),
                    reason=f"Worker {worker_id} has been retried {current_retries} times",
                )

        # Rule 3: Duplicate output detection
        if results:
            for result in results:
                if self._is_duplicate_output(result.raw_output):
                    triggered.append("duplicate_output_detected")
                    return GuardrailResult(
                        action=GuardrailAction.OVERRIDE,
                        triggered_rules=triggered,
                        modified_decision=JudgeDecision(
                            action="stop",
                            target_worker=None,
                            reason="Detected duplicate/stuck output",
                            confidence="high",
                            stop_flag=True,
                        ),
                        reason="System appears stuck in a loop",
                    )

        # Rule 4: Budget limits
        if self._total_cost >= self.config.max_cost_usd:
            triggered.append("budget_exceeded")
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                triggered_rules=triggered,
                reason=f"Budget limit (${self.config.max_cost_usd}) exceeded",
            )

        # Rule 5: API call limits
        if self._total_api_calls >= self.config.max_api_calls:
            triggered.append("api_calls_exceeded")
            return GuardrailResult(
                action=GuardrailAction.OVERRIDE,
                triggered_rules=triggered,
                modified_decision=JudgeDecision(
                    action="stop",
                    target_worker=None,
                    reason="API call limit reached",
                    confidence="high",
                    stop_flag=True,
                ),
                reason=f"API call limit ({self.config.max_api_calls}) exceeded",
            )

        # Rule 6: Escalation requires human
        if decision.action == "escalate" and self.config.require_human_approval_on_escalate:
            triggered.append("escalation_flagged")
            # Don't block, but add warning
            return GuardrailResult(
                action=GuardrailAction.WARN,
                triggered_rules=triggered,
                reason="Escalation decision - human review recommended",
            )

        # No rules triggered - allow
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            triggered_rules=[],
        )

    def _is_duplicate_output(self, output: str) -> bool:
        """Check if output is similar to recent outputs."""
        if not output or len(output) < 50:
            return False

        # Simple hash-based duplicate detection
        output_hash = hashlib.md5(output.encode()).hexdigest()
        
        # Check against recent hashes
        duplicate_count = self._output_hashes.count(output_hash)
        
        # Add to history
        self._output_hashes.append(output_hash)
        if len(self._output_hashes) > 10:
            self._output_hashes.pop(0)

        return duplicate_count >= self.config.max_duplicate_rounds

    def record_round(self, decision: JudgeDecision) -> None:
        """Record a round for tracking."""
        self._round_count += 1
        
        if decision.action == "retry" and decision.target_worker:
            worker_id = decision.target_worker
            self._retry_counts[worker_id] = self._retry_counts.get(worker_id, 0) + 1

    def record_api_call(self, cost: float = 0.0) -> None:
        """Record an API call and its cost."""
        self._total_api_calls += 1
        self._total_cost += cost

    def reset(self) -> None:
        """Reset all counters."""
        self._round_count = 0
        self._retry_counts.clear()
        self._output_hashes.clear()
        self._total_api_calls = 0
        self._total_cost = 0.0
        self._start_time = None

    @property
    def stats(self) -> dict[str, Any]:
        """Get current guardrail stats."""
        return {
            "round_count": self._round_count,
            "retry_counts": dict(self._retry_counts),
            "api_calls": self._total_api_calls,
            "total_cost": self._total_cost,
            "remaining_rounds": self.config.max_rounds - self._round_count,
        }
