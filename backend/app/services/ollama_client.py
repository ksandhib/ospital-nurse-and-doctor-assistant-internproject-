"""Thin HTTP client for talking to a local Ollama server.

Ollama is the sole AI engine for AI ClinicOS. The frontend never talks to
Ollama directly - every request flows Browser -> FastAPI -> Ollama -> Response.
This module centralizes that connection so ai_service.py and
chat_assistant.py share one implementation, one timeout policy, and one
error-handling strategy.
"""

import json
import logging

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Low temperature keeps clinical answers consistent/precise run-to-run
# instead of creatively varying the wording of the same symptoms.
DEFAULT_OPTIONS = {"temperature": 0.15, "top_p": 0.9}


class OllamaUnavailableError(RuntimeError):
    """Raised when Ollama cannot be reached or returns an error."""


class OllamaClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url.rstrip("/")
        self.model = self.settings.ollama_model
        self.timeout = self.settings.ollama_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.base_url and self.model)

    def health_check(self) -> bool:
        """Quick check that Ollama is reachable. Does not guarantee the model is pulled."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.ok
        except requests.RequestException:
            return False

    def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Send a chat completion request to Ollama and return the raw text content.

        Raises OllamaUnavailableError if the server can't be reached or errors out,
        so callers can decide how to degrade gracefully.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": DEFAULT_OPTIONS,
        }
        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Ollama request failed: %s", exc)
            raise OllamaUnavailableError(str(exc)) from exc

        data = response.json()
        message = data.get("message") or {}
        content = message.get("content", "")
        if not content:
            raise OllamaUnavailableError("Ollama returned an empty response.")
        return content

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Chat with JSON mode enabled and parse the result. Returns {} on failure."""
        try:
            content = self.chat(system_prompt, user_prompt, json_mode=True)
        except OllamaUnavailableError:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Ollama did not return valid JSON: %s", content[:200])
            return {}
