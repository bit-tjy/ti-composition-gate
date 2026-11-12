# AgentArts Stdio 专用入口。输入沿用现有工作流的 query 字符串。
# query 的内容为 {"basis":"at%","composition":{"Ti":70,"Nb":30}} 这样的 JSON。
# 通过 Python 安装包提供 ti-composition-gate 命令，适合平台的 UVX 安装方式。

import hashlib
import json
from uuid import uuid4

from mcp.server.fastmcp import FastMCP
from agentarts_gate_check import main

mcp = FastMCP("ti-formulas")


@mcp.tool()
def gate_check(query: str) -> dict[str, object]:
    """输入JSON配方，包含basis和composition。"""
    # 复用检查核心，通过相同的 query 输入拿到检查结果。
    checked = json.loads(main({"query": query})["result"])
    # call_id 标识本次调用。input_hash 对原始 query 文本求摘要。
    # 相同文本得到相同摘要，字段顺序或空格不同的文本会有不同摘要。
    return {
        "call_id": f"gate-{uuid4().hex}",
        "tool": "ti-formulas.gate_check",
        "tool_version": checked["tool_version"],
        "input_hash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "status": "ok" if checked["passed"] else "rejected",
        "error_code": checked["error_code"],
        "result": {key: checked[key] for key in ("passed", "basis", "total", "composition_at_pct", "message")},
        "warnings": [],
    }


def serve():
    # 安装包中的命令行入口，只在实际启动服务时运行。
    # 使用标准输入输出通信，由调用方启动并管理进程。
    mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()
