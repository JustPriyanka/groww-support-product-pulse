"""stdio MCP client: spawns mcp_server/server.py and calls one tool per connection."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from config import APPROVAL_SECRET, WORKSPACE_DB

ROOT = Path(__file__).resolve().parents[1]


def _params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(ROOT),
        env={"APPROVAL_SECRET": APPROVAL_SECRET, "WORKSPACE_DB": str(WORKSPACE_DB), "PYTHONPATH": str(ROOT),
             "PATH": os.environ.get("PATH", "")},
    )


async def _call(tool: str, args: dict) -> dict | list:
    async with Client(_params(), read_timeout_seconds=30) as client:
        res = await client.call_tool(tool, args)
        if getattr(res, "is_error", False) or getattr(res, "isError", False):
            raise RuntimeError(f"MCP tool error: {res.content}")
        text = next((c.text for c in res.content if getattr(c, "type", "") == "text"), None)
        if text is None:
            sc = getattr(res, "structured_content", None) or getattr(res, "structuredContent", None)
            text = sc.get("result") if isinstance(sc, dict) else json.dumps(sc)
        return json.loads(text)


def call(tool: str, args: dict) -> dict | list:
    """Synchronous wrapper (safe to call from FastAPI threadpool endpoints)."""
    return asyncio.run(_call(tool, args))


async def list_tools() -> list[str]:
    async with Client(_params()) as client:
        r = await client.list_tools()
        return [t.name for t in r.tools]
