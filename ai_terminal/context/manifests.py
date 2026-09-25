"""
Project manifest detectors for Node, Python, Make, Rust, Go, and Docker.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


def parse_package_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.is_file():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scripts = list(data.get("scripts", {}).keys())
        dependencies = list(data.get("dependencies", {}).keys())
        dev_dependencies = list(data.get("devDependencies", {}).keys())
        return {
            "name": data.get("name", ""),
            "scripts": scripts,
            "has_typescript": "typescript" in dependencies or "typescript" in dev_dependencies,
            "package_manager": "yarn" if (path.parent / "yarn.lock").exists() else ("pnpm" if (path.parent / "pnpm-lock.yaml").exists() else "npm"),
        }
    except Exception:
        return None


def parse_makefile(path: Path) -> Optional[List[str]]:
    try:
        if not path.is_file():
            return None
        targets = []
        target_regex = re.compile(r"^([a-zA-Z0-9_\-\.]+)\s*:(?!=)")
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith(("#", "\t", " ")):
                    continue
                match = target_regex.match(line)
                if match:
                    target = match.group(1)
                    if not target.startswith("."):
                        targets.append(target)
        return targets[:30]
    except Exception:
        return None


def parse_python_project(root: Path) -> Optional[Dict[str, Any]]:
    tools = []
    pyproject = root / "pyproject.toml"
    setup_py = root / "setup.py"
    reqs = root / "requirements.txt"
    pipfile = root / "Pipfile"

    if not (pyproject.exists() or setup_py.exists() or reqs.exists() or pipfile.exists()):
        return None

    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            if "tool.pytest" in content or "pytest" in content:
                tools.append("pytest")
            if "tool.ruff" in content or "ruff" in content:
                tools.append("ruff")
            if "tool.poetry" in content:
                tools.append("poetry")
            if "tool.uv" in content:
                tools.append("uv")
            if "tool.black" in content:
                tools.append("black")
            if "tool.mypy" in content:
                tools.append("mypy")
        except Exception:
            pass

    if reqs.exists() and not tools:
        try:
            content = reqs.read_text(encoding="utf-8", errors="ignore")
            if "pytest" in content:
                tools.append("pytest")
            if "django" in content.lower():
                tools.append("django")
            if "flask" in content.lower():
                tools.append("flask")
            if "fastapi" in content.lower():
                tools.append("fastapi")
        except Exception:
            pass

    return {
        "tools": list(set(tools)),
        "has_pyproject": pyproject.exists(),
        "has_setup_py": setup_py.exists(),
        "has_requirements": reqs.exists(),
    }


def parse_cargo_project(root: Path) -> Optional[Dict[str, Any]]:
    cargo_toml = root / "Cargo.toml"
    if cargo_toml.exists():
        return {"type": "rust"}
    return None


def parse_go_project(root: Path) -> Optional[Dict[str, Any]]:
    go_mod = root / "go.mod"
    if go_mod.exists():
        return {"type": "go"}
    return None


def parse_docker_project(root: Path) -> Optional[Dict[str, Any]]:
    dockerfile = root / "Dockerfile"
    compose1 = root / "docker-compose.yml"
    compose2 = root / "compose.yaml"
    if dockerfile.exists() or compose1.exists() or compose2.exists():
        return {
            "has_dockerfile": dockerfile.exists(),
            "has_compose": compose1.exists() or compose2.exists(),
        }
    return None
