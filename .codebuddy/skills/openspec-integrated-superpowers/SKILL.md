---
name: openspec-integrated-superpowers
description: 当用户执行 /opsx:propose、/openspec:proposal、/opsx:apply 或 /openspec:apply，或希望在使用 OpenSpec 的项目中提案新功能、变更或 Bug 修复，或开始实施已确认的 OpenSpec 变更时触发。将独立的 brainstorming→writing-plans 流程替换为 OpenSpec 原生工作流。
---

# OpenSpec 集成提案技能

## 概述

本技能将 Superpowers brainstorming 集成到 OpenSpec `/opsx:propose`（旧版：`/openspec:proposal`）工作流中。不再走 brainstorming → writing-plans → docs/plans/ 的独立流程，而是：
brainstorming → 设计确认 → 环境检查 → 在 worktree 中生成 OpenSpec 文档。

**HARD RULE: Do NOT invoke writing-plans. Do NOT create docs/plans/. The terminal
state of this skill is writing tasks.md with TDD subtasks under openspec/changes/
inside the feature branch worktree.**

## 技能基础路径解析

本技能的文件引用均使用相对路径。AI 执行时必须先确定技能的实际安装路径（`SKILL_BASE`）：

**路径发现顺序**（按优先级）：
1. 当前已加载的 SKILL.md 所在目录（首选，直接可用）
2. `~/.codebuddy/skills/openspec-integrated-superpowers/`
3. `~/.claude-internal/skills/openspec-integrated-superpowers/`
4. 兜底搜索：`find ~ -path "*/openspec-integrated-superpowers/SKILL.md" -type f 2>/dev/null | head -1`

确定 `SKILL_BASE` 后，所有 `read_file` 调用使用 `${SKILL_BASE}/<相对路径>` 格式。

## 入口判断与路由

技能启动时，根据触发命令决定执行路径：

### propose 路径（Phase 1 + 1.5 + 2）

触发条件：收到 `/opsx:propose` 或 `/openspec:proposal`

**【必须】先执行 `read_file` 读取 `${SKILL_BASE}/phases/phase1-propose.md`，将完整内容加载到当前上下文后，严格按该文件指引执行 Phase 1 → Phase 1.5 → Phase 2。未读取前禁止执行任何后续步骤。**

### apply 路径（Phase 3）

触发条件：收到 `/opsx:apply` 或 `/openspec:apply`

**【必须】先执行 `read_file` 读取 `${SKILL_BASE}/phases/phase3-execution.md`，将完整内容加载到当前上下文后，严格按本文件的"Phase 3：实施（apply）"节和该文件的详细规范执行。未读取前禁止执行任何后续步骤。**

### rollback 路径

触发条件：收到 `/opsx:rollback` 或 "回滚"

**【必须】先执行 `read_file` 读取 `${SKILL_BASE}/phases/phase3-execution.md`，定位"紧急回滚"节执行。**

### 无法判断时

询问用户："请问您是要进行提案设计（propose）还是开始实施（apply）？"

## HARD STOPS — 违反以下任何规则必须立即停止并向用户报错

| ID | Phase | 规则 | 违规后果 |
|----|-------|------|---------|
| P1.1 | 1 | 禁止创建任何文件或目录（包括 openspec 文档） | 立即停止 |
| P1.2 | 1 | 禁止跳过 `superpowers:brainstorming` 技能调用，必须先调用再开始设计讨论 | 立即停止 |
| P1.3 | 1 | 禁止在用户明确确认完整设计之前进入 Phase 1.5（需"确认"/"ok"/"yes"等明确同意） | 停止并追问 |
| P1.4 | 1 | 禁止在确认询问中提议直接实施代码，只能问"是否开始生成文档" | 重新询问 |
| P1.5.1 | 1.5 | 禁止跳过 Phase 1.5 环境检查，不在 worktree 中必须输出选项并停止 | 立即停止 |
| P1.5.2 | 1.5 | 禁止在 Phase 2 之前跳过 worktree 环境检查 | 立即停止 |
| P1.5.3 | 1.5 | 禁止跳过阶段顺序：必须严格按 Phase 1 → 1.5 → 2 执行 | 立即停止 |
| P2.1 | 2 | 禁止调用 writing-plans 技能 | 立即停止 |
| P2.2 | 2 | 禁止在 docs/plans/ 下创建任何文件 | 立即停止 |
| P2.3 | 2 | 禁止凭记忆生成 tasks.md：必须先重新读取模板文件再生成 | 立即停止 |
| P2.4 | 2 | 禁止在 `docs/` 根目录下直接创建文件，必须在 `docs/<change-name>/` 子目录下 | 立即停止 |
| P3.1 | 3 | 禁止跳过 execution_mode 询问：前置检查通过后必须停等用户选择 | 立即停止 |
| P3.2 | 3 | 禁止跳过任务执行步骤（TDD: N.M.1→N.M.5；非 TDD: N.M.1→N.M.3） | 立即停止 |
| P3.3 | 3 | 禁止跳过代码审查：每个任务组的审查不可省略，审查前必须先调用 verification-before-completion | 立即停止 |
| P3.4 | 3 | 禁止在代码审查中跳过 `superpowers:receiving-code-review`：用户选择处理后必须先技术验证 | 立即停止 |
| P3.5 | 3 | 禁止在 N.M.2/N.M.4 出现意外结果时跳过 `superpowers:systematic-debugging` | 立即停止 |
| P3.6 | 3 | 禁止在完成前跳过 `superpowers:finishing-a-development-branch` | 立即停止 |
| P3.7 | 3 | 禁止跳过前置 tasks.md 分析：必须读取 tasks.md 并生成完整 TODO 列表随推荐一并展示 | 立即停止 |

**自检提示**（AI 即将违规时必须输出对应消息后停止）：

- 即将在 Phase 1 创建文件 → "我正在执行 Phase 1（设计讨论），此阶段不能创建任何文件。请先完成设计确认。"
- 即将跳过 brainstorming → "Phase 1 必须先调用 superpowers:brainstorming 技能，禁止跳过直接输出设计方案。"
- 即将跳过 Phase 1.5 → "Phase 1 完成后必须执行 Phase 1.5 环境检查，禁止直接进入 Phase 2。"
- 即将在 Phase 3 跳步 → "Phase 3 要求严格按任务执行流程执行（TDD: N.M.1→N.M.5，非 TDD: N.M.1→N.M.3），禁止跳过任何步骤。"

## 阶段状态追踪

每次阶段转换时，AI 必须在内部维护当前状态并输出简要状态确认：

**状态格式**：
- Phase: {1 | 1.5 | 2 | 3}
- 当前任务组: {N}（仅 Phase 3）
- 当前子任务: {N.M.X}（仅 Phase 3）
- 已完成任务组: [列表]（仅 Phase 3）
- 待执行任务组: [列表]（仅 Phase 3）

**阶段转换时输出**（内嵌在回复中）：
- "[状态] 进入 Phase 1 — 设计讨论"
- "[状态] 进入 Phase 1.5 — 环境检查"
- "[状态] 进入 Phase 2 — 文档生成"
- "[状态] Phase 3 / 任务组 1 / 子步骤 1.1.3（写最小实现）"

状态标记与 `todo_write` 工具的 TODO 列表关联，确保任务状态在工具和文本输出中一致。

## 上下文刷新检查点

长对话中 AI 可能遗忘早期指令。以下检查点处，AI 必须重新读取对应引用文件的指定节：

| 检查点 | 重新加载内容 |
|--------|------------|
| 每 5 个顶层任务完成后 | 本文件 "HARD STOPS" 表格（Phase 3 相关行） |
| 每次代码审查前 | `${SKILL_BASE}/phases/phase3-execution.md` 的 "代码审查用户指令" 节 |
| 每次派发子代理前（subagent 模式） | `${SKILL_BASE}/phases/phase3-execution.md` 的 "subagent prompt 标准模板" 节 |
| PreCI 检查前 | `${SKILL_BASE}/phases/phase3-execution.md` 的 "PreCI 代码规范检查规范" 节 |
| Documentation Sync 前 | `${SKILL_BASE}/phases/phase3-execution.md` 的 "Phase 3 禁止行为" 节 |

## Phase 间数据契约

| 数据 | 产生阶段 | 消费阶段 | 传递方式 |
|------|---------|---------|---------|
| 设计方案摘要 | Phase 1 | Phase 2 | 写入 `design.md` 的 Context 和 Decisions 节 |
| worktree 路径 | Phase 1.5 | Phase 2, 3 | 通过 `pwd` 命令动态获取 |
| change name（kebab-case） | Phase 2 | Phase 3 | 通过扫描 `openspec/changes/` 目录获取 |
| 配置值 | 规则文件 | Phase 3 | 通过读取规则文件或会话上下文获取 |
| tasks.md 内容 | Phase 2 | Phase 3 | 通过 `read_file` 读取 |

**跨会话恢复协议**（Phase 3 通过 `/opsx:apply` 独立触发时）：
Phase 3 前置检查已覆盖必要的恢复步骤（读取 tasks.md、检查分支、检查 worktree）。
AI 不应假设任何 Phase 1/2 的上下文仍在内存中。

## 前置要求

**环境检查时机**：技能启动后，Phase 1 完成时（不是启动时）检查 worktree 环境。

**Phase 1 可在任意目录执行**：设计讨论阶段只需要读取代码和与用户交互，无需 worktree 环境。

**检查逻辑**：见 `${SKILL_BASE}/phases/phase1-propose.md` 的 Phase 1.5 部分。

## 配置默认值

```
execution_mode: agent     # agent：主代理直接执行 / subagent：每任务派独立子代理
review_mode: per_task     # per_task：每个顶层任务完成后审查 / final：全部完成后统一审查
review_action: confirm    # confirm：输出审查结果后等待用户指令 / auto：自动修复 Critical 问题
skip_preci: false         # true 时跳过 PreCI 检查
skip_worktree_check: false # true 时跳过 worktree 检查
max_auto_fix_rounds: 3    # PreCI 自动修正最大重试次数
tdd_strict: true          # false 时允许非 TDD 任务跳过验证
```

项目可通过集成规则文件声明这些配置值来覆盖以上默认值。
执行 Phase 3 时，若当前会话上下文中已存在这些配置声明，以上下文中的值为准；否则使用以上默认值。

## Phase 3：实施（apply）

**本阶段在用户执行 `/opsx:apply` 或 `/openspec:apply` 时触发。**

**【必须】执行本阶段前，先通过 `read_file` 读取 `${SKILL_BASE}/phases/phase3-execution.md` 获取完整执行规范。未读取前禁止执行任何任务。**

### 前置检查（必须全部通过才能开始执行）

1. 运行 `git branch --show-current`，确认当前分支为 `feature/<name>`（非 master/main）；配置 `skip_worktree_check: true` 时跳过此检查
2. 运行 `git worktree list`，确认当前路径是 worktree 路径（非主仓库路径）；配置 `skip_worktree_check: true` 时跳过此检查
3. 确认 `openspec/changes/<name>/tasks.md` 文件存在
4. 读取配置：若当前会话上下文中已存在配置声明，以上下文值为准；否则使用本技能"配置默认值"节中的默认值
4.1. **校验配置值**：
   - `execution_mode` 不在 `[agent, subagent]` 中 → 输出警告，回退到默认值 `agent`
   - `review_mode` 不在 `[per_task, final]` 中 → 输出警告，回退到默认值 `per_task`
   - `review_action` 不在 `[confirm, auto]` 中 → 输出警告，回退到默认值 `confirm`
   - `skip_preci` 不在 `[true, false]` 中 → 回退到 `false`
   - `skip_worktree_check` 不在 `[true, false]` 中 → 回退到 `false`
   - `max_auto_fix_rounds` 不在 `1-10` 范围 → 回退到 `3`
   - `tdd_strict` 不在 `[true, false]` 中 → 回退到 `true`
   - 输出："⚠️ 配置值 {key} = '{value}' 无效，已回退到默认值 '{default}'。"
5. **读取 tasks.md，生成完整 TODO 列表**：逐行分析所有顶层任务，识别每个任务的类型（TDD / 非 TDD）、判断代码审查任务编号，生成包含所有顶层任务的 TODO 列表（含代码审查任务、PreCI 检查组 `N-1`、Documentation Sync `N`），将在 execution_mode 推荐中随推荐格式一并展示供用户确认
6. **中断恢复检测**：读取 tasks.md 后，检查是否有已标记 `[x]` 的任务
   - 若有 → 输出恢复提示："检测到以下任务已完成，将从第一个未完成任务继续：\n[已完成列表]\n[待执行列表]\n是否确认继续？"
   - 若 tasks.md 中有 `[x]` 但对应代码文件不存在 → 警告："任务 X.Y 标记为已完成但实现文件缺失，建议重置为未完成"

如果任何一项检查未通过，立即停止并向用户说明原因，等待用户修正后再继续。

### execution_mode 智能推荐

前置检查通过后，读取 tasks.md，统计顶层实现任务数量，给出推荐并让用户选择执行模式：

**推荐判断标准：**
- 顶层实现任务 **≤ 5 个**，且各任务逻辑连续 → 推荐 **agent**
- 顶层实现任务 **> 5 个**，或涉及多个独立模块/服务 → 推荐 **subagent**

**必须按以下格式输出推荐，然后停止等待用户选择：**

```
根据本次任务规模（共 X 个顶层任务，[逻辑连续/涉及多个独立模块]），推荐执行模式：

1. agent（推荐）— 主代理直接执行，上下文连续，适合当前任务规模
2. subagent — 每任务派独立子代理+两阶段内部审查，适合任务多或模块独立的场景
   ⚠️ 注意：subagent 模式每个任务会启动独立子代理，整体执行时间较长（视任务数量可能需要数分钟到十余分钟）

本次将执行以下任务（TODO 列表，完整来自 tasks.md）：
- [ ] 1.1 <任务描述>（TDD）
- [ ] 1.2 <任务描述>（非 TDD）
- [ ] 1.3 代码审查
- [ ] 2.1 <任务描述>（TDD）
- [ ] 2.2 代码审查
- [ ] N-1. PreCI 代码规范检查
- [ ] N. Documentation Sync

请选择执行模式（输入 1 或 2）：
（如需稍后执行，可以直接重新输入 /opsx:apply 重新开始）
```

（若推荐 subagent，则第 2 项标注"推荐"，第 1 项不标注）

**停等实现**：输出推荐格式后，优先使用 `ask_followup_question` 工具（如可用）强制等待用户输入，
确保物理性暂停执行；若工具不可用，则输出推荐后以明确的问句结尾并停止，
禁止在同一轮次中继续执行任何任务。

**用户输入处理：**
- 输入 `1` 或 `agent` → 本次 apply 使用 agent 模式执行
- 输入 `2` 或 `subagent` → 本次 apply 使用 subagent 模式执行
- 用户选择覆盖会话上下文中的 `execution_mode` 配置值，仅对本次 apply 生效

### Phase 3 详细执行规范

**任务执行、代码审查、subagent 模式、PreCI 检查、文档同步、禁止行为、回滚等详细规范**，
请读取 `${SKILL_BASE}/phases/phase3-execution.md` 文件。

AI 在 Phase 3 执行期间必须按需读取该文件的对应节（参见上方"上下文刷新检查点"表格）。

# 重要
**与用户沟通时一律使用中文**