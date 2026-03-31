# AutoTeam

**中文** | [English](#english)

---

## 中文说明

AutoTeam 是一个运行在 Claude Code 和 Copilot CLI 中的自主 AI 开发团队框架。输入一个需求，8 个专业 AI 智能体自动协作完成分析、设计、编码、测试和文档，全程无需人工干预。

### 快速开始

**Claude Code：**
```
/autoteam "构建一个任务管理的 REST API"
```

**Copilot CLI（仓库内自然语言触发，不支持 `/autoteam`）：**
```
让 AutoTeam 执行这个需求：构建一个任务管理的 REST API
```

Copilot 版本通过仓库指令文件触发：`.github/copilot-instructions.md` + `.github/instructions/autoteam.instructions.md`。

### 工作流程

```
需求输入
  ↓
产品规划师 ──→ requirement-card.yaml（结构化验收标准）
  ↓
架构设计师 ──→ adr.md + interface-contracts.yaml
  ↓  ← [讨论轮次：最多 3 轮]
实现工程师 ──→ 源代码
  ↓
多门控检查（Gates A-F）──→ 机械性违规校验 + 棘轮模式（棕地项目）
  ↓
QA 委员会（3 智能体 + 多模型投票）
  QA 安全  ──→ security-report.md
  QA 质量  ──→ quality-report.md
  QA 测试  ──→ test-report.md
  ↓  ← [修复循环：最多 3 轮，最小变更原则]
文档智能体 ──→ docs/ + AGENTS.md
  ↓
Work Chunk 证据文件 ──→ chunk.md（提交存证）
  ↓
Git 提交到新分支
  ↓
✅ 完成
```

### 团队成员

| 智能体 | 模型 (Claude Code) | 模型 (Copilot CLI) | 职责 |
|---|---|---|---|
| 编排 | opus | opus | 流水线控制、讨论调解、质量门控 |
| 产品规划师 | sonnet | sonnet | 需求分析 → 验收标准 |
| 架构设计师 | opus | opus | 技术选型 + 接口契约 |
| 实现工程师 | sonnet | sonnet | 编写代码，最小化修复 QA 问题 |
| QA 安全 | sonnet | sonnet | OWASP Top 10、注入、认证漏洞 |
| QA 质量 | sonnet | **gpt-5.1** | 复杂度、重复代码、SOLID 违规 |
| QA 测试 | sonnet | sonnet | 测试覆盖率对比验收标准 |
| 文档 | haiku | haiku | README、API 文档、AGENTS.md |

> Copilot CLI 中 QA Quality 使用 GPT 模型，实现**多模型委员会**投票，不同模型视角发现不同问题。
>
> Copilot CLI 通过 **GitHub Copilot 的模型路由**访问 Claude/GPT，不需要单独再配置 Anthropic API Key。

### v3.0 新特性（OpenAI Harness 集成）

| 特性 | 说明 |
|---|---|
| **多门控检查（Gates A-F）** | Gate A 格式/Lint → B 导入边界 → C 结构规则 → D 快照 → E 黄金输出 → F 数值等价 |
| **棘轮模式** | 棕地/遗留/重构项目中，允许现有违规，阻止新增违规 |
| **委员会投票** | 每个 QA 智能体输出 ACCEPT/REJECT 票，需 ≥2/3 ACCEPT 才能通过 |
| **AGENTS.md 自动生成** | 文档智能体自动检测 harness 命令，生成项目根目录的 AGENTS.md |
| **Work Chunk 证据** | 每次提交前生成 chunk.md，记录意图、前置条件、QA 结果、回滚方案 |

### 设计来源

| 设计 | 原则 | 来源 |
|---|---|---|
| `.autoteam/workspace/` 文件协议 | 仓库即真相 | Harness Engineering |
| 多门控检查（A-F） | 机械性强制 | OpenAI Harness |
| 棘轮机制 | 棕地支持 | OpenAI Harness |
| 委员会投票（2/3 多模型） | 智能体互审 | OpenAI Harness |
| Work Chunks 证据协议 | 证据化提交 | OpenAI Harness |
| AGENTS.md 自动生成 | 渐进式披露 | OpenAI Harness |
| 黄金规则 + QA 循环 | 熵管理 | Harness Engineering |
| 阶段摘要 + STEP 0: ORIENT | 智能体可读性 | Harness Engineering |
| Git 分支 + 提交集成 | 吞吐量→合并 | Harness Engineering |
| Sprint 契约 | 生成-评估契约 | Anthropic Original |
| 结构化评分（5 维度） | 评分标准 | Anthropic Original |
| Section 7: 简化规则 | Harness 简化 | Anthropic Original |

---

## English

AutoTeam is an autonomous AI development team framework running entirely inside Claude Code and Copilot CLI. One command triggers a full 8-agent pipeline that analyzes, designs, implements, tests, and documents software — no human steps between.

### Quick Start

**Claude Code:**
```
/autoteam "build a REST API for task management"
```

**Copilot CLI (repo-native natural language trigger, no `/autoteam` slash command):**
```
Use AutoTeam to implement: build a REST API for task management
```

The Copilot version is activated by repository instruction files: `.github/copilot-instructions.md` and `.github/instructions/autoteam.instructions.md`.

### How It Works

```
Explicit AutoTeam request
        ↓
  Orchestration (Opus)
        ↓
  Product Planner ──→ requirement-card.yaml
        ↓
  Architecture ──→ adr.md + interface-contracts.yaml
        ↓  ← [Discussion: up to 3 rounds]
  Implementation ──→ source code
        ↓
  Multi-Gate Check (Gates A-F) ──→ gate-report.md
        ↓
  QA Council (3 agents, multi-model voting)
    QA Security ──→ security-report.md
    QA Quality  ──→ quality-report.md
    QA Test     ──→ test-report.md
        ↓  ← [Fix loop: up to 3 rounds, minimal-change rule]
  Documentation ──→ docs/ + AGENTS.md
        ↓
  Work Chunk Evidence ──→ chunk.md
        ↓
  Git commit on new branch
        ↓
  ✅ Done
```

### Team

| Agent | Model (Claude Code) | Model (Copilot CLI) | Responsibility |
|---|---|---|---|
| Orchestration | opus | opus | Pipeline controller, mediator, quality arbiter |
| Product Planner | sonnet | sonnet | Requirement → acceptance criteria |
| Architecture | opus | opus | Tech stack + interface contracts |
| Implementation | sonnet | sonnet | Writes code; minimal-change fixes |
| QA Security | sonnet | sonnet | OWASP Top 10, injection, auth |
| QA Quality | sonnet | **gpt-5.1** | Complexity, duplication, SOLID |
| QA Test | sonnet | sonnet | Test coverage vs acceptance criteria |
| Documentation | haiku | haiku | README, API docs, AGENTS.md |

### Key Design Decisions

**Multi-Gate Check (A-F)** — Before QA agents run, deterministic gates check lint, import boundaries, structural rules, snapshots, golden outputs, and numerical equivalence. Gates B-F are conditional on project config. Ratchet mode allows existing violations in brownfield projects while blocking new ones.

**Council voting** — Each QA agent outputs a vote (ACCEPT/REJECT) with rationale and confidence. ALL_CLEAR requires ≥2/3 ACCEPT + zero CRITICAL + score ≥3.0/5. Copilot CLI uses GPT for QA Quality to provide cross-model perspective.

**Work Chunk evidence** — Before every commit, `chunk.md` is generated with intent, preconditions, gate results, council scores, and rollback instructions. Committed alongside code for auditable history.

**Minimal-change fix rule** — Implementation fixes only the specific file/function/lines in `fix-instructions.md`. No opportunistic refactoring.

**File ownership** — Each agent owns exactly one set of output files. Workspace: `.autoteam/workspace/`.

**Bounded loops** — Discussion phase and QA fix loop both capped at 3 rounds.

**AGENTS.md** — Documentation agent auto-detects the harness command (justfile/package.json/pyproject.toml/Makefile) and generates `AGENTS.md` at project root for future AI agent onboarding.

### Plugin Structure (v3.0)

AutoTeam is now a standard Claude Code plugin with multi-platform support:

```
.
├── .claude-plugin/
│   ├── plugin.json          # Claude Code plugin manifest
│   └── marketplace.json     # Claude marketplace metadata
├── skills/autoteam/
│   └── SKILL.md             # Canonical skill file (v3.0, self-contained)
├── commands/
│   ├── autoteam.md          # /autoteam slash command
│   └── autoteam-status.md   # /autoteam:status slash command
├── scripts/
│   ├── init-session.{sh,ps1}       # Session initialization
│   └── check-status.{sh,ps1}       # Status check utilities
├── hooks/                   # Claude Code lifecycle hooks
├── templates/               # Pipeline tracking templates
├── .github/
│   ├── copilot-instructions.md            # Copilot entry + AutoTeam trigger
│   ├── instructions/autoteam.instructions.md  # Copilot orchestration
│   └── hooks/               # Copilot-specific hooks
├── .codex/skills/           # Codex CLI support
├── .claude/skills/          # Legacy entry (deprecated, use skills/autoteam/SKILL.md)
├── src/                     # AutoTeam Python source (CLI runner)
├── tests/                   # Test suite
├── CLAUDE.md                # Project index + alignment table
└── config/                  # Configuration
```

**Entry points by platform:**
- **Claude Code:** `.claude-plugin/` + `skills/autoteam/SKILL.md` (canonical)
- **Copilot CLI:** `.github/copilot-instructions.md` + `.github/instructions/autoteam.instructions.md`
- **Codex CLI:** `.codex/skills/autoteam.md`

> The legacy `.claude/skills/autoteam.md` is deprecated. Use `skills/autoteam/SKILL.md` as the canonical entry.

### Requirements

- [Claude Code](https://claude.ai/code) CLI v0.5.0+ — for plugin installation
- [GitHub Copilot CLI](https://githubnext.com/projects/copilot-cli) — for repo-native `.github/` instruction version
- [Codex CLI](https://codex.dev) — for `.codex/skills/` version
- Anthropic API key (Claude Opus 4, Sonnet 4, Haiku models) for Claude Code
- GitHub Copilot subscription with multi-model access for Copilot CLI (no separate Anthropic/OpenAI key required by this repo)

