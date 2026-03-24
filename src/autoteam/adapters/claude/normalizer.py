"""Normalize Claude CLI output to WorkerResult.

Converts parsed Claude output into the standard WorkerResult contract.
"""

from datetime import datetime, timezone
from typing import Any
import hashlib

from autoteam.contracts import (
    WorkerResult,
    ResultStatus,
    Artifact,
    ArtifactType,
    Metrics,
    NextActionHint,
)
from autoteam.adapters.claude.parser import ParsedOutput, OutputFormat, CodeBlock
from autoteam.adapters.claude.runner import ClaudeRunResult


class ClaudeNormalizer:
    """Converts Claude CLI output to WorkerResult."""

    def __init__(self, worker_id: str = "claude"):
        self.worker_id = worker_id

    def normalize(
        self,
        run_result: ClaudeRunResult,
        parsed: ParsedOutput,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> WorkerResult:
        """Normalize Claude output to WorkerResult.
        
        Args:
            run_result: Raw execution result
            parsed: Parsed output structure
            prompt: Original prompt
            context: Optional execution context
            
        Returns:
            Normalized WorkerResult
        """
        # Determine status
        status = self._determine_status(run_result, parsed)

        # Build artifacts
        artifacts = self._build_artifacts(parsed)

        # Build metrics
        metrics = self._build_metrics(run_result, parsed)

        # Determine confidence
        confidence = self._estimate_confidence(run_result, parsed)

        # Build next action hint
        next_hint = self._suggest_next_action(parsed, status)

        return WorkerResult(
            worker_id=self.worker_id,
            status=status,
            summary=parsed.summary or "No output",
            raw_output=run_result.stdout,
            artifacts=artifacts,
            confidence=confidence,
            metrics=metrics,
            next_action_hint=next_hint,
            timestamp=datetime.now(timezone.utc),
            error_info=None,  # Errors handled in error_mapper
        )

    def _determine_status(
        self,
        run_result: ClaudeRunResult,
        parsed: ParsedOutput,
    ) -> ResultStatus:
        """Determine result status from execution and output."""
        if run_result.exit_code != 0:
            if run_result.truncated:
                return ResultStatus.TIMEOUT
            return ResultStatus.FAILED

        if parsed.errors:
            return ResultStatus.PARTIAL  # Got output but with errors

        if not parsed.raw_text.strip():
            return ResultStatus.PARTIAL  # Empty output

        return ResultStatus.SUCCESS

    def _build_artifacts(self, parsed: ParsedOutput) -> list[Artifact]:
        """Build artifact list from parsed output."""
        artifacts = []

        # Main analysis as artifact
        if parsed.detailed_analysis:
            artifacts.append(Artifact(
                type=ArtifactType.ANALYSIS,
                content=parsed.detailed_analysis,
                name="analysis",
                metadata={
                    "format": parsed.format.value,
                    "has_code_blocks": len(parsed.code_blocks) > 0,
                },
            ))

        # Code blocks as artifacts
        for i, block in enumerate(parsed.code_blocks):
            artifacts.append(Artifact(
                type=ArtifactType.CODE_SNIPPET,
                content=block.content,
                name=f"code_{i}_{block.language}",
                metadata={
                    "language": block.language,
                    "start_line": block.start_line,
                    "end_line": block.end_line,
                },
            ))

        # File references as artifact
        if parsed.file_references:
            artifacts.append(Artifact(
                type=ArtifactType.FILE_LIST,
                content="\n".join(parsed.file_references),
                name="file_references",
                metadata={"count": len(parsed.file_references)},
            ))

        # Suggestions as artifact
        if parsed.suggestions:
            artifacts.append(Artifact(
                type=ArtifactType.SUGGESTIONS,
                content="\n".join(f"- {s}" for s in parsed.suggestions),
                name="suggestions",
                metadata={"count": len(parsed.suggestions)},
            ))

        return artifacts

    def _build_metrics(
        self,
        run_result: ClaudeRunResult,
        parsed: ParsedOutput,
    ) -> Metrics:
        """Build metrics from execution."""
        # Extract cost from JSON if available
        cost = None
        if parsed.json_data and "cost" in parsed.json_data:
            try:
                cost = float(parsed.json_data["cost"])
            except (TypeError, ValueError):
                pass

        # Estimate tokens from text length (rough)
        input_tokens = None
        output_tokens = len(parsed.raw_text) // 4 if parsed.raw_text else None

        return Metrics(
            duration_seconds=run_result.elapsed_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            api_calls=1,
        )

    def _estimate_confidence(
        self,
        run_result: ClaudeRunResult,
        parsed: ParsedOutput,
    ) -> float:
        """Estimate confidence in the result (0.0 - 1.0)."""
        confidence = 0.8  # Base confidence for successful execution

        # Penalize for errors/warnings
        if parsed.errors:
            confidence -= 0.2 * min(len(parsed.errors), 3)
        if parsed.warnings:
            confidence -= 0.1 * min(len(parsed.warnings), 3)

        # Penalize for short output
        if len(parsed.raw_text) < 100:
            confidence -= 0.1

        # Penalize for timeout/truncation
        if run_result.truncated:
            confidence -= 0.3

        # Penalize for non-zero exit
        if run_result.exit_code != 0:
            confidence -= 0.4

        # Boost for JSON output (more structured)
        if parsed.format == OutputFormat.JSON:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def _suggest_next_action(
        self,
        parsed: ParsedOutput,
        status: ResultStatus,
    ) -> NextActionHint:
        """Suggest next action based on output."""
        if status == ResultStatus.FAILED:
            return NextActionHint(
                action="retry",
                reason="Execution failed",
                suggested_target=None,
            )

        if status == ResultStatus.TIMEOUT:
            return NextActionHint(
                action="retry",
                reason="Execution timed out, consider simpler prompt",
                suggested_target=None,
            )

        if parsed.errors:
            return NextActionHint(
                action="review",
                reason=f"Output contains {len(parsed.errors)} error(s)",
                suggested_target="copilot",
            )

        if parsed.code_blocks:
            return NextActionHint(
                action="review",
                reason="Code analysis complete, recommend peer review",
                suggested_target="copilot",
            )

        return NextActionHint(
            action="continue",
            reason="Analysis complete",
            suggested_target=None,
        )


def hash_content(content: str) -> str:
    """Generate content hash for deduplication."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]
