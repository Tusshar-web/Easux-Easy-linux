"""
Git command completion adapter.
"""

from typing import List
from ai_terminal.completion.adapters.base import BaseCompletionAdapter
from ai_terminal.models import ParsedBuffer, ProjectContext, Candidate, RiskLevel

GIT_SUBCOMMANDS = [
    ("checkout", "Switch branches or restore working tree files"),
    ("cherry-pick", "Apply the changes introduced by some existing commits"),
    ("cherry", "Find commits yet to be applied to upstream"),
    ("commit", "Record changes to the repository"),
    ("branch", "List, create, or delete branches"),
    ("status", "Show the working tree status"),
    ("diff", "Show changes between commits, commit and working tree"),
    ("log", "Show commit logs"),
    ("push", "Update remote refs along with associated objects"),
    ("pull", "Fetch from and integrate with another repository or local branch"),
    ("merge", "Join two or more development histories together"),
    ("rebase", "Reapply commits on top of another base tip"),
    ("add", "Add file contents to the index"),
    ("reset", "Reset current HEAD to the specified state"),
    ("restore", "Restore working tree files"),
    ("switch", "Switch branches"),
    ("clone", "Clone a repository into a new directory"),
    ("fetch", "Download objects and refs from another repository"),
    ("stash", "Stash the changes in a dirty working directory away"),
    ("tag", "Create, list, delete or verify a tag object"),
    ("remote", "Manage set of tracked repositories"),
]

GIT_OPTIONS = {
    "commit": [
        ("-m", "Use the given message as the commit message"),
        ("--amend", "Amend previous commit"),
        ("-a", "Automatically stage files that have been modified and deleted"),
        ("--no-edit", "Use the selected commit message without editing"),
    ],
    "push": [
        ("-u", "Set upstream for git pull/status"),
        ("--set-upstream", "Set upstream for git pull/status"),
        ("--dry-run", "Do everything except actually send the updates"),
        ("--force-with-lease", "Safer force push ensuring remote ref hasn't changed"),
        ("-f", "Force update remote refs (destructive)"),
    ],
    "pull": [
        ("--rebase", "Rebase current branch on top of upstream branch"),
        ("--no-rebase", "Merge upstream branch into current branch"),
        ("--ff-only", "Refuse to merge and exit with a non-zero status unless fast-forward"),
    ],
    "checkout": [
        ("-b", "Create and switch to a new branch"),
        ("-B", "Create/reset and switch to a branch"),
    ],
    "switch": [
        ("-c", "Create and switch to a new branch"),
    ],
    "branch": [
        ("-a", "List both remote-tracking and local branches"),
        ("-d", "Delete a branch (safe)"),
        ("-D", "Force delete a branch"),
        ("-m", "Move/rename a branch"),
    ],
    "diff": [
        ("--staged", "Show changes staged for commit"),
        ("--cached", "Synonym for --staged"),
        ("--stat", "Show diffstat instead of patch"),
    ],
    "status": [
        ("-s", "Give output in short format"),
        ("--short", "Give output in short format"),
        ("-b", "Show branch and tracking info even in short-format"),
    ],
}


class GitAdapter(BaseCompletionAdapter):
    name = "git_adapter"

    def can_handle(self, parsed: ParsedBuffer, ctx: ProjectContext) -> bool:
        return parsed.command_name == "git"

    def complete(self, parsed: ParsedBuffer, ctx: ProjectContext) -> List[Candidate]:
        candidates: List[Candidate] = []
        token = parsed.active_token
        index = parsed.active_token_index

        # Completing git subcommand: e.g. "git che<Tab>"
        if index == 1 and not token.startswith("-"):
            for cmd, desc in GIT_SUBCOMMANDS:
                if cmd.startswith(token):
                    candidates.append(
                        Candidate(
                            value=cmd,
                            display=cmd,
                            description=desc,
                            source=self.name,
                            score=90.0 if cmd.startswith(token) else 50.0,
                            risk=RiskLevel.LOW,
                        )
                    )
            return candidates

        subcmd = parsed.subcommand

        # Completing option: e.g. "git commit --am<Tab>"
        if token.startswith("-") and subcmd in GIT_OPTIONS:
            for opt, desc in GIT_OPTIONS[subcmd]:
                if opt.startswith(token):
                    risk = RiskLevel.HIGH if opt in ("-f", "--force", "-D") else RiskLevel.LOW
                    candidates.append(
                        Candidate(
                            value=opt,
                            display=opt,
                            description=desc,
                            source=self.name,
                            score=85.0,
                            risk=risk,
                        )
                    )
            return candidates

        # Branch completion for checkout / switch / merge
        if subcmd in ("checkout", "switch", "merge", "rebase") and not token.startswith("-"):
            if ctx.git_branch and ctx.git_branch.startswith(token) and ctx.git_branch != token:
                candidates.append(
                    Candidate(
                        value=ctx.git_branch,
                        display=ctx.git_branch,
                        description="Current branch",
                        source=self.name,
                        score=80.0,
                    )
                )

        return candidates
