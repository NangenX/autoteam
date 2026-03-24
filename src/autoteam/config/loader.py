"""YAML configuration loader for AutoTeam.

Loads role-to-CLI bindings and workflow configurations.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WorkerConfig:
    """Configuration for a single worker."""
    id: str
    vendor: str  # "claude" or "copilot"
    role: str
    executable: str | None = None
    timeout_seconds: int = 120
    max_retries: int = 2
    extra_args: list[str] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)


@dataclass
class JudgeConfig:
    """Configuration for the Judge."""
    provider: str = "deepseek"  # "deepseek", "claude", "openai"
    model: str | None = None
    api_key_env: str | None = None  # Environment variable name
    temperature: float = 0.1
    timeout_seconds: int = 60


@dataclass
class GuardrailsConfig:
    """Configuration for guardrails."""
    max_rounds: int = 5
    max_retries_per_worker: int = 2
    max_total_runtime_seconds: int = 600
    max_cost_usd: float = 1.0
    block_code_execution: bool = True


@dataclass
class WorkflowConfig:
    """Configuration for a workflow."""
    name: str
    description: str = ""
    worker_sequence: list[str] = field(default_factory=list)
    initial_worker: str = ""
    allow_parallel: bool = False


@dataclass
class AutoTeamConfig:
    """Complete AutoTeam configuration."""
    workers: dict[str, WorkerConfig] = field(default_factory=dict)
    judge: JudgeConfig = field(default_factory=JudgeConfig)
    guardrails: GuardrailsConfig = field(default_factory=GuardrailsConfig)
    workflows: dict[str, WorkflowConfig] = field(default_factory=dict)
    default_workflow: str = "review"


class ConfigLoader:
    """Loads and validates AutoTeam configuration from YAML."""

    DEFAULT_CONFIG_PATHS = [
        "autoteam.yaml",
        "autoteam.yml",
        ".autoteam.yaml",
        ".autoteam.yml",
        "config/autoteam.yaml",
    ]

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else None

    def load(self) -> AutoTeamConfig:
        """Load configuration from file.
        
        Returns:
            Parsed AutoTeamConfig
        """
        path = self._find_config_file()
        if path is None:
            return self._default_config()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return self._parse_config(data)

    def _find_config_file(self) -> Path | None:
        """Find configuration file."""
        if self.config_path and self.config_path.exists():
            return self.config_path

        for candidate in self.DEFAULT_CONFIG_PATHS:
            path = Path(candidate)
            if path.exists():
                return path

        return None

    def _parse_config(self, data: dict[str, Any]) -> AutoTeamConfig:
        """Parse configuration from dictionary."""
        config = AutoTeamConfig()

        # Parse workers
        if "workers" in data:
            for worker_id, worker_data in data["workers"].items():
                config.workers[worker_id] = WorkerConfig(
                    id=worker_id,
                    vendor=worker_data.get("vendor", "claude"),
                    role=worker_data.get("role", worker_id),
                    executable=worker_data.get("executable"),
                    timeout_seconds=worker_data.get("timeout_seconds", 120),
                    max_retries=worker_data.get("max_retries", 2),
                    extra_args=worker_data.get("extra_args", []),
                    env_vars=worker_data.get("env_vars", {}),
                )

        # Parse judge
        if "judge" in data:
            j = data["judge"]
            config.judge = JudgeConfig(
                provider=j.get("provider", "deepseek"),
                model=j.get("model"),
                api_key_env=j.get("api_key_env"),
                temperature=j.get("temperature", 0.1),
                timeout_seconds=j.get("timeout_seconds", 60),
            )

        # Parse guardrails
        if "guardrails" in data:
            g = data["guardrails"]
            config.guardrails = GuardrailsConfig(
                max_rounds=g.get("max_rounds", 5),
                max_retries_per_worker=g.get("max_retries_per_worker", 2),
                max_total_runtime_seconds=g.get("max_total_runtime_seconds", 600),
                max_cost_usd=g.get("max_cost_usd", 1.0),
                block_code_execution=g.get("block_code_execution", True),
            )

        # Parse workflows
        if "workflows" in data:
            for wf_name, wf_data in data["workflows"].items():
                config.workflows[wf_name] = WorkflowConfig(
                    name=wf_name,
                    description=wf_data.get("description", ""),
                    worker_sequence=wf_data.get("worker_sequence", []),
                    initial_worker=wf_data.get("initial_worker", ""),
                    allow_parallel=wf_data.get("allow_parallel", False),
                )

        config.default_workflow = data.get("default_workflow", "review")

        # Add defaults if no workers defined
        if not config.workers:
            config = self._default_config()

        return config

    def _default_config(self) -> AutoTeamConfig:
        """Create default configuration."""
        return AutoTeamConfig(
            workers={
                "claude": WorkerConfig(
                    id="claude",
                    vendor="claude",
                    role="analyst",
                    executable="claude",
                ),
                "copilot": WorkerConfig(
                    id="copilot",
                    vendor="copilot",
                    role="reviewer",
                    executable="copilot",
                ),
            },
            judge=JudgeConfig(),
            guardrails=GuardrailsConfig(),
            workflows={
                "review": WorkflowConfig(
                    name="review",
                    description="Code review workflow",
                    worker_sequence=["claude", "copilot"],
                    initial_worker="claude",
                ),
            },
            default_workflow="review",
        )


def load_config(path: str | Path | None = None) -> AutoTeamConfig:
    """Convenience function to load configuration.
    
    Args:
        path: Optional path to config file
        
    Returns:
        Parsed AutoTeamConfig
    """
    loader = ConfigLoader(path)
    return loader.load()
