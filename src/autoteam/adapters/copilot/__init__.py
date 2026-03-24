"""Copilot CLI Adapter package.

Provides integration with GitHub Copilot CLI using TTY interaction.
"""

from autoteam.adapters.copilot.adapter import CopilotAdapter, create_copilot_adapter
from autoteam.adapters.copilot.tty_runner import TTYRunner, TTYSession, TTYConfig, TTYOutput, SessionState
from autoteam.adapters.copilot.prompt_sender import PromptSender, PromptResult, PromptMode
from autoteam.adapters.copilot.permission_controller import (
    PermissionController,
    PermissionPolicy,
    PermissionRequest,
    PermissionDecision,
    PermissionAction,
    OperationType,
    create_review_only_policy,
)
from autoteam.adapters.copilot.timeline_parser import (
    TimelineParser,
    ParsedTimeline,
    TimelineEvent,
    EventType,
    extract_judgeable_content,
)
from autoteam.adapters.copilot.normalizer import CopilotNormalizer

__all__ = [
    # Main adapter
    "CopilotAdapter",
    "create_copilot_adapter",
    # TTY runner
    "TTYRunner",
    "TTYSession",
    "TTYConfig",
    "TTYOutput",
    "SessionState",
    # Prompt sender
    "PromptSender",
    "PromptResult",
    "PromptMode",
    # Permission controller
    "PermissionController",
    "PermissionPolicy",
    "PermissionRequest",
    "PermissionDecision",
    "PermissionAction",
    "OperationType",
    "create_review_only_policy",
    # Timeline parser
    "TimelineParser",
    "ParsedTimeline",
    "TimelineEvent",
    "EventType",
    "extract_judgeable_content",
    # Normalizer
    "CopilotNormalizer",
]
