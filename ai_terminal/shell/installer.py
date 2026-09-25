"""
Shell hook installation, removal, and status inspector.
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional

SHELL_MARKER_START = "# >>> ai-terminal >>>"
SHELL_MARKER_END = "# <<< ai-terminal <<<"

SCRIPTS_DIR = Path(__file__).parent / "scripts"


def get_init_script(shell: str) -> str:
    script_file = SCRIPTS_DIR / f"ai.{shell}"
    if script_file.exists():
        return script_file.read_text(encoding="utf-8")
    return ""


def get_default_rc(shell: str) -> Path:
    home = Path.home()
    if shell == "bash":
        return home / ".bashrc"
    elif shell == "zsh":
        return home / ".zshrc"
    return home / f".{shell}rc"


def install_hook(shell: str, custom_rc: Optional[Path] = None) -> Tuple[bool, str]:
    rc_file = custom_rc or get_default_rc(shell)
    if not rc_file.exists():
        try:
            rc_file.touch()
        except OSError as e:
            return False, f"Could not create {rc_file}: {e}"

    content = rc_file.read_text(encoding="utf-8", errors="ignore")
    if SHELL_MARKER_START in content:
        return True, f"ai-terminal integration is already installed in {rc_file}"

    snippet = (
        f"\n{SHELL_MARKER_START}\n"
        f"# Loaded ai-terminal shell hooks\n"
        f'eval "$(ai shell init {shell})"\n'
        f"{SHELL_MARKER_END}\n"
    )

    try:
        with open(rc_file, "a", encoding="utf-8") as f:
            f.write(snippet)
        return True, f"Successfully installed ai-terminal integration in {rc_file}"
    except OSError as e:
        return False, f"Failed to write to {rc_file}: {e}"


def uninstall_hook(shell: str, custom_rc: Optional[Path] = None) -> Tuple[bool, str]:
    rc_file = custom_rc or get_default_rc(shell)
    if not rc_file.exists():
        return True, f"{rc_file} does not exist."

    content = rc_file.read_text(encoding="utf-8", errors="ignore")
    if SHELL_MARKER_START not in content:
        return True, f"No ai-terminal integration found in {rc_file}"

    start_idx = content.find(SHELL_MARKER_START)
    end_idx = content.find(SHELL_MARKER_END)

    if start_idx != -1 and end_idx != -1:
        end_idx += len(SHELL_MARKER_END)
        new_content = content[:start_idx].rstrip() + "\n" + content[end_idx:].lstrip()
        try:
            rc_file.write_text(new_content, encoding="utf-8")
            return True, f"Successfully removed ai-terminal integration from {rc_file}"
        except OSError as e:
            return False, f"Failed to update {rc_file}: {e}"

    return False, f"Malformed marker block in {rc_file}."


def inspect_status(shell: str, custom_rc: Optional[Path] = None) -> Dict[str, Any]:
    rc_file = custom_rc or get_default_rc(shell)
    installed = False
    if rc_file.exists():
        content = rc_file.read_text(encoding="utf-8", errors="ignore")
        installed = (SHELL_MARKER_START in content)

    return {
        "shell": shell,
        "rc_path": str(rc_file),
        "rc_exists": rc_file.exists(),
        "installed": installed,
    }
