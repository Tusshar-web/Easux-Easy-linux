"""
Data models and schemas for ai-terminal.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class TokenType(str, Enum):
    QUOTED_OR_ESCAPED = "quoted_or_escaped"
    PATH_LIKE = "path_like"
    FIRST_COMMAND = "first_command"
    KNOWN_SUBCOMMAND = "known_subcommand"
    OPTION = "option"
    POSITIONAL = "positional"


@dataclass
class Candidate:
    value: str
    display: str
    description: str = ""
    score: float = 0.0
    source: str = "generic"
    risk: RiskLevel = RiskLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "display": self.display,
            "description": self.description,
            "score": round(self.score, 2),
            "source": self.source,
            "risk": self.risk.value,
        }


@dataclass
class Suggestion:
    command: str
    reason: str
    score: float = 0.0
    risk: RiskLevel = RiskLevel.LOW
    source: str = "context"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "reason": self.reason,
            "score": round(self.score, 2),
            "risk": self.risk.value,
            "source": self.source,
        }


@dataclass
class ParsedBuffer:
    raw_buffer: str
    cursor_pos: int
    tokens: List[str] = field(default_factory=list)
    active_token_index: int = 0
    active_token: str = ""
    token_type: TokenType = TokenType.FIRST_COMMAND
    prefix: str = ""
    command_name: Optional[str] = None
    subcommand: Optional[str] = None


@dataclass
class ProjectContext:
    root_dir: str
    kinds: List[str] = field(default_factory=list)  # e.g., ["node", "git", "python", "make"]
    facts: Dict[str, Any] = field(default_factory=dict)
    git_branch: Optional[str] = None
    git_dirty: bool = False
    git_modified_files: int = 0
    git_untracked_files: int = 0
    npm_scripts: List[str] = field(default_factory=list)
    make_targets: List[str] = field(default_factory=list)
    python_tools: List[str] = field(default_factory=list)


@dataclass
class GenerateRequest:
    task: str
    cwd: str = ""
    project_facts: Dict[str, Any] = field(default_factory=dict)
    relevant_prefix: str = ""


@dataclass
class GenerateResponse:
    command: str
    explanation: str
    assumptions: str = ""
    risk: RiskLevel = RiskLevel.LOW
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "explanation": self.explanation,
            "assumptions": self.assumptions,
            "risk": self.risk.value,
            "alternatives": self.alternatives,
        }


@dataclass
class ExplainRequest:
    command: str


@dataclass
class ExplainResponse:
    explanation: str
    effects: str
    risk: RiskLevel = RiskLevel.LOW
    safer_variant: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation": self.explanation,
            "effects": self.effects,
            "risk": self.risk.value,
            "safer_variant": self.safer_variant,
        }


@dataclass
class FixRequest:
    failed_command: str
    exit_code: int
    stderr_excerpt: str


@dataclass
class FixResponse:
    diagnosis: str
    confidence: float
    next_command: str
    risk: RiskLevel = RiskLevel.LOW
    questions: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnosis": self.diagnosis,
            "confidence": round(self.confidence, 2),
            "next_command": self.next_command,
            "risk": self.risk.value,
            "questions": self.questions,
        }
