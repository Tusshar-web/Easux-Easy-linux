"""
Tests for deterministic ranking engine.
"""

from ai_terminal.models import Candidate, RiskLevel, ParsedBuffer, TokenType, ProjectContext
from ai_terminal.ranking.ranker import Ranker


def test_ranking_prefix_and_exact_match():
    ranker = Ranker()
    parsed = ParsedBuffer(
        raw_buffer="git checkout",
        cursor_pos=12,
        active_token="checkout",
        active_token_index=1,
        token_type=TokenType.KNOWN_SUBCOMMAND,
    )
    ctx = ProjectContext(root_dir="/tmp")

    candidates = [
        Candidate(value="checkout", display="checkout", source="git_adapter"),
        Candidate(value="check", display="check", source="git_adapter"),
        Candidate(value="unrelated", display="unrelated", source="generic"),
    ]

    ranked = ranker.rank(candidates, parsed, ctx)
    assert ranked[0].value == "checkout"
    assert ranked[0].score > ranked[1].score


def test_ranking_excludes_blocked_candidates():
    ranker = Ranker()
    parsed = ParsedBuffer(raw_buffer="rm", cursor_pos=2, active_token="rm", token_type=TokenType.FIRST_COMMAND)
    ctx = ProjectContext(root_dir="/tmp")

    candidates = [
        Candidate(value="rm -rf /", display="rm -rf /", risk=RiskLevel.BLOCKED, source="history"),
        Candidate(value="rm test.txt", display="rm test.txt", risk=RiskLevel.LOW, source="history"),
    ]

    ranked = ranker.rank(candidates, parsed, ctx)
    values = [r.value for r in ranked]
    assert "rm -rf /" not in values
    assert "rm test.txt" in values


def test_ranking_context_bonus():
    ranker = Ranker()
    parsed = ParsedBuffer(raw_buffer="npm run d", cursor_pos=9, active_token="d", command_name="npm", subcommand="run")
    ctx_with_dev = ProjectContext(root_dir="/tmp", kinds=["node"], npm_scripts=["dev"])

    cands = [
        Candidate(value="dev", display="dev", source="npm_adapter"),
        Candidate(value="docs", display="docs", source="generic"),
    ]

    ranked = ranker.rank(cands, parsed, ctx_with_dev)
    assert ranked[0].value == "dev"
    assert ranked[0].score > ranked[1].score
