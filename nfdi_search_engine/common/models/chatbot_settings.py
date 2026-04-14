from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class ChatbotSettings:
    enabled: bool
    server: str
    endpoint_save_docs_with_embeddings: str
    endpoint_are_embeddings_generated: str
    endpoint_chat: str
    timeout_s: int = 20

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "ChatbotSettings":
        c = cfg.get("CHATBOT", {}) or {}
        return cls(
            enabled=bool(c.get("chatbot_enable", False)),
            server=str(c.get("chatbot_server", "")),
            endpoint_save_docs_with_embeddings=str(
                c.get("endpoint_save_docs_with_embeddings", "")
            ),
            endpoint_are_embeddings_generated=str(
                c.get("endpoint_are_embeddings_generated", "")
            ),
            endpoint_chat=str(c.get("endpoint_chat", "")),
            timeout_s=int(c.get("timeout_s", 20)),
        )
