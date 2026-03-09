from __future__ import annotations
import logging
import anthropic
from config import config

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all Claude-powered agents."""

    SONNET = "claude-sonnet-4-6"
    HAIKU = "claude-haiku-4-5-20251001"

    def __init__(self, model: str = HAIKU):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = model

    def run(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ) -> str:
        logger.debug(f"[{self.__class__.__name__}] Calling {self.model}")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def _load_prompt(self, filename: str) -> str:
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "prompts", filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
