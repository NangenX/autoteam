"""Timeline parser for Copilot CLI output.

Extracts structured information from Copilot's timeline-style output,
including tool calls, file operations, and decision points.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Type of timeline event."""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    CODE_BLOCK = "code_block"
    RESPONSE = "response"
    PERMISSION = "permission"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class TimelineEvent:
    """A single event in the timeline."""
    type: EventType
    content: str
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    line_start: int = 0
    line_end: int = 0


@dataclass
class ParsedTimeline:
    """Structured timeline from Copilot output."""
    events: list[TimelineEvent]
    raw_text: str
    # Aggregated data
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    code_blocks: list[dict[str, str]] = field(default_factory=list)
    response_text: str = ""
    has_errors: bool = False
    permission_requests: list[str] = field(default_factory=list)


class TimelineParser:
    """Parser for Copilot CLI timeline output.
    
    Copilot CLI outputs a rich timeline with:
    - Tool calls and results
    - File operations
    - Code snippets
    - Thinking/reasoning steps
    - Permission dialogs
    """

    # Patterns for detecting different event types
    PATTERNS = {
        # Tool calls: ◼ tool_name or [tool_name]
        "tool_call": re.compile(
            r'(?:◼|■|\[)(\w+)(?:\])?(?:\s*\(([^)]*)\))?',
        ),
        # File paths
        "file_path": re.compile(
            r'(?:Reading|Writing|Opening|Viewing|Created|Modified)\s+[`"\']?([^\s`"\']+\.[a-zA-Z0-9]+)[`"\']?',
            re.IGNORECASE,
        ),
        # Code blocks
        "code_block_start": re.compile(r'^```(\w*)'),
        "code_block_end": re.compile(r'^```$'),
        # Thinking indicators
        "thinking": re.compile(r'(?:Thinking|Analyzing|Processing|Searching)\.{0,3}', re.I),
        # Permission requests
        "permission": re.compile(r'(?:Allow|Approve|Permission|Confirm)[:\s]', re.I),
        # Errors
        "error": re.compile(r'(?:Error|Failed|Exception|Traceback)[:.\s]', re.I),
        # Response markers
        "response": re.compile(r'^(?:Answer|Response|Result|Summary)[:.\s]', re.I),
    }

    def parse(self, raw_output: str) -> ParsedTimeline:
        """Parse Copilot output into structured timeline.
        
        Args:
            raw_output: Raw text from Copilot CLI
            
        Returns:
            ParsedTimeline with events and aggregated data
        """
        lines = raw_output.split('\n')
        events: list[TimelineEvent] = []
        
        # Tracking state
        in_code_block = False
        code_block_lang = ""
        code_block_lines: list[str] = []
        code_block_start = 0
        
        files_read: set[str] = set()
        files_written: set[str] = set()
        tool_calls: list[dict[str, Any]] = []
        code_blocks: list[dict[str, str]] = []
        permission_requests: list[str] = []
        has_errors = False
        response_lines: list[str] = []
        in_response = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Code block handling
            if in_code_block:
                if self.PATTERNS["code_block_end"].match(line_stripped):
                    # End code block
                    code_content = '\n'.join(code_block_lines)
                    events.append(TimelineEvent(
                        type=EventType.CODE_BLOCK,
                        content=code_content,
                        metadata={"language": code_block_lang},
                        line_start=code_block_start,
                        line_end=i,
                    ))
                    code_blocks.append({
                        "language": code_block_lang,
                        "content": code_content,
                    })
                    in_code_block = False
                    code_block_lines = []
                else:
                    code_block_lines.append(line)
                continue

            # Check for code block start
            code_match = self.PATTERNS["code_block_start"].match(line_stripped)
            if code_match:
                in_code_block = True
                code_block_lang = code_match.group(1) or "text"
                code_block_start = i
                continue

            # Check for tool calls
            tool_match = self.PATTERNS["tool_call"].search(line)
            if tool_match:
                tool_name = tool_match.group(1)
                tool_args = tool_match.group(2) if tool_match.lastindex >= 2 else None
                events.append(TimelineEvent(
                    type=EventType.TOOL_CALL,
                    content=line_stripped,
                    metadata={"tool": tool_name, "args": tool_args},
                    line_start=i,
                    line_end=i,
                ))
                tool_calls.append({
                    "name": tool_name,
                    "args": tool_args,
                    "line": i,
                })
                continue

            # Check for file operations
            file_match = self.PATTERNS["file_path"].search(line)
            if file_match:
                filepath = file_match.group(1)
                if "read" in line.lower() or "view" in line.lower() or "open" in line.lower():
                    events.append(TimelineEvent(
                        type=EventType.FILE_READ,
                        content=filepath,
                        line_start=i,
                        line_end=i,
                    ))
                    files_read.add(filepath)
                elif "writ" in line.lower() or "creat" in line.lower() or "modif" in line.lower():
                    events.append(TimelineEvent(
                        type=EventType.FILE_WRITE,
                        content=filepath,
                        line_start=i,
                        line_end=i,
                    ))
                    files_written.add(filepath)
                continue

            # Check for permission requests
            if self.PATTERNS["permission"].search(line):
                events.append(TimelineEvent(
                    type=EventType.PERMISSION,
                    content=line_stripped,
                    line_start=i,
                    line_end=i,
                ))
                permission_requests.append(line_stripped)
                continue

            # Check for errors
            if self.PATTERNS["error"].search(line):
                events.append(TimelineEvent(
                    type=EventType.ERROR,
                    content=line_stripped,
                    line_start=i,
                    line_end=i,
                ))
                has_errors = True
                continue

            # Check for thinking
            if self.PATTERNS["thinking"].search(line):
                events.append(TimelineEvent(
                    type=EventType.THINKING,
                    content=line_stripped,
                    line_start=i,
                    line_end=i,
                ))
                continue

            # Check for response start
            if self.PATTERNS["response"].search(line):
                in_response = True
                events.append(TimelineEvent(
                    type=EventType.RESPONSE,
                    content=line_stripped,
                    line_start=i,
                    line_end=i,
                ))

            # Collect response lines
            if in_response and line_stripped:
                response_lines.append(line)

        # Build parsed timeline
        return ParsedTimeline(
            events=events,
            raw_text=raw_output,
            tool_calls=tool_calls,
            files_read=sorted(files_read),
            files_written=sorted(files_written),
            code_blocks=code_blocks,
            response_text='\n'.join(response_lines),
            has_errors=has_errors,
            permission_requests=permission_requests,
        )

    def extract_summary(self, timeline: ParsedTimeline, max_length: int = 500) -> str:
        """Extract a summary from parsed timeline.
        
        Args:
            timeline: Parsed timeline
            max_length: Maximum summary length
            
        Returns:
            Summary string
        """
        parts = []

        # Tool activity summary
        if timeline.tool_calls:
            tools = set(tc["name"] for tc in timeline.tool_calls)
            parts.append(f"Used tools: {', '.join(tools)}")

        # File activity summary
        if timeline.files_read:
            parts.append(f"Read {len(timeline.files_read)} file(s)")
        if timeline.files_written:
            parts.append(f"Modified {len(timeline.files_written)} file(s)")

        # Code blocks summary
        if timeline.code_blocks:
            langs = set(cb["language"] for cb in timeline.code_blocks)
            parts.append(f"Produced {len(timeline.code_blocks)} code block(s): {', '.join(langs)}")

        # Error status
        if timeline.has_errors:
            parts.append("⚠️ Encountered errors")

        # Permission requests
        if timeline.permission_requests:
            parts.append(f"Required {len(timeline.permission_requests)} permission(s)")

        summary = "; ".join(parts)

        # Add response excerpt if there's room
        if timeline.response_text and len(summary) < max_length - 100:
            remaining = max_length - len(summary) - 10
            excerpt = timeline.response_text[:remaining]
            if len(timeline.response_text) > remaining:
                excerpt += "..."
            summary += f"\n{excerpt}"

        return summary[:max_length]


def extract_judgeable_content(timeline: ParsedTimeline) -> str:
    """Extract content suitable for Judge evaluation.
    
    Focuses on:
    - Tool call results
    - Code blocks
    - Response text
    - Errors
    
    Args:
        timeline: Parsed timeline
        
    Returns:
        Text suitable for Judge evaluation
    """
    parts = []

    # Tool calls
    if timeline.tool_calls:
        parts.append("## Tool Calls")
        for tc in timeline.tool_calls:
            parts.append(f"- {tc['name']}: {tc.get('args', '')}")

    # File operations
    if timeline.files_read or timeline.files_written:
        parts.append("\n## File Operations")
        if timeline.files_read:
            parts.append(f"Read: {', '.join(timeline.files_read)}")
        if timeline.files_written:
            parts.append(f"Written: {', '.join(timeline.files_written)}")

    # Code blocks
    if timeline.code_blocks:
        parts.append("\n## Code Produced")
        for cb in timeline.code_blocks:
            parts.append(f"```{cb['language']}")
            parts.append(cb['content'][:500])  # Truncate long code
            parts.append("```")

    # Response
    if timeline.response_text:
        parts.append("\n## Response")
        parts.append(timeline.response_text[:1000])  # Truncate

    # Errors
    if timeline.has_errors:
        parts.append("\n## Errors")
        for event in timeline.events:
            if event.type == EventType.ERROR:
                parts.append(f"- {event.content}")

    return '\n'.join(parts)
