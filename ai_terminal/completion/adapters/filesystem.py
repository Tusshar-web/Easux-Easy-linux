"""
Filesystem path completion adapter.
"""

import os
from pathlib import Path
from typing import List
from ai_terminal.completion.adapters.base import BaseCompletionAdapter
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate, TokenType, RiskLevel


class FilesystemAdapter(BaseCompletionAdapter):
    name = "filesystem"

    def can_handle(self, parsed: ParsedBuffer, ctx: ProjectContext) -> bool:
        # Matches when token looks like a path or when token_type is PATH_LIKE or POSITIONAL
        if parsed.token_type == TokenType.PATH_LIKE:
            return True
        if parsed.active_token_index > 0:
            return True
        return False

    def complete(self, parsed: ParsedBuffer, ctx: ProjectContext) -> List[Candidate]:
        candidates: List[Candidate] = []
        token = parsed.active_token

        # Determine target search directory and file prefix
        show_hidden = False
        try:
            if "/" in token:
                dir_part, file_prefix = token.rsplit("/", 1)
                show_hidden = file_prefix.startswith(".")

                if token.startswith("~"):
                    expanded = os.path.expanduser(dir_part)
                    search_dir = Path(expanded)
                elif token.startswith("/"):
                    search_dir = Path(dir_part if dir_part else "/")
                else:
                    search_dir = Path(ctx.root_dir) / dir_part
                prefix_lead = dir_part + "/"
            else:
                search_dir = Path(ctx.root_dir)
                file_prefix = token
                show_hidden = token.startswith(".")
                prefix_lead = ""

            if not search_dir.is_dir():
                return []

            with os.scandir(search_dir) as it:
                for entry in it:
                    name = entry.name
                    if not show_hidden and name.startswith("."):
                        continue
                    if name.startswith(file_prefix):
                        is_dir = entry.is_dir()
                        completion_val = f"{prefix_lead}{name}{'/' if is_dir else ''}"
                        display_val = f"{name}{'/' if is_dir else ''}"
                        desc = "directory" if is_dir else "file"
                        candidates.append(
                            Candidate(
                                value=completion_val,
                                display=display_val,
                                description=desc,
                                source=self.name,
                                score=75.0 if is_dir else 70.0,
                                risk=RiskLevel.LOW,
                            )
                        )
                        if len(candidates) >= 50:
                            break
        except Exception:
            return []

        return candidates
