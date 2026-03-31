## ADDED Requirements

### Requirement: MCP Server 生命周期管理

MCPAgentSDK 实例通过 `init()` 启动内置 Streamable HTTP MCP Server，通过 `shutdown()` 关闭。

#### Scenario: 正常初始化与关闭
- **WHEN** 调用 `await sdk.init()`
- **THEN** Streamable HTTP Server 在指定地址启动，`POST /mcp` 端点可用

#### Scenario: 自动选择端口
- **WHEN** 调用 `await sdk.init(port=0)`
- **THEN** 系统自动选择可用端口，可通过 `sdk.port` 获取实际端口号

#### Scenario: 关闭清理
- **WHEN** 调用 `await sdk.shutdown()`
- **THEN** MCP Server 停止，所有资源释放，registry 清空

---

### Requirement: Agent 运行与流式输出

`run_agent()` 启动 codebuddy 子进程并流式返回消息。

#### Scenario: 正常运行并完成
- **WHEN** 调用 `sdk.run_agent(config)` 且 Agent 调用 `Complete` 工具且校验通过
- **THEN** 流式输出包含所有 Agent 消息，最终 yield 一条 status="completed" 的结果消息，子进程终止

#### Scenario: 校验不通过重试
- **WHEN** Agent 调用 `Complete` 但 `validate_fn` 返回 `(False, message)`
- **THEN** MCP Server 返回失败信息给 Agent，Agent 继续工作，retry_count 递增

#### Scenario: 超过最大重试次数
- **WHEN** retry_count 达到 `max_retries`
- **THEN** 状态变为 blocked（reason="验证重试次数超限"），触发 `on_block` 回调，子进程终止

#### Scenario: Agent 主动受阻
- **WHEN** Agent 调用 `Block(agent_run_id, reason)` 工具
- **THEN** 触发 `on_block` 回调，子进程终止，yield 结果消息含 status="blocked"、reason、session_id

---

### Requirement: MCP 工具路由

MCP Server 通过 `agent_run_id` 将工具调用路由到对应的处理逻辑。

#### Scenario: 按 ID 路由
- **WHEN** MCP Server 收到 `Complete(agent_run_id="abc", result="...")` 请求
- **THEN** 从 registry 中查找 id="abc" 对应的 validate_fn 和回调执行

#### Scenario: 并发多个 Agent
- **WHEN** 同时运行两个 `run_agent()`，各自有不同的 agent_run_id
- **THEN** 各自的 Complete/Block 调用路由到各自的校验函数和回调，互不干扰

#### Scenario: ID 不存在
- **WHEN** MCP Server 收到未知 agent_run_id 的工具调用
- **THEN** 返回错误信息 "unknown agent_run_id"

---

### Requirement: System Prompt 注入

`run_agent()` 自动在用户 prompt 前注入 MCP 工具使用指引。

#### Scenario: 注入内容
- **WHEN** 调用 `run_agent(prompt="做任务X")`
- **THEN** 实际发送给 codebuddy 的 prompt 包含 Complete/Block 工具说明、agent_run_id、使用规则，以及用户原始 prompt

---

### Requirement: 结构化结果

Agent 运行结束后返回结构化结果。

#### Scenario: 完成结果
- **WHEN** Agent 任务完成
- **THEN** 结果包含 status="completed"、message、session_id、agent_run_id

#### Scenario: 结构化结果
- **WHEN** Agent 任务受阻
- **THEN** 结果包含 status="blocked"、message（含 reason）、session_id、agent_run_id，可通过 session_id 后续恢复会话

---

### Requirement: 自定义 MCP Server 透传

`AgentRunConfig` 支持通过 `mcp_servers` 字段传入额外的 MCP Server 配置，这些配置会与内置的 `agent-controller` 合并后传递给 Agent 子进程。

#### Scenario: 透传额外 MCP Server
- **WHEN** 调用 `run_agent(config)` 且 config 包含 `mcp_servers={"my-server": {"type": "http", "url": "http://localhost:8080/mcp"}}`
- **THEN** Agent 子进程的 `--mcp-config` 参数同时包含 `agent-controller` 和 `my-server` 两个 MCP Server

#### Scenario: 内置 agent-controller 不可覆盖
- **WHEN** `mcp_servers` 中包含 key 为 `"agent-controller"` 的条目
- **THEN** 该条目被忽略，内置的 `agent-controller` 配置始终生效，确保 Complete/Block 工具可用

#### Scenario: 默认不传额外 MCP Server
- **WHEN** `mcp_servers` 未指定（默认空 dict）
- **THEN** 行为与之前一致，仅包含内置 `agent-controller`
