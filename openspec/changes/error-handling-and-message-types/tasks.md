## 1. 异常处理体系

- [x] 1.1 创建 `errors.py`，定义异常层次  <!-- TDD 任务 -->
  - [x] 1.1.1 写失败测试：`tests/test_errors.py` — 测试各异常类的属性（stderr、exit_code、errors、subtype）
  - [x] 1.1.2 验证测试失败（运行：`python -m pytest tests/test_errors.py -v`，确认失败原因是模块不存在）
  - [x] 1.1.3 写最小实现：`mcp_agent_sdk/errors.py` — `MCPAgentSDKError`、`CLINotFoundError`、`AgentStartupError`、`AgentProcessError`、`AgentExecutionError`
  - [x] 1.1.4 验证测试通过（运行：`python -m pytest tests/test_errors.py -v`，确认所有测试通过，输出干净）
  - [x] 1.1.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 1.2 `process.py` 增加 stderr 异步读取与缓冲  <!-- TDD 任务 -->
  - [x] 1.2.1 写失败测试：`tests/test_process.py` — 测试 stderr 读取 task 创建、deque 缓冲行为、`get_stderr()` 返回内容
  - [x] 1.2.2 验证测试失败（运行：`python -m pytest tests/test_process.py -v`，确认失败原因是缺少 stderr 读取功能）
  - [x] 1.2.3 写最小实现：`mcp_agent_sdk/process.py` — 增加 `start_stderr_reader()` 创建异步 task 读取 stderr 到 `deque(maxlen=100)`，`get_stderr()` 返回缓冲内容
  - [x] 1.2.4 验证测试通过（运行：`python -m pytest tests/test_process.py -v`，确认所有测试通过，输出干净）
  - [x] 1.2.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 1.3 `sdk.py` 异常抛出逻辑  <!-- TDD 任务 -->
  - [x] 1.3.1 写失败测试：`tests/test_sdk_errors.py` — 测试进程启动即崩溃抛 `AgentStartupError`、运行中异常退出抛 `AgentProcessError`，验证异常包含 stderr 和 exit_code
  - [x] 1.3.2 验证测试失败（运行：`python -m pytest tests/test_sdk_errors.py -v`，确认失败原因是 sdk.py 仍 yield error Message）
  - [x] 1.3.3 写最小实现：`mcp_agent_sdk/sdk.py` — 替换 yield error Message 为 raise 对应异常，集成 stderr 缓冲
  - [x] 1.3.4 验证测试通过（运行：`python -m pytest tests/test_sdk_errors.py -v`，确认所有测试通过，输出干净）
  - [x] 1.3.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 1.4 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/error-handling-and-message-types/specs/*.md` 和 `openspec/changes/error-handling-and-message-types/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → `mcp_agent_sdk/errors.py`、`mcp_agent_sdk/process.py`、`mcp_agent_sdk/sdk.py`、`tests/test_errors.py`、`tests/test_process.py`、`tests/test_sdk_errors.py`
    - `{BASE_SHA}` → 任务组开始前的 commit SHA
    - `{HEAD_SHA}` → 当前 HEAD
  - 若存在 Critical/Important 问题：输出审查结果后停止等待用户输入
  - 若仅有 Minor 或无问题：自动继续下一任务组

## 2. 消息结构化类型体系

- [x] 2.1 `types.py` 定义 `ContentBlock` 系列和 `StreamEvent` 系列  <!-- TDD 任务 -->
  - [x] 2.1.1 写失败测试：`tests/test_types.py` — 测试 `TextBlock`、`ThinkingBlock`、`ToolUseBlock`、`ToolResultBlock` 的属性；测试 `AssistantMessage`、`SystemMessage`、`ResultMessage`、`AgentResult` 的属性和继承关系
  - [x] 2.1.2 验证测试失败（运行：`python -m pytest tests/test_types.py -v`，确认失败原因是类不存在）
  - [x] 2.1.3 写最小实现：`mcp_agent_sdk/types.py` — 定义 `StreamEvent` 基类、`ContentBlock` 基类及所有子类、所有消息类型，删除 `Message` 类
  - [x] 2.1.4 验证测试通过（运行：`python -m pytest tests/test_types.py -v`，确认所有测试通过，输出干净）
  - [x] 2.1.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 2.2 `message_parser.py` 解析返回具体类型  <!-- TDD 任务 -->
  - [x] 2.2.1 写失败测试：`tests/test_message_parser.py` — 测试各类 JSON 输入解析为对应的具体类型（`AssistantMessage`、`SystemMessage`、`ResultMessage`）；测试未知 type 降级为 `SystemMessage(subtype="unknown")`；测试无效 JSON 返回 None
  - [x] 2.2.2 验证测试失败（运行：`python -m pytest tests/test_message_parser.py -v`，确认失败原因是 parser 仍返回旧 Message）
  - [x] 2.2.3 写最小实现：`mcp_agent_sdk/message_parser.py` — 按 type 路由到 `_parse_assistant`、`_parse_system`、`_parse_result` 等函数，返回具体类型
  - [x] 2.2.4 验证测试通过（运行：`python -m pytest tests/test_message_parser.py -v`，确认所有测试通过，输出干净）
  - [x] 2.2.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 2.3 `sdk.py` 适配新类型体系  <!-- TDD 任务 -->
  - [x] 2.3.1 写失败测试：`tests/test_sdk_messages.py` — 测试 `run_agent()` yield 的对象均为 `StreamEvent` 子类（`AssistantMessage | SystemMessage | ResultMessage | AgentResult`）；测试 `AgentResult` 包含正确的 status/message/session_id
  - [x] 2.3.2 验证测试失败（运行：`python -m pytest tests/test_sdk_messages.py -v`，确认失败原因是 sdk.py 仍 yield Message）
  - [x] 2.3.3 写最小实现：`mcp_agent_sdk/sdk.py` — 所有 yield 改为具体类型，agent_result 构造改为 `AgentResult` 实例
  - [x] 2.3.4 验证测试通过（运行：`python -m pytest tests/test_sdk_messages.py -v`，确认所有测试通过，输出干净）
  - [x] 2.3.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 2.4 `__init__.py` 导出更新 + `example.py` 适配  <!-- 非 TDD 任务 -->
  - [x] 2.4.1 执行变更：`mcp_agent_sdk/__init__.py` — 移除 `Message` 导出，新增所有结构化类型和异常类导出；`example.py` — 适配新类型
  - [x] 2.4.2 验证无回归（运行：`python -m pytest -v`，确认全部测试通过，输出干净）
  - [x] 2.4.3 检查：确认变更范围完整，`__init__.py` 导出列表与实际类型一致，example.py 可正常运行

- [x] 2.5 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/error-handling-and-message-types/specs/*.md` 和 `openspec/changes/error-handling-and-message-types/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → `mcp_agent_sdk/types.py`、`mcp_agent_sdk/message_parser.py`、`mcp_agent_sdk/sdk.py`、`mcp_agent_sdk/__init__.py`、`example.py`、`tests/test_types.py`、`tests/test_message_parser.py`、`tests/test_sdk_messages.py`
    - `{BASE_SHA}` → 任务组开始前的 commit SHA
    - `{HEAD_SHA}` → 当前 HEAD
  - 若存在 Critical/Important 问题：输出审查结果后停止等待用户输入
  - 若仅有 Minor 或无问题：自动继续下一任务组

## 3. PreCI 代码规范检查

- [x] 3.1 检测 preci 安装状态（跳过：skip_preci: true）
- [x] 3.2 检测项目是否已 preci 初始化（跳过：skip_preci: true）
- [x] 3.3 检测 PreCI Server 状态（跳过：skip_preci: true）
- [x] 3.4 执行代码规范扫描（跳过：skip_preci: true）
- [x] 3.5 处理扫描结果（跳过：skip_preci: true）

## 4. Documentation Sync (Required)

- [x] 4.1 sync design.md: record technical decisions, deviations, and implementation details after each code change
- [x] 4.2 sync tasks.md: 逐一检查所有顶层任务及其子任务，将已完成但仍为 `[ ]` 的条目标记为 `[x]`；每次更新只修改 `[ ]` → `[x]`，禁止修改任何任务描述文字
- [x] 4.3 sync proposal.md: update scope/impact if changed
- [x] 4.4 sync specs/*.md: update requirements if changed
- [x] 4.5 Final review: ensure all OpenSpec docs reflect actual implementation
