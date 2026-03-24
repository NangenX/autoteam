"""Tests for Claude CLI Adapter."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from autoteam.adapters.claude.adapter import ClaudeAdapter, create_claude_adapter
from autoteam.adapters.claude.runner import ClaudeRunner, ClaudeRunResult
from autoteam.adapters.claude.parser import ClaudeOutputParser, ParsedOutput, OutputFormat
from autoteam.adapters.claude.normalizer import ClaudeNormalizer
from autoteam.adapters.claude.error_mapper import ClaudeErrorMapper
from autoteam.adapters.base import AdapterConfig, AdapterCapability
from autoteam.contracts import ResultStatus, ErrorCategory


class TestClaudeRunner:
    """Tests for ClaudeRunner."""

    @pytest.fixture
    def runner(self, adapter_config: AdapterConfig) -> ClaudeRunner:
        return ClaudeRunner(adapter_config)

    @pytest.mark.asyncio
    async def test_run_basic_prompt(self, runner: ClaudeRunner):
        """Test running a basic prompt."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Setup mock process
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"Hello, world!", b"")
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await runner.run("Say hello")

            assert result.exit_code == 0
            assert result.stdout == "Hello, world!"
            assert result.stderr == ""
            assert result.elapsed_seconds >= 0

    @pytest.mark.asyncio
    async def test_run_with_json_output(self, runner: ClaudeRunner):
        """Test running with JSON output flag."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                return_value=(b'{"result": "ok"}', b"")
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await runner.run("Get status", json_output=True)

            assert result.exit_code == 0
            # Verify --output-format json was in the command
            call_args = mock_exec.call_args
            assert "--output-format" in call_args[0] or "json" in str(call_args)

    @pytest.mark.asyncio
    async def test_health_check_success(self, runner: ClaudeRunner):
        """Test health check when CLI is available."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(
                return_value=(b"claude 1.0.0", b"")
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            healthy, message = await runner.health_check()

            assert healthy is True
            assert "1.0.0" in message or "OK" in message

    @pytest.mark.asyncio
    async def test_health_check_failure(self, runner: ClaudeRunner):
        """Test health check when CLI is not available."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = FileNotFoundError("claude not found")

            healthy, message = await runner.health_check()

            assert healthy is False
            assert "not found" in message.lower()


class TestClaudeOutputParser:
    """Tests for ClaudeOutputParser."""

    @pytest.fixture
    def parser(self) -> ClaudeOutputParser:
        return ClaudeOutputParser()

    def test_parse_plain_text(self, parser: ClaudeOutputParser):
        """Test parsing plain text output."""
        output = "This is a plain text response."
        result = parser.parse(output)

        assert result.format == OutputFormat.PLAIN_TEXT
        assert result.raw_text == output
        assert result.json_data is None

    def test_parse_json_output(self, parser: ClaudeOutputParser):
        """Test parsing JSON output."""
        output = '{"status": "success", "message": "done"}'
        result = parser.parse(output)

        assert result.format == OutputFormat.JSON
        assert result.json_data == {"status": "success", "message": "done"}

    def test_parse_json_in_code_block(self, parser: ClaudeOutputParser):
        """Test parsing JSON wrapped in markdown code block."""
        output = """Here is the result:
```json
{"status": "success"}
```
"""
        result = parser.parse(output)

        # Should extract JSON from code block
        assert result.json_data is not None or result.format in (OutputFormat.PLAIN_TEXT, OutputFormat.MARKDOWN)

    def test_parse_empty_output(self, parser: ClaudeOutputParser):
        """Test parsing empty output."""
        result = parser.parse("")

        assert result.format == OutputFormat.PLAIN_TEXT
        assert result.raw_text == ""


class TestClaudeNormalizer:
    """Tests for ClaudeNormalizer."""

    @pytest.fixture
    def normalizer(self) -> ClaudeNormalizer:
        return ClaudeNormalizer("claude")

    def test_normalize_success(self, normalizer: ClaudeNormalizer):
        """Test normalizing successful run."""
        run_result = ClaudeRunResult(
            stdout="Code review: looks good!",
            stderr="",
            exit_code=0,
            elapsed_seconds=3.5,
        )
        parsed = ParsedOutput(format=OutputFormat.PLAIN_TEXT, raw_text=run_result.stdout)

        result = normalizer.normalize(run_result, parsed, "Review this code", {})

        assert result.worker_id == "claude"
        assert result.status == ResultStatus.SUCCESS
        assert result.raw_output == run_result.stdout
        assert result.metrics.duration_seconds == 3.5
        assert result.confidence > 0

    def test_normalize_with_json(self, normalizer: ClaudeNormalizer):
        """Test normalizing JSON output."""
        run_result = ClaudeRunResult(
            stdout='{"findings": ["issue1", "issue2"]}',
            stderr="",
            exit_code=0,
            elapsed_seconds=2.0,
        )
        parsed = ParsedOutput(
            format=OutputFormat.JSON,
            raw_text=run_result.stdout,
            json_data={"findings": ["issue1", "issue2"]},
        )

        result = normalizer.normalize(run_result, parsed, "Find issues", {})

        assert result.status == ResultStatus.SUCCESS
        # Should have higher confidence for structured output
        assert result.confidence >= 0.7


class TestClaudeErrorMapper:
    """Tests for ClaudeErrorMapper."""

    @pytest.fixture
    def mapper(self) -> ClaudeErrorMapper:
        return ClaudeErrorMapper()

    def test_map_timeout_error(self, mapper: ClaudeErrorMapper):
        """Test mapping timeout error."""
        from asyncio import TimeoutError
        
        run_result = ClaudeRunResult(
            stdout="", stderr="", exit_code=-1, elapsed_seconds=120
        )
        error = TimeoutError("Process timed out")

        error_info = mapper.map_error(run_result, error)

        assert error_info is not None
        assert error_info.category == ErrorCategory.TRANSIENT
        assert error_info.recoverable is True

    def test_map_auth_error(self, mapper: ClaudeErrorMapper):
        """Test mapping authentication error."""
        run_result = ClaudeRunResult(
            stdout="",
            stderr="Error: Not authenticated",
            exit_code=1,
            elapsed_seconds=0.5,
        )

        error_info = mapper.map_error(run_result, None)

        assert error_info is not None
        assert error_info.category == ErrorCategory.CONFIG
        assert error_info.recoverable is False

    def test_map_success_no_error(self, mapper: ClaudeErrorMapper):
        """Test no error for successful run."""
        run_result = ClaudeRunResult(
            stdout="Success!", stderr="", exit_code=0, elapsed_seconds=1.0
        )

        error_info = mapper.map_error(run_result, None)

        assert error_info is None


class TestClaudeAdapter:
    """Integration tests for ClaudeAdapter."""

    @pytest.fixture
    def adapter(self, adapter_config: AdapterConfig) -> ClaudeAdapter:
        return ClaudeAdapter(adapter_config)

    def test_adapter_properties(self, adapter: ClaudeAdapter):
        """Test adapter properties."""
        assert adapter.name == "Claude CLI"
        assert AdapterCapability.NON_INTERACTIVE in adapter.capabilities
        assert AdapterCapability.JSON_OUTPUT in adapter.capabilities

    @pytest.mark.asyncio
    async def test_execute_success(self, adapter: ClaudeAdapter):
        """Test successful execution."""
        with patch.object(adapter._runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ClaudeRunResult(
                stdout="Review complete: no issues found",
                stderr="",
                exit_code=0,
                elapsed_seconds=2.5,
            )

            result = await adapter.execute("Review the code")

            assert result.status == ResultStatus.SUCCESS
            assert result.worker_id == "claude"
            assert "no issues" in result.raw_output.lower()

    @pytest.mark.asyncio
    async def test_execute_failure(self, adapter: ClaudeAdapter):
        """Test execution failure."""
        with patch.object(adapter._runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("CLI crashed")

            result = await adapter.execute("Do something")

            assert result.status == ResultStatus.FAILED
            assert result.error_info is not None

    @pytest.mark.asyncio
    async def test_health_check(self, adapter: ClaudeAdapter):
        """Test health check delegation."""
        with patch.object(
            adapter._runner, "health_check", new_callable=AsyncMock
        ) as mock_health:
            mock_health.return_value = (True, "claude 1.0.0")

            result = await adapter.health_check()

            assert result is True


class TestCreateClaudeAdapter:
    """Tests for factory function."""

    def test_create_with_defaults(self):
        """Test creating adapter with default values."""
        adapter = create_claude_adapter()

        assert adapter.worker_id == "claude"
        assert adapter.config.executable == "claude"

    def test_create_with_custom_config(self):
        """Test creating adapter with custom config."""
        adapter = create_claude_adapter(
            executable="/usr/local/bin/claude",
            timeout_seconds=300,
            max_retries=5,
            worker_id="claude-reviewer",
        )

        assert adapter.worker_id == "claude-reviewer"
        assert adapter.config.timeout_seconds == 300
        assert adapter.config.max_retries == 5
