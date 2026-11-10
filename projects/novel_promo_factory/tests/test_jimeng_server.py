from jimeng_mcp.server import ALLOWED_TOOL_NAMES


def test_jimeng_tool_allowlist_is_exact():
    assert ALLOWED_TOOL_NAMES == {
        "seedream_health_check",
        "seedream_generate_image",
        "seedance_health_check",
        "seedance_create_video_task",
        "seedance_get_video_task",
        "seedance_wait_and_download",
    }
