"""
Smart suggestion generator for the current terminal context.
Generates up to 5 explainable suggestions based on project manifests, git status, and history.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from ai_terminal.models import Suggestion, ProjectContext, RiskLevel
from ai_terminal.context.detector import ProjectDetector
from ai_terminal.safety.classifier import RiskClassifier
from ai_terminal.storage.repository import Repository


class ContextSuggester:
    def __init__(self, repository: Optional[Repository] = None):
        self.repo = repository
        self.detector = ProjectDetector(repository)

    def suggest(self, cwd: Optional[Path] = None, max_suggestions: int = 5) -> List[Suggestion]:
        path = cwd or Path.cwd()
        ctx = self.detector.detect(path)
        suggestions: List[Suggestion] = []
        seen_cmds = set()

        def add_sugg(cmd: str, reason: str, score: float, source: str = "context"):
            cmd = cmd.strip()
            if not cmd or cmd in seen_cmds:
                return
            risk, _ = RiskClassifier.classify(cmd)
            if risk == RiskLevel.BLOCKED:
                return
            seen_cmds.add(cmd)
            suggestions.append(
                Suggestion(
                    command=cmd,
                    reason=reason,
                    score=score,
                    risk=risk,
                    source=source,
                )
            )

        # 1. Project Manifest Suggestions
        # Node / NPM
        if "node" in ctx.kinds:
            if "dev" in ctx.npm_scripts:
                add_sugg("npm run dev", "Found scripts.dev in package.json", 95.0, "manifest")
            if "test" in ctx.npm_scripts:
                add_sugg("npm test", "Found scripts.test in package.json", 90.0, "manifest")
            if "start" in ctx.npm_scripts and "dev" not in ctx.npm_scripts:
                add_sugg("npm start", "Found scripts.start in package.json", 88.0, "manifest")
            if "build" in ctx.npm_scripts:
                add_sugg("npm run build", "Found scripts.build in package.json", 85.0, "manifest")
            if "lint" in ctx.npm_scripts:
                add_sugg("npm run lint", "Found scripts.lint in package.json", 80.0, "manifest")

        # Python
        if "python" in ctx.kinds:
            if "pytest" in ctx.python_tools:
                add_sugg("pytest", "Found pytest configuration", 92.0, "manifest")
            if "ruff" in ctx.python_tools:
                add_sugg("ruff check", "Found ruff linter configuration", 88.0, "manifest")
            if "poetry" in ctx.python_tools:
                add_sugg("poetry run python main.py", "Found poetry project", 80.0, "manifest")

        # Makefile
        if "make" in ctx.kinds:
            if "test" in ctx.make_targets:
                add_sugg("make test", "Found test target in Makefile", 90.0, "manifest")
            if "build" in ctx.make_targets:
                add_sugg("make build", "Found build target in Makefile", 89.0, "manifest")
            if "run" in ctx.make_targets:
                add_sugg("make run", "Found run target in Makefile", 88.0, "manifest")
            elif ctx.make_targets:
                first_target = ctx.make_targets[0]
                add_sugg(f"make {first_target}", f"Found {first_target} target in Makefile", 82.0, "manifest")

        # Rust
        if "rust" in ctx.kinds:
            add_sugg("cargo test", "Rust project detected", 90.0, "manifest")
            add_sugg("cargo run", "Rust project detected", 88.0, "manifest")

        # Go
        if "go" in ctx.kinds:
            add_sugg("go test ./...", "Go project detected", 90.0, "manifest")
            add_sugg("go run .", "Go project detected", 88.0, "manifest")

        # Docker
        if "docker" in ctx.kinds:
            facts = ctx.facts.get("docker", {})
            if facts.get("has_compose"):
                add_sugg("docker compose up", "Found compose configuration", 86.0, "manifest")
            elif facts.get("has_dockerfile"):
                add_sugg("docker build -t app .", "Found Dockerfile", 84.0, "manifest")

        # 2. Git Status Suggestions
        if "git" in ctx.kinds:
            if ctx.git_dirty:
                add_sugg("git status", "Repository has modified or untracked files", 94.0, "git")
                add_sugg("git diff", "Inspect uncommitted changes", 89.0, "git")
            git_info = ctx.facts.get("git", {})
            if git_info.get("ahead", 0) > 0:
                add_sugg("git push", f"Local branch is {git_info['ahead']} commit(s) ahead", 91.0, "git")
            if git_info.get("behind", 0) > 0:
                add_sugg("git pull", f"Remote has {git_info['behind']} commit(s) to fetch", 91.0, "git")

        # 3. Local History Suggestions
        if self.repo:
            history_rows = self.repo.get_recent_and_frequent_commands(str(path), limit=15)
            for row in history_rows:
                cmd = row["command"]
                freq = row["frequency"]
                if freq >= 2:
                    score = min(87.0, 70.0 + (freq * 2.5))
                    add_sugg(cmd, f"Frequently run in this directory ({freq}x)", score, "history")
                elif not suggestions:
                    add_sugg(cmd, "Recently run command", 65.0, "history")

        # Sort suggestions by score DESC
        suggestions.sort(key=lambda s: -s.score)

        return suggestions[:max_suggestions]
