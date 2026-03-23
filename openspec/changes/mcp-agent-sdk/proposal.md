## Why

需要一个独立的 Agent SDK，能够以编程方式调用 codebuddy CLI 执行任务，并通过 MCP 工具实现"自动验证 + 人工兜底"的闭环控制：Agent 完成任务后自动校验结果，校验不通过则让 Agent 继续修正；遇到无法解决的问题则标记受阻、终止并返回结构化结果供后续恢复。

## What Changes

- 新增 `mcp_agent_sdk` Python 包，不依赖官方 `codebuddy_agent_sdk`
- 提供 `MCPAgentSDK` 主类，管理内置 Streamable HTTP MCP Server 的生命周期
- MCP Server 暴露 `Complete` 和 `Block` 两个工具，通过 `agent_run_id` 路由到对应的校验函数和回调
- 提供 `run_agent()` 方法，流式返回 `AsyncIterator[Message]`，支持并发多个 Agent 运行
- 通过 subprocess 调用 PATH 中的 `codebuddy` 命令（非 codebuddy-headless.exe）
- 自动注入 system prompt 指导 Agent 使用 Complete/Block 工具

## Impact

- 新包，无现有代码影响
- 依赖：`aiohttp`（Streamable HTTP Server）、Python 标准库（asyncio, json, uuid, dataclasses）
- 运行时依赖 PATH 中的 `codebuddy` CLI
