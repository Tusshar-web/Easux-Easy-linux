"""
Command risk classification based on heuristics and security rules.
"""

import re
import shlex
from typing import Tuple, List, Optional
from ai_terminal.models import RiskLevel


# Blocked patterns: destructive placeholders, root deletes, fork bombs, disk overwrites
BLOCKED_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Fork bomb
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"), "Fork bomb detected"),
    # rm -rf / or rm -rf /*
    (re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?:\*|\s*$)"), "Dangerous root directory recursive deletion"),
    (re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+(?:~|\$HOME)(?:/\*|\s*$)"), "Dangerous home directory recursive deletion"),
    # Undefined fallback to root in deletion
    (re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+.*?\$\{.*?:-/(?:\*|\s*)\}?"), "Dangerous fallback to root path expansion"),
    # Raw disk overwrite via redirection
    (re.compile(r">\s*/dev/(?:sd[a-z]|nvme[0-9]n[0-9]|hd[a-z]|mapper/[a-zA-Z0-9_-]+)"), "Direct redirection to storage block device"),
    # Destructive placeholders: e.g. rm <path> or dd if=<target>
    (re.compile(r"(?i)\b(?:rm|dd|mkfs|chmod|chown)\b.*?(?:<[a-z0-9_-]+>|TODO|FIXME|REPLACE_ME)"), "Unsubstituted destructive placeholder detected"),
]

# High-risk patterns: sudo, rm -r, dd, mkfs, chmod -R, chown -R, device redirection, force-push
HIGH_RISK_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # rm recursive or force
    (re.compile(r"\brm\s+-[a-zA-Z]*[rf]"), "Recursive or forced file deletion"),
    # dd command
    (re.compile(r"\bdd\b(?:\s+.*)?\bof=/dev/"), "Direct disk block write using dd"),
    (re.compile(r"\bdd\s+"), "Low-level data duplicator (dd) execution"),
    # mkfs filesystem format
    (re.compile(r"\bmkfs(?:\.[a-z0-9]+)?\b"), "Filesystem formatting command"),
    # chmod -R or chown -R
    (re.compile(r"\bchmod\s+-[a-zA-Z]*R"), "Recursive permission modification"),
    (re.compile(r"\bchown\s+-[a-zA-Z]*R"), "Recursive ownership modification"),
    # sudo execution
    (re.compile(r"\bsudo\b"), "Privilege escalation (sudo)"),
    # git force push
    (re.compile(r"\bgit\s+push\b.*?(?:--force|-f\b|--force-with-lease)"), "Force-pushing to remote git repository"),
    # git reset --hard
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "Hard git reset discarding uncommitted changes"),
    # Redirection to system dirs (/etc, /boot, /sys, /proc)
    (re.compile(r">\s*/(?:etc|boot|sys|proc)/"), "Writing to sensitive system directory"),
    # System shutdown/reboot
    (re.compile(r"\b(?:shutdown|reboot|poweroff|init\s+0)\b"), "System power state modification"),
]

# Medium-risk patterns: package installs, service restarts, file creation/move, branch deletion
MEDIUM_RISK_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:npm|pnpm|yarn)\s+(?:install|i|add|remove|uninstall)\b"), "Package dependency modification"),
    (re.compile(r"\bpip(?:3)?\s+(?:install|uninstall)\b"), "Python package installation or removal"),
    (re.compile(r"\b(?:apt|apt-get|dnf|pacman|zypper)\s+(?:install|remove|purge)\b"), "System package management"),
    (re.compile(r"\bgit\s+(?:rebase|merge|branch\s+-D|clean\s+-[a-zA-Z]*f)\b"), "History-altering git operation"),
    (re.compile(r"\b(?:systemctl|service)\s+(?:restart|stop|reload)\b"), "System service status modification"),
    (re.compile(r"\b(?:mv|cp|mkdir|touch)\b"), "Filesystem modification"),
    (re.compile(r"\bdocker\s+(?:stop|rm|rmi|system\s+prune)\b"), "Container or image removal"),
    (re.compile(r"\bkill(?:\s+-[0-9a-zA-Z]+)?\s+[0-9]+"), "Terminating process"),
]


class RiskClassifier:
    """Classifies a shell command into a RiskLevel with an explanatory reason."""

    @classmethod
    def classify(cls, command: str) -> Tuple[RiskLevel, str]:
        cmd = command.strip()
        if not cmd:
            return RiskLevel.LOW, "Empty command"

        # Check blocked patterns first
        for pattern, reason in BLOCKED_PATTERNS:
            if pattern.search(cmd):
                return RiskLevel.BLOCKED, reason

        # Check generic unquoted placeholders like `<file>` anywhere in command
        if re.search(r"(?<!['\"])<[a-zA-Z0-9_-]+>(?!['\"])", cmd):
            return RiskLevel.BLOCKED, "Command contains unreplaced template placeholder"

        # Check high-risk patterns
        for pattern, reason in HIGH_RISK_PATTERNS:
            if pattern.search(cmd):
                return RiskLevel.HIGH, reason

        # Check medium-risk patterns
        for pattern, reason in MEDIUM_RISK_PATTERNS:
            if pattern.search(cmd):
                return RiskLevel.MEDIUM, reason

        # Default is low risk
        return RiskLevel.LOW, "Safe inspection or read-only command"


def classify_command(command: str) -> Tuple[RiskLevel, str]:
    return RiskClassifier.classify(command)
