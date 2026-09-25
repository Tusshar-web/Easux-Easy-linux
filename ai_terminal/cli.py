"""
Main CLI Controller for ai-terminal.
Handles all subcommands and natural language queries.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from ai_terminal import __version__
from ai_terminal.models import RiskLevel, GenerateRequest
from ai_terminal.completion.engine import CompletionEngine
from ai_terminal.completion.suggester import ContextSuggester
from ai_terminal.llm.client import LLMClient
from ai_terminal.safety.classifier import RiskClassifier
from ai_terminal.safety.policy import SafetyPolicy
from ai_terminal.storage.database import Database
from ai_terminal.storage.repository import Repository
from ai_terminal.ui.formatter import (
    console,
    render_suggestions,
    render_generate_result,
    render_explain_result,
    render_fix_result,
    format_risk_badge,
)
from ai_terminal.ui.interactive import select_suggestion_interactive, prompt_action_menu
from ai_terminal.shell.installer import (
    get_init_script,
    install_hook,
    uninstall_hook,
    inspect_status,
)


def get_repo() -> Repository:
    return Repository()


def handle_complete(args: argparse.Namespace) -> int:
    """
    Subcommand: ai complete --shell <bash|zsh> --buffer <buffer> --cursor <cursor> [--json]
    """
    repo = get_repo()
    engine = CompletionEngine(repo)

    buffer = args.buffer or ""
    cursor = int(args.cursor) if args.cursor is not None else len(buffer)
    shell = args.shell.lower() if args.shell else "bash"

    candidates = engine.complete(buffer=buffer, cursor=cursor, shell=shell)

    if args.json:
        data = [c.to_dict() for c in candidates]
        print(json.dumps(data, indent=2))
        return 0

    formatted = engine.format_for_shell(candidates, shell=shell)
    if formatted:
        print(formatted)
    return 0


def handle_suggest(args: argparse.Namespace) -> int:
    """
    Subcommand: ai suggest [--json] [--shell-insert]
    """
    repo = get_repo()
    suggester = ContextSuggester(repo)
    suggestions = suggester.suggest(max_suggestions=5)

    if args.json:
        data = [s.to_dict() for s in suggestions]
        print(json.dumps(data, indent=2))
        return 0

    if not suggestions:
        if not args.shell_insert:
            console.print("[dim]No contextual suggestions found for this directory.[/dim]")
        return 0

    if args.shell_insert:
        # Non-interactive insert helper for shell keybinding
        top = suggestions[0]
        repo.mark_suggestion_accepted(top.command, source=top.source)
        print(top.command)
        return 0

    # Interactive selection
    render_suggestions(suggestions)
    if sys.stdin.isatty():
        selected = select_suggestion_interactive(suggestions)
        if selected:
            repo.mark_suggestion_accepted(selected.command, source=selected.source)
            console.print(f"[bold green]Inserted:[/bold green] [bold cyan]{selected.command}[/bold cyan]")
            # In shell integration, printing command allows wrapper to insert into buffer
            print(f"__AI_INSERT_BUFFER__:{selected.command}", file=sys.stderr)
    return 0


def handle_explain(args: argparse.Namespace) -> int:
    """
    Subcommand: ai explain <command...>
    Never executes the command!
    """
    command_str = " ".join(args.command)
    if not command_str.strip():
        console.print("[red]Error: Please supply a command to explain.[/red]")
        return 1

    repo = get_repo()
    client = LLMClient(repo)
    resp, privacy = client.explain(command_str)

    if not resp:
        console.print("[red]Could not generate explanation.[/red]")
        return 1

    if args.json:
        print(json.dumps(resp.to_dict(), indent=2))
        return 0

    render_explain_result(command_str, resp)
    return 0


def handle_fix(args: argparse.Namespace) -> int:
    """
    Subcommand: ai fix [--command <cmd>] [--error <err>] [--json]
    """
    repo = get_repo()
    latest_err = repo.get_latest_error()

    failed_cmd = args.command or (latest_err["command_hash"] if latest_err else "")
    err_text = args.error or (latest_err["stderr"] if latest_err else "")
    exit_code = latest_err["exit_code"] if latest_err else 1

    if not err_text and not failed_cmd:
        console.print("[yellow]No recent failed command recorded.[/yellow]")
        try:
            failed_cmd = input("Enter the failed command to diagnose: ").strip()
            if not failed_cmd:
                return 0
            err_text = input("Enter error message or output: ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0

    if sys.stdin.isatty() and not args.yes:
        try:
            choice = input("Send the redacted error excerpt to the configured LLM? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Cancelled.[/dim]")
            return 0

        if choice not in ("y", "yes"):
            console.print("[dim]Aborted by user.[/dim]")
            return 0

    client = LLMClient(repo)
    resp, _ = client.fix(failed_cmd=failed_cmd, exit_code=exit_code, stderr_excerpt=err_text)

    if not resp:
        console.print("[red]Could not determine repair proposal.[/red]")
        return 1

    if args.json:
        print(json.dumps(resp.to_dict(), indent=2))
        return 0

    render_fix_result(resp)

    if sys.stdin.isatty():
        action, final_cmd = prompt_action_menu(resp.next_command, allow_run=False)
        if action == "insert":
            console.print(f"[bold green]Inserted:[/bold green] [bold cyan]{final_cmd}[/bold cyan]")
            print(f"__AI_INSERT_BUFFER__:{final_cmd}", file=sys.stderr)
    return 0


def handle_record(args: argparse.Namespace) -> int:
    """
    Subcommand: ai record --command <cmd> --exit <code;> [--error <err>]
    Used by shell hooks to record post-command events and failures.
    """
    cmd = args.command or ""
    exit_code = args.exit
    cwd = str(Path.cwd())
    repo = get_repo()

    if cmd:
        repo.record_command(command=cmd, cwd=cwd, exit_code=exit_code)

    if exit_code != 0:
        err_msg = args.error or f"Command '{cmd}' exited with code {exit_code}"
        repo.record_error_event(command=cmd, exit_code=exit_code, stderr_redacted=err_msg)

    return 0


def handle_config(args: argparse.Namespace) -> int:
    repo = get_repo()
    action = args.config_action

    if action == "list" or not action:
        settings = repo.get_all_settings()
        console.print("[bold cyan]Current ai-terminal Configuration:[/bold cyan]")
        for k, v in sorted(settings.items()):
            console.print(f"  [bold]{k}[/bold] = {v}")
        return 0

    if action == "get":
        if not args.key:
            console.print("[red]Error: specify key to get[/red]")
            return 1
        val = repo.get_setting(args.key)
        console.print(f"{args.key} = {val}")
        return 0

    if action == "set":
        if not args.key or args.value is None:
            console.print("[red]Error: specify key and value to set[/red]")
            return 1
        repo.set_setting(args.key, args.value)
        console.print(f"[green]Updated[/green] {args.key} = {args.value}")
        return 0

    return 0


def handle_history(args: argparse.Namespace) -> int:
    repo = get_repo()
    action = args.history_action or "list"

    if action == "clear":
        res = repo.clear_all_data()
        console.print("[green]Cleared local history, error logs, and suggestion cache.[/green]")
        for k, v in res.items():
            console.print(f"  {k}: {v}")
        return 0

    if action == "stats":
        stats = repo.get_suggestion_stats()
        console.print("[bold cyan]Suggestion Statistics:[/bold cyan]")
        for k, v in stats.items():
            console.print(f"  {k}: {v}")
        return 0

    if action == "list":
        rows = repo.get_recent_and_frequent_commands(limit=20)
        if not rows:
            console.print("[dim]No command history recorded yet.[/dim]")
            return 0
        console.print("[bold cyan]Recent Command History:[/bold cyan]")
        for r in rows:
            console.print(f"  ({r['frequency']}x) {r['command']} [dim]last: {r['last_seen']}[/dim]")
        return 0

    return 0


def handle_data_export(args: argparse.Namespace) -> int:
    repo = get_repo()
    data = repo.export_data()
    print(json.dumps(data, indent=2))
    return 0


def handle_shell(args: argparse.Namespace) -> int:
    action = args.shell_action
    target_shell = (args.target_shell or "bash").lower()

    if action == "init":
        script = get_init_script(target_shell)
        if script:
            print(script)
            return 0
        else:
            console.print(f"[red]No init script found for shell: {target_shell}[/red]")
            return 1

    if action == "install":
        ok, msg = install_hook(target_shell)
        console.print(f"[{'green' if ok else 'red'}]{msg}[/{'green' if ok else 'red'}]")
        return 0 if ok else 1

    if action == "uninstall":
        ok, msg = uninstall_hook(target_shell)
        console.print(f"[{'green' if ok else 'red'}]{msg}[/{'green' if ok else 'red'}]")
        return 0 if ok else 1

    if action == "status":
        info = inspect_status(target_shell)
        console.print(f"[bold]Shell Integration Status ({target_shell}):[/bold]")
        console.print(f"  RC file: {info['rc_path']} (exists: {info['rc_exists']})")
        console.print(f"  Installed: {'[bold green]YES[/bold green]' if info['installed'] else '[dim]NO[/dim]'}")
        return 0

    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    """
    Subcommand: ai doctor
    Validates system requirements, database integrity, latency, and shell hooks.
    """
    console.print(f"[bold cyan]ai-terminal v{__version__} Diagnostics[/bold cyan]\n")

    # 1. Python version
    py_ver = sys.version.split()[0]
    console.print(f"  Python version: [green]{py_ver}[/green]")

    # 2. SQLite
    try:
        repo = get_repo()
        conn = repo.db.get_connection()
        conn.execute("SELECT 1").fetchone()
        console.print(f"  SQLite database: [green]OK[/green] ({repo.db.db_path})")
    except Exception as e:
        console.print(f"  SQLite database: [red]FAILED[/red] ({e})")

    # 3. Local completion latency benchmark (< 80 ms)
    engine = CompletionEngine(repo)
    t0 = time.perf_counter()
    candidates = engine.complete(buffer="git che", cursor=7, shell="bash")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    lat_status = "[green]PASS[/green]" if elapsed_ms < 80.0 else "[yellow]WARN[/yellow]"
    console.print(f"  Local completion latency: {lat_status} ({elapsed_ms:.2f} ms, target < 80 ms)")

    # 4. Shell hooks
    for sh in ("bash", "zsh"):
        st = inspect_status(sh)
        h_str = "[green]installed[/green]" if st["installed"] else "[dim]not installed[/dim]"
        console.print(f"  {sh.title()} hook: {h_str} in {st['rc_path']}")

    # 5. LLM Provider
    client = LLMClient(repo)
    prov_name = type(client.provider).__name__
    console.print(f"  LLM Provider: [bold]{prov_name}[/bold]")
    if prov_name == "OfflineHeuristicProvider":
        console.print("  [dim]Note: Set AI_TERMINAL_API_KEY to activate cloud LLM models.[/dim]")

    console.print("\n[bold green]System check complete.[/bold green]")
    return 0


def handle_natural_language(task: str, args: argparse.Namespace) -> int:
    """
    Handles natural language queries: ai <task...>
    e.g. ai find Python files modified in the last 7 days
    """
    repo = get_repo()
    client = LLMClient(repo)
    cwd = str(Path.cwd())

    # Detect context facts
    from ai_terminal.context.detector import ProjectDetector
    detector = ProjectDetector(repo)
    ctx = detector.detect(Path.cwd())
    facts = {"kinds": ctx.kinds, "git_branch": ctx.git_branch}

    resp, privacy_status = client.generate(task=task, cwd=cwd, project_facts=facts)
    if not resp:
        console.print("[red]Failed to generate command proposal.[/red]")
        return 1

    if args.json:
        print(json.dumps(resp.to_dict(), indent=2))
        return 0

    render_generate_result(resp)

    # Interactive flow
    if sys.stdin.isatty():
        action, final_cmd = prompt_action_menu(resp.command, allow_run=True)
        if action == "cancel":
            return 0
        elif action == "insert":
            console.print(f"[bold green]Inserted:[/bold green] [bold cyan]{final_cmd}[/bold cyan]")
            print(f"__AI_INSERT_BUFFER__:{final_cmd}", file=sys.stderr)
            repo.record_command(final_cmd, cwd=cwd, exit_code=0)
            return 0
        elif action == "run":
            console.print(f"[bold]Executing:[/bold] [bold cyan]{final_cmd}[/bold cyan]")
            res = subprocess.run(final_cmd, shell=True)
            repo.record_command(final_cmd, cwd=cwd, exit_code=res.returncode)
            return res.returncode
    else:
        # Piped stdout: output suggested command
        print(resp.command)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai",
        description="AI Enhanced Linux Terminal Assistant - Safe, fast command companion for Bash and Zsh.",
    )
    parser.add_argument("--version", action="version", version=f"ai-terminal {__version__}")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # ai complete
    p_comp = subparsers.add_parser("complete", help="Complete shell buffer tokens")
    p_comp.add_argument("--shell", default="bash", choices=["bash", "zsh"], help="Shell type")
    p_comp.add_argument("--buffer", required=True, help="Current shell buffer line")
    p_comp.add_argument("--cursor", type=int, help="Cursor position in buffer")
    p_comp.add_argument("--json", action="store_true", help="Output results in JSON format")

    # ai suggest
    p_sugg = subparsers.add_parser("suggest", help="Show context-aware command suggestions")
    p_sugg.add_argument("--shell-insert", action="store_true", help="Non-interactive output for shell keybinding")
    p_sugg.add_argument("--json", action="store_true", help="Output results in JSON format")

    # ai explain
    p_expl = subparsers.add_parser("explain", help="Explain a shell command without executing")
    p_expl.add_argument("--json", action="store_true", help="Output results in JSON format")
    p_expl.add_argument("command", nargs=argparse.REMAINDER, help="Shell command to explain")

    # ai fix
    p_fix = subparsers.add_parser("fix", help="Diagnose and propose fix for the last failed command")
    p_fix.add_argument("--command", help="Explicit failed command")
    p_fix.add_argument("--error", help="Explicit error message")
    p_fix.add_argument("-y", "--yes", action="store_true", help="Skip approval prompt")
    p_fix.add_argument("--json", action="store_true", help="Output results in JSON format")

    # ai record
    p_rec = subparsers.add_parser("record", help="Record command and exit code (called by shell hook)")
    p_rec.add_argument("--command", help="Executed command string")
    p_rec.add_argument("--exit", type=int, default=0, help="Command exit status")
    p_rec.add_argument("--error", help="Redacted stderr excerpt if failed")

    # ai config
    p_cfg = subparsers.add_parser("config", help="View or modify configuration")
    p_cfg.add_argument("config_action", nargs="?", choices=["list", "get", "set"], default="list")
    p_cfg.add_argument("key", nargs="?", help="Configuration key")
    p_cfg.add_argument("value", nargs="?", help="Configuration value")

    # ai history
    p_hist = subparsers.add_parser("history", help="Inspect or clear local history")
    p_hist.add_argument("history_action", nargs="?", choices=["list", "stats", "clear"], default="list")

    # ai data export
    p_data = subparsers.add_parser("data", help="Data management")
    p_data.add_argument("data_action", choices=["export"], help="Action to perform")

    # ai shell
    p_sh = subparsers.add_parser("shell", help="Manage shell integration hooks")
    p_sh.add_argument("shell_action", choices=["init", "install", "uninstall", "status"])
    p_sh.add_argument("target_shell", nargs="?", default="bash", choices=["bash", "zsh"])

    # ai doctor
    subparsers.add_parser("doctor", help="Run system diagnostics and verify performance")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args_list = argv if argv is not None else sys.argv[1:]

    KNOWN_SUBS = {"complete", "suggest", "explain", "fix", "record", "config", "history", "data", "shell", "doctor"}
    
    # Filter out flags to inspect positionals
    non_flags = [a for a in args_list if not a.startswith("-")]

    # If no subcommand is present among known subcommands and there are positional words, it's NL
    if non_flags and non_flags[0] not in KNOWN_SUBS:
        json_mode = "--json" in args_list
        clean_words = [a for a in args_list if not a.startswith("-")]
        task_str = " ".join(clean_words)
        dummy_args = argparse.Namespace(json=json_mode)
        return handle_natural_language(task_str, dummy_args)

    parser = build_parser()
    args = parser.parse_args(args_list)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "complete":
        return handle_complete(args)
    elif args.subcommand == "suggest":
        return handle_suggest(args)
    elif args.subcommand == "explain":
        return handle_explain(args)
    elif args.subcommand == "fix":
        return handle_fix(args)
    elif args.subcommand == "record":
        return handle_record(args)
    elif args.subcommand == "config":
        return handle_config(args)
    elif args.subcommand == "history":
        return handle_history(args)
    elif args.subcommand == "data":
        if args.data_action == "export":
            return handle_data_export(args)
    elif args.subcommand == "shell":
        return handle_shell(args)
    elif args.subcommand == "doctor":
        return handle_doctor(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
