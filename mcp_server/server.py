"""MCP Server 入口：注册 4 个工具，stdio 传输。

基于 mcp 2.x 的 MCPServer（原 FastMCP）高层 API：@tool 装饰器自动生成
inputSchema，list_tools/call_tool 内建。工具逻辑全在 tools.py（可单测）；
McpToolError 转结构化 error JSON 返回，不让协议层崩溃。
"""

from pathlib import Path

from mcp.server.mcpserver import MCPServer

from mcp_server.errors import McpToolError
from mcp_server.index import InMemorySkillIndex
from mcp_server.tools import (
    get_skill as _get_skill,
    get_skill_artifacts as _get_skill_artifacts,
    get_trial_report as _get_trial_report,
    search_skills as _search_skills,
)

_DEFAULT_REPORT_PATH = (
    Path(__file__).resolve().parent.parent / "reports" / "phase0_trial_report.json"
)

TOOL_NAMES: frozenset[str] = frozenset(
    {"search_skills", "get_skill", "get_skill_artifacts", "get_trial_report"}
)


def build_server(
    index: InMemorySkillIndex | None = None,
    report_path: Path = _DEFAULT_REPORT_PATH,
) -> MCPServer:
    server = MCPServer(
        "ai-skill-benchmark",
        instructions=(
            "Public AI-skill index with static-review results. Metadata and "
            "artifact references only: skill bodies, scripts and binaries are "
            "never served; install via origin_url. Evidence grades are capped "
            "at D/U in this phase."
        ),
    )
    skill_index = index if index is not None else InMemorySkillIndex()

    @server.tool(
        description=(
            "Search public skills by name/description substring. Returns metadata "
            "summaries only; install via origin_url (no file downloads)."
        )
    )
    def search_skills(query: str, limit: int = 10) -> dict:
        try:
            return _search_skills(skill_index, query=query, limit=limit)
        except McpToolError as exc:
            return exc.to_payload()

    @server.tool(
        description=(
            "Get one skill's declared metadata, status, static-review summary and "
            "admission reasons. Never returns SKILL.md body or script sources."
        )
    )
    def get_skill(skill_id: str) -> dict:
        try:
            return _get_skill(skill_index, skill_id)
        except McpToolError as exc:
            return exc.to_payload()

    @server.tool(
        description=(
            "Get artifact references (bucket/key/sha256/size) for a skill. "
            "References only; artifact content is never served."
        )
    )
    def get_skill_artifacts(skill_id: str) -> dict:
        try:
            return _get_skill_artifacts(skill_index, skill_id)
        except McpToolError as exc:
            return exc.to_payload()

    @server.tool(
        description=(
            "Get the Phase 0 trial closure report (sanitized summary). Evidence "
            "grades are capped at D/U; results are shape-validation, not evidence."
        )
    )
    def get_trial_report() -> dict:
        try:
            return _get_trial_report(report_path)
        except McpToolError as exc:
            return exc.to_payload()

    return server


async def serve_stdio(server: MCPServer) -> None:
    await server.run_stdio_async()
