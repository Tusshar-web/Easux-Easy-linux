"""
Shell integration package.
"""

from ai_terminal.shell.installer import (
    get_init_script,
    install_hook,
    uninstall_hook,
    inspect_status,
)

__all__ = ["get_init_script", "install_hook", "uninstall_hook", "inspect_status"]
