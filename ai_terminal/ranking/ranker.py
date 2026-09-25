"""
Deterministic and explainable ranking engine.
Follows the weighted scoring rules defined in the PRD.
"""

import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ai_terminal.models import Candidate, RiskLevel, ParsedBuffer, ProjectContext
from ai_terminal.storage.repository import Repository


SOURCE_PRIORITIES = {
    "git_adapter": 10,
    "npm_adapter": 10,
    "pip_adapter": 10,
    "docker_adapter": 10,
    "make_adapter": 10,
    "history": 8,
    "installed_commands": 7,
    "filesystem": 6,
    "generic": 5,
}


class Ranker:
    def __init__(self, repository: Optional[Repository] = None):
        self.repo = repository

    def rank(
        self,
        candidates: List[Candidate],
        parsed: ParsedBuffer,
        ctx: ProjectContext,
        history_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Candidate]:
        """
        Ranks candidates deterministically using the weighted scoring signals.
        Filters out blocked candidates.
        """
        weights = self._get_weights()
        scored: List[Candidate] = []

        seen_values = set()
        for cand in candidates:
            # Policy filter: exclude BLOCKED candidates
            if cand.risk == RiskLevel.BLOCKED:
                continue

            if cand.value in seen_values:
                continue
            seen_values.add(cand.value)

            token = parsed.active_token
            s_prefix = self._score_prefix_match(cand.value, token, weights["weight_prefix"])
            s_context = self._score_context_match(cand, parsed, ctx, weights["weight_context"])
            s_recency, s_frequency = self._score_history(cand.value, history_map, weights["weight_recency"], weights["weight_frequency"])
            s_source = self._score_source(cand.source, weights["weight_source"])

            total_score = s_prefix + s_context + s_recency + s_frequency + s_source

            scored_cand = Candidate(
                value=cand.value,
                display=cand.display,
                description=cand.description,
                score=round(total_score, 2),
                source=cand.source,
                risk=cand.risk,
            )
            scored.append(scored_cand)

        # Sort: first by score DESC, then by source priority DESC, then alphabetically ASC
        scored.sort(
            key=lambda c: (
                -c.score,
                -SOURCE_PRIORITIES.get(c.source, 0),
                c.value.lower(),
                c.value,
            )
        )
        return scored

    def _get_weights(self) -> Dict[str, float]:
        if not self.repo:
            return {
                "weight_prefix": 45.0,
                "weight_context": 25.0,
                "weight_recency": 15.0,
                "weight_frequency": 10.0,
                "weight_source": 5.0,
            }
        return {
            "weight_prefix": float(self.repo.get_setting("weight_prefix", "45") or 45),
            "weight_context": float(self.repo.get_setting("weight_context", "25") or 25),
            "weight_recency": float(self.repo.get_setting("weight_recency", "15") or 15),
            "weight_frequency": float(self.repo.get_setting("weight_frequency", "10") or 10),
            "weight_source": float(self.repo.get_setting("weight_source", "5") or 5),
        }

    def _score_prefix_match(self, candidate_val: str, token: str, max_w: float) -> float:
        if not token:
            return max_w * 0.5

        if candidate_val == token:
            return max_w  # Exact match (100% of prefix weight, e.g. 45)
        if candidate_val.startswith(token):
            return max_w * 0.85  # Case-sensitive prefix match
        if candidate_val.lower().startswith(token.lower()):
            return max_w * 0.65  # Case-insensitive prefix match
        if token.lower() in candidate_val.lower():
            return max_w * 0.35  # Substring match
        return 0.0

    def _score_context_match(self, cand: Candidate, parsed: ParsedBuffer, ctx: ProjectContext, max_w: float) -> float:
        score = 0.0

        # Node project context
        if "node" in ctx.kinds:
            if parsed.command_name in ("npm", "yarn", "pnpm"):
                score += max_w * 0.5
                if cand.value in ctx.npm_scripts:
                    score += max_w * 0.5

        # Git context
        if "git" in ctx.kinds:
            if parsed.command_name == "git":
                score += max_w * 0.5
                if ctx.git_dirty and cand.value in ("status", "diff", "add", "commit"):
                    score += max_w * 0.5

        # Make context
        if "make" in ctx.kinds and parsed.command_name == "make":
            score += max_w * 0.5
            if cand.value in ctx.make_targets:
                score += max_w * 0.5

        # Python context
        if "python" in ctx.kinds:
            if parsed.command_name in ("python", "python3", "pytest", "ruff", "pip"):
                score += max_w * 0.5

        return min(max_w, score)

    def _score_history(
        self,
        command_or_val: str,
        history_map: Optional[Dict[str, Dict[str, Any]]],
        max_recency_w: float,
        max_freq_w: float,
    ) -> (float, float):
        if not history_map or command_or_val not in history_map:
            return 0.0, 0.0

        item = history_map[command_or_val]
        freq = item.get("frequency", 0)
        last_seen = item.get("last_seen")

        # Frequency score: capped logarithmic
        if freq > 0:
            freq_score = min(max_freq_w, math.log(freq + 1) * (max_freq_w / 2.5))
        else:
            freq_score = 0.0

        # Recency score: exponential decay
        recency_score = 0.0
        if last_seen:
            try:
                dt = datetime.fromisoformat(last_seen)
                diff_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
                if diff_hours < 24:
                    recency_score = max_recency_w
                elif diff_hours < 72:
                    recency_score = max_recency_w * 0.7
                elif diff_hours < 168:
                    recency_score = max_recency_w * 0.4
                else:
                    recency_score = max_recency_w * 0.1
            except Exception:
                recency_score = max_recency_w * 0.2

        return recency_score, freq_score

    def _score_source(self, source: str, max_w: float) -> float:
        if source in ("git_adapter", "npm_adapter", "pip_adapter", "docker_adapter", "make_adapter"):
            return max_w  # 5
        if source == "installed_commands":
            return max_w * 0.8  # 4
        if source == "history":
            return max_w * 0.7  # 3.5
        if source == "filesystem":
            return max_w * 0.6  # 3
        return max_w * 0.4
