"""
LLM Client factory and dispatcher.
Ensures context minimization and secret redaction before sending.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from ai_terminal.models import (
    GenerateRequest,
    GenerateResponse,
    ExplainRequest,
    ExplainResponse,
    FixRequest,
    FixResponse,
)
from ai_terminal.llm.providers import (
    BaseLLMProvider,
    OfflineHeuristicProvider,
    OpenAICompatibleProvider,
)
from ai_terminal.safety.redactor import redact_secrets
from ai_terminal.storage.repository import Repository


class LLMClient:
    def __init__(self, repository: Optional[Repository] = None):
        self.repo = repository
        self.provider = self._resolve_provider()

    def _resolve_provider(self) -> BaseLLMProvider:
        # Check environment variables and settings
        api_key = (
            os.environ.get("AI_TERMINAL_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        base_url = os.environ.get("AI_TERMINAL_BASE_URL", "https://api.openai.com/v1")
        model = "gpt-4o-mini"

        if self.repo:
            stored_model = self.repo.get_setting("model")
            if stored_model:
                model = stored_model
            stored_url = self.repo.get_setting("base_url")
            if stored_url:
                base_url = stored_url

        if api_key:
            return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)

        # Default to fast, zero-network offline heuristic provider
        return OfflineHeuristicProvider()

    def generate(self, task: str, cwd: str, project_facts: dict) -> Tuple[Optional[GenerateResponse], str]:
        """
        Executes generate with redacted input and least-context minimization.
        Returns (response, privacy_status).
        """
        # Minimal context payload
        clean_task = redact_secrets(task)
        cwd_name = Path(cwd).name if cwd else ""

        req = GenerateRequest(
            task=clean_task,
            cwd=cwd_name,
            project_facts=project_facts,
        )

        resp = self.provider.generate(req)
        provider_name = type(self.provider).__name__
        privacy_status = f"Context sent: task, directory name ({cwd_name}), project facts via {provider_name}"
        return resp, privacy_status

    def explain(self, command: str) -> Tuple[Optional[ExplainResponse], str]:
        clean_cmd = redact_secrets(command)
        req = ExplainRequest(command=clean_cmd)
        resp = self.provider.explain(req)
        privacy_status = "Context sent: command string (secrets redacted)"
        return resp, privacy_status

    def fix(self, failed_cmd: str, exit_code: int, stderr_excerpt: str) -> Tuple[Optional[FixResponse], str]:
        clean_cmd = redact_secrets(failed_cmd)
        # Bounded stderr excerpt (max 2000 chars)
        clean_err = redact_secrets(stderr_excerpt[:2000])

        req = FixRequest(
            failed_command=clean_cmd,
            exit_code=exit_code,
            stderr_excerpt=clean_err,
        )
        resp = self.provider.fix(req)
        privacy_status = "Context sent: failed command, exit status, redacted error excerpt"
        return resp, privacy_status
