"""Claude CLI output parser.

Parses both plain text and JSON structured output from Claude CLI.
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OutputFormat(Enum):
    """Detected output format."""
    PLAIN_TEXT = "plain_text"
    JSON = "json"
    MARKDOWN = "markdown"
    MIXED = "mixed"


@dataclass
class CodeBlock:
    """Extracted code block from output."""
    language: str
    content: str
    start_line: int
    end_line: int


@dataclass
class ParsedOutput:
    """Structured representation of Claude CLI output."""
    format: OutputFormat
    raw_text: str
    # For JSON output
    json_data: dict[str, Any] | None = None
    # Text sections
    summary: str = ""
    detailed_analysis: str = ""
    # Extracted elements
    code_blocks: list[CodeBlock] = field(default_factory=list)
    file_references: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ClaudeOutputParser:
    """Parser for Claude CLI output.
    
    Handles both JSON structured output (from --output-format json)
    and plain text/markdown output.
    """

    # Patterns for extracting structured info from text
    CODE_BLOCK_PATTERN = re.compile(
        r"```(\w*)\n(.*?)```",
        re.DOTALL | re.MULTILINE
    )
    FILE_REF_PATTERN = re.compile(
        r"`([^`]+\.[a-zA-Z0-9]+)`|'([^']+\.[a-zA-Z0-9]+)'"
    )
    WARNING_PATTERN = re.compile(
        r"(?:⚠️|warning|Warning|WARNING)[:\s]+(.+?)(?:\n|$)",
        re.IGNORECASE
    )
    ERROR_PATTERN = re.compile(
        r"(?:❌|error|Error|ERROR)[:\s]+(.+?)(?:\n|$)",
        re.IGNORECASE
    )

    def parse(self, raw_output: str) -> ParsedOutput:
        """Parse Claude CLI output.
        
        Args:
            raw_output: Raw stdout from Claude CLI
            
        Returns:
            ParsedOutput with structured data
        """
        if not raw_output.strip():
            return ParsedOutput(
                format=OutputFormat.PLAIN_TEXT,
                raw_text=raw_output,
            )

        # Try JSON first
        json_data = self._try_parse_json(raw_output)
        if json_data is not None:
            return self._parse_json_output(raw_output, json_data)

        # Parse as text/markdown
        return self._parse_text_output(raw_output)

    def _try_parse_json(self, text: str) -> dict[str, Any] | None:
        """Attempt to parse as JSON."""
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to find JSON embedded in output
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _parse_json_output(self, raw: str, data: dict[str, Any]) -> ParsedOutput:
        """Parse JSON structured output."""
        # Claude JSON output format varies, extract common fields
        result = ParsedOutput(
            format=OutputFormat.JSON,
            raw_text=raw,
            json_data=data,
        )

        # Extract summary from various possible keys
        for key in ["result", "response", "content", "output", "answer"]:
            if key in data and isinstance(data[key], str):
                result.summary = data[key][:500]
                result.detailed_analysis = data[key]
                break

        # Extract cost/usage info if present
        if "cost" in data:
            result.summary += f"\n[Cost: ${data['cost']:.4f}]"

        return result

    def _parse_text_output(self, raw: str) -> ParsedOutput:
        """Parse plain text or markdown output."""
        has_code_blocks = "```" in raw
        output_format = OutputFormat.MARKDOWN if has_code_blocks else OutputFormat.PLAIN_TEXT

        result = ParsedOutput(
            format=output_format,
            raw_text=raw,
        )

        # Extract code blocks
        result.code_blocks = self._extract_code_blocks(raw)

        # Extract file references
        result.file_references = self._extract_file_references(raw)

        # Extract warnings and errors
        result.warnings = self._extract_warnings(raw)
        result.errors = self._extract_errors(raw)

        # Generate summary (first paragraph or first 500 chars)
        result.summary = self._generate_summary(raw)
        result.detailed_analysis = raw

        # Extract suggestions (lines starting with - or *)
        result.suggestions = self._extract_suggestions(raw)

        return result

    def _extract_code_blocks(self, text: str) -> list[CodeBlock]:
        """Extract fenced code blocks."""
        blocks = []
        lines = text.split("\n")
        current_line = 0

        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or "text"
            content = match.group(2).strip()

            # Find line numbers
            start_pos = match.start()
            start_line = text[:start_pos].count("\n") + 1
            end_line = start_line + content.count("\n") + 2

            blocks.append(CodeBlock(
                language=language,
                content=content,
                start_line=start_line,
                end_line=end_line,
            ))

        return blocks

    def _extract_file_references(self, text: str) -> list[str]:
        """Extract file path references."""
        refs = set()
        for match in self.FILE_REF_PATTERN.finditer(text):
            ref = match.group(1) or match.group(2)
            if ref and "/" in ref or "\\" in ref or "." in ref:
                refs.add(ref)
        return sorted(refs)

    def _extract_warnings(self, text: str) -> list[str]:
        """Extract warning messages."""
        return [m.group(1).strip() for m in self.WARNING_PATTERN.finditer(text)]

    def _extract_errors(self, text: str) -> list[str]:
        """Extract error messages."""
        return [m.group(1).strip() for m in self.ERROR_PATTERN.finditer(text)]

    def _extract_suggestions(self, text: str) -> list[str]:
        """Extract bullet points as suggestions."""
        suggestions = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "* ", "• ")):
                # Skip short bullets or code
                content = line[2:].strip()
                if len(content) > 10 and not content.startswith("`"):
                    suggestions.append(content)
        return suggestions[:10]  # Limit to top 10

    def _generate_summary(self, text: str) -> str:
        """Generate a summary from the output."""
        # Remove code blocks for summary
        text_no_code = self.CODE_BLOCK_PATTERN.sub("[code]", text)

        # Get first paragraph or first 500 chars
        paragraphs = text_no_code.strip().split("\n\n")
        first_para = paragraphs[0] if paragraphs else text_no_code

        if len(first_para) > 500:
            return first_para[:497] + "..."
        return first_para
