"""
Completion pipeline coordinator.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate, RiskLevel
from ai_terminal.completion.tokenizer import parse_shell_buffer
from ai_terminal.completion.adapters import (
    BaseCompletionAdapter,
    GitAdapter,
    NpmAdapter,
    PipAdapter,
    DockerAdapter,
    MakeAdapter,
    FilesystemAdapter,
    InstalledCommandsAdapter,
)
from ai_terminal.context.detector import ProjectDetector
from ai_terminal.ranking.ranker import Ranker
from ai_terminal.storage.repository import Repository


class CompletionEngine:
    def __init__(self, repository: Optional[Repository] = None):
        self.repo = repository
        self.detector = ProjectDetector(repository)
        self.ranker = Ranker(repository)
        self.adapters: List[BaseCompletionAdapter] = [
            GitAdapter(),
            NpmAdapter(),
            PipAdapter(),
            DockerAdapter(),
            MakeAdapter(),
            InstalledCommandsAdapter(),
            FilesystemAdapter(),
        ]

    def complete(
        self,
        buffer: str,
        cursor: Optional[int] = None,
        cwd: Optional[Path] = None,
        shell: str = "bash",
    ) -> List[Candidate]:
        path = cwd or Path.cwd()
        parsed = parse_shell_buffer(buffer, cursor)
        ctx = self.detector.detect(path)

        candidates: List[Candidate] = []

        # 1. Run relevant adapters
        for adapter in self.adapters:
            if adapter.can_handle(parsed, ctx):
                cands = adapter.complete(parsed, ctx)
                if cands:
                    candidates.extend(cands)

        # 2. Add history matches if relevant
        history_map: Dict[str, Dict[str, Any]] = {}
        if self.repo:
            history_rows = self.repo.get_recent_and_frequent_commands(str(path), limit=25)
            for row in history_rows:
                cmd = row["command"]
                history_map[cmd] = row
                if parsed.active_token and cmd.startswith(parsed.active_token):
                    candidates.append(
                        Candidate(
                            value=cmd,
                            display=cmd,
                            description=f"history (used {row['frequency']}x)",
                            source="history",
                            score=75.0,
                            risk=RiskLevel.LOW,
                        )
                    )

        # 3. Deterministic weighted ranking
        ranked = self.ranker.rank(candidates, parsed, ctx, history_map)
        return ranked

    def format_for_shell(self, candidates: List[Candidate], shell: str = "bash") -> str:
        """
        Formats candidates for native Bash COMPREPLY or Zsh completion.
        """
        if not candidates:
            return ""

        if shell == "zsh":
            # For zsh compadd, formatting lines as 'value:description' allows descriptive completion
            lines = []
            for c in candidates:
                desc = c.description.replace(":", " - ") if c.description else ""
                lines.append(f"{c.value}:{desc}")
            return "\n".join(lines)
        else:
            # Bash completion expects values separated by newline
            return "\n".join(c.value for c in candidates)
