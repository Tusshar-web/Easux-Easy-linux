"""
Base interface for completion adapters.
"""

from abc import ABC, abstractmethod
from typing import List
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate


class BaseCompletionAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def can_handle(self, parsed: ParsedBuffer, ctx: ProjectContext) -> bool:
        """Determines if this adapter can generate candidates for the parsed buffer."""
        pass

    @abstractmethod
    def complete(self, parsed: ParsedBuffer, ctx: ProjectContext) -> List[Candidate]:
        """Generates a list of completion candidates."""
        pass
