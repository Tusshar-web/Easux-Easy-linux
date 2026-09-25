"""
Installed PATH executables completion adapter for first command token.
"""

import os
from typing import List, Set, Optional
from ai_terminal.completion.adapters.base import BaseCompletionAdapter
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate, TokenType, RiskLevel


_CACHED_BINARIES: Optional[Set[str]] = None


def get_installed_executables() -> Set[str]:
    global _CACHED_BINARIES
    if _CACHED_BINARIES is not None:
        return _CACHED_BINARIES

    executables: Set[str] = set()
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for p in path_dirs:
        if not p or not os.path.isdir(p):
            continue
        try:
            with os.scandir(p) as it:
                for entry in it:
                    if entry.is_file() and os.access(entry.path, os.X_OK):
                        executables.add(entry.name)
        except (PermissionError, OSError):
            continue

    _CACHED_BINARIES = executables
    return _CACHED_BINARIES


class InstalledCommandsAdapter(BaseCompletionAdapter):
    name = "installed_commands"

    def can_handle(self, parsed: ParsedBuffer, ctx: ProjectContext) -> bool:
        return parsed.token_type == TokenType.FIRST_COMMAND

    def complete(self, parsed: ParsedBuffer, ctx: ProjectContext) -> List[Candidate]:
        candidates: List[Candidate] = []
        token = parsed.active_token
        if not token:
            return []

        all_bins = get_installed_executables()
        matches = [b for b in all_bins if b.startswith(token)]

        for b in sorted(matches)[:40]:
            candidates.append(
                Candidate(
                    value=b,
                    display=b,
                    description="executable in PATH",
                    source=self.name,
                    score=80.0,
                    risk=RiskLevel.LOW,
                )
            )

        return candidates
