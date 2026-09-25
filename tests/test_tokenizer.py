"""
Tests for tokenizer and token classification.
"""

from ai_terminal.completion.tokenizer import parse_shell_buffer
from ai_terminal.models import TokenType


def test_first_command_token():
    parsed = parse_shell_buffer("git")
    assert parsed.token_type == TokenType.FIRST_COMMAND
    assert parsed.active_token == "git"
    assert parsed.active_token_index == 0


def test_known_subcommand():
    parsed = parse_shell_buffer("git che", 7)
    assert parsed.command_name == "git"
    assert parsed.active_token == "che"
    assert parsed.active_token_index == 1
    assert parsed.token_type == TokenType.KNOWN_SUBCOMMAND


def test_option_token():
    parsed = parse_shell_buffer("git commit -m")
    assert parsed.active_token == "-m"
    assert parsed.token_type == TokenType.OPTION


def test_path_like_token():
    parsed = parse_shell_buffer("cat ./src/main")
    assert parsed.active_token == "./src/main"
    assert parsed.token_type == TokenType.PATH_LIKE

    parsed_root = parse_shell_buffer("ls /etc/")
    assert parsed_root.token_type == TokenType.PATH_LIKE


def test_quoted_token():
    parsed = parse_shell_buffer('git commit -m "initial commit')
    assert parsed.token_type == TokenType.QUOTED_OR_ESCAPED


def test_trailing_space_starts_new_token():
    parsed = parse_shell_buffer("npm run ")
    assert parsed.active_token == ""
    assert parsed.active_token_index == 2
    assert parsed.command_name == "npm"
    assert parsed.subcommand == "run"
