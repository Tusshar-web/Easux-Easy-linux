"""
Tests for SQLite storage, settings, events, retention, and export.
"""

from ai_terminal.storage.repository import Repository


def test_settings_crud(temp_repo):
    temp_repo.set_setting("model", "custom-model")
    assert temp_repo.get_setting("model") == "custom-model"

    all_s = temp_repo.get_all_settings()
    assert all_s.get("model") == "custom-model"


def test_command_events_and_frequency(temp_repo):
    temp_repo.record_command("pytest", "/tmp/proj1", exit_code=0)
    temp_repo.record_command("pytest", "/tmp/proj1", exit_code=0)
    temp_repo.record_command("git status", "/tmp/proj1", exit_code=0)

    rows = temp_repo.get_recent_and_frequent_commands("/tmp/proj1")
    assert len(rows) == 2
    cmd_freq = {r["command"]: r["frequency"] for r in rows}
    assert cmd_freq["pytest"] == 2
    assert cmd_freq["git status"] == 1


def test_error_events(temp_repo):
    temp_repo.record_error_event("git push", exit_code=1, stderr_redacted="rejected non-fast-forward")
    err = temp_repo.get_latest_error()
    assert err is not None
    assert err["exit_code"] == 1
    assert "rejected" in err["stderr"]


def test_clear_all_data(temp_repo):
    temp_repo.record_command("ls -la", "/tmp", exit_code=0)
    temp_repo.record_error_event("bad_cmd", exit_code=127, stderr_redacted="not found")

    res = temp_repo.clear_all_data()
    assert res["deleted_command_events"] == 1
    assert res["deleted_error_events"] == 1

    assert temp_repo.get_recent_and_frequent_commands() == []
    assert temp_repo.get_latest_error() is None


def test_export_data(temp_repo):
    temp_repo.record_command("echo test", "/tmp", exit_code=0)
    exported = temp_repo.export_data()
    assert "settings" in exported
    assert "command_events" in exported
    assert len(exported["command_events"]) == 1
