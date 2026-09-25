"""
Comprehensive CLI tests covering all subcommands and terminal interactions.
"""

import json
from unittest.mock import patch
from ai_terminal.cli import main


def test_cli_version(capsys):
    try:
        main(["--version"])
    except SystemExit:
        pass
    captured = capsys.readouterr()
    assert "ai-terminal" in captured.out or "0.1.0" in captured.out


def test_cli_complete_json(capsys):
    ret = main(["complete", "--shell", "bash", "--buffer", "git che", "--cursor", "7", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    values = [item["value"] for item in data]
    assert "checkout" in values


def test_cli_suggest_json(capsys):
    ret = main(["suggest", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)


def test_cli_explain_json(capsys):
    ret = main(["explain", "--json", "tar", "-xzf", "archive.tgz"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "explanation" in data
    assert "effects" in data
    assert data["risk"] == "low"


def test_cli_natural_language_json(capsys):
    ret = main(["--json", "find", "Python", "files", "modified", "in", "the", "last", "7", "days"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "find" in data["command"]
    assert "-mtime -7" in data["command"]
    assert data["risk"] == "low"


def test_cli_record_and_fix(capsys):
    # 1. Record error
    ret1 = main(["record", "--command", "git push origin main", "--exit", "1", "--error", "! [rejected] main -> main (non-fast-forward)"])
    assert ret1 == 0

    # 2. Fix error
    ret2 = main(["fix", "--yes", "--json"])
    assert ret2 == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "rebase" in data["next_command"]
    assert data["confidence"] > 0.8


def test_cli_config(capsys):
    ret_set = main(["config", "set", "test_key", "test_val"])
    assert ret_set == 0

    ret_get = main(["config", "get", "test_key"])
    assert ret_get == 0
    captured = capsys.readouterr()
    assert "test_key = test_val" in captured.out


def test_cli_history_and_export(capsys):
    main(["record", "--command", "ls -l", "--exit", "0"])
    ret_list = main(["history", "list"])
    assert ret_list == 0

    ret_stats = main(["history", "stats"])
    assert ret_stats == 0

    # Flush output from prior commands
    capsys.readouterr()

    ret_export = main(["data", "export"])
    assert ret_export == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "command_events" in data

    ret_clear = main(["history", "clear"])
    assert ret_clear == 0


def test_cli_doctor(capsys):
    ret = main(["doctor"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Diagnostics" in captured.out
    assert "SQLite database" in captured.out


def test_cli_shell_init(capsys):
    ret = main(["shell", "init", "bash"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "_ai_bash_completion" in captured.out
