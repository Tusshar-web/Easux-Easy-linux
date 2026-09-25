"""
NPM and Node.js completion adapter.
"""

from typing import List
from ai_terminal.completion.adapters.base import BaseCompletionAdapter
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate, RiskLevel

NPM_SUBCOMMANDS = [
    ("run", "Run arbitrary package scripts"),
    ("test", "Test a package"),
    ("start", "Start a package"),
    ("build", "Build a package"),
    ("install", "Install a package and dependencies"),
    ("uninstall", "Remove a package"),
    ("ci", "Install a project with a clean slate"),
    ("audit", "Run a security audit on dependencies"),
    ("init", "Create a package.json file"),
    ("publish", "Publish a package to registry"),
    ("list", "List installed packages"),
    ("update", "Update packages to latest versions"),
    ("outdated", "Check for outdated packages"),
]

NPM_OPTIONS = [
    ("--save", "Save package to dependencies"),
    ("--save-dev", "Save package to devDependencies"),
    ("-D", "Short for --save-dev"),
    ("--global", "Install package globally"),
    ("-g", "Short for --global"),
    ("--dry-run", "Report what would be done without modifying"),
]


class NpmAdapter(BaseCompletionAdapter):
    name = "npm_adapter"

    def can_handle(self, parsed: ParsedBuffer, ctx: ProjectContext) -> bool:
        return parsed.command_name in ("npm", "pnpm", "yarn")

    def complete(self, parsed: ParsedBuffer, ctx: ProjectContext) -> List[Candidate]:
        candidates: List[Candidate] = []
        token = parsed.active_token
        index = parsed.active_token_index
        subcmd = parsed.subcommand

        # Completing npm script after "run": e.g. "npm run dev"
        if subcmd == "run" and index >= 2 and not token.startswith("-"):
            for script in ctx.npm_scripts:
                if script.startswith(token):
                    candidates.append(
                        Candidate(
                            value=script,
                            display=script,
                            description="script in package.json",
                            source=self.name,
                            score=95.0,
                            risk=RiskLevel.LOW,
                        )
                    )
            return candidates

        # Completing subcommand: e.g. "npm run", "npm test"
        if index == 1 and not token.startswith("-"):
            # Also if the token matches a script directly, e.g. "npm test" or "npm start"
            for cmd, desc in NPM_SUBCOMMANDS:
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

        # Options
        if token.startswith("-"):
            for opt, desc in NPM_OPTIONS:
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
