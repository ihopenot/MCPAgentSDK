# tasks.md 模板与规则（Phase 2 生成时必须重新读取本文件）

tasks.md 支持两类任务：**TDD 任务**（新功能、Bug 修复、复杂逻辑）使用 5 步子任务；**非 TDD 任务**（配置修改、重命名、文档更新、依赖升级、构建脚本等不需要先写失败测试的变更）使用 3 步子任务。

**代码审查任务（N.审查编号）编号连续跟随该组最后一个实现任务**（如实现任务为 1.1、1.2，审查任务为 1.3；实现任务为 2.1~2.4，审查任务为 2.5）。代码审查任务是任务组的必要组成部分，生成 TODO 列表时必须包含。

Each task group MUST end with a dedicated code review task. The LAST task group MUST be a Documentation Sync group:

```markdown
## 1. <任务组名称（包含 TDD 任务的示例）>

- [ ] 1.1 <新功能/Bug修复类任务描述>  <!-- TDD 任务：使用 5 步子任务 -->
  - [ ] 1.1.1 写失败测试：`<测试文件路径>`
  - [ ] 1.1.2 验证测试失败（运行：`<测试命令>`，确认失败原因是缺少功能）
  - [ ] 1.1.3 写最小实现：`<实现文件路径>`
  - [ ] 1.1.4 验证测试通过（运行：`<测试命令>`，确认所有测试通过，输出干净）
  - [ ] 1.1.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [ ] 1.2 <配置修改/重命名/文档类任务描述>  <!-- 非 TDD 任务：使用 3 步子任务 -->
  - [ ] 1.2.1 执行变更：`<变更文件路径>`
  - [ ] 1.2.2 验证无回归（运行：`<测试或构建命令>`，确认输出干净）
  - [ ] 1.2.3 检查：确认变更范围完整，无遗漏文件或引用

- [ ] 1.3 代码审查  <!-- 审查任务：编号连续，1.3 = 最后实现任务 1.2 的下一个序号 -->
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射（以 OpenSpec 路径为准）：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/<name>/specs/*.md` 和 `openspec/changes/<name>/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → 本任务组所有变更文件
    - `{BASE_SHA}` → 任务组开始前的 commit SHA（或分支基点）
    - `{HEAD_SHA}` → 当前 HEAD
  - 若存在 Critical/Important 问题：输出审查结果后追加选项提示（见 SKILL.md "代码审查用户指令"节），停止等待用户输入；用户选择"处理"类操作后，调用 superpowers:receiving-code-review 对每条审查意见做技术验证后再实施；按指令处理完成后继续下一任务组
  - 若仅有 Minor 或无问题：自动继续下一任务组，无需等待用户确认
  - subagent 模式下：本任务仍须执行（子代理内置审查为内部质量门控，不替代本任务的用户可见审查）

## 2. <任务组名称（全部为非 TDD 任务的示例）>

- [ ] 2.1 <依赖升级类任务>  <!-- 非 TDD 任务 -->
  - [ ] 2.1.1 执行变更：`<变更文件路径>`
  - [ ] 2.1.2 验证无回归（运行：`<测试或构建命令>`，确认输出干净）
  - [ ] 2.1.3 检查：确认变更范围完整，无遗漏文件或引用

- [ ] 2.2 代码审查  <!-- 编号连续，2.2 = 最后实现任务 2.1 的下一个序号 -->
  - （同 1.3 审查任务格式）

## N-1. PreCI 代码规范检查

- [ ] (N-1).1 检测 preci 安装状态
  - 按以下优先级检测：① `~/PreCI/preci`（优先）→ ② `command -v preci`（PATH）
  - 若均未找到：执行本技能 "PreCI 代码规范检查规范" 节中的安装命令，安装完成后继续
  - 若找到：记录可用路径，直接继续
- [ ] (N-1).2 检测项目是否已 preci 初始化
  - 检查 `.preci/`、`build.yml`、`.codecc/` 任一存在即为已初始化
  - 若未初始化：执行 `preci init`，等待完成后继续
- [ ] (N-1).3 检测 PreCI Server 状态
  - 执行 `<preci路径> server status` 检查服务是否启动
  - 若未启动：执行 `<preci路径> server start`，等待服务启动（最多 10 秒）
  - 若启动失败：输出警告但继续扫描流程
- [ ] (N-1).4 执行代码规范扫描
  - 依次执行两个扫描命令：
    1. `<preci路径> scan --diff`（扫描未暂存变更）
    2. `<preci路径> scan --pre-commit`（扫描已暂存变更）
  - 合并两次扫描结果，去重后统一处理
  - 仅扫描代码文件（跳过 .md/.yml/.json/.xml/.txt/.png/.jpg 等非代码文件）
- [ ] (N-1).5 处理扫描结果
  - 若无告警：输出 `✅ PreCI 检查通过`，继续 Documentation Sync
  - 若有告警：自动修正（最多重试次数由配置 `max_auto_fix_rounds` 决定，默认 3 次），修正后重新扫描验证
  - **若重试用尽后仍有无法自动修正的告警且 `skip_preci: false`**：暂停流程，输出剩余问题列表及以下选项，等待用户明确确认：
    ```
    ⚠️ PreCI 检查发现无法自动修正的告警，由于配置 skip_preci: false，必须处理后才能继续。
    
    请选择操作：
    a. 处理 <编号> — 手动修复指定条目后继续
    b. 全部处理 — 修复所有剩余告警后继续
    c. 跳过检查 — 不修改代码，直接继续 Documentation Sync
    d. 中止 — 停止当前任务执行
    ```
    **禁止在用户未明确选择的情况下自动继续执行**

## N. Documentation Sync (Required)

- [ ] N.1 sync design.md: record technical decisions, deviations, and implementation details after each code change
- [ ] N.2 sync tasks.md: 逐一检查所有顶层任务及其子任务，将已完成但仍为 `[ ]` 的条目标记为 `[x]`；每次更新只修改 `[ ]` → `[x]`，禁止修改任何任务描述文字
- [ ] N.3 sync proposal.md: update scope/impact if changed
- [ ] N.4 sync specs/*.md: update requirements if changed
- [ ] N.5 Final review: ensure all OpenSpec docs reflect actual implementation
```

## tasks.md 规则

- **任务类型判断**：新功能/Bug 修复/复杂逻辑 → TDD 任务（5 步）；配置修改/重命名/文档更新/依赖升级/构建脚本/无需先有失败测试的变更 → 非 TDD 任务（3 步）；若无法判断，默认按 TDD 任务处理
- **代码审查任务编号**：审查任务编号连续跟随该组最后一个实现任务（例：实现任务为 1.1、1.2 → 审查为 1.3；实现任务为 2.1~2.4 → 审查为 2.5）；禁止使用 `N.X` 占位符
- **TODO 列表必须包含所有任务**：Phase 3 开始执行前生成 TODO 列表时，必须包含 tasks.md 中的每一个顶层任务，含代码审查任务（如 1.3、2.5）、PreCI 检查组和 Documentation Sync；禁止遗漏任何任务
- TDD 子任务顺序固定：写失败测试 → 验证失败 → 写最小实现 → 验证通过 → 重构
- 非 TDD 子任务顺序固定：执行变更 → 验证无回归 → 检查完整性
- 禁止在未观察到测试失败的情况下编写 TDD 任务的实现代码（N.M.2 必须在 N.M.3 之前完成）
- 禁止跳过代码审查任务，Critical/Important 问题必须修复后才能继续下一任务组
- 禁止在子任务中添加 Commit 步骤，所有变更在开发完成后统一提交
- The Documentation Sync group is REQUIRED and must be the last group；其子任务为平铺检查项，无需嵌套子任务
- 文件路径必须精确（相对于项目根目录）
- 测试命令必须可直接运行
- 遵循 YAGNI 原则：只包含本次变更所需的实现任务，不做推测性规划
- PreCI 代码规范检查组（`N-1. PreCI 代码规范检查`）是 REQUIRED 的，必须位于所有实现任务组之后、Documentation Sync 之前；配置 `skip_preci: true` 或非内网环境无法安装 preci 时可选择跳过

## TDD 执行规范（apply 阶段强制遵守）

- **任务类型识别**：执行前先判断任务类型（TDD / 非 TDD），tasks.md 中标注了 `<!-- TDD 任务 -->` 或 `<!-- 非 TDD 任务 -->` 的注释；未标注时，新功能/Bug 修复/复杂逻辑默认为 TDD 任务，其余默认为非 TDD 任务
- **TDD 任务**：N.M.2（验证失败）或 N.M.4（验证通过）出现意外结果时，必须停止并调用 superpowers:systematic-debugging 进行根因分析，禁止跳过或直接猜测修复（agent 模式由主代理执行；subagent 模式由子代理在内部执行）
- **非 TDD 任务**：N.M.2（验证无回归）出现问题时，同样必须停止并调用 superpowers:systematic-debugging，禁止猜测修复
- N.审查编号 代码审查执行前，必须先调用 superpowers:verification-before-completion 运行全量测试，确认所有测试通过且输出干净，再调用 superpowers:requesting-code-review
- 用户选择处理审查意见（选项 a 或 b）后，必须调用 superpowers:receiving-code-review 对每条待处理意见做技术验证，确认技术上正确后再实施，禁止盲目执行
- 所有顶层任务完成（所有 checkbox 为 [x]）后，必须调用 superpowers:finishing-a-development-branch，引导分支合并/PR/清理决策，禁止直接提示"请手动 merge"
