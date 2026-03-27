## Context

MCPAgentSDK 是一个通过 MCP 协议控制 codebuddy CLI 子进程的 Python SDK。当前 SDK 在子进程异常退出时仅返回简单错误字符串，所有 stdout 消息以原始 dict 传递，缺少类型安全和诊断能力。

参考 `codebuddy_agent_sdk`（位于 `D:\work\StockAgent\venv\Lib\site-packages\codebuddy_agent_sdk`），其具备完善的异常层次（`CLIStartupError`、`ProcessError` 等）和 stderr 缓冲机制（`deque(maxlen=100)`），是本次改造的主要参考。

## Goals / Non-Goals

**Goals:**
- 进程异常退出时抛出包含 stderr、exit_code 的具体异常，便于调用方定位问题
- 所有 stdout 消息转为结构化类型，提供完整的类型提示
- 删除通用 `Message` 类，`run_agent()` 直接 yield 具体类型
- 异步持续读取 stderr 并缓冲，不阻塞主流程

**Non-Goals:**
- 不引入日志框架（logging）— 异常本身即承载诊断信息
- 不实现断线重连或进程恢复
- 不做向后兼容 — 这是 breaking change

## Decisions

1. **异常层次**：借鉴 codebuddy_agent_sdk 的分层思路，使用 MCPAgentSDK 自己的命名
   - `MCPAgentSDKError`（基类）→ `CLINotFoundError` / `AgentStartupError` / `AgentProcessError` / `AgentExecutionError`
   - 理由：自有命名避免与参考 SDK 混淆，同时保持语义清晰

2. **stderr 缓冲策略**：`deque(maxlen=100)` 保存最后 100 行
   - 理由：平衡内存占用与诊断信息量，参考 SDK 同款方案
   - 实现为独立的 `StderrReader` 类，在 `process.py` 中，通过 `asyncio.Task` 后台读取

3. **类型体系**：引入 `StreamEvent` 抽象基类，所有 yield 类型继承自它
   - `AssistantMessage`（含 `ContentBlock` 列表）、`SystemMessage`、`ResultMessage`、`AgentResult`
   - 理由：`isinstance` 判断比字符串 type 更安全，IDE 自动补全友好

4. **ContentBlock 子类**：`TextBlock`、`ThinkingBlock`、`ToolUseBlock`、`ToolResultBlock`
   - 未知 block type 降级为基类 `ContentBlock(type=原始类型名)`
   - 理由：覆盖 codebuddy CLI 输出的主要内容块类型

5. **未知消息降级**：无法识别的 type 解析为 `SystemMessage(subtype=原始类型名)`
   - 包括 `error` 类型 → `SystemMessage(subtype="error")`
   - 理由：不丢数据，保持前向兼容

6. **不保留 raw dict**：结构化类型不附带原始 dict
   - 理由：用户明确要求不向后兼容，保持简洁

7. **异常区分策略**：进程异常退出分两种情况
   - 无 stdout 输出 → `AgentStartupError`（启动即崩溃）
   - 有 stdout 但未调用 Complete/Block → `AgentProcessError`（运行中退出）
   - `AgentProcessError` 额外携带 `stdout_tail`（最后 20 行）辅助诊断

8. **Message 临时兼容 shim**：types.py 中在 2.1→2.3 过渡期保留了 Message compat shim，在 2.4 中完全移除
   - 理由：sdk.py 和 message_parser.py 同时依赖 Message，需分步迁移

## Risks / Trade-offs

- **Breaking Change**：所有现有调用方代码需要适配，`Message` 类不再存在
- **stderr 读取开销**：新增一个 asyncio Task 持续读取 stderr，但对性能影响极小
- **异常 vs yield**：进程异常退出从 yield error Message 改为 raise，调用方需要 try/except 包裹 `async for` 循环
