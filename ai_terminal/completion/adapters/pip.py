"""
Pip completion adapter.
"""

from typing import List
from ai_terminal.completion.adapters.base import BaseCompletionAdapter
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate, RiskLevel

PIP_SUBCOMMANDS = [
    ("install", "Install packages"),
    ("uninstall", "Uninstall packages"),
    ("freeze", "Output installed packages in requirements format"),
    ("list", "List installed packages"),
    ("show", "Show information about installed packages"),
    ("check", "Verify installed packages have compatible dependencies"),
    ("cache", "Inspect and manage pip's wheel cache"),
    ("config", "Manage local and global configuration"),
    ("wheel", "Build wheels from your requirements"),
    ("download", "Download packages without installing"),
]

PIP_OPTIONS = [
    ("-r", "Install from the given requirements file"),
    ("-e", "Install a project in editable mode"),
    ("-U", "Upgrade all specified packages to newest available"),
    ("--upgrade", "Upgrade all specified packages to newest available"),
    ("--no-deps", "Do not install package dependencies"),
    ("--user", "Install to Python user install directory"),
    ("--dry-run", "Don't actually install or change anything"),
]


class PipAdapter(BaseCompletionAdapter):
    name = "pip_adapter"

    def can_handle(self, parsed: ParsedBuffer, ctx: ProjectContext) -> bool:
        return parsed.command_name in ("pip", "pip3")

    def complete(self, parsed: ParsedBuffer, ctx: ProjectContext) -> List[Candidate]:
        candidates: List[Candidate] = []
        token = parsed.active_token
        index = parsed.active_token_index

        if index == 1 and not token.startswith("-"):
            for cmd, desc in PIP_SUBCOMMANDS:
                if cmd.startswith(token):
                    candidates.append(
                        Candidate(
                            value=cmd,
                            display=cmd,
                            description=desc,
                            source=self.name,
                            score=90.0,
                            risk=RiskLevel.LOW,
                        )
                    )
            return candidates

        if token.startswith("-"):
            for opt, desc in PIP_OPTIONS:
                if opt.startswith(token):
                    candidates.append(
                        Candidate(
                            value=opt,
                            display=opt,
                            description=desc,
                            source=self.name,
                            score=85.0,
                        )
                    )

        return candidates
