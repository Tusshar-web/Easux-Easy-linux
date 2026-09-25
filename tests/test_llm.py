"""
Tests for LLM schemas, JSON parsing, validation, and offline provider.
"""

from ai_terminal.models import GenerateRequest, ExplainRequest, FixRequest, RiskLevel
from ai_terminal.llm.schemas import (
    parse_and_validate_generate,
    parse_and_validate_explain,
    parse_and_validate_fix,
)
from ai_terminal.llm.providers import OfflineHeuristicProvider


def test_parse_generate_with_markdown_fences():
    raw = """```json
{
  "command": "`find . -name '*.py'`",
  "explanation": "Finds python files",
  "assumptions": "in current dir",
  "risk": "low",
  "alternatives": ["find . -type f"]
}
```"""
    resp = parse_and_validate_generate(raw)
    assert resp is not None
    assert resp.command == "find . -name '*.py'"
    assert resp.risk == RiskLevel.LOW
    assert len(resp.alternatives) == 1


def test_parse_generate_detects_blocked():
    raw = '{"command": "rm -rf /", "explanation": "deletes root", "risk": "low"}'
    resp = parse_and_validate_generate(raw)
    assert resp is not None
    # Local safety check overrides false low risk to BLOCKED
    assert resp.risk == RiskLevel.BLOCKED


def test_offline_heuristic_provider_generate():
    provider = OfflineHeuristicProvider()
    req = GenerateRequest(task="find Python files modified in the last 7 days")
    resp = provider.generate(req)
    assert resp is not None
    assert "find" in resp.command
    assert "-mtime -7" in resp.command
    assert resp.risk == RiskLevel.LOW


def test_offline_heuristic_provider_explain():
    provider = OfflineHeuristicProvider()
    req = ExplainRequest(command="tar -xzf archive.tgz")
    resp = provider.explain(req)
    assert resp is not None
    assert "extracts" in resp.explanation
    assert resp.risk == RiskLevel.LOW
    assert resp.safer_variant is not None


def test_offline_heuristic_provider_fix():
    provider = OfflineHeuristicProvider()
    req = FixRequest(
        failed_command="git push origin main",
        exit_code=1,
        stderr_excerpt="! [rejected] main -> main (non-fast-forward)",
    )
    resp = provider.fix(req)
    assert resp is not None
    assert "rebase" in resp.next_command
    assert resp.risk == RiskLevel.MEDIUM
