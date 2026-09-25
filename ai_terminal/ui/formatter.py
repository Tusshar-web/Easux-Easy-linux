"""
Rich terminal formatting for commands, explanations, suggestions, and safety badges.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from ai_terminal.models import RiskLevel, Suggestion, GenerateResponse, ExplainResponse, FixResponse


console = Console()


def format_risk_badge(risk: RiskLevel) -> Text:
    if risk == RiskLevel.LOW:
        return Text("low", style="bold green")
    elif risk == RiskLevel.MEDIUM:
        return Text("medium", style="bold yellow")
    elif risk == RiskLevel.HIGH:
        return Text("high", style="bold red")
    elif risk == RiskLevel.BLOCKED:
        return Text("blocked", style="bold white on red")
    return Text(str(risk.value), style="bold")


def render_suggestions(suggestions: list[Suggestion]) -> None:
    if not suggestions:
        console.print("[dim]No suggestions available for current context.[/dim]")
        return

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Index", style="bold cyan", justify="right")
    table.add_column("Command", style="bold white")
    table.add_column("Reason", style="dim")
    table.add_column("Risk", justify="center")

    for i, s in enumerate(suggestions, 1):
        risk_badge = format_risk_badge(s.risk)
        table.add_row(f"{i}.", s.command, s.reason, risk_badge)

    console.print(table)


def render_generate_result(resp: GenerateResponse) -> None:
    risk_badge = format_risk_badge(resp.risk)

    console.print()
    console.print(f"[bold]Suggested command:[/bold] [bold cyan]{resp.command}[/bold cyan]")
    console.print(f"[bold]Why:[/bold] {resp.explanation}")
    if resp.assumptions:
        console.print(f"[bold]Assumptions:[/bold] [dim]{resp.assumptions}[/dim]")
    console.print(Text.assemble(("Risk: ", "bold"), risk_badge))

    if resp.alternatives:
        console.print(f"[bold]Alternatives:[/bold] [dim]{', '.join(resp.alternatives)}[/dim]")
    console.print()


def render_explain_result(command: str, resp: ExplainResponse) -> None:
    risk_badge = format_risk_badge(resp.risk)

    console.print()
    console.print(f"[bold]Command:[/bold] [bold cyan]{command}[/bold cyan]")
    console.print(f"[bold]Explanation:[/bold] {resp.explanation}")
    console.print(f"[bold]Effects:[/bold] [dim]{resp.effects}[/dim]")
    console.print(Text.assemble(("Risk: ", "bold"), risk_badge))
    if resp.safer_variant:
        console.print(f"[bold]Safer variant:[/bold] [green]{resp.safer_variant}[/green]")
    console.print()


def render_fix_result(resp: FixResponse) -> None:
    risk_badge = format_risk_badge(resp.risk)

    console.print()
    console.print(f"[bold]Likely cause:[/bold] {resp.diagnosis}")
    console.print(f"[bold]Safe next step:[/bold] [bold cyan]{resp.next_command}[/bold cyan]")
    risk_text = Text.assemble(("Risk: ", "bold"), risk_badge)
    if resp.questions:
        risk_text.append(f" — {resp.questions}")
    console.print(risk_text)
    console.print()
