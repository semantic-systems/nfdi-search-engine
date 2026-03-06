from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class OpenAISettings:
    url_chat_completions: str
    api_key: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    timeout_s: int = 30

    @classmethod
    def from_config(cls, cfg: dict) -> "OpenAISettings":
        llms = cfg.get("LLMS", {}) or {}
        openai = llms.get("openai", {}) or {}
        return cls(
            url_chat_completions=str(openai.get("url_chat_completions", "")),
            api_key=str(cfg.get("OPENAI_API_KEY", "")) or "",
        )
