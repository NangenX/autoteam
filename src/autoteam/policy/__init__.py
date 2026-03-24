"""Policy Engine package.

Provides AI Judge for decision-making and rule-based guardrails for safety.
"""

from autoteam.policy.base_provider import (
    BaseJudgeProvider,
    JudgeProviderConfig,
    JudgeProviderType,
    JudgeRequest,
    JudgeResponse,
)
from autoteam.policy.deepseek_provider import DeepSeekJudgeProvider, create_deepseek_judge
from autoteam.policy.evidence_builder import EvidenceBuilder, EvidencePackage, build_simple_evidence
from autoteam.policy.rule_guardrails import (
    RuleGuardrails,
    GuardrailConfig,
    GuardrailResult,
    GuardrailAction,
)
from autoteam.policy.decision_executor import (
    DecisionExecutor,
    AsyncDecisionExecutor,
    ExecutionPlan,
    ExecutionAction,
)
from autoteam.policy.judge_adapter import JudgeAdapter, JudgeResult

__all__ = [
    # Base provider
    "BaseJudgeProvider",
    "JudgeProviderConfig",
    "JudgeProviderType",
    "JudgeRequest",
    "JudgeResponse",
    # DeepSeek provider
    "DeepSeekJudgeProvider",
    "create_deepseek_judge",
    # Evidence
    "EvidenceBuilder",
    "EvidencePackage",
    "build_simple_evidence",
    # Guardrails
    "RuleGuardrails",
    "GuardrailConfig",
    "GuardrailResult",
    "GuardrailAction",
    # Executor
    "DecisionExecutor",
    "AsyncDecisionExecutor",
    "ExecutionPlan",
    "ExecutionAction",
    # Main adapter
    "JudgeAdapter",
    "JudgeResult",
]
