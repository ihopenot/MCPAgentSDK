## ADDED Requirements

### Requirement: 异常处理体系

Agent 子进程异常退出时，SDK 必须抛出包含诊断信息的具体异常，而非返回通用错误消息。

#### Scenario: CLI 可执行文件未找到
- **WHEN** `find_codebuddy_cli()` 无法在 PATH 中找到 CLI 二进制文件
- **THEN** 抛出 `CLINotFoundError`，包含搜索路径信息

#### Scenario: Agent 进程启动即崩溃
- **WHEN** 子进程启动后立即退出（无 stdout JSON 输出），exit_code 非 0
- **THEN** 抛出 `AgentStartupError`，包含 `stderr` 内容和 `exit_code`

#### Scenario: Agent 进程运行中异常退出
- **WHEN** 子进程在运行过程中退出，且未通过 MCP 调用 Complete 或 Block
- **THEN** 抛出 `AgentProcessError`，包含 `stderr` 缓冲内容、`stdout_tail`（最后若干行）和 `exit_code`

#### Scenario: Agent 执行逻辑错误
- **WHEN** 从 stdout 流中解析到 error 类型消息（如认证失败、API 错误）
- **THEN** 抛出 `AgentExecutionError`，包含错误列表和错误子类型

### Requirement: stderr 异步捕获

#### Scenario: 正常运行期间持续读取 stderr
- **WHEN** Agent 子进程运行期间产生 stderr 输出
- **THEN** SDK 在后台异步读取并缓冲最后 100 行 stderr 内容

#### Scenario: 进程退出后 stderr 可用
- **WHEN** 进程异常退出，异常被抛出
- **THEN** 异常对象的 `stderr` 属性包含缓冲的 stderr 内容

### Requirement: 消息结构化

所有从 stdout 解析的消息必须转为具体的结构化类型，不再使用通用 `Message(type, content: dict)`。

#### Scenario: LLM 回复消息
- **WHEN** stdout 输出一行 type="assistant" 的 JSON
- **THEN** 解析为 `AssistantMessage`，其 `content` 为 `list[ContentBlock]`，包含 `TextBlock`、`ThinkingBlock`、`ToolUseBlock` 等具体类型

#### Scenario: 系统消息
- **WHEN** stdout 输出一行 type="system" 的 JSON
- **THEN** 解析为 `SystemMessage`，包含 `subtype` 和 `data` 字段

#### Scenario: 结果消息
- **WHEN** stdout 输出一行 type="result" 的 JSON
- **THEN** 解析为 `ResultMessage`，包含 `session_id`、`cost_usd`、`duration_ms` 等结构化字段

#### Scenario: Agent 最终结果
- **WHEN** Agent 通过 MCP 调用 Complete 或 Block
- **THEN** yield `AgentResult`，包含 `status`、`message`、`session_id`、`agent_run_id`

#### Scenario: run_agent() yield 类型
- **WHEN** 调用方迭代 `run_agent()` 的异步生成器
- **THEN** 每个 yield 的对象都是 `AssistantMessage | SystemMessage | ResultMessage | AgentResult` 之一，调用方通过 `isinstance` 判断类型

#### Scenario: 未知消息类型
- **WHEN** stdout 输出一行无法识别 type 的 JSON
- **THEN** 解析为通用的 `SystemMessage(subtype="unknown", data=原始dict)`，不丢弃数据

### Requirement: Message 类移除

#### Scenario: Breaking change
- **WHEN** 调用方升级到新版本 SDK
- **THEN** `Message` 类不再存在，`from mcp_agent_sdk import Message` 会导致 ImportError
- **THEN** 调用方需要改用具体类型（`AssistantMessage`、`AgentResult` 等）
