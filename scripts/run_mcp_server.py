"""启动 MCP Server（stdio 传输）。

用法：uv run python scripts/run_mcp_server.py
（MCP 客户端经 stdio 连接；日志走 stderr，stdout 归协议。）
TODO(真实数据源)：索引当前构建自 scripts/samples.py 的公开样本；
Phase 1 接数据层后替换。
"""

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp_server.index import InMemorySkillIndex  # noqa: E402
from mcp_server.server import build_server, serve_stdio  # noqa: E402


def main() -> int:
    index = InMemorySkillIndex()
    print(
        f"[mcp] ai-skill-benchmark server: {len(index)} public skills indexed; "
        "stdio transport ready",
        file=sys.stderr,
    )
    server = build_server(index=index)
    asyncio.run(serve_stdio(server))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
