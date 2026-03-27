# MCP Agent SDK

[English](README.md) | 中文

用于编程式执行 AI Agent 任务的 Python SDK，支持**自动验证**和**人机协作**控制。

## 特性

- **Agent 执行** — 以托管子进程方式启动 `codebuddy` CLI Agent
- **自动验证** — 通过自定义函数验证任务结果；验证失败时自动重试
- **人机协作** — Agent 可调用 `Block` 工具标记需要人工介入的任务
- **结构化流式输出** — 通过 `AsyncIterator[StreamEvent]` 接收类型化事件（`AssistantMessage`、`SystemMessage`、`AgentResult`）
- **错误诊断** — 进程崩溃时抛出具体异常，包含 stderr 捕获和退出码
- **并发 Agent** — 同时运行多个 Agent，每个通过唯一 run ID 跟踪
- **超时支持** — 设置单次运行超时，超时后自动阻塞 Agent

## 安装

```bash
pip install mcp-agent-sdk
```

或从源码安装：

```bash
git clone <repo-url>
cd MCPAgentSDK
pip install -e .
```

### 前置条件

- Python ≥ 3.10
- `codebuddy` CLI 已安装并在 `PATH` 中可用

## 快速开始

```python
import asyncio
from mcp_agent_sdk import (
    MCPAgentSDK, AgentRunConfig, AgentResult,
    AssistantMessage, SystemMessage, TextBlock,
    AgentStartupError, AgentProcessError,
)

async def main():
    sdk = MCPAgentSDK()
    await sdk.init()

    config = AgentRunConfig(
        prompt="创建一个名为 hello.txt 的文件，内容为 'Hello, World!'",
    )

    try:
        async for event in sdk.run_agent(config):
            if isinstance(event, AgentResult):
                print(f"完成：{event.status} — {event.message}")
            elif isinstance(event, AssistantMessage):
                for block in event.content:
                    if isinstance(block, TextBlock):
                        print(f"[assistant] {block.text}")
            elif isinstance(event, SystemMessage):
                print(f"[system:{event.subtype}] {event.data}")
    except AgentStartupError as e:
        print(f"启动失败：{e}（stderr={e.stderr}, exit_code={e.exit_code}）")
    except AgentProcessError as e:
        print(f"进程崩溃：{e}（stderr={e.stderr}, exit_code={e.exit_code}）")

    await sdk.shutdown()

asyncio.run(main())
```

## API 参考

### `MCPAgentSDK`

运行 Agent 的主入口。

```python
sdk = MCPAgentSDK()
await sdk.init(host="127.0.0.1", port=0)  # port=0 自动选择可用端口
```

| 属性              | 类型   | 说明                          |
|-------------------|--------|-------------------------------|
| `port`            | `int`  | MCP 服务器实际绑定的端口       |
| `mcp_server_url`  | `str`  | MCP 端点的完整 URL            |

| 方法              | 说明                                            |
|-------------------|-------------------------------------------------|
| `init(host, port)`   | 启动内部 MCP 服务器                          |
| `shutdown()`         | 停止服务器并清理资源                          |
| `run_agent(config)`  | 运行 Agent；返回 `AsyncIterator[StreamEvent]` |

### `AgentRunConfig`

单次 Agent 运行的配置数据类。

```python
@dataclass
class AgentRunConfig:
    prompt: str                                                   # 任务描述
    validate_fn: Callable[[str], tuple[bool, str]] | None = None  # 自定义验证函数
    on_complete: Callable[[str], None] | None = None              # 完成回调
    on_block: Callable[[str], None] | None = None                 # 阻塞回调
    max_retries: int = 3                                          # 验证重试上限
    model: str | None = None                                      # LLM 模型覆盖
    permission_mode: str = "bypassPermissions"                    # CLI 权限模式
    cwd: str | None = None                                        # 工作目录
    allowed_tools: list[str] | None = None                        # 限制可用工具
    extra_args: dict[str, str | None] = field(default_factory=dict)  # 额外 CLI 参数
    timeout: float | None = None                                  # 超时时间（秒）
```

### 流式事件类型

`run_agent()` 产出 `StreamEvent` 子类，使用 `isinstance` 处理不同类型：

#### `AssistantMessage`

LLM 回复，包含类型化的内容块。

```python
@dataclass
class AssistantMessage(StreamEvent):
    content: list[ContentBlock]   # TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock
    session_id: str = ""
```

#### `SystemMessage`

系统事件（初始化、费用等）。

```python
@dataclass
class SystemMessage(StreamEvent):
    subtype: str = ""             # "init", "cost", "error" 等
    data: dict[str, Any] = {}
```

#### `ResultMessage`

会话结束元数据（内部消费，不对外产出）。

```python
@dataclass
class ResultMessage(StreamEvent):
    session_id: str = ""
    cost_usd: float = 0.0
    duration_ms: int = 0
    is_error: bool = False
    num_turns: int = 0
```

#### `AgentResult`

Agent 运行的最终结果。

```python
@dataclass
class AgentResult(StreamEvent):
    status: str = ""              # "completed" | "blocked"
    message: str = ""             # 结果描述
    session_id: str = ""
    agent_run_id: str = ""
    exit_code: int | None = None
    stderr_output: str = ""
```

### 内容块类型

`AssistantMessage.content` 中的内容块：

| 类型 | 字段 | 说明 |
|------|------|------|
| `TextBlock` | `text: str` | 纯文本回复 |
| `ThinkingBlock` | `thinking: str` | LLM 内部推理 |
| `ToolUseBlock` | `tool_use_id`, `name`, `input` | Agent 请求工具调用 |
| `ToolResultBlock` | `tool_use_id`, `output`, `is_error` | 工具执行结果 |

### 异常类型

进程故障时抛出具体异常，而非产出错误事件：

| 异常 | 触发时机 | 属性 |
|------|----------|------|
| `CLINotFoundError` | `codebuddy` 不在 PATH 中 | — |
| `AgentStartupError` | 进程在产出任何输出前崩溃 | `stderr`, `exit_code` |
| `AgentProcessError` | 进程退出但未调用 Complete/Block | `stderr`, `stdout_tail`, `exit_code` |
| `AgentExecutionError` | 逻辑错误（认证失败、API 错误等） | `errors`, `subtype` |

所有异常均继承自 `MCPAgentSDKError`（继承自 `Exception`）。

## 使用模式

### 自动验证与重试

提供 `validate_fn` 自动验证结果。验证失败时，Agent 会收到反馈并重试，最多 `max_retries` 次。

```python
def validate(result: str) -> tuple[bool, str]:
    if "success" in result.lower():
        return (True, "")
    return (False, "结果必须包含 success。请修复后重试。")

config = AgentRunConfig(
    prompt="创建并测试一个 hello-world 脚本",
    validate_fn=validate,
    max_retries=3,
)
```

### 回调函数

使用 `on_complete` 和 `on_block` 在运行结束时执行副作用：

```python
config = AgentRunConfig(
    prompt="部署预发布环境",
    on_complete=lambda result: notify_slack(f"✅ 部署完成：{result}"),
    on_block=lambda reason: page_oncall(f"🚧 部署阻塞：{reason}"),
)
```

### 超时控制

设置最大运行时间。超时后 Agent 自动被阻塞：

```python
config = AgentRunConfig(
    prompt="运行完整测试套件",
    timeout=120.0,  # 2 分钟
)
```

### 错误处理

用 try/except 包裹 `run_agent()` 捕获进程故障：

```python
from mcp_agent_sdk import AgentStartupError, AgentProcessError

try:
    async for event in sdk.run_agent(config):
        if isinstance(event, AgentResult):
            print(f"结果：{event.status}")
except AgentStartupError as e:
    print(f"CLI 启动时崩溃：{e}")
    print(f"stderr: {e.stderr}")
    print(f"退出码: {e.exit_code}")
except AgentProcessError as e:
    print(f"Agent 未完成就退出了：{e}")
    print(f"最后输出: {e.stdout_tail}")
```

### 并发 Agent

并行启动多个 Agent — 每个拥有独立的运行上下文：

```python
async def run_all():
    sdk = MCPAgentSDK()
    await sdk.init()

    configs = [
        AgentRunConfig(prompt="对代码库执行 Lint 检查"),
        AgentRunConfig(prompt="运行单元测试"),
    ]

    async def _run(cfg):
        try:
            async for event in sdk.run_agent(cfg):
                if isinstance(event, AgentResult):
                    print(event.status)
        except (AgentStartupError, AgentProcessError) as e:
            print(f"错误：{e}")

    await asyncio.gather(*[_run(c) for c in configs])
    await sdk.shutdown()
```

## 工作原理

```
你的代码 ──► MCPAgentSDK.run_agent(config)
                │
                ├─ 启动 MCP HTTP 服务器（JSON-RPC 2.0）
                ├─ 以唯一 agent_run_id 注册 RunContext
                ├─ 注入包含 Complete/Block 工具说明的系统提示词
                ├─ 携带 MCP 配置启动 codebuddy 子进程
                ├─ 启动异步 stderr 读取器（deque 缓冲，保留最后 100 行）
                │
                │   ┌─────────────────────────────────────┐
                │   │  codebuddy agent 执行任务             │
                │   │  ├─ 调用 Complete(result) ───────────┼──► validate_fn() ──► 重试或完成
                │   │  ├─ 调用 Block(reason)   ───────────┼──► on_block 回调
                │   │  └─ 未调用任一工具就崩溃  ───────────┼──► 抛出 AgentProcessError(stderr)
                │   └─────────────────────────────────────┘
                │
                └─ 产出 StreamEvent 流 ──► 你的 async for 循环
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行单元测试
pytest

# 运行端到端测试（需要 codebuddy 在 PATH 中）
pytest -m e2e
```

## 许可证

详见 [LICENSE](LICENSE)。
