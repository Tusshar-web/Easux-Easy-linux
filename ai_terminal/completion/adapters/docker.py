"""
Docker completion adapter.
"""

from typing import List
from ai_terminal.completion.adapters.base import BaseCompletionAdapter
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate, RiskLevel

DOCKER_SUBCOMMANDS = [
    ("run", "Run a command in a new container"),
    ("exec", "Run a command in a running container"),
    ("ps", "List containers"),
    ("build", "Build an image from a Dockerfile"),
    ("images", "List images"),
    ("pull", "Download an image from a registry"),
    ("push", "Upload an image to a registry"),
    ("stop", "Stop one or more running containers"),
    ("start", "Start one or more stopped containers"),
    ("restart", "Restart one or more containers"),
    ("rm", "Remove one or more containers"),
    ("rmi", "Remove one or more images"),
    ("logs", "Fetch the logs of a container"),
    ("compose", "Docker Compose multi-container application"),
    ("system", "Manage Docker system resources"),
]

DOCKER_OPTIONS = [
    ("-d", "Run container in background and print container ID"),
    ("-p", "Publish a container's port(s) to the host"),
    ("-v", "Bind mount a volume"),
    ("-it", "Allocate a pseudo-TTY connected to container's stdin"),
    ("--rm", "Automatically remove the container when it exits"),
    ("--name", "Assign a name to the container"),
    ("-e", "Set environment variables"),
]


class DockerAdapter(BaseCompletionAdapter):
    name = "docker_adapter"

    def can_handle(self, parsed: ParsedBuffer, ctx: ProjectContext) -> bool:
        return parsed.command_name == "docker"

    def complete(self, parsed: ParsedBuffer, ctx: ProjectContext) -> List[Candidate]:
        candidates: List[Candidate] = []
        token = parsed.active_token
        index = parsed.active_token_index

        if index == 1 and not token.startswith("-"):
            for cmd, desc in DOCKER_SUBCOMMANDS:
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
            for opt, desc in DOCKER_OPTIONS:
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
