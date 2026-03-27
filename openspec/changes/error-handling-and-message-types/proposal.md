## Why

当 Agent 子进程异常退出（未调用 Complete 或 Block）时，SDK 仅返回一条简单的错误字符串，缺少 stderr、exit code 等诊断信息，调用方无法定位问题根因。

同时，所有从 stdout 解析的消息都以原始 `dict` 形式通过通用 `Message(type, content: dict)` 返回，调用方缺乏类型提示和字段保障，容易出错。

## What Changes

### 1. 异常处理体系
- 新增 `errors.py`，定义 `MCPAgentSDKError` 异常层次（`CLINotFoundError`、`AgentStartupError`、`AgentProcessError`、`AgentExecutionError`）
- `process.py` 增加 stderr 异步读取与缓冲（`deque(maxlen=100)`）
- `sdk.py` 在进程异常退出时抛出具体异常（附带 stderr、exit_code），不再 yield error Message

### 2. 消息结构化
- 删除通用 `Message` 类
- 引入 `StreamEvent` 基类，派生 `AssistantMessage`、`SystemMessage`、`ResultMessage`、`AgentResult`
- 引入 `ContentBlock` 基类，派生 `TextBlock`、`ThinkingBlock`、`ToolUseBlock`、`ToolResultBlock`
- `run_agent()` 直接 yield 具体类型，调用方通过 `isinstance` 判断
- `message_parser.py` 按消息 type 路由到具体解析函数

## Impact

- **errors.py**: 新文件 — 异常层次定义
- **types.py**: 重写 — 删除 `Message`，新增 `StreamEvent`/`ContentBlock` 体系，保留 `AgentRunConfig`/`RunContext`/`AgentResult`
- **message_parser.py**: 重写 — 按类型路由解析，返回具体 `StreamEvent` 子类
- **sdk.py**: 重写 — yield 结构化类型，异常抛出，stderr 集成
- **process.py**: 扩展 — 新增 `StderrReader` 类，`CLINotFoundError` 替换 `FileNotFoundError`
- **__init__.py**: 更新导出 — 新增所有结构化类型和错误类
- **example.py**: 适配 — `isinstance` 模式 + try/except 错误处理
- **tests/**: 新增 `test_errors.py`、`test_stderr_reader.py`、`test_types.py`、`test_message_parser_v2.py`、`test_sdk_errors.py`、`test_sdk_messages.py`；更新 `test_message_parser.py`、`test_sdk.py`
- **Breaking Change**: `Message` 类被完全移除，`run_agent()` 的 yield 类型变更为 `StreamEvent` 子类
