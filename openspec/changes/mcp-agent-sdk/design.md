## Context

需要一个独立的 Python Agent SDK，通过 subprocess 调用 `codebuddy` CLI，并内置 MCP Server 提供 Complete/Block 工具，实现自动校验 + 人工兜底的 Agent 运行闭环。

官方 `codebuddy_agent_sdk` 使用 `codebuddy-headless.exe` 和 SDK 内置 MCP 协议（通过 stdio control protocol），本 SDK 选择独立实现，直接依赖 PATH 中的 `codebuddy` 命令，通过外部 Streamable HTTP MCP Server 提供工具。

## Goals / Non-Goals

**Goals:**
- 提供 `MCPAgentSDK` 类，管理 MCP Server 生命周期（init/shutdown）
- 提供 `run_agent()` 方法，流式返回 Agent 消息（AsyncIterator[Message]）
- MCP Server 提供 Complete 和 Block 两个工具，按 agent_run_id 路由
- 支持校验函数、完成/受阻回调、最大重试次数
- 支持并发多个 Agent 运行
- 注入 system prompt 指导 Agent 正确使用 MCP 工具

**Non-Goals:**
- 不实现官方 SDK 的 stdio control protocol（不需要 can_use_tool、hooks 等）
- 不实现 SSE 传输方式（仅 Streamable HTTP）
- 不实现会话恢复功能（返回 session_id 供调用方自行处理）
- 不实现 Agent 间通信（不是多 Agent 框架）

## Decisions

1. **独立实现，不依赖官方 SDK**：避免与 `codebuddy-headless.exe` 绑定，保持简洁
2. **Streamable HTTP MCP Server**：使用 `aiohttp` 实现单端点 `POST /mcp`（JSON-RPC 2.0），codebuddy CLI 通过 `--mcp-config` JSON 字符串连接
3. **agent_run_id 路由机制**：每次 `run_agent()` 生成唯一 id，注入到 Agent prompt 中，MCP Server 通过 id 查 registry 路由到对应的校验函数和回调
4. **回调与 run_agent 绑定**：validate_fn、on_complete、on_block 作为 `run_agent()` 参数传入，生命周期与单次运行绑定
5. **状态检测驱动终止**：MCP handler 修改 registry 状态，run_agent 的流式循环检测到非 running 状态后终止子进程
6. **MCP config 直接传 JSON 字符串**：`--mcp-config '{...}'` 无需落地临时文件
7. **agent_result 消息类型**：SDK 合成的最终结果使用 `type="agent_result"` 而非 `type="result"`，避免与 CLI 原生 result 消息混淆。CLI 原生 result 消息仅用于提取 session_id，不 yield 给调用方
8. **async 回调支持**：validate_fn 和 on_complete/on_block 回调均支持 sync 和 async 两种形式，通过 `inspect.iscoroutinefunction` 检测后分别处理，避免阻塞事件循环
9. **回调异常隔离**：validate_fn 异常返回 MCP 错误响应给 Agent；on_complete/on_block 回调异常被静默捕获，不影响 SDK 主流程
10. **init() 幂等性**：重复调用 init() 会先 shutdown 已有 server，避免资源泄漏
11. **Prompt 通过 stdin 发送**：使用 `--input-format=stream-json` 模式，prompt 通过 stdin 以 JSON 消息格式发送而非命令行参数，避免 shell 转义问题和长度限制
12. **设置隔离**：默认 `--setting-sources none`，不加载文件系统设置，确保 SDK 环境干净

## Risks / Trade-offs

- **Agent 可能不调用 Complete/Block**：依赖 system prompt 注入来确保 Agent 行为，极端情况下 Agent 可能忽略指引直接停止——此时 run_agent 通过进程退出检测兜底
- **并发安全**：多个 run_agent 共享同一个 MCP Server，通过 agent_run_id 隔离，但需要确保 registry 操作线程安全（asyncio 单线程模型下天然安全）
- **端口冲突**：默认 port=0 自动选端口，避免冲突
- **codebuddy CLI 不在 PATH**：启动时应做检测，给出明确错误提示
