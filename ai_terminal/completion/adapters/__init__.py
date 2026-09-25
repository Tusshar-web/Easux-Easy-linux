"""
Completion adapters package.
"""

from ai_terminal.completion.adapters.base import BaseCompletionAdapter
from ai_terminal.completion.adapters.git import GitAdapter
from ai_terminal.completion.adapters.npm import NpmAdapter
from ai_terminal.completion.adapters.pip import PipAdapter
from ai_terminal.completion.adapters.docker import DockerAdapter
from ai_terminal.completion.adapters.make import MakeAdapter
from ai_terminal.completion.adapters.filesystem import FilesystemAdapter
from ai_terminal.completion.adapters.installed import InstalledCommandsAdapter

__all__ = [
    "BaseCompletionAdapter",
    "GitAdapter",
    "NpmAdapter",
    "PipAdapter",
    "DockerAdapter",
    "MakeAdapter",
    "FilesystemAdapter",
    "InstalledCommandsAdapter",
]
