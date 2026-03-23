# MCP Agent SDK 实施任务

## 1. 核心类型与项目基础设施

- [x] 1.1 创建包结构和类型定义  <!-- 非 TDD 任务 -->
  - [x] 1.1.1 执行变更：`mcp_agent_sdk/__init__.py`、`mcp_agent_sdk/types.py`、`pyproject.toml`
  - [x] 1.1.2 验证无回归（运行：`python -c "from mcp_agent_sdk import MCPAgentSDK, AgentRunConfig, Message, AgentResult"`，确认导入成功）
  - [x] 1.1.3 检查：确认所有数据类型（AgentRunConfig, AgentResult, Message, RunContext）定义完整，字段与设计文档一致

- [x] 1.2 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/mcp-agent-sdk/specs/*.md` 和 `openspec/changes/mcp-agent-sdk/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → 本任务组所有变更文件
    - `{BASE_SHA}` → 任务组开始前的 commit SHA
    - `{HEAD_SHA}` → 当前 HEAD

## 2. Streamable HTTP MCP Server

- [x] 2.1 实现 MCP Server 核心（JSON-RPC 2.0 处理、initialize、tools/list）  <!-- TDD 任务 -->
  - [x] 2.1.1 写失败测试：`tests/test_mcp_server.py`
  - [x] 2.1.2 验证测试失败（运行：`python -m pytest tests/test_mcp_server.py -v`，确认失败原因是缺少功能）
  - [x] 2.1.3 写最小实现：`mcp_agent_sdk/mcp_server.py`
  - [x] 2.1.4 验证测试通过（运行：`python -m pytest tests/test_mcp_server.py -v`，确认所有测试通过，输出干净）
  - [x] 2.1.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 2.2 实现 tools/call 处理（Complete 和 Block 工具调用路由、registry 查找、validate_fn 执行）  <!-- TDD 任务 -->
  - [x] 2.2.1 写失败测试：`tests/test_mcp_server.py`（追加 tools/call 相关测试）
  - [x] 2.2.2 验证测试失败（运行：`python -m pytest tests/test_mcp_server.py -v`，确认失败原因是缺少功能）
  - [x] 2.2.3 写最小实现：`mcp_agent_sdk/mcp_server.py`（追加 tools/call handler）
  - [x] 2.2.4 验证测试通过（运行：`python -m pytest tests/test_mcp_server.py -v`，确认所有测试通过，输出干净）
  - [x] 2.2.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 2.3 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/mcp-agent-sdk/specs/*.md` 和 `openspec/changes/mcp-agent-sdk/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → 本任务组所有变更文件
    - `{BASE_SHA}` → 任务组开始前的 commit SHA
    - `{HEAD_SHA}` → 当前 HEAD

## 3. 消息解析与子进程管理

- [x] 3.1 实现 stdout JSON 流消息解析器  <!-- TDD 任务 -->
  - [x] 3.1.1 写失败测试：`tests/test_message_parser.py`
  - [x] 3.1.2 验证测试失败（运行：`python -m pytest tests/test_message_parser.py -v`，确认失败原因是缺少功能）
  - [x] 3.1.3 写最小实现：`mcp_agent_sdk/message_parser.py`
  - [x] 3.1.4 验证测试通过（运行：`python -m pytest tests/test_message_parser.py -v`，确认所有测试通过，输出干净）
  - [x] 3.1.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 3.2 实现子进程启动与参数构造（codebuddy CLI 调用、mcp-config JSON 注入）  <!-- TDD 任务 -->
  - [x] 3.2.1 写失败测试：`tests/test_process.py`
  - [x] 3.2.2 验证测试失败（运行：`python -m pytest tests/test_process.py -v`，确认失败原因是缺少功能）
  - [x] 3.2.3 写最小实现：`mcp_agent_sdk/process.py`
  - [x] 3.2.4 验证测试通过（运行：`python -m pytest tests/test_process.py -v`，确认所有测试通过，输出干净）
  - [x] 3.2.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 3.3 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/mcp-agent-sdk/specs/*.md` 和 `openspec/changes/mcp-agent-sdk/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → 本任务组所有变更文件
    - `{BASE_SHA}` → 任务组开始前的 commit SHA
    - `{HEAD_SHA}` → 当前 HEAD

## 4. System Prompt 模板与 SDK 主类

- [x] 4.1 实现 system prompt 模板（agent_run_id 注入、Complete/Block 使用指引）  <!-- 非 TDD 任务 -->
  - [x] 4.1.1 执行变更：`mcp_agent_sdk/prompt_template.py`
  - [x] 4.1.2 验证无回归（运行：`python -m pytest tests/ -v`，确认输出干净）
  - [x] 4.1.3 检查：确认模板包含 agent_run_id 占位、Complete/Block 工具说明、使用规则

- [x] 4.2 实现 MCPAgentSDK 主类（init、run_agent、shutdown、registry 管理、状态检测终止）  <!-- TDD 任务 -->
  - [x] 4.2.1 写失败测试：`tests/test_sdk.py`
  - [x] 4.2.2 验证测试失败（运行：`python -m pytest tests/test_sdk.py -v`，确认失败原因是缺少功能）
  - [x] 4.2.3 写最小实现：`mcp_agent_sdk/sdk.py`
  - [x] 4.2.4 验证测试通过（运行：`python -m pytest tests/test_sdk.py -v`，确认所有测试通过，输出干净）
  - [x] 4.2.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 4.3 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/mcp-agent-sdk/specs/*.md` 和 `openspec/changes/mcp-agent-sdk/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → 本任务组所有变更文件
    - `{BASE_SHA}` → 任务组开始前的 commit SHA
    - `{HEAD_SHA}` → 当前 HEAD

## 5. PreCI 代码规范检查

- [x] 5.1 检测 preci 安装状态
  - 按以下优先级检测：① `~/PreCI/preci`（优先）→ ② `command -v preci`（PATH）
  - 若均未找到：执行本技能 "PreCI 代码规范检查规范" 节中的安装命令，安装完成后继续
  - 若找到：记录可用路径，直接继续
- [x] 5.2 检测项目是否已 preci 初始化  <!-- 用户选择跳过 -->
  - 检查 `.preci/`、`build.yml`、`.codecc/` 任一存在即为已初始化
  - 若未初始化：执行 `preci init`，等待完成后继续
- [x] 5.3 检测 PreCI Server 状态  <!-- 用户选择跳过 -->
  - 执行 `<preci路径> server status` 检查服务是否启动
  - 若未启动：执行 `<preci路径> server start`，等待服务启动（最多 10 秒）
  - 若启动失败：输出警告但继续扫描流程
- [x] 5.4 执行代码规范扫描  <!-- 用户选择跳过 -->
  - 依次执行两个扫描命令：
    1. `<preci路径> scan --diff`（扫描未暂存变更）
    2. `<preci路径> scan --pre-commit`（扫描已暂存变更）
  - 合并两次扫描结果，去重后统一处理
  - 仅扫描代码文件（跳过 .md/.yml/.json/.xml/.txt/.png/.jpg 等非代码文件）
- [x] 5.5 处理扫描结果  <!-- 用户选择跳过 -->
  - 若无告警：输出 `PreCI 检查通过`，继续 Documentation Sync
  - 若有告警：自动修正（最多 3 次），修正后重新扫描验证
  - 若重试用尽后仍有无法自动修正的告警：暂停流程，输出剩余问题列表及选项，等待用户确认

## 6. Documentation Sync (Required)

- [x] 6.1 sync design.md: record technical decisions, deviations, and implementation details after each code change
- [x] 6.2 sync tasks.md: 逐一检查所有顶层任务及其子任务，将已完成但仍为 `[ ]` 的条目标记为 `[x]`；每次更新只修改 `[ ]` → `[x]`，禁止修改任何任务描述文字
- [x] 6.3 sync proposal.md: update scope/impact if changed
- [x] 6.4 sync specs/*.md: update requirements if changed
- [x] 6.5 Final review: ensure all OpenSpec docs reflect actual implementation
