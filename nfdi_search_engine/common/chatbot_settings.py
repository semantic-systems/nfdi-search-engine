from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class ChatbotSettings:
    enabled: bool
    server: str
    endpoint_save_docs_with_embeddings: str

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "ChatbotSettings":
        c = cfg.get("CHATBOT", {}) or {}
        return cls(
            enabled=bool(c.get("chatbot_enable", False)),
            server=str(c.get("chatbot_server", "")),
            endpoint_save_docs_with_embeddings=str(
                c.get("endpoint_save_docs_with_embeddings", "")),
        )
