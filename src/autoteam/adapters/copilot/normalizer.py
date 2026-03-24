"""Normalize Copilot CLI output to WorkerResult.

Converts parsed Copilot timeline into the standard WorkerResult contract.
"""

from datetime import datetime, timezone
from typing import Any

from autoteam.contracts import (
    WorkerResult,
    ResultStatus,
    Artifact,
    ArtifactType,
    Metrics,
    NextActionHint,
    ErrorInfo,
    ErrorCategory,
)
from autoteam.adapters.copilot.timeline_parser import (
    ParsedTimeline,
    TimelineParser,
    extract_judgeable_content,
)
from autoteam.adapters.copilot.prompt_sender import PromptResult


class CopilotNormalizer:
    """Converts Copilot CLI output to WorkerResult."""

    def __init__(self, worker_id: str = "copilot"):
        self.worker_id = worker_id
        self._timeline_parser = TimelineParser()

    def normalize(
        self,
        prompt_result: PromptResult,
        context: dict[str, Any] | None = None,
    ) -> WorkerResult:
        """Normalize Copilot output to WorkerResult.
        
        Args:
            prompt_result: Result from prompt sender
            context: Optional execution context
            
        Returns:
            Normalized WorkerResult
        """
        # Parse timeline
        timeline = self._timeline_parser.parse(prompt_result.response_text)

        # Determine status
        status = self._determine_status(prompt_result, timeline)

        # Build artifacts
        artifacts = self._build_artifacts(timeline)

        # Build metrics
        metrics = self._build_metrics(prompt_result, timeline)

        # Determine confidence
        confidence = self._estimate_confidence(prompt_result, timeline)

        # Build next action hint
        next_hint = self._suggest_next_action(timeline, status)

        # Build error info if applicable
        error_info = self._build_error_info(prompt_result, timeline) if not prompt_result.success else None

        return WorkerResult(
            worker_id=self.worker_id,
            status=status,
            summary=self._timeline_parser.extract_summary(timeline),
            raw_output=prompt_result.response_text,
            artifacts=artifacts,
            confidence=confidence,
            metrics=metrics,
            next_action_hint=next_hint,
            timestamp=datetime.now(timezone.utc),
            error_info=error_info,
            vendor="copilot",
        )

    def _determine_status(
        self,
        prompt_result: PromptResult,
        timeline: ParsedTimeline,
    ) -> ResultStatus:
        """Determine result status from execution and output."""
        if not prompt_result.success:
            if prompt_result.error and "timeout" in prompt_result.error.lower():
                return ResultStatus.TIMEOUT
            return ResultStatus.FAILED

        if timeline.has_errors:
            return ResultStatus.PARTIAL

        if not prompt_result.response_text.strip():
            return ResultStatus.PARTIAL

        return ResultStatus.SUCCESS

    def _build_artifacts(self, timeline: ParsedTimeline) -> list[Artifact]:
        """Build artifact list from parsed timeline."""
        artifacts = []

        # Analysis content for Judge
        judgeable = extract_judgeable_content(timeline)
        if judgeable:
            artifacts.append(Artifact(
                type=ArtifactType.ANALYSIS,
                content=judgeable,
                name="analysis",
                metadata={
                    "tool_count": len(timeline.tool_calls),
                    "has_errors": timeline.has_errors,
                },
            ))

        # Code blocks as artifacts
        for i, block in enumerate(timeline.code_blocks):
            artifacts.append(Artifact(
                type=ArtifactType.CODE_SNIPPET,
                content=block["content"],
                name=f"code_{i}_{block['language']}",
                metadata={"language": block["language"]},
            ))

        # File list artifact
        all_files = timeline.files_read + timeline.files_written
        if all_files:
            artifacts.append(Artifact(
                type=ArtifactType.FILE_LIST,
                content="\n".join(f"- {f}" for f in all_files),
                name="file_operations",
                metadata={
                    "read_count": len(timeline.files_read),
                    "write_count": len(timeline.files_written),
                },
            ))

        # Tool calls artifact
        if timeline.tool_calls:
            tool_content = "\n".join(
                f"- {tc['name']}: {tc.get('args', '')}"
                for tc in timeline.tool_calls
            )
            artifacts.append(Artifact(
                type=ArtifactType.OTHER,
                content=tool_content,
                name="tool_calls",
                metadata={"count": len(timeline.tool_calls)},
            ))

        return artifacts

    def _build_metrics(
        self,
        prompt_result: PromptResult,
        timeline: ParsedTimeline,
    ) -> Metrics:
        """Build metrics from execution."""
        return Metrics(
            duration_seconds=prompt_result.elapsed_seconds,
            api_calls=len(timeline.tool_calls) + 1,  # +1 for main call
        )

    def _estimate_confidence(
        self,
        prompt_result: PromptResult,
        timeline: ParsedTimeline,
    ) -> float:
        """Estimate confidence in the result (0.0 - 1.0)."""
        confidence = 0.8  # Base confidence

        # Penalize for errors
        if timeline.has_errors:
            confidence -= 0.3

        # Penalize for failed execution
        if not prompt_result.success:
            confidence -= 0.4

        # Penalize for short output
        if len(prompt_result.response_text) < 100:
            confidence -= 0.1

        # Boost for tool usage (indicates engagement)
        if timeline.tool_calls:
            confidence += 0.05 * min(len(timeline.tool_calls), 3)

        # Boost for code production
        if timeline.code_blocks:
            confidence += 0.1

        # Penalize for permission blocks
        if timeline.permission_requests:
            confidence -= 0.1 * min(len(timeline.permission_requests), 3)

        return max(0.0, min(1.0, confidence))

    def _suggest_next_action(
        self,
        timeline: ParsedTimeline,
        status: ResultStatus,
    ) -> NextActionHint:
        """Suggest next action based on output."""
        if status == ResultStatus.FAILED:
            return NextActionHint(
                action="retry",
                reason="Execution failed",
            )

        if status == ResultStatus.TIMEOUT:
            return NextActionHint(
                action="retry",
                reason="Execution timed out",
            )

        if timeline.has_errors:
            return NextActionHint(
                action="review",
                reason=f"Output contains errors",
                suggested_target="claude",
            )

        if timeline.code_blocks:
            return NextActionHint(
                action="review",
                reason="Review produced code",
                suggested_target="claude",
            )

        return NextActionHint(
            action="continue",
            reason="Analysis complete",
        )

    def _build_error_info(
        self,
        prompt_result: PromptResult,
        timeline: ParsedTimeline,
    ) -> ErrorInfo | None:
        """Build error info from failed result."""
        if prompt_result.success and not timeline.has_errors:
            return None

        # Determine category
        if prompt_result.error:
            error_text = prompt_result.error.lower()
            if "timeout" in error_text:
                category = ErrorCategory.TRANSIENT
            elif "permission" in error_text:
                category = ErrorCategory.INPUT
            else:
                category = ErrorCategory.UNKNOWN
        else:
            category = ErrorCategory.UNKNOWN

        # Extract error message
        message = prompt_result.error or "Unknown error"
        if timeline.has_errors:
            error_events = [e for e in timeline.events if e.type.value == "error"]
            if error_events:
                message = error_events[0].content

        return ErrorInfo(
            category=category,
            code="COPILOT_ERROR",
            message=message,
            recoverable=category == ErrorCategory.TRANSIENT,
            suggestion="Check Copilot CLI logs for details",
        )
