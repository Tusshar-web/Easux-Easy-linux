"""
LLM Provider implementations (Offline Heuristic and API-based).
"""

import json
import os
import re
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from ai_terminal.models import (
    GenerateRequest,
    GenerateResponse,
    ExplainRequest,
    ExplainResponse,
    FixRequest,
    FixResponse,
    RiskLevel,
)
from ai_terminal.llm.schemas import (
    parse_and_validate_generate,
    parse_and_validate_explain,
    parse_and_validate_fix,
)
from ai_terminal.safety.classifier import RiskClassifier
from ai_terminal.safety.redactor import redact_secrets


SYSTEM_PROMPT = """You are an AI-enhanced Linux Terminal Assistant.
Your task is to generate, explain, or fix shell commands for Bash and Zsh.
Output MUST strictly be valid JSON adhering to the specified schema.
Rules:
1. Command field must be a single shell command or a clearly labeled multi-step sequence.
2. NO Markdown code fences inside the command field.
3. Target shell: Bash or Zsh on Linux.
4. Risk classification must be: low, medium, high, or blocked.
5. Never execute automatically.
"""


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, request: GenerateRequest) -> Optional[GenerateResponse]:
        pass

    @abstractmethod
    def explain(self, request: ExplainRequest) -> Optional[ExplainResponse]:
        pass

    @abstractmethod
    def fix(self, request: FixRequest) -> Optional[FixResponse]:
        pass


class OfflineHeuristicProvider(BaseLLMProvider):
    """
    Fast, deterministic offline helper that provides instant local assistance
    when no API key or network is available.
    """

    def generate(self, request: GenerateRequest) -> Optional[GenerateResponse]:
        task = request.task.lower().strip()

        # "find python files modified in the last 7 days"
        if "python" in task and ("modified" in task or "changed" in task) and ("7 days" in task or "week" in task):
            return GenerateResponse(
                command='find . -type f -name "*.py" -mtime -7',
                explanation="Finds regular Python files below the current directory changed in seven days.",
                assumptions="Search starts in the current directory.",
                risk=RiskLevel.LOW,
                alternatives=['find . -name "*.py" -ctime -7', 'git log --name-only --since="7 days ago"'],
            )

        # "find python files"
        if "find" in task and "python" in task:
            return GenerateResponse(
                command='find . -type f -name "*.py"',
                explanation="Recursively locates all Python (.py) source files in the current directory.",
                assumptions="Current directory is the project root.",
                risk=RiskLevel.LOW,
                alternatives=['find . -name "*.py" -not -path "*/.*"'],
            )

        # "find files larger than ..."
        m_size = re.search(r"larger than (\d+)\s*(mb|gb|kb|m|g)", task)
        if m_size:
            num, unit = m_size.group(1), m_size.group(2).upper()
            unit_flag = "M" if "M" in unit else ("G" if "G" in unit else "k")
            return GenerateResponse(
                command=f'find . -type f -size +{num}{unit_flag} -exec ls -lh {{}} +',
                explanation=f"Locates files larger than {num}{unit} in the current directory tree and lists details.",
                assumptions="Current directory tree has read permissions.",
                risk=RiskLevel.LOW,
                alternatives=[f'find . -type f -size +{num}{unit_flag}'],
            )

        # "kill process on port ..."
        m_port = re.search(r"port\s+(\d+)", task)
        if "kill" in task and m_port:
            port = m_port.group(1)
            return GenerateResponse(
                command=f"fuser -k {port}/tcp",
                explanation=f"Finds and terminates the process currently listening on TCP port {port}.",
                assumptions="Requires necessary process termination permissions.",
                risk=RiskLevel.MEDIUM,
                alternatives=[f"lsof -ti:{port} | xargs kill -9"],
            )

        # "check port ..." or "who is using port ..."
        if m_port and ("listen" in task or "using" in task or "check" in task):
            port = m_port.group(1)
            return GenerateResponse(
                command=f"lsof -i :{port}",
                explanation=f"Lists process IDs and details holding port {port}.",
                assumptions="lsof utility is installed.",
                risk=RiskLevel.LOW,
                alternatives=[f"ss -tulpn | grep :{port}"],
            )

        # "git undo last commit"
        if "git" in task and "undo" in task and "commit" in task:
            return GenerateResponse(
                command="git reset --soft HEAD~1",
                explanation="Undoes the most recent commit while preserving changes staged in the index.",
                assumptions="Current branch has at least one commit.",
                risk=RiskLevel.MEDIUM,
                alternatives=["git reset HEAD~1", "git revert HEAD"],
            )

        # "show disk usage"
        if "disk" in task and ("usage" in task or "free" in task or "space" in task):
            return GenerateResponse(
                command="df -h",
                explanation="Displays available and used disk space on all mounted filesystems in human-readable format.",
                assumptions="Standard coreutils available.",
                risk=RiskLevel.LOW,
                alternatives=["ncdu", "du -sh * | sort -h"],
            )

        # "extract tar file"
        if "extract" in task and ("tar" in task or ".gz" in task or ".tgz" in task):
            return GenerateResponse(
                command="tar -xzf archive.tar.gz",
                explanation="Extracts a gzip-compressed tarball into the current directory.",
                assumptions="Replace archive.tar.gz with your target archive name.",
                risk=RiskLevel.LOW,
                alternatives=["tar -tf archive.tar.gz"],
            )

        # Fallback generic command proposal
        return GenerateResponse(
            command=f"echo '{request.task}'",
            explanation=f"Generated fallback command for: {request.task}",
            assumptions="Offline fallback mode active. Configure an LLM API key for full AI capability.",
            risk=RiskLevel.LOW,
            alternatives=[],
        )

    def explain(self, request: ExplainRequest) -> Optional[ExplainResponse]:
        cmd = request.command.strip()

        # tar explanation
        if cmd.startswith("tar"):
            parts = []
            if "-x" in cmd or "x" in cmd.split()[1] if len(cmd.split()) > 1 else False:
                parts.append("extracts files (-x)")
            if "-z" in cmd or "z" in cmd.split()[1] if len(cmd.split()) > 1 else False:
                parts.append("decompresses gzip (-z)")
            if "-f" in cmd or "f" in cmd.split()[1] if len(cmd.split()) > 1 else False:
                parts.append("reads from specified archive file (-f)")
            summary = ", ".join(parts) if parts else "manipulates tar archives"
            return ExplainResponse(
                explanation=f"The tar command {summary}.",
                effects="Extracts archive content into the current working directory without modifying the archive itself.",
                risk=RiskLevel.LOW,
                safer_variant=f"tar -tvf {' '.join(cmd.split()[2:]) if len(cmd.split()) > 2 else 'archive.tgz'}",
            )

        # rm explanation
        if cmd.startswith("rm"):
            risk, _ = RiskClassifier.classify(cmd)
            return ExplainResponse(
                explanation="Deletes specified files or directories from the filesystem permanently.",
                effects="Unlinks filesystem nodes. Removed files cannot be restored from a recycle bin.",
                risk=risk,
                safer_variant="rm -i " + " ".join(cmd.split()[1:]),
            )

        # chmod explanation
        if cmd.startswith("chmod"):
            return ExplainResponse(
                explanation="Modifies the file mode (read/write/execute permissions) of targets.",
                effects="Alters POSIX file security access control bits.",
                risk=RiskLevel.MEDIUM if "-R" in cmd else RiskLevel.LOW,
                safer_variant=None,
            )

        # git push explanation
        if cmd.startswith("git push"):
            is_force = "--force" in cmd or "-f" in cmd
            return ExplainResponse(
                explanation="Uploads local repository commits to the remote tracking branch.",
                effects="Updates remote refs. Force pushing can overwrite remote history!" if is_force else "Fast-forwards remote branch.",
                risk=RiskLevel.HIGH if is_force else RiskLevel.LOW,
                safer_variant="git push --force-with-lease" if is_force else None,
            )

        # General explanation
        risk, reason = RiskClassifier.classify(cmd)
        return ExplainResponse(
            explanation=f"Executes shell command '{cmd.split()[0]}'.",
            effects="Performs command action in the current shell environment.",
            risk=risk,
            safer_variant=None,
        )

    def fix(self, request: FixRequest) -> Optional[FixResponse]:
        err = request.stderr_excerpt.lower()
        cmd = request.failed_command.strip()

        # Git non-fast-forward
        if "non-fast-forward" in err or "fetch first" in err or "[rejected]" in err:
            return FixResponse(
                diagnosis="The remote branch contains commits not in your local branch.",
                confidence=0.96,
                next_command="git pull --rebase origin main",
                risk=RiskLevel.MEDIUM,
                questions="rewrites local commits during rebase if conflicts require resolution.",
            )

        # Permission denied
        if "permission denied" in err or "eacces" in err:
            return FixResponse(
                diagnosis="The command failed due to missing filesystem read or execute permissions.",
                confidence=0.90,
                next_command=f"chmod +x {cmd.split()[-1] if cmd.split() else 'file'}",
                risk=RiskLevel.MEDIUM,
                questions="Verify that you have ownership of the file before altering permissions.",
            )

        # Command not found
        if "command not found" in err or "not found" in err:
            prog = cmd.split()[0] if cmd.split() else "command"
            return FixResponse(
                diagnosis=f"The executable '{prog}' is not installed or not in your current PATH.",
                confidence=0.92,
                next_command=f"which {prog} || sudo apt install {prog}",
                risk=RiskLevel.MEDIUM,
                questions=None,
            )

        # Port in use
        if "address already in use" in err or "eaddrinuse" in err:
            return FixResponse(
                diagnosis="A previous process is already occupying the requested network port.",
                confidence=0.95,
                next_command="lsof -i :3000",
                risk=RiskLevel.LOW,
                questions="Identify the process PID holding the port before killing it.",
            )

        # General fallback fix
        return FixResponse(
            diagnosis="Command failed with non-zero exit code.",
            confidence=0.50,
            next_command=f"{cmd} --help",
            risk=RiskLevel.LOW,
            questions="Inspect command usage flags.",
        )


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Standard HTTP client for OpenAI-compatible completions endpoints
    (OpenAI, Groq, Together, DeepSeek, LocalAI, vLLM, Ollama).
    Uses standard library urllib with strict timeouts.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini", timeout: float = 4.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.fallback = OfflineHeuristicProvider()

    def _call_api(self, prompt: str) -> Optional[str]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    choices = resp_data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
        except Exception:
            return None
        return None

    def generate(self, request: GenerateRequest) -> Optional[GenerateResponse]:
        user_prompt = f"""Generate a Linux shell command for:
Task: {request.task}
Context: cwd={request.cwd}, project_facts={json.dumps(request.project_facts)}
Return strictly JSON matching:
{{
  "command": "shell command here",
  "explanation": "concise explanation",
  "assumptions": "any assumptions made",
  "risk": "low|medium|high|blocked",
  "alternatives": ["alt1", "alt2"]
}}
"""
        raw = self._call_api(user_prompt)
        if raw:
            parsed = parse_and_validate_generate(raw)
            if parsed:
                return parsed
        return self.fallback.generate(request)

    def explain(self, request: ExplainRequest) -> Optional[ExplainResponse]:
        user_prompt = f"""Explain this shell command:
Command: {request.command}
Return strictly JSON matching:
{{
  "explanation": "plain-language summary",
  "effects": "system or filesystem effects",
  "risk": "low|medium|high|blocked",
  "safer_variant": "optional safer alternative or null"
}}
"""
        raw = self._call_api(user_prompt)
        if raw:
            parsed = parse_and_validate_explain(raw)
            if parsed:
                return parsed
        return self.fallback.explain(request)

    def fix(self, request: FixRequest) -> Optional[FixResponse]:
        user_prompt = f"""Diagnose and fix this failed shell command:
Failed command: {request.failed_command}
Exit code: {request.exit_code}
Error excerpt:
{request.stderr_excerpt}

Return strictly JSON matching:
{{
  "diagnosis": "likely cause of failure",
  "confidence": 0.85,
  "next_command": "safe next step command",
  "risk": "low|medium|high|blocked",
  "questions": "optional missing info or caveat"
}}
"""
        raw = self._call_api(user_prompt)
        if raw:
            parsed = parse_and_validate_fix(raw)
            if parsed:
                return parsed
        return self.fallback.fix(request)
