# Tasks: Add can_use_tool Callback

## 1. Type Definitions and Default Function

- [x] 1.1 Add `CanUseToolOptions`, `PermissionResultAllow`, `PermissionResultDeny`, `PermissionResult`, `CanUseTool` types and `default_deny_can_use_tool` function to `types.py`  <!-- TDD 任务 -->
  - [x] 1.1.1 写失败测试：`tests/test_can_use_tool_types.py` — 测试新 dataclass 构造、字段默认值、`default_deny_can_use_tool` 返回 deny 结果
  - [x] 1.1.2 验证测试失败（运行：`cd d:/work/MCPAgentSDK/.worktrees/can-use-tool && python -m pytest tests/test_can_use_tool_types.py -v`，确认失败原因是缺少类型定义）
  - [x] 1.1.3 写最小实现：`mcp_agent_sdk/types.py` — 添加类型定义和默认拒绝函数
  - [x] 1.1.4 验证测试通过（运行：`cd d:/work/MCPAgentSDK/.worktrees/can-use-tool && python -m pytest tests/test_can_use_tool_types.py -v`，确认所有测试通过，输出干净）
  - [x] 1.1.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 1.2 Add `can_use_tool` field to `AgentRunConfig`  <!-- 非 TDD 任务 -->
  - [x] 1.2.1 执行变更：`mcp_agent_sdk/types.py` — 在 `AgentRunConfig` dataclass 中添加 `can_use_tool: CanUseTool | None = None` 字段
  - [x] 1.2.2 验证无回归（运行：`cd d:/work/MCPAgentSDK/.worktrees/can-use-tool && python -m pytest tests/ -v`，确认输出干净）
  - [x] 1.2.3 检查：确认 `AgentRunConfig` 字段完整，无遗漏引用

- [x] 1.3 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/add-can-use-tool-callback/specs/*.md` 和 `openspec/changes/add-can-use-tool-callback/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → `mcp_agent_sdk/types.py`, `tests/test_can_use_tool_types.py`
    - `{BASE_SHA}` → 任务组开始前的 commit SHA
    - `{HEAD_SHA}` → 当前 HEAD
  - 若存在 Critical/Important 问题：输出审查结果后停止等待用户输入
  - 若仅有 Minor 或无问题：自动继续下一任务组

## 2. SDK Control Request Handling

- [x] 2.1 Handle `can_use_tool` control requests in `sdk.py`  <!-- TDD 任务 -->
  - [x] 2.1.1 写失败测试：`tests/test_can_use_tool_handling.py` — 测试 SDK 收到 `can_use_tool` 控制请求时：(a) 无回调时返回 deny，(b) 自定义回调 allow/deny 响应正确，(c) 回调异常时返回 deny
  - [x] 2.1.2 验证测试失败（运行：`cd d:/work/MCPAgentSDK/.worktrees/can-use-tool && python -m pytest tests/test_can_use_tool_handling.py -v`，确认失败原因是缺少 `can_use_tool` 处理逻辑）
  - [x] 2.1.3 写最小实现：`mcp_agent_sdk/sdk.py` — 在控制请求处理中添加 `can_use_tool` 分支
  - [x] 2.1.4 验证测试通过（运行：`cd d:/work/MCPAgentSDK/.worktrees/can-use-tool && python -m pytest tests/test_can_use_tool_handling.py -v`，确认所有测试通过，输出干净）
  - [x] 2.1.5 重构：整理代码、改善命名、消除重复（保持所有测试通过）

- [x] 2.2 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更，占位符映射：
    - `{PLAN_OR_REQUIREMENTS}` → `openspec/changes/add-can-use-tool-callback/specs/*.md` 和 `openspec/changes/add-can-use-tool-callback/tasks.md`
    - `{WHAT_WAS_IMPLEMENTED}` → `mcp_agent_sdk/sdk.py`, `tests/test_can_use_tool_handling.py`
    - `{BASE_SHA}` → 任务组开始前的 commit SHA
    - `{HEAD_SHA}` → 当前 HEAD
  - 若存在 Critical/Important 问题：输出审查结果后停止等待用户输入
  - 若仅有 Minor 或无问题：自动继续下一任务组

## 3. Public API Export

- [x] 3.1 Export new types from `__init__.py`  <!-- 非 TDD 任务 -->
  - [x] 3.1.1 执行变更：`mcp_agent_sdk/__init__.py` — 添加 `CanUseTool`, `CanUseToolOptions`, `PermissionResult`, `PermissionResultAllow`, `PermissionResultDeny`, `default_deny_can_use_tool` 到导入和 `__all__`
  - [x] 3.1.2 验证无回归（运行：`cd d:/work/MCPAgentSDK/.worktrees/can-use-tool && python -m pytest tests/ -v`，确认输出干净）
  - [x] 3.1.3 检查：确认 `from mcp_agent_sdk import CanUseTool, PermissionResultAllow, PermissionResultDeny, default_deny_can_use_tool` 可正常导入

- [x] 3.2 代码审查
  - 前置验证：调用 superpowers:verification-before-completion 运行全量测试，确认输出干净后才继续
  - 调用 superpowers:requesting-code-review 审查本任务组所有变更
  - 若存在 Critical/Important 问题：输出审查结果后停止等待用户输入
  - 若仅有 Minor 或无问题：自动继续下一任务组

## 4. PreCI 代码规范检查

- [x] 4.1 检测 preci 安装状态
- [x] 4.2 检测项目是否已 preci 初始化
- [x] 4.3 检测 PreCI Server 状态
- [x] 4.4 执行代码规范扫描
- [x] 4.5 处理扫描结果

## 5. Documentation Sync (Required)

- [x] 5.1 sync design.md: record technical decisions, deviations, and implementation details after each code change
- [x] 5.2 sync tasks.md: 逐一检查所有顶层任务及其子任务，将已完成但仍为 `[ ]` 的条目标记为 `[x]`；每次更新只修改 `[ ]` → `[x]`，禁止修改任何任务描述文字
- [x] 5.3 sync proposal.md: update scope/impact if changed
- [x] 5.4 sync specs/*.md: update requirements if changed
- [x] 5.5 Final review: ensure all OpenSpec docs reflect actual implementation
