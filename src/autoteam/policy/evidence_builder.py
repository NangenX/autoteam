"""Evidence builder for Judge input.

Formats worker results into structured evidence for Judge evaluation.
"""

from dataclasses import dataclass
from typing import Any

from autoteam.contracts import WorkerResult, ResultStatus


@dataclass
class EvidencePackage:
    """Packaged evidence for Judge evaluation."""
    formatted_text: str
    worker_count: int
    has_errors: bool
    total_confidence: float
    metadata: dict[str, Any]


class EvidenceBuilder:
    """Builds evidence packages from worker results.
    
    The evidence is formatted as structured text that the Judge
    can easily parse and evaluate.
    """

    def __init__(
        self,
        max_output_length: int = 4000,
        include_raw_output: bool = False,
    ):
        self.max_output_length = max_output_length
        self.include_raw_output = include_raw_output

    def build(
        self,
        results: list[WorkerResult],
        context: dict[str, Any] | None = None,
    ) -> EvidencePackage:
        """Build evidence package from worker results.
        
        Args:
            results: List of WorkerResult from workers
            context: Optional additional context
            
        Returns:
            EvidencePackage with formatted evidence
        """
        parts = []
        has_errors = False
        total_confidence = 0.0

        for result in results:
            part = self._format_result(result)
            parts.append(part)
            
            if result.status in (ResultStatus.FAILED, ResultStatus.TIMEOUT):
                has_errors = True
            total_confidence += result.confidence

        # Add context if provided
        if context:
            parts.append(self._format_context(context))

        formatted = "\n\n---\n\n".join(parts)

        # Truncate if too long
        if len(formatted) > self.max_output_length:
            formatted = formatted[:self.max_output_length - 100] + "\n\n[... truncated ...]"

        return EvidencePackage(
            formatted_text=formatted,
            worker_count=len(results),
            has_errors=has_errors,
            total_confidence=total_confidence / len(results) if results else 0,
            metadata={
                "worker_ids": [r.worker_id for r in results],
                "statuses": [r.status.value for r in results],
            },
        )

    def _format_result(self, result: WorkerResult) -> str:
        """Format a single worker result."""
        lines = [
            f"### Worker: {result.worker_id}",
            f"**Status:** {result.status.value}",
            f"**Confidence:** {result.confidence:.2f}",
            "",
            "**Summary:**",
            result.summary,
        ]

        # Add artifacts summary
        if result.artifacts:
            lines.append("")
            lines.append("**Artifacts:**")
            for artifact in result.artifacts[:5]:  # Limit to 5
                lines.append(f"- {artifact.name} ({artifact.type.value})")

        # Add error info if present
        if result.error_info:
            lines.append("")
            lines.append("**Error:**")
            lines.append(f"- Category: {result.error_info.category.value}")
            lines.append(f"- Message: {result.error_info.message}")
            if result.error_info.suggestion:
                lines.append(f"- Suggestion: {result.error_info.suggestion}")

        # Add next action hint
        if result.next_action_hint:
            lines.append("")
            lines.append("**Worker's Suggestion:**")
            lines.append(f"- Action: {result.next_action_hint.action}")
            lines.append(f"- Reason: {result.next_action_hint.reason}")

        # Optionally include raw output
        if self.include_raw_output and result.raw_output:
            lines.append("")
            lines.append("**Raw Output (excerpt):**")
            lines.append("```")
            lines.append(result.raw_output[:1000])
            if len(result.raw_output) > 1000:
                lines.append("[... truncated ...]")
            lines.append("```")

        return "\n".join(lines)

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format additional context."""
        lines = ["### Additional Context"]
        
        if "original_task" in context:
            lines.append(f"**Original Task:** {context['original_task']}")
        
        if "round_number" in context:
            lines.append(f"**Round:** {context['round_number']}")
        
        if "remaining_budget" in context:
            lines.append(f"**Remaining Rounds:** {context['remaining_budget']}")

        if "previous_decisions" in context:
            lines.append("**Previous Decisions:**")
            for dec in context["previous_decisions"][-3:]:  # Last 3
                lines.append(f"- {dec.get('action', 'unknown')}: {dec.get('reason', '')[:50]}")

        return "\n".join(lines)


def build_simple_evidence(
    result: WorkerResult,
    task: str | None = None,
) -> str:
    """Quick helper to build evidence from a single result.
    
    Args:
        result: Single WorkerResult
        task: Original task description
        
    Returns:
        Formatted evidence string
    """
    builder = EvidenceBuilder()
    context = {"original_task": task} if task else None
    package = builder.build([result], context)
    return package.formatted_text
