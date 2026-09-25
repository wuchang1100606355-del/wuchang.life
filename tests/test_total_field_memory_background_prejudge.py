import importlib.util
import json
from pathlib import Path

from contextlib import contextmanager


MODULE_PATH = Path("/home/taiji_admin/Taiji_Hub/tools/total_field_memory_background_prejudge.py")


spec = importlib.util.spec_from_file_location("total_field_memory_background_prejudge", MODULE_PATH)
bgp = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bgp)


@contextmanager
def with_root(path: Path):
    old_root = bgp.ROOT
    try:
        bgp.ROOT = Path(path)
        yield
    finally:
        bgp.ROOT = old_root


def _mutations_for_text(content: str, root: Path):
    target = root / "sample.md"
    root.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    with with_root(root):
        hits = bgp.grep_patterns(bgp.MUTATION_PATTERNS, [str(root)], classify_context=True)
    return hits


def test_no_command_text_is_safe_and_non_blocking(tmp_path: Path):
    hits = _mutations_for_text(
        "- NO odoo -i wuchang_wish_tree_coin",
        tmp_path / "safe",
    )
    assert len(hits) == 1
    assert hits[0]["safe_context"] is True
    assert hits[0]["blocking"] is False


def test_forbid_phrase_in_policy_stays_safe(tmp_path: Path):
    hits = _mutations_for_text(
        "FORBIDDEN: odoo -i wuchang_wish_tree_coin\n"
        "不得 git push 任何生產環境分支\n"
        "禁止 service restart",
        tmp_path / "policy",
    )
    assert len(hits) == 3
    for hit in hits:
        assert hit["safe_context"] is True
        assert hit["blocking"] is False


def test_shell_like_odoo_install_command_is_blocked(tmp_path: Path):
    hits = _mutations_for_text(
        "odoo -i wuchang_wish_tree_coin",
        tmp_path / "block_odoo",
    )
    assert len(hits) == 1
    assert hits[0]["blocking"] is True
    assert hits[0]["safe_context"] is False


def test_git_push_shell_like_command_is_blocked(tmp_path: Path):
    hits = _mutations_for_text(
        "git push origin main",
        tmp_path / "block_git",
    )
    assert len(hits) == 1
    assert hits[0]["blocking"] is True
    assert hits[0]["safe_context"] is False


def test_script_executable_mutation_command_is_blocked(tmp_path: Path):
    hits = _mutations_for_text(
        "#!/usr/bin/env bash\n"
        "set -e\n"
        "if command -v odoo >/dev/null 2>&1; then\n"
        "  odoo -i wuchang_wish_tree_coin\n"
        "fi",
        tmp_path / "script",
    )
    assert any(hit["blocking"] for hit in hits)
    assert any("odoo" in hit["text_preview"] and hit["blocking"] for hit in hits)
    assert all(not hit["safe_context"] for hit in hits if hit["blocking"])


def test_json_false_values_are_not_blocking_as_mutation(tmp_path: Path):
    root = tmp_path / "json_false"
    root.mkdir(parents=True, exist_ok=True)
    target = root / "sample.json"
    target.write_text(
        '{\"odoo_install\": false, \"service_restart\": false, \"git_push\": false}\\n',
        encoding="utf-8",
    )
    with with_root(root):
        hits = bgp.grep_patterns(bgp.MUTATION_PATTERNS, [str(root)], classify_context=True)
    assert hits == []
