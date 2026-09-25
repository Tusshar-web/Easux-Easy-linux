"""
Tests for safety classification and execution policy.
"""

from ai_terminal.models import RiskLevel
from ai_terminal.safety.classifier import RiskClassifier
from ai_terminal.safety.policy import SafetyPolicy


def test_classify_safe_commands():
    risk, _ = RiskClassifier.classify("ls -la")
    assert risk == RiskLevel.LOW

    risk, _ = RiskClassifier.classify("git status")
    assert risk == RiskLevel.LOW

    risk, _ = RiskClassifier.classify('find . -name "*.py"')
    assert risk == RiskLevel.LOW


def test_classify_medium_commands():
    risk, _ = RiskClassifier.classify("npm install express")
    assert risk == RiskLevel.MEDIUM

    risk, _ = RiskClassifier.classify("pip install rich")
    assert risk == RiskLevel.MEDIUM

    risk, _ = RiskClassifier.classify("git merge feature-branch")
    assert risk == RiskLevel.MEDIUM


def test_classify_high_risk_commands():
    risk, _ = RiskClassifier.classify("sudo apt update")
    assert risk == RiskLevel.HIGH

    risk, _ = RiskClassifier.classify("rm -rf node_modules")
    assert risk == RiskLevel.HIGH

    risk, _ = RiskClassifier.classify("git push -f origin main")
    assert risk == RiskLevel.HIGH

    risk, _ = RiskClassifier.classify("chmod -R 777 .")
    assert risk == RiskLevel.HIGH


def test_classify_blocked_patterns():
    # Fork bomb
    risk, _ = RiskClassifier.classify(":(){ :|:& };:")
    assert risk == RiskLevel.BLOCKED

    # Root deletion
    risk, _ = RiskClassifier.classify("rm -rf /")
    assert risk == RiskLevel.BLOCKED

    # Destructive unreplaced placeholder
    risk, _ = RiskClassifier.classify("rm -rf <path>")
    assert risk == RiskLevel.BLOCKED

    # Device redirection
    risk, _ = RiskClassifier.classify("echo test > /dev/sda")
    assert risk == RiskLevel.BLOCKED


def test_policy_enforcement():
    # Never auto-execute
    assert SafetyPolicy.can_auto_execute() is False

    # Blocked command cannot run without force override
    allowed, _ = SafetyPolicy.can_run("rm -rf /", first_confirmed=True)
    assert allowed is False

    allowed_force, _ = SafetyPolicy.can_run("rm -rf /", force_override=True)
    assert allowed_force is True

    # High-risk requires second confirmation
    allowed_high_no_sec, _ = SafetyPolicy.can_run("sudo reboot", first_confirmed=True, second_confirmed=False)
    assert allowed_high_no_sec is False

    allowed_high_sec, _ = SafetyPolicy.can_run("sudo reboot", first_confirmed=True, second_confirmed=True)
    assert allowed_high_sec is True
