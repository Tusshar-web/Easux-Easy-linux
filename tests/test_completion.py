"""
Tests for autocomplete engine and adapters.
"""

from pathlib import Path
from ai_terminal.completion.engine import CompletionEngine
from ai_terminal.models import ProjectContext, ParsedBuffer, TokenType


def test_git_subcommand_completion(temp_repo):
    engine = CompletionEngine(temp_repo)
    candidates = engine.complete(buffer="git che", cursor=7, shell="bash")
    values = [c.value for c in candidates]

    assert "checkout" in values
    assert "cherry" in values
    assert "cherry-pick" in values
    assert not any(v.startswith("commit") for v in values)


def test_git_option_completion(temp_repo):
    engine = CompletionEngine(temp_repo)
    candidates = engine.complete(buffer="git commit -m", cursor=13, shell="bash")
    values = [c.value for c in candidates]
    assert "-m" in values


def test_npm_script_completion(temp_repo, temp_dir):
    pkg_file = temp_dir / "package.json"
    pkg_file.write_text('{"scripts": {"dev": "vite", "build": "vite build", "test": "vitest"}}')

    engine = CompletionEngine(temp_repo)
    candidates = engine.complete(buffer="npm run d", cursor=9, cwd=temp_dir, shell="bash")
    values = [c.value for c in candidates]
    assert "dev" in values


def test_make_target_completion(temp_repo, temp_dir):
    makefile = temp_dir / "Makefile"
    makefile.write_text("build:\n\techo build\n\ntest:\n\techo test\n")

    engine = CompletionEngine(temp_repo)
    candidates = engine.complete(buffer="make t", cursor=6, cwd=temp_dir, shell="bash")
    values = [c.value for c in candidates]
    assert "test" in values


def test_filesystem_completion(temp_repo, temp_dir):
    (temp_dir / "alpha.txt").touch()
    (temp_dir / "beta.py").touch()
    (temp_dir / "docs").mkdir()

    engine = CompletionEngine(temp_repo)
    candidates = engine.complete(buffer="cat al", cursor=6, cwd=temp_dir, shell="bash")
    values = [c.value for c in candidates]
    assert "alpha.txt" in values


def test_shell_formatting(temp_repo):
    engine = CompletionEngine(temp_repo)
    candidates = engine.complete(buffer="git che", cursor=7, shell="bash")

    bash_fmt = engine.format_for_shell(candidates, shell="bash")
    assert "checkout" in bash_fmt
    assert "\n" in bash_fmt

    zsh_fmt = engine.format_for_shell(candidates, shell="zsh")
    assert "checkout:" in zsh_fmt
