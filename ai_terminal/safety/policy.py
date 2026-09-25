"""
Safety policy enforcement for command execution and display.
"""

from typing import Tuple
from ai_terminal.models import RiskLevel
from ai_terminal.safety.classifier import RiskClassifier


class SafetyPolicy:
    """Enforces execution rules based on risk levels and user approval."""

    @classmethod
    def can_auto_execute(cls) -> bool:
        """The assistant NEVER auto-executes generated commands."""
        return False

    @classmethod
    def can_run(
        cls,
        command: str,
        first_confirmed: bool = False,
        second_confirmed: bool = False,
        force_override: bool = False
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a command can be executed.
        Returns: (allowed: bool, message: str)
        """
        risk, reason = RiskClassifier.classify(command)

        if risk == RiskLevel.BLOCKED:
            if force_override:
                return True, "Allowed via explicit force override."
            return (
                False,
                f"BLOCKED: Execution prevented by safety policy ({reason}). "
                "Edit the command or use --force-override to bypass."
            )

        if not first_confirmed:
            return False, "Requires explicit confirmation to run."

        if risk == RiskLevel.HIGH:
            if not second_confirmed:
                return (
                    False,
                    f"HIGH RISK: Command involves potentially destructive operations ({reason}). "
                    "Requires explicit secondary confirmation."
                )

        return True, "Execution allowed."

    @classmethod
    def sanitize_for_display(cls, command: str) -> str:
        """
        Ensures command is treated as literal text and not interpreted during display.
        """
        return command.strip()
