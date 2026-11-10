from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from . import config

ALLOWED_TOOLS = {
    "seedream_health_check",
    "seedream_generate_image",
    "seedance_health_check",
    "seedance_create_video_task",
    "seedance_get_video_task",
    "seedance_wait_and_download",
}


class JimengMCPError(RuntimeError):
    pass


def _payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            try:
                value = json.loads(text)
                return value if isinstance(value, dict) else {"value": value}
            except json.JSONDecodeError:
                return {"text": text}
    return {}


class JimengMCPClient:
    def __init__(self, *, source_root: Path | None = None, timeout: float | None = None):
        self.source_root = source_root or config.mcp_source_root()
        self.timeout = timeout

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        project_root = str(config.PROJECT_ROOT)
        pieces = [project_root, str(self.source_root)]
        existing = env.get("PYTHONPATH", "")
        if existing:
            pieces.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(pieces)
        return env

    @asynccontextmanager
    async def session(self) -> AsyncIterator[ClientSession]:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "jimeng_mcp.server"],
            env=self._env(),
            cwd=str(config.PROJECT_ROOT),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                unexpected = names - ALLOWED_TOOLS
                if unexpected:
                    raise JimengMCPError(f"检测到非即梦工具，已拒绝运行：{sorted(unexpected)}")
                yield session

    async def call(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if tool_name not in ALLOWED_TOOLS:
            raise JimengMCPError(f"工具不在即梦白名单中：{tool_name}")
        async with self.session() as session:
            result = await session.call_tool(tool_name, arguments or {})
            if getattr(result, "is_error", False) or getattr(result, "isError", False):
                raise JimengMCPError(str(_payload(result)))
            return _payload(result)

    async def health(self) -> dict[str, Any]:
        image = await self.call("seedream_health_check", {})
        video = await self.call("seedance_health_check", {})
        return {"ok": bool(image.get("ok")) and bool(video.get("ok")), "seedream": image, "seedance": video}

    async def generate_image(self, prompt: str, output_dir: str, **kwargs: Any) -> dict[str, Any]:
        return await self.call(
            "seedream_generate_image",
            {"prompt": prompt, "output_dir": output_dir, **kwargs},
        )

    async def create_video_task(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        return await self.call("seedance_create_video_task", {"prompt": prompt, **kwargs})

    async def wait_video(self, task_id: str, output_dir: str, **kwargs: Any) -> dict[str, Any]:
        return await self.call(
            "seedance_wait_and_download",
            {"task_id": task_id, "output_dir": output_dir, **kwargs},
        )
