# Phase 3 详细执行规范（SKILL.md 引用文件）

## 每个顶层任务执行步骤（agent 模式）

1. **判断任务类型**：读取 tasks.md 中的任务注释（`<!-- TDD 任务 -->` / `<!-- 非 TDD 任务 -->`），未标注时按默认规则判断
2. **执行**：
   - TDD 任务：严格按 N.M.1→N.M.5 子任务顺序执行，禁止在测试失败前写实现代码
   - 非 TDD 任务：按 N.M.1→N.M.3（执行变更 → 验证无回归 → 检查完整性）执行
3. **调试规范**：N.M.2（TDD 验证失败/非 TDD 验证无回归）或 N.M.4（TDD 验证通过）出现意外结果时，必须立即调用 superpowers:systematic-debugging 进行根因分析，禁止跳过或直接猜测修复
4. **更新 tasks.md**：子任务完成即标记 `[x]`，顶层任务全部子任务完成后也标记 `[x]`
5. **文档同步**：代码变更后立即同步以下 OpenSpec 文档（无需用户提醒）：

   | 文档 | 更新时机 |
   |------|----------|
   | `tasks.md` | 任务完成时标记 `[x]`，发现新任务时追加；禁止写入审查结果或审查备注 |
   | `design.md` | 每次代码变更后记录技术决策和实现细节；代码审查产生的修复（无论是 Critical/Important 修复还是跳过的备注原因）必须在此记录，写入 `## Decisions` 节 |
   | `proposal.md` | 变更范围或影响发生变化时更新 |
   | `specs/*.md` | 需求发生变化时更新 |

   **只更新当前变更**（`openspec/changes/<change-id>/`），不更新 `archive/` 下的已归档文档。

6. **代码审查**：按 review_mode 配置执行：
   - 先调用 superpowers:verification-before-completion 运行全量测试，确认所有测试通过且输出干净
   - 再调用 superpowers:requesting-code-review 执行审查，按以下逻辑处理结果：
     - 若存在 Critical 或 Important 问题：输出审查结果后立即停止，追加"代码审查用户指令"节中的选项提示，等待用户指令（review_action: confirm）或自动修复后继续（review_action: auto）
     - 若仅有 Minor 或无问题：**无需等待用户确认，自动继续下一任务**

## review_mode 执行差异

| 配置值 | 任务组代码审查行为 | PreCI 检查时机 |
|--------|------------------|---------------|
| `per_task` | 每个任务组结尾执行代码审查（默认行为） | 所有任务组完成后 |
| `final` | 任务组结尾的代码审查任务标记为 [DEFERRED]，所有实现任务完成后统一执行一次代码审查（scope 为全部变更） | 统一审查通过后 |

**final 模式注意**：
- TODO 列表中仍展示每个任务组的审查任务，但标注"[延迟至最终统一审查]"
- 统一审查的 `{BASE_SHA}` 为第一个任务组开始前的 SHA
- 统一审查的 `{WHAT_WAS_IMPLEMENTED}` 为所有任务组的变更文件合集

## 与其他 alwaysApply 规则的交互

- `java-api-version-snapshot` 规则可能在修改 API 模块代码时自动升级版本号，这是期望行为。
  如果 pom.xml 被修改，将其纳入当前任务组的变更文件列表，无需单独处理。

## subagent 模式补充

主代理在派发子代理时，prompt 中必须注入：任务完整文本、specs/ 需求内容、design.md 架构决策、Worktree 路径、TDD 调试规范要求（N.M.2/N.M.4 出现意外结果时，子代理内部调用 superpowers:systematic-debugging 进行根因分析，禁止跳过或猜测修复）。

**subagent prompt 标准模板**（派发子代理时使用）：

```
任务：{任务完整文本，来自 tasks.md}
任务类型：{TDD / 非 TDD}
需求规格：{读取 openspec/changes/<name>/specs/*.md 的相关内容}
架构决策：{读取 openspec/changes/<name>/design.md 的 Decisions 节}
工作目录：{worktree 绝对路径}

执行规范：
- TDD 任务严格按 N.M.1→N.M.5 顺序执行
- 非 TDD 任务按 N.M.1→N.M.3 顺序执行
- N.M.2/N.M.4 出现意外结果时，调用 superpowers:systematic-debugging 进行根因分析
- 禁止跳过任何子任务步骤
- 完成后输出：变更文件列表、测试执行结果、是否有意外偏差
```

**子代理内置审查与 tasks.md 代码审查任务的关系：**
- 子代理内部执行两阶段审查（spec 合规 → 代码质量），这是子代理的内部质量门控，结果不输出给用户
- tasks.md 中的代码审查任务（N.审查编号）是面向用户的可见审查，由主代理调用 superpowers:requesting-code-review 执行并输出给用户确认
- **两者不重复**：子代理内置审查处理 spec 合规问题（自动修复后子代理任务完成），主代理用户可见审查关注代码质量和整体一致性
- subagent 模式下，主代理**仍须**执行 tasks.md 中的代码审查任务（不可跳过）

**subagent 错误恢复**：

| 子代理状态 | 恢复策略 |
|-----------|---------|
| 执行超时（无响应） | 主代理重新派发该任务，prompt 中追加"上次执行超时，请优先检查工作目录状态" |
| 返回执行失败（测试不过） | 主代理检查子代理输出，判断：① 可继续 → 重新派发并附加上次错误信息 ② 需架构调整 → 停等用户 |
| 返回部分完成 | 主代理读取 tasks.md 当前状态，识别已完成和未完成子任务，重新派发仅含未完成部分的任务 |
| 子代理修改了不应修改的文件 | 主代理用 `git diff` 检查变更范围，回滚超出范围的修改 |

## tasks.md checkbox 更新策略

**单个更新**（常规子任务完成时）：
- `old_str` 选取任务编号行的完整文本（编号保证唯一性）

**批量更新**（Documentation Sync N.2 执行时）：
- 先 `read_file` 获取完整 tasks.md
- 构建需要更新的行列表（所有已完成但仍为 `[ ]` 的条目）
- 按从后向前的顺序逐一 `replace_in_file`（避免行号偏移）
- 或使用单次 `replace_in_file` 更新一个包含多行的连续区块
- 每次更新后验证：`search_content` 检查是否还有应标记未标记的条目

## 代码审查用户指令

存在 Critical/Important 问题时，输出审查结果后必须追加以下选项提示，然后停止等待用户输入：

```
请选择操作：
a. 处理指定条目 — 输入 `处理 1,2` 或 `fix 1,2` 修复指定编号后继续
b. 全部处理 — 修复所有 Critical 和 Important 后继续
c. 跳过 — 不修改代码，直接继续下一任务
d. 跳过并备注 — 输入 `跳过，备注：<原因>` 跳过并记录原因（禁止写入任何 OpenSpec 文档）
```

**用户输入匹配规则（按优先级）**：

| 用户输入 | 匹配规则 | 行为 |
|----------|---------|------|
| `处理 X,Y` 或 `fix X,Y` | 包含"处理"/"fix" + 数字 | 调用 superpowers:receiving-code-review 对指定条目逐一验证技术正确性后实施 |
| `全部处理` 或 `all` 或 `b` | 完全匹配 | 调用 superpowers:receiving-code-review 对所有 Critical 和 Important 条目逐一验证后实施 |
| `跳过` 或 `skip` 或 `c` 或 `继续` | 完全匹配 | 不修改代码，直接继续下一任务 |
| `跳过，备注：...` 或 `d` | 包含"备注"/"跳过" | 不修改代码，直接继续（备注仅供 AI 内部记录，禁止写入任何 OpenSpec 文档） |
| `a` | 完全匹配 | 追问："请输入要处理的条目编号，如 `处理 1,2`" |
| 纯数字（如 `1`） | 仅数字 | 追问："请明确操作：输入 `处理 1` 修复第 1 条，或输入 `全部处理` 修复所有。" |

## Phase 3 禁止行为

- TDD 任务中，无失败测试时禁止写实现代码
- review_action: confirm 时，未收到用户指令禁止修改代码或继续下一任务
- 禁止修改 tasks.md 已确认的任务结构（仅可更新 checkbox 状态，禁止追加审查结果、审查备注或任何审查相关内容）
- 禁止将代码审查结果、审查意见、跳过备注写入 tasks.md 或任何 OpenSpec 文档
- 禁止生成 `docs/plans/` 或调用 writing-plans 技能
- **禁止在 `docs/` 目录下直接创建任何文件**：若确有必要在 `docs/` 下生成报告等文件，必须在 `docs/<change-name>/` 子目录下创建（`<change-name>` 为当前 openspec/changes/ 下的提案目录名）；直接写入 `docs/` 根目录视为违规
- 更新 tasks.md checkbox 时（**包括 Documentation Sync 的 N.2 子任务执行期间**），`old_str` 必须选取目标任务行的完整文本（利用任务编号保证唯一性），`new_str` 仅将 `[ ]` 替换为 `[x]`，禁止修改任务描述文字、追加执行结果或任何其他文本变更
- **Documentation Sync N.2 必须全量标记**：执行 N.2 时，必须逐一扫描 tasks.md 的所有顶层任务及其子任务，将每一个已实际完成但仍为 `[ ]` 的条目标记为 `[x]`；禁止只标记部分任务（如仅标记代码审查或文档同步任务），遗漏其他已完成任务视为违规

## PreCI 代码规范检查规范

所有实现任务组完成后（包含所有代码审查任务），在 Documentation Sync 之前执行此检查。

**配置 `skip_preci: true` 时**：跳过整个 PreCI 检查组，直接进入 Documentation Sync。

**配置 `skip_preci: false` 时（默认）**：PreCI 检查为强制流程，任何失败情况（服务未启动/扫描失败/告警无法修正）都必须暂停并等待用户明确确认后才能继续，**禁止自动跳过**。

**preci 命令路径检测优先级：**
1. 默认安装路径（优先）：`~/PreCI/preci`，若存在则直接使用
2. 系统 PATH：`command -v preci`，作为备选

**PreCI Server 状态检测**：
1. 执行 `<preci路径> server status` 检查服务状态
2. 若服务未启动，执行 `<preci路径> server start` 启动服务
3. 等待服务启动完成（最多等待 10 秒），若启动失败则输出警告继续

**扫描命令**（按顺序执行）：
1. `<preci路径> scan --diff`：扫描已修改但未 git add 的文件（未暂存变更）
2. `<preci路径> scan --pre-commit`：扫描已 git add 的文件（已暂存变更）

两次扫描结果合并处理，去重后统一进入自动修正流程。

**若 preci 未安装，执行安装脚本：**

安装脚本位于本技能目录下 `scripts/preci_install.sh`。执行时需使用 SKILL.md 中定义的 `${SKILL_BASE}` 路径：

```bash
bash ${SKILL_BASE}/scripts/preci_install.sh "$HOME"
```

**`${SKILL_BASE}` 路径发现**（按优先级）：
1. 当前已加载的 SKILL.md 所在目录（首选）
2. `~/.codebuddy/skills/openspec-integrated-superpowers/`
3. `~/.claude-internal/skills/openspec-integrated-superpowers/`
4. 兜底搜索：`find ~ -path "*/openspec-integrated-superpowers/scripts/preci_install.sh" -type f 2>/dev/null | head -1`

安装完成后重新检测 preci 路径，若仍未找到则根据配置处理：

**若 `skip_preci: false`（默认）**：输出错误信息并暂停流程：
```
❌ PreCI 安装失败（可能原因：非腾讯内网环境或网络问题）。
由于配置 skip_preci: false，PreCI 检查为强制流程。

请选择操作：
a. 重试安装 — 尝试重新安装 PreCI
b. 手动安装 — 手动安装后输入 'continue' 继续
c. 跳过检查 — 跳过 PreCI 检查并继续后续流程
d. 中止 — 停止当前任务执行
```
只有用户明确选择后才继续执行，**禁止自动跳过**。

**若 `skip_preci: true`**：输出警告信息后自动跳过，直接进入 Documentation Sync。

**告警自动修正规则：**

| 告警类型 | 自动修正策略 |
|---------|------------|
| `inner_ip_leak` | 添加 `// NOCC:inner_ip_leak(该IP已脱敏)` 注释 |
| `sensitive_info` | 脱敏处理或添加忽略注释 |
| `code_style` | 修正缩进、空格、换行 |
| `naming_convention` | 修正命名（谨慎处理，可能影响其他引用） |

**忽略注释格式**：`// NOCC:CheckerName(填写忽略原因)`

## 实施完成条件

所有 checkbox 为 `[x]` 且最后一次审查经用户回复后，必须调用 superpowers:finishing-a-development-branch 技能，引导用户做出分支决策（合并、创建 PR、保留或丢弃），不得直接提示"请手动 merge"。

## 紧急回滚

用户输入 `/opsx:rollback` 或 "回滚" 时：
1. 执行 `git diff --stat` 显示所有未提交变更
2. 询问用户确认回滚范围
3. 执行 `git checkout -- .` 回滚所有未暂存变更
4. 重新读取 tasks.md，将已完成但代码已回滚的任务重置为 `[ ]`
