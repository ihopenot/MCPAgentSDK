# Phase 1 + 1.5 + 2 详细执行规范（SKILL.md 引用文件）

## Phase 1：设计讨论（Brainstorming）

**本阶段可在任意目录执行**，无需提前创建 worktree。

**⚠️ 第一步（强制）：必须使用 Skill 工具调用 `superpowers:brainstorming` 技能**。禁止在未调用该技能的情况下直接输出设计方案或开始提问。

**brainstorming 技能调用失败处理**：
- 若 Skill 工具返回错误（技能未安装/不可用）→ 输出：
  "superpowers:brainstorming 技能不可用。请检查 superpowers 插件是否已安装。
   或者，您可以手动进行设计讨论后执行 /opsx:propose --skip-brainstorming。"
- 禁止在技能不可用时跳过设计讨论直接生成文档

调用 `superpowers:brainstorming` 技能后，按照该技能的指引完成完整的设计讨论过程。

**⛔ 重要覆盖**：brainstorming 技能的 "After the Design" 部分指令在本集成技能中**全部被禁止**，
包括但不限于：写入 `docs/plans/`、调用 `writing-plans`、调用 `using-git-worktrees`（环境检查由 Phase 1.5 统一处理）。
设计讨论完成后，直接进入本技能的设计确认询问流程，忽略 brainstorming 技能中关于后续步骤的所有建议。

**⛔ 双重防护**：在 brainstorming 技能完成设计呈现后、进入 "After the Design" 部分前，
AI 必须立即检查——如果 brainstorming 输出包含以下任何关键词，必须忽略并输出覆盖提示：
- "docs/plans/"
- "writing-plans"
- "Ready to set up for implementation?"
- "using-git-worktrees"（在 Phase 1 上下文中）

检测到时输出：
"brainstorming 技能建议的后续步骤已被 OpenSpec 集成技能覆盖。现在进入 OpenSpec 设计确认流程。"

**在此阶段绝对禁止：创建任何文件、执行任何写操作。只允许读文件和向用户提问。**

1. 探索项目上下文（读取现有文件，检查 openspec/changes/ 中的活跃变更）
2. 逐一提问以了解目的、约束和成功标准
3. 提出 2-3 个方案及其权衡分析，并给出推荐
4. 分节呈现设计方案，每节后获取用户确认

**Phase 1 完成的唯一标准**：用户对完整设计方案（包括架构、技术选型、任务范围）给出明确的
整体确认回复，例如："确认"、"ok"、"同意"、"好的，开始创建"等。
用户对单个问题的回答不构成整体设计确认。若不确定用户是否已确认完整设计，必须明确询问：
"以上是完整的设计方案，请确认是否可以开始生成 OpenSpec 文档？"

**模糊回复处理规则**：若用户回复不在明确确认列表（"确认"/"ok"/"yes"/"同意"/"好的开始"/"开始生成"/"可以"/"没问题"）中，
且不是明确拒绝（"不"/"不行"/"重新设计"/"修改"/"再想想"），则视为模糊回复（如"嗯"/"差不多了"/"先这样吧"），
必须追问："您的回复不够明确，请确认是否可以开始生成 OpenSpec 文档？（请回复'确认'或'需要修改'）"

**⛔ 确认询问的强制格式**：询问用户时只能提供"生成文档"这一后续选项，禁止在询问语中出现
"直接实施代码"、"立即修改代码"、"直接开始开发"等选项——本技能的唯一后续动作是生成 OpenSpec 文档，
实施代码必须通过 `/opsx:apply` 单独触发。

**⛔ 检查点**：进入 Phase 1.5 之前，确认以下全部为真：
- [ ] 已使用 Skill 工具调用了 `superpowers:brainstorming` 技能
- [ ] 用户已对完整设计方案给出明确整体确认
- [ ] 本阶段未创建任何文件
- [ ] 未调用 writing-plans 或任何其他技能

## Phase 1.5：Worktree 环境检查

**Phase 1 完成后立即执行，不需要用户手动触发。**

**配置 `skip_worktree_check: true` 时**：跳过 worktree 检测，直接进入 Phase 2（在当前目录生成文档）。

运行以下命令检测当前环境：

```bash
git rev-parse --git-dir
```

**情况 A：输出包含 `.git/worktrees/`** → 当前已在 worktree 中，直接进入 Phase 2。

**情况 B：输出为 `.git`**（当前在主仓库）→ 输出以下选项提示，停止等待用户选择：

```
当前在主仓库目录，生成 OpenSpec 文档需要在功能分支的 worktree 中进行。

请选择操作：
1. 创建新 worktree（推荐）— 调用 superpowers:using-git-worktrees 技能创建功能分支，文档将生成在新 worktree 中
2. 在当前目录继续（不推荐）— 直接在主仓库生成文档，需自行管理分支
3. 取消操作
```

**情况 C：命令执行失败**（当前目录不是 Git 仓库）→ 输出以下提示后停止：
```
当前目录不是 Git 仓库。OpenSpec 工作流需要 Git 版本控制。
请在 Git 仓库中执行 /opsx:propose，或先运行 git init 初始化仓库。
```

| 用户选择 | 行为 |
|---------|------|
| `1` 或 `创建 worktree` | 调用 `superpowers:using-git-worktrees` 技能创建功能分支 worktree，worktree 就绪后进入 Phase 2 |
| `2` 或 `继续` | 在当前主仓库目录继续，进入 Phase 2（不推荐，用户自行负责分支管理） |
| `3` 或 `取消` | 终止流程，不生成任何文件 |

## Phase 2：生成 OpenSpec 文档

**必须且只能在 Phase 1.5 完成（已确认在 worktree 中或用户选择在主仓库继续）后执行此阶段。**

**推荐环境**：在 worktree 目录中生成文档，保持主分支干净。

### ⚠️ 强制前置步骤：重新加载模板

**在生成任何文件之前，必须执行以下步骤（防止长对话导致模板遗忘）：**

1. **重新读取模板文件**：使用 `read_file` 工具读取 `${SKILL_BASE}/templates/tasks-template.md`（`${SKILL_BASE}` 路径见 SKILL.md "技能基础路径解析"节），将模板完整加载到当前上下文
2. **自我确认**：在内部确认以下要素已就绪后才开始生成：
   - tasks.md 的每个 **TDD 顶层任务**必须有 N.M.1~N.M.5 五个子任务（写失败测试→验证失败→写最小实现→验证通过→重构）
   - tasks.md 的每个**非 TDD 顶层任务**必须有 N.M.1~N.M.3 三个子任务（执行变更→验证无回归→检查完整性）
   - 每个任务组必须以代码审查任务结尾（编号连续跟随该组最后一个实现任务，如 1.1、1.2 → 审查为 1.3）
   - 倒数第二组必须是 `PreCI 代码规范检查`
   - 最后一组必须是 `Documentation Sync (Required)`（5 条平铺检查项）
3. **禁止凭记忆生成 tasks.md**：即使认为自己"记得"格式，也必须执行步骤 1 重新加载

**如果跳过此步骤直接生成文件，视为违反 HARD STOPS 规则 P2.3。**

创建以下结构，路径相对于当前目录根目录：

```
openspec/changes/<kebab-case-feature-name>/
├── proposal.md
├── specs/
│   └── <feature>.md
├── design.md
└── tasks.md
```

### proposal.md format

```markdown
## Why
<!-- Problem being solved -->

## What Changes
<!-- New capabilities and modifications -->

## Impact
<!-- Affected code, APIs, dependencies -->
```

### specs/<feature>.md format

```markdown
## ADDED Requirements

### Requirement: <requirement-name>
<!-- requirement text -->

#### Scenario: <scenario-name>
- **WHEN** <condition>
- **THEN** <expected outcome>
```

### design.md format

```markdown
## Context
<!-- Background and current state -->

## Goals / Non-Goals
**Goals:**
<!-- What this design achieves -->

**Non-Goals:**
<!-- Explicitly out of scope -->

## Decisions
<!-- Key design decisions and rationale -->

## Risks / Trade-offs
<!-- Known risks -->
```

### tasks.md format — CRITICAL

**生成前必须重新读取模板文件**：`${SKILL_BASE}/templates/tasks-template.md`

完整的 tasks.md 模板、规则和 TDD 执行规范定义在 `${SKILL_BASE}/templates/tasks-template.md` 中。此处不再重复，
AI 必须通过 `read_file` 加载该文件获取完整模板。

Then announce:
"OpenSpec documents generated in branch feature/<branch-name> at <worktree-path>.
Please review the files under openspec/changes/<name>/, then run /opsx:apply
(legacy: /openspec:apply) to start implementation.
After implementation, merge the feature branch to master and run /opsx:archive."

Do NOT invoke writing-plans. Do NOT invoke any other skill.
