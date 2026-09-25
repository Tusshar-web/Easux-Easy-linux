"""
Fast, bounded git repository context detector.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


def detect_git_status(cwd: Path, timeout_seconds: float = 0.08) -> Optional[Dict[str, Any]]:
    """
    Detects git repository branch, modified files, untracked files, and ahead/behind count.
    Strictly bounded by timeout.
    """
    try:
        # Check if inside git directory
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree", "--show-toplevel"],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout_seconds,
        )
        if res.returncode != 0:
            return None

        lines = res.stdout.strip().splitlines()
        if not lines or lines[0] != "true":
            return None
        repo_root = lines[1] if len(lines) > 1 else str(cwd)

        # Get branch and status in porcelain format
        status_res = subprocess.run(
            ["git", "status", "--porcelain=v1", "-b"],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout_seconds,
        )
        if status_res.returncode != 0:
            return {"root": repo_root, "branch": "unknown", "dirty": False, "modified": 0, "untracked": 0}

        status_lines = status_res.stdout.splitlines()
        branch_line = status_lines[0] if status_lines else ""
        branch = "unknown"
        ahead = 0
        behind = 0

        if branch_line.startswith("## "):
            branch_info = branch_line[3:].split("...")[0].strip()
            branch = branch_info
            if "[" in branch_line and "]" in branch_line:
                extra = branch_line[branch_line.find("[") + 1 : branch_line.find("]")]
                if "ahead" in extra:
                    for part in extra.split(","):
                        if "ahead" in part:
                            try:
                                ahead = int(part.replace("ahead", "").strip())
                            except ValueError:
                                pass
                if "behind" in extra:
                    for part in extra.split(","):
                        if "behind" in part:
                            try:
                                behind = int(part.replace("behind", "").strip())
                            except ValueError:
                                pass

        modified_count = 0
        untracked_count = 0
        for line in status_lines[1:]:
            if line.startswith("??"):
                untracked_count += 1
            elif line.strip():
                modified_count += 1

        return {
            "root": repo_root,
            "branch": branch,
            "dirty": (modified_count > 0 or untracked_count > 0),
            "modified": modified_count,
            "untracked": untracked_count,
            "ahead": ahead,
            "behind": behind,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
