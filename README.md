# 钛合金成分检查 MCP 工具

用于 AgentArts 的成分预检原型。当前规则采用生物医用示例白名单，允许 Ti、Nb、Ta、Zr、Mo、Sn、O，要求含有 Ti，检查数值范围与总和容差，并支持 wt% 到 at% 的换算。

## MCP 接口

工具名为 `gate_check`，必填参数 `query` 为 JSON 字符串，其内容例如下面这份配方。

```json
{"basis":"at%","composition":{"Ti":70,"Nb":20,"Zr":10}}
```

结果包含 `call_id`、`tool_version`、`input_hash`、`status`、`error_code` 和 `result`。`result.passed` 表示是否通过当前检查，拒绝原因由 `error_code` 和 `result.message` 提供。输入摘要基于原始 query 文本。

## 安装包

仓库中的 `ti_composition_gate-0.1.0-py3-none-any.whl` 包含检查核心和 Stdio 入口，依赖官方 MCP Python SDK 1.30.0，需要 Python 3.10 及以上。安装后的命令为 `ti-composition-gate`。

AgentArts Stdio 可使用 `uvx` 配合 `--from` 指定 wheel 的直接下载地址，并运行 `ti-composition-gate`。平台参数中只需包含地址和命令。

## 验证范围

检查核心已在 AgentArts 代码节点完成代表性测试。wheel 已在本地 UVX 环境完成安装、工具发现及正常和异常配方的 MCP 调用测试。安装包在 AgentArts 的安装和 MCP 调用仍待验证。

通过成分预检表示满足当前配置的规则，材料的性能和应用效果需要后续评估。Fe、单元素专用上下限及配料精度等场景参数仍需团队确认。守门代码权限隔离及持久化日志需在整体系统中落实。
