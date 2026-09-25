"""
JSON schemas and validation for LLM responses.
"""

import json
import re
from typing import Dict, Any, Optional
from ai_terminal.models import (
    GenerateResponse,
    ExplainResponse,
    FixResponse,
    RiskLevel,
)
from ai_terminal.safety.classifier import RiskClassifier


GENERATE_SCHEMA = {
    "type": "object",
    "required": ["command", "explanation", "risk"],
    "properties": {
        "command": {"type": "string"},
        "explanation": {"type": "string"},
        "assumptions": {"type": "string"},
        "risk": {"type": "string", "enum": ["low", "medium", "high", "blocked"]},
        "alternatives": {"type": "array", "items": {"type": "string"}},
    },
}

EXPLAIN_SCHEMA = {
    "type": "object",
    "required": ["explanation", "effects", "risk"],
    "properties": {
        "explanation": {"type": "string"},
        "effects": {"type": "string"},
        "risk": {"type": "string", "enum": ["low", "medium", "high", "blocked"]},
        "safer_variant": {"type": "string"},
    },
}

FIX_SCHEMA = {
    "type": "object",
    "required": ["diagnosis", "confidence", "next_command", "risk"],
    "properties": {
        "diagnosis": {"type": "string"},
        "confidence": {"type": "number"},
        "next_command": {"type": "string"},
        "risk": {"type": "string", "enum": ["low", "medium", "high", "blocked"]},
        "questions": {"type": "string"},
    },
}


def clean_markdown_json(raw_text: str) -> str:
    """Strips markdown code blocks (```json ... ```) if returned by an LLM."""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


def clean_command_field(command: str) -> str:
    """Removes any surrounding markdown backticks from command string."""
    cmd = command.strip()
    if cmd.startswith("```") and cmd.endswith("```"):
        lines = cmd.splitlines()
        cmd = "\n".join(lines[1:-1]).strip()
    cmd = cmd.strip("`").strip()
    return cmd


def parse_and_validate_generate(raw: str) -> Optional[GenerateResponse]:
    try:
        clean = clean_markdown_json(raw)
        data = json.loads(clean)
        cmd = clean_command_field(data.get("command", ""))
        if not cmd:
            return None

        # Verify risk level or classify if missing/invalid
        risk_str = str(data.get("risk", "low")).lower()
        if risk_str not in [r.value for r in RiskLevel]:
            risk_str, _ = RiskClassifier.classify(cmd)
            risk_val = risk_str
        else:
            risk_val = RiskLevel(risk_str)

        # Cross-check with local safety classifier
        local_risk, _ = RiskClassifier.classify(cmd)
        if local_risk == RiskLevel.BLOCKED:
            risk_val = RiskLevel.BLOCKED
        elif local_risk == RiskLevel.HIGH and risk_val != RiskLevel.BLOCKED:
            risk_val = RiskLevel.HIGH

        alternatives = data.get("alternatives", [])
        if not isinstance(alternatives, list):
            alternatives = []

        return GenerateResponse(
            command=cmd,
            explanation=str(data.get("explanation", "")),
            assumptions=str(data.get("assumptions", "")),
            risk=risk_val,
            alternatives=[str(a) for a in alternatives],
        )
    except Exception:
        return None


def parse_and_validate_explain(raw: str) -> Optional[ExplainResponse]:
    try:
        clean = clean_markdown_json(raw)
        data = json.loads(clean)
        risk_str = str(data.get("risk", "low")).lower()
        risk_val = RiskLevel(risk_str) if risk_str in [r.value for r in RiskLevel] else RiskLevel.LOW

        safer = data.get("safer_variant")
        if safer:
            safer = clean_command_field(str(safer))

        return ExplainResponse(
            explanation=str(data.get("explanation", "")),
            effects=str(data.get("effects", "")),
            risk=risk_val,
            safer_variant=safer,
        )
    except Exception:
        return None


def parse_and_validate_fix(raw: str) -> Optional[FixResponse]:
    try:
        clean = clean_markdown_json(raw)
        data = json.loads(clean)
        cmd = clean_command_field(data.get("next_command", ""))
        conf = float(data.get("confidence", 0.8))
        conf = max(0.0, min(1.0, conf))

        risk_str = str(data.get("risk", "low")).lower()
        risk_val = RiskLevel(risk_str) if risk_str in [r.value for r in RiskLevel] else RiskLevel.LOW
        if cmd:
            local_risk, _ = RiskClassifier.classify(cmd)
            if local_risk in (RiskLevel.BLOCKED, RiskLevel.HIGH):
                risk_val = local_risk

        return FixResponse(
            diagnosis=str(data.get("diagnosis", "")),
            confidence=conf,
            next_command=cmd,
            risk=risk_val,
            questions=data.get("questions"),
        )
    except Exception:
        return None
