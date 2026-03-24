# AutoTeam Multi-CLI Control Plane 实施计划

**日期:** 2026-03-24  
**状态:** 待实施  
**分支:** autoteam-cli  
**语言:** Python 3.11+

---

## 1. 目标

把 AutoTeam 从 Claude Code 内部编排升级为**外部 Control Plane**，支持：

- 1 个 Claude CLI + 1 个 Copilot CLI 协作
- AI Judge 主导决策 + 规则护栏兜底
- 仅分析/评审类输出，不直接改代码

---

## 2. MVP 链路

```text
用户输入
    ↓
Control Plane 创建 run
    ↓
Claude Adapter 执行任务
    ↓
Judge (claude -p) 裁决
    ↓
Copilot Adapter 复核
    ↓
Judge 裁决
    ↓
停止 / 继续下一轮
```

---

## 3. 关键决策

| 决策项 | 结论 |
|--------|------|
| 架构 | 外部 control plane |
| MVP 链路 | Claude → Judge → Copilot → Judge → stop/continue |
| 输出边界 | 仅分析/评审，不改代码 |
| 会话模型 | 每次 run 新建即销毁 |
| 权限策略 | 策略层按场景决定 + 规则护栏兜底 |
| Policy Engine | AI Judge 主导 + 规则安全护栏 |
| Judge 执行 | Claude CLI `-p` + JSON schema |
| 实现语言 | Python |
| 角色绑定 | YAML 配置 |

---

## 4. 模块依赖顺序

```text
M1 基座
  ↓
M2 Claude Adapter
  ↓
M3 Copilot Adapter
  ↓
M4 Judge / Policy Engine
  ↓
M5 MVP Workflow
  ↓
M6 验证与可观测性
```

---

## 5. 模块详细拆分

### M1 基座

| 任务 ID | 文件 | 描述 |
|---------|------|------|
| m1-01 | `pyproject.toml` | 项目配置、依赖声明 |
| m1-02 | `src/autoteam/__init__.py` | 包入口 |
| m1-03 | `src/autoteam/contracts/run_state.py` | RunState 数据结构 |
| m1-04 | `src/autoteam/contracts/worker_result.py` | WorkerResult 标准化结果 |
| m1-05 | `src/autoteam/contracts/decision_schema.py` | Judge 决策 schema |
| m1-06 | `src/autoteam/runtime/run_manager.py` | run 生命周期管理 |
| m1-07 | `src/autoteam/runtime/process_runner.py` | 子进程启动/超时/收集 |
| m1-08 | `src/autoteam/runtime/session_registry.py` | 会话 ID 注册与状态 |
| m1-09 | `src/autoteam/storage/transcript_store.py` | 原始输出存储 |
| m1-10 | `src/autoteam/storage/run_store.py` | run 元数据持久化 |
| m1-11 | `src/autoteam/cli.py` | CLI 入口 (click/typer) |

### M2 Claude Adapter

| 任务 ID | 文件 | 描述 |
|---------|------|------|
| m2-01 | `src/autoteam/adapters/base.py` | Adapter 基类接口 |
| m2-02 | `src/autoteam/adapters/claude/runner.py` | `claude -p` 执行器 |
| m2-03 | `src/autoteam/adapters/claude/parser.py` | 输出解析 (text/json) |
| m2-04 | `src/autoteam/adapters/claude/normalizer.py` | 转 WorkerResult |
| m2-05 | `src/autoteam/adapters/claude/error_mapper.py` | 错误分类 |

### M3 Copilot Adapter

| 任务 ID | 文件 | 描述 |
|---------|------|------|
| m3-01 | `src/autoteam/adapters/copilot/tty_runner.py` | TTY 会话驱动 |
| m3-02 | `src/autoteam/adapters/copilot/prompt_sender.py` | 发送 prompt |
| m3-03 | `src/autoteam/adapters/copilot/permission_controller.py` | 权限策略执行 |
| m3-04 | `src/autoteam/adapters/copilot/timeline_parser.py` | 提取可判定输出 |
| m3-05 | `src/autoteam/adapters/copilot/normalizer.py` | 转 WorkerResult |

### M4 Judge / Policy Engine

| 任务 ID | 文件 | 描述 |
|---------|------|------|
| m4-01 | `src/autoteam/policy/evidence_builder.py` | 整理证据包 |
| m4-02 | `src/autoteam/policy/judge_adapter.py` | 调用 Judge (claude -p) |
| m4-03 | `src/autoteam/policy/judge_schema.py` | JSON schema 定义 |
| m4-04 | `src/autoteam/policy/rule_guardrails.py` | 硬限制：轮次/超时/预算 |
| m4-05 | `src/autoteam/policy/decision_executor.py` | 决策转动作 |

### M5 MVP Workflow

| 任务 ID | 文件 | 描述 |
|---------|------|------|
| m5-01 | `src/autoteam/workflows/review_flow.py` | Claude→Judge→Copilot→Judge 链路 |
| m5-02 | `config/roles.example.yaml` | 角色→CLI 绑定示例 |
| m5-03 | `src/autoteam/config/loader.py` | YAML 配置加载 |

### M6 验证与可观测性

| 任务 ID | 文件 | 描述 |
|---------|------|------|
| m6-01 | `src/autoteam/observability/event_bus.py` | 事件发布 |
| m6-02 | `src/autoteam/observability/run_summary.py` | run 结束汇总 |
| m6-03 | `tests/test_claude_adapter.py` | Claude adapter 单测 |
| m6-04 | `tests/test_copilot_adapter.py` | Copilot adapter 单测 |
| m6-05 | `tests/test_judge.py` | Judge 决策单测 |
| m6-06 | `tests/e2e/test_review_flow.py` | 端到端 MVP 链路测试 |

---

## 6. 目录结构

```text
autoteam/
├── .claude/
├── .openclaw/
├── docs/
│   └── superpowers/
│       ├── specs/
│       └── plans/
├── src/
│   └── autoteam/
│       ├── __init__.py
│       ├── cli.py
│       ├── contracts/
│       │   ├── run_state.py
│       │   ├── worker_result.py
│       │   └── decision_schema.py
│       ├── runtime/
│       │   ├── run_manager.py
│       │   ├── process_runner.py
│       │   └── session_registry.py
│       ├── storage/
│       │   ├── transcript_store.py
│       │   └── run_store.py
│       ├── adapters/
│       │   ├── base.py
│       │   ├── claude/
│       │   │   ├── runner.py
│       │   │   ├── parser.py
│       │   │   ├── normalizer.py
│       │   │   └── error_mapper.py
│       │   └── copilot/
│       │       ├── tty_runner.py
│       │       ├── prompt_sender.py
│       │       ├── permission_controller.py
│       │       ├── timeline_parser.py
│       │       └── normalizer.py
│       ├── policy/
│       │   ├── evidence_builder.py
│       │   ├── judge_adapter.py
│       │   ├── judge_schema.py
│       │   ├── rule_guardrails.py
│       │   └── decision_executor.py
│       ├── workflows/
│       │   └── review_flow.py
│       ├── config/
│       │   └── loader.py
│       └── observability/
│           ├── event_bus.py
│           └── run_summary.py
├── config/
│   └── roles.example.yaml
├── tests/
│   ├── test_claude_adapter.py
│   ├── test_copilot_adapter.py
│   ├── test_judge.py
│   └── e2e/
│       └── test_review_flow.py
├── runs/                          # 运行记录 (gitignore)
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## 7. 核心数据结构

### WorkerResult

```python
@dataclass
class WorkerResult:
    worker_id: str
    vendor: Literal["claude", "copilot"]
    role: str
    run_id: str
    status: Literal["succeeded", "failed", "timeout", "cancelled"]
    summary: str
    raw_output_path: Path
    artifacts: list[Artifact]
    confidence: Literal["high", "medium", "low", "unknown"]
    next_action_hint: NextActionHint | None
    metrics: Metrics
    error: ErrorInfo | None
```

### DecisionSchema (Judge 输出)

```python
@dataclass
class JudgeDecision:
    action: Literal["continue", "stop", "retry", "escalate"]
    target_worker: str | None
    reason: str
    confidence: Literal["high", "medium", "low"]
    stop_flag: bool
```

### RunState

```python
@dataclass
class RunState:
    run_id: str
    status: Literal["ready", "running", "done", "blocked", "failed"]
    current_step: int
    loop_count: int
    workers: list[WorkerResult]
    decisions: list[JudgeDecision]
    started_at: datetime
    finished_at: datetime | None
```

---

## 8. 规则护栏

| 规则 | 默认值 |
|------|--------|
| 最大轮次 | 5 |
| 单步超时 | 120s |
| 最大重试 | 2 |
| 重复输出检测阈值 | 0.9 相似度 |
| 预算上限 | 可选配置 |

---

## 9. YAML 配置示例

```yaml
# config/roles.example.yaml

roles:
  analyst:
    vendor: claude
    model: claude-sonnet-4
    prompt_template: prompts/analyst.md

  reviewer:
    vendor: copilot
    model: default
    prompt_template: prompts/reviewer.md

  judge:
    vendor: claude
    model: claude-sonnet-4
    output_format: json
    schema: schemas/judge_decision.json

guardrails:
  max_rounds: 5
  step_timeout_seconds: 120
  max_retries: 2
  duplicate_threshold: 0.9
```

---

## 10. MVP 验收标准

1. CLI 能启动一次 run，指定 requirement
2. Claude adapter 能执行并返回 WorkerResult
3. Copilot adapter 能执行并返回 WorkerResult
4. Judge 能返回结构化 JudgeDecision
5. review_flow 能跑通完整链路
6. 超时、重试、重复检测正常工作
7. run 结束后能生成汇总和转录

---

## 11. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Copilot CLI TTY 不稳定 | 先做受限模式 PoC，验证后再扩展 |
| Judge 输出不符合 schema | 强制 `--json-schema`，解析失败则重试 |
| 死循环 | 强制最大轮次 + 重复检测 |
| 权限提示阻塞 | permission_controller 自动处理或拒绝 |

---

## 12. 下一步

1. 创建 `pyproject.toml` 和目录骨架
2. 实现 M1 基座
3. 实现 M2 Claude Adapter
4. 实现 M3 Copilot Adapter
5. 实现 M4 Judge / Policy
6. 实现 M5 MVP Flow
7. 实现 M6 验证
8. 端到端测试
9. 提交 PR
