import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.mcp_plugins import _common
from app.mcp_plugins import disk_plugin


def test_run_command_returns_none_on_failed_command(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="permission denied")

    monkeypatch.setattr(_common.subprocess, "run", fake_run)
    assert _common.run_command(["find", "/missing"]) is None


def test_disk_large_files_surfaces_command_failure(monkeypatch):
    monkeypatch.setattr(disk_plugin, "_run_command", lambda *args, **kwargs: None)
    result = disk_plugin.disk_large_files(path="/tmp", top_n=5, min_size_mb=10)
    assert result["risk_level"] == "error"
    assert result["summary"]["error"] == "find 命令执行失败"
