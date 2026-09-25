"""
Coordinator for lightweight, fast project context detection.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from ai_terminal.models import ProjectContext
from ai_terminal.context.git import detect_git_status
from ai_terminal.context.manifests import (
    parse_package_json,
    parse_makefile,
    parse_python_project,
    parse_cargo_project,
    parse_go_project,
    parse_docker_project,
)
from ai_terminal.storage.repository import Repository


class ProjectDetector:
    def __init__(self, repository: Optional[Repository] = None):
        self.repo = repository

    def detect(self, cwd: Optional[Path] = None, use_cache: bool = True) -> ProjectContext:
        path = cwd or Path.cwd()
        try:
            path = path.resolve()
        except OSError:
            pass

        kinds: List[str] = []
        facts: Dict[str, Any] = {}
        npm_scripts: List[str] = []
        make_targets: List[str] = []
        python_tools: List[str] = []
        git_branch: Optional[str] = None
        git_dirty = False
        git_modified = 0
        git_untracked = 0

        # Check cache if repository available
        if use_cache and self.repo:
            cached = self.repo.get_cached_project(str(path), max_age_seconds=15)
            if cached:
                return ProjectContext(
                    root_dir=cached.get("root_dir", str(path)),
                    kinds=cached.get("kinds", []),
                    facts=cached.get("facts", {}),
                    git_branch=cached.get("git_branch"),
                    git_dirty=cached.get("git_dirty", False),
                    git_modified_files=cached.get("git_modified_files", 0),
                    git_untracked_files=cached.get("git_untracked_files", 0),
                    npm_scripts=cached.get("npm_scripts", []),
                    make_targets=cached.get("make_targets", []),
                    python_tools=cached.get("python_tools", []),
                )

        # 1. Git status
        git_info = detect_git_status(path, timeout_seconds=0.07)
        if git_info:
            kinds.append("git")
            git_branch = git_info.get("branch")
            git_dirty = git_info.get("dirty", False)
            git_modified = git_info.get("modified", 0)
            git_untracked = git_info.get("untracked", 0)
            facts["git"] = git_info

        # 2. Node.js
        pkg_json = parse_package_json(path / "package.json")
        if pkg_json:
            kinds.append("node")
            npm_scripts = pkg_json.get("scripts", [])
            facts["node"] = pkg_json

        # 3. Python
        py_info = parse_python_project(path)
        if py_info:
            kinds.append("python")
            python_tools = py_info.get("tools", [])
            facts["python"] = py_info

        # 4. Makefile
        makefile_targets = parse_makefile(path / "Makefile")
        if makefile_targets:
            kinds.append("make")
            make_targets = makefile_targets
            facts["make"] = {"targets": makefile_targets}

        # 5. Rust
        cargo = parse_cargo_project(path)
        if cargo:
            kinds.append("rust")
            facts["rust"] = cargo

        # 6. Go
        go = parse_go_project(path)
        if go:
            kinds.append("go")
            facts["go"] = go

        # 7. Docker
        docker = parse_docker_project(path)
        if docker:
            kinds.append("docker")
            facts["docker"] = docker

        ctx = ProjectContext(
            root_dir=str(path),
            kinds=kinds,
            facts=facts,
            git_branch=git_branch,
            git_dirty=git_dirty,
            git_modified_files=git_modified,
            git_untracked_files=git_untracked,
            npm_scripts=npm_scripts,
            make_targets=make_targets,
            python_tools=python_tools,
        )

        # Cache in repository
        if self.repo:
            self.repo.set_cached_project(
                root_path=str(path),
                kind=",".join(kinds),
                metadata={
                    "root_dir": str(path),
                    "kinds": kinds,
                    "facts": facts,
                    "git_branch": git_branch,
                    "git_dirty": git_dirty,
                    "git_modified_files": git_modified,
                    "git_untracked_files": git_untracked,
                    "npm_scripts": npm_scripts,
                    "make_targets": make_targets,
                    "python_tools": python_tools,
                },
            )

        return ctx
