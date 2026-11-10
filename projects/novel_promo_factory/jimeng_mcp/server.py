from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

# Reuse only the two Ark/Jimeng providers from the existing MCP package.
# Do not import kling_image_mcp.server or kling_image_mcp.kling.
_DEFAULT_SOURCE_ROOT = Path(r"C:\Users\陈楷浩\OneDrive\桌面\脚本数据\kling-image-mcp")
_SOURCE_ROOT = Path(os.getenv("JIMENG_MCP_SOURCE_ROOT") or _DEFAULT_SOURCE_ROOT).resolve()
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from kling_image_mcp.seedance import SeedanceClient, SeedanceSettings  # noqa: E402
from kling_image_mcp.seedream import SeedreamClient, SeedreamSettings  # noqa: E402

logger = logging.getLogger(__name__)

ALLOWED_TOOL_NAMES = {
    "seedream_health_check",
    "seedream_generate_image",
    "seedance_health_check",
    "seedance_create_video_task",
    "seedance_get_video_task",
    "seedance_wait_and_download",
}

mcp = MCPServer(
    name="jimeng_only",
    title="Jimeng Seedream + Seedance MCP",
    description="Jimeng-source image and video generation through Volcengine Ark only. No Kling tools are registered.",
)


async def seedream_health_check() -> dict[str, Any]:
    """Check Ark/Jimeng image credentials and model-list access without billing."""
    settings = SeedreamSettings.from_env()
    if not settings.api_key:
        return {"ok": False, "base_url": settings.base_url, "error": "未配置 ARK_API_KEY"}
    async with SeedreamClient(settings) as client:
        return await client.health_check()


async def seedream_generate_image(
    prompt: str,
    output_dir: str,
    *,
    filename_prefix: str | None = None,
    model_name: str | None = None,
    reference_image: str | None = None,
    reference_images: list[str] | None = None,
    resolution: str | None = None,
    n: int | None = 1,
    aspect_ratio: str | None = None,
    watermark: bool | None = None,
    output_format: str = "png",
) -> dict[str, Any]:
    """Generate Jimeng-source Seedream images and download them locally."""
    settings = SeedreamSettings.from_env()
    reference: str | list[str] | None = reference_images or reference_image
    async with SeedreamClient(settings) as client:
        return await client.generate_image(
            prompt=prompt,
            output_dir=output_dir,
            filename_prefix=filename_prefix,
            model_name=model_name,
            image=reference,
            resolution=resolution,
            n=n,
            aspect_ratio=aspect_ratio,
            watermark=watermark,
            output_format=output_format,
        )


async def seedance_health_check() -> dict[str, Any]:
    """Check Ark/Jimeng video credentials and model-list access without billing."""
    settings = SeedanceSettings.from_env()
    if not settings.api_key:
        return {"ok": False, "base_url": settings.base_url, "error": "未配置 ARK_API_KEY"}
    async with SeedanceClient(settings) as client:
        return await client.health_check()


async def seedance_create_video_task(
    prompt: str,
    *,
    model_name: str | None = None,
    reference_image: str | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    resolution: str | None = None,
    ratio: str | None = None,
    duration: int | None = None,
    generate_audio: bool | None = None,
    watermark: bool | None = None,
    return_last_frame: bool = False,
    seed: int | None = None,
) -> dict[str, Any]:
    """Create a Jimeng-source Seedance video task."""
    settings = SeedanceSettings.from_env()
    settings.require_api_key()
    async with SeedanceClient(settings) as client:
        return await client.create_video_task(
            prompt=prompt,
            model_name=model_name,
            image=reference_image,
            first_frame=first_frame,
            last_frame=last_frame,
            resolution=resolution,
            ratio=ratio,
            duration=duration,
            generate_audio=generate_audio,
            watermark=watermark,
            return_last_frame=return_last_frame,
            seed=seed,
        )


async def seedance_get_video_task(task_id: str) -> dict[str, Any]:
    """Query a Jimeng-source Seedance task."""
    settings = SeedanceSettings.from_env()
    settings.require_api_key()
    async with SeedanceClient(settings) as client:
        return await client.get_video_task(task_id)


async def seedance_wait_and_download(
    task_id: str,
    output_dir: str,
    *,
    filename_prefix: str | None = None,
    poll_interval: float | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Wait for a Seedance task and download the resulting MP4 locally."""
    settings = SeedanceSettings.from_env()
    settings.require_api_key()
    async with SeedanceClient(settings) as client:
        task = await client.wait_for_task(task_id, poll_interval=poll_interval, timeout=timeout)
        url = client.extract_video_url(task)
        if not url:
            raise ValueError("Seedance 任务成功但没有返回 video_url")
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        path = await client.download_file(url, output / f"{filename_prefix or task_id}.mp4")
        return {"task_id": task_id, "task_status": task.get("status"), "video_url": url, "local_path": str(path.resolve()), "raw": task}


def register_tools() -> None:
    mcp.tool()(seedream_health_check)
    mcp.tool()(seedream_generate_image)
    mcp.tool()(seedance_health_check)
    mcp.tool()(seedance_create_video_task)
    mcp.tool()(seedance_get_video_task)
    mcp.tool()(seedance_wait_and_download)


register_tools()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Jimeng-only Seedream/Seedance MCP server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
