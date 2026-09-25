"""
Interactive terminal selection and action prompts using Rich and prompt_toolkit.
"""

import sys
from typing import Optional, Tuple
from ai_terminal.models import Suggestion, RiskLevel
from ai_terminal.safety.classifier import RiskClassifier
from ai_terminal.ui.formatter import console

try:
    from prompt_toolkit import prompt as pt_prompt
except ImportError:
    pt_prompt = None


def select_suggestion_interactive(suggestions: list[Suggestion]) -> Optional[Suggestion]:
    if not suggestions:
        return None

    count = len(suggestions)
    prompt_str = f"Select [1–{count}, q]: "

    try:
        choice = input(prompt_str).strip()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[dim]Cancelled.[/dim]")
        return None

    if choice.lower() in ("q", "quit", "cancel"):
        return None

    try:
        idx = int(choice)
        if 1 <= idx <= count:
            return suggestions[idx - 1]
    except ValueError:
        pass

    console.print("[yellow]Invalid selection. Cancelled.[/yellow]")
    return None


def prompt_action_menu(command: str, allow_run: bool = True) -> Tuple[str, str]:
    """
    Prompts user with options: [Enter] insert, [r] run, [e] edit, [q] cancel.
    Returns: (action, final_command)
    action: "insert" | "run" | "cancel"
    """
    curr_cmd = command

    while True:
        if allow_run:
            menu_str = "[Enter] insert  [r] run  [e] edit  [q] cancel"
        else:
            menu_str = "[Enter] insert  [e] edit  [q] cancel"

        console.print(f"[bold dim]{menu_str}[/bold dim]")
        try:
            choice = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Cancelled.[/dim]")
            return "cancel", curr_cmd

        if choice == "" or choice == "insert":
            return "insert", curr_cmd

        elif choice in ("q", "cancel", "quit"):
            return "cancel", curr_cmd

        elif choice in ("e", "edit"):
            # Prompt user to edit command
            edited = prompt_edit_line(curr_cmd)
            if edited is not None:
                curr_cmd = edited.strip()
                console.print(f"[bold]Updated command:[/bold] [bold cyan]{curr_cmd}[/bold cyan]")
            continue

        elif choice in ("r", "run") and allow_run:
            risk, reason = RiskClassifier.classify(curr_cmd)
            if risk == RiskLevel.BLOCKED:
                console.print(f"[bold red]BLOCKED: Cannot run command ({reason}). Edit the command first.[/bold red]")
                continue

            if risk == RiskLevel.HIGH:
                console.print(f"[bold red]WARNING: High-risk command detected ({reason}).[/bold red]")
                try:
                    conf = input("Are you sure you want to execute? Type 'yes' to proceed: ").strip()
                except (EOFError, KeyboardInterrupt):
                    return "cancel", curr_cmd

                if conf.lower() == "yes":
                    return "run", curr_cmd
                else:
                    console.print("[dim]Execution cancelled.[/dim]")
                    continue
            else:
                # Low or medium risk confirmation
                try:
                    conf = input("Execute command? [y/N]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    return "cancel", curr_cmd

                if conf in ("y", "yes"):
                    return "run", curr_cmd
                else:
                    console.print("[dim]Execution cancelled.[/dim]")
                    continue

        else:
            console.print("[dim]Unrecognized option. Press Enter to insert, 'e' to edit, or 'q' to cancel.[/dim]")


def prompt_edit_line(initial_text: str) -> Optional[str]:
    """
    Allows the user to edit a command line with full terminal line editing support.
    """
    try:
        if pt_prompt is not None:
            return pt_prompt("Edit command: ", default=initial_text)
        else:
            console.print(f"Current: {initial_text}")
            new_text = input("New command (leave blank to keep): ").strip()
            return new_text if new_text else initial_text
    except (EOFError, KeyboardInterrupt):
        return None
