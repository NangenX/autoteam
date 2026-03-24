"""Permission controller for Copilot CLI.

Implements policy-driven permission handling for Copilot operations.
Integrates with the Policy Engine for decision making.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any
import re


class PermissionAction(Enum):
    """Actions for permission requests."""
    APPROVE = "approve"
    DENY = "deny"
    ASK_USER = "ask_user"
    ASK_POLICY = "ask_policy"


class OperationType(Enum):
    """Type of operation being requested."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    COMMAND_EXECUTE = "command_execute"
    NETWORK_REQUEST = "network_request"
    TOOL_USE = "tool_use"
    UNKNOWN = "unknown"


@dataclass
class PermissionRequest:
    """A permission request from Copilot CLI."""
    raw_text: str
    operation_type: OperationType
    target: str | None = None  # File path, command, URL, etc.
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class PermissionDecision:
    """Decision for a permission request."""
    action: PermissionAction
    key_to_send: str  # "y", "n", etc.
    reason: str
    logged: bool = True


class PermissionPolicy:
    """Policy rules for permission decisions."""

    def __init__(
        self,
        # Default behavior
        default_action: PermissionAction = PermissionAction.DENY,
        # Path-based rules
        allowed_paths: list[str] | None = None,
        denied_paths: list[str] | None = None,
        # Command-based rules
        allowed_commands: list[str] | None = None,
        denied_commands: list[str] | None = None,
        # Operation-based rules
        allowed_operations: list[OperationType] | None = None,
        denied_operations: list[OperationType] | None = None,
    ):
        self.default_action = default_action
        self.allowed_paths = allowed_paths or []
        self.denied_paths = denied_paths or [
            "**/.env*",
            "**/secrets*",
            "**/credentials*",
            "**/*.pem",
            "**/*.key",
        ]
        self.allowed_commands = allowed_commands or []
        self.denied_commands = denied_commands or [
            "rm -rf",
            "del /s /q",
            "format",
            "fdisk",
            "curl | sh",
            "wget | sh",
        ]
        self.allowed_operations = allowed_operations or [
            OperationType.FILE_READ,
            OperationType.TOOL_USE,
        ]
        self.denied_operations = denied_operations or [
            OperationType.FILE_DELETE,
            OperationType.COMMAND_EXECUTE,
        ]

    def evaluate(self, request: PermissionRequest) -> PermissionDecision:
        """Evaluate a permission request against policy.
        
        Args:
            request: The permission request to evaluate
            
        Returns:
            PermissionDecision with action and reason
        """
        # Check operation type first
        if request.operation_type in self.denied_operations:
            return PermissionDecision(
                action=PermissionAction.DENY,
                key_to_send="n",
                reason=f"Operation {request.operation_type.value} denied by policy",
            )

        # Check target path
        if request.target:
            for denied in self.denied_paths:
                if self._match_glob(request.target, denied):
                    return PermissionDecision(
                        action=PermissionAction.DENY,
                        key_to_send="n",
                        reason=f"Path matches denied pattern: {denied}",
                    )

            for allowed in self.allowed_paths:
                if self._match_glob(request.target, allowed):
                    return PermissionDecision(
                        action=PermissionAction.APPROVE,
                        key_to_send="y",
                        reason=f"Path matches allowed pattern: {allowed}",
                    )

        # Check commands
        if request.operation_type == OperationType.COMMAND_EXECUTE and request.target:
            for denied in self.denied_commands:
                if denied.lower() in request.target.lower():
                    return PermissionDecision(
                        action=PermissionAction.DENY,
                        key_to_send="n",
                        reason=f"Command matches denied pattern: {denied}",
                    )

        # Check if operation is allowed
        if request.operation_type in self.allowed_operations:
            return PermissionDecision(
                action=PermissionAction.APPROVE,
                key_to_send="y",
                reason=f"Operation {request.operation_type.value} allowed by policy",
            )

        # Default action
        return PermissionDecision(
            action=self.default_action,
            key_to_send="n" if self.default_action == PermissionAction.DENY else "y",
            reason="Default policy action applied",
        )

    def _match_glob(self, path: str, pattern: str) -> bool:
        """Match path against glob pattern."""
        import fnmatch
        # Normalize path separators
        path = path.replace("\\", "/")
        pattern = pattern.replace("\\", "/")
        return fnmatch.fnmatch(path, pattern)


class PermissionController:
    """Controller for handling Copilot permission requests.
    
    Combines:
    - Permission detection from output
    - Policy evaluation
    - Action execution
    - Audit logging
    """

    # Patterns for detecting permission requests
    PERMISSION_PATTERNS = [
        # File operations
        (re.compile(r"(read|view|open)\s+(?:file\s+)?['\"]?([^\s'\"]+)['\"]?", re.I),
         OperationType.FILE_READ),
        (re.compile(r"(write|create|modify|edit)\s+(?:file\s+)?['\"]?([^\s'\"]+)['\"]?", re.I),
         OperationType.FILE_WRITE),
        (re.compile(r"(delete|remove)\s+(?:file\s+)?['\"]?([^\s'\"]+)['\"]?", re.I),
         OperationType.FILE_DELETE),
        # Commands
        (re.compile(r"(run|execute|exec)\s+[`'\"]?([^`'\"]+)[`'\"]?", re.I),
         OperationType.COMMAND_EXECUTE),
        # Tools
        (re.compile(r"use\s+(?:tool\s+)?['\"]?(\w+)['\"]?", re.I),
         OperationType.TOOL_USE),
    ]

    def __init__(
        self,
        policy: PermissionPolicy | None = None,
        audit_callback: Callable[[PermissionRequest, PermissionDecision], None] | None = None,
    ):
        self.policy = policy or PermissionPolicy()
        self.audit_callback = audit_callback
        self._history: list[tuple[PermissionRequest, PermissionDecision]] = []

    def parse_request(self, text: str) -> PermissionRequest:
        """Parse permission request from Copilot output.
        
        Args:
            text: Raw text containing permission request
            
        Returns:
            Parsed PermissionRequest
        """
        import time

        operation_type = OperationType.UNKNOWN
        target = None

        # Try to match against known patterns
        for pattern, op_type in self.PERMISSION_PATTERNS:
            match = pattern.search(text)
            if match:
                operation_type = op_type
                # Get target from capture group
                if match.lastindex and match.lastindex >= 2:
                    target = match.group(2)
                elif match.lastindex and match.lastindex >= 1:
                    target = match.group(1)
                break

        return PermissionRequest(
            raw_text=text,
            operation_type=operation_type,
            target=target,
            timestamp=time.time(),
        )

    def handle(self, text: str) -> str:
        """Handle a permission request and return key to send.
        
        Args:
            text: Raw permission request text
            
        Returns:
            Key to send ("y", "n", etc.)
        """
        request = self.parse_request(text)
        decision = self.policy.evaluate(request)

        # Log to history
        self._history.append((request, decision))

        # Audit callback
        if self.audit_callback and decision.logged:
            self.audit_callback(request, decision)

        return decision.key_to_send

    async def handle_async(self, text: str) -> str:
        """Async version of handle for use with TTY sessions."""
        return self.handle(text)

    def get_history(self) -> list[tuple[PermissionRequest, PermissionDecision]]:
        """Get permission handling history."""
        return self._history.copy()

    def clear_history(self) -> None:
        """Clear permission history."""
        self._history.clear()


def create_review_only_policy() -> PermissionPolicy:
    """Create a policy for review-only operations (no modifications).
    
    This policy:
    - Allows file reads
    - Allows tool usage
    - Denies all writes, deletes, and command execution
    """
    return PermissionPolicy(
        default_action=PermissionAction.DENY,
        allowed_operations=[
            OperationType.FILE_READ,
            OperationType.TOOL_USE,
        ],
        denied_operations=[
            OperationType.FILE_WRITE,
            OperationType.FILE_DELETE,
            OperationType.COMMAND_EXECUTE,
            OperationType.NETWORK_REQUEST,
        ],
        denied_paths=[
            "**/.env*",
            "**/secrets*",
            "**/credentials*",
            "**/*.pem",
            "**/*.key",
            "**/node_modules/**",
            "**/.git/**",
        ],
    )
