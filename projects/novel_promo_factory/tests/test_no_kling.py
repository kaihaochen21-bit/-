import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_no_kling_imports_in_owned_code():
    forbidden = {"kling_image_mcp.server", "kling_image_mcp.kling"}
    for path in list((ROOT / "app").rglob("*.py")) + list((ROOT / "jimeng_mcp").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in forbidden, f"{path} imports {node.module}"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden, f"{path} imports {alias.name}"


def test_no_kling_key_dependency():
    for path in list((ROOT / "app").rglob("*.py")) + list((ROOT / "jimeng_mcp").rglob("*.py")):
        assert "KLING_API_KEY" not in path.read_text(encoding="utf-8"), str(path)
