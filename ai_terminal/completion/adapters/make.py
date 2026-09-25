"""
Make command completion adapter.
"""

from typing import List
from ai_terminal.completion.adapters.base import BaseCompletionAdapter
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate, RiskLevel

MAKE_FLAGS = [
    ("-j", "Execute N jobs in parallel"),
    ("-f", "Read FILE as a makefile"),
    ("-C", "Change to DIRECTORY before doing anything"),
    ("-n", "Print the commands that would be executed, but do not execute them"),
    ("-B", "Unconditionally make all targets"),
    ("--dry-run", "Print commands without running them"),
]


class MakeAdapter(BaseCompletionAdapter):
    name = "make_adapter"

    def can_handle(self, parsed: ParsedBuffer, ctx: ProjectContext) -> bool:
        return parsed.command_name == "make"

    def complete(self, parsed: ParsedBuffer, ctx: ProjectContext) -> List[Candidate]:
        candidates: List[Candidate] = []
        token = parsed.active_token

        if token.startswith("-"):
            for flag, desc in MAKE_FLAGS:
                if flag.startswith(token):
                    candidates.append(
                        Candidate(
                            value=flag,
                            display=flag,
                            description=desc,
                            source=self.name,
                            score=80.0,
                        )
                    )
            return candidates

        for target in ctx.make_targets:
            if target.startswith(token):
                candidates.append(
                    Candidate(
                        value=target,
                        display=target,
                        description="Makefile target",
                        source=self.name,
                        score=92.0,
                        risk=RiskLevel.LOW,
                    )
                )

        return candidates
