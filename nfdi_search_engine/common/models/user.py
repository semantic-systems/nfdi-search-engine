from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from werkzeug.security import generate_password_hash, check_password_hash


@dataclass
class User:
    id: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    password_hash: str = ""
    oauth_source: str = "self"
    included_data_sources: str = ""
    excluded_data_sources: str = ""

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return self.__str__()

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.id

    @classmethod
    def from_dict(cls, doc: dict[str, Any]) -> "User":
        return cls(
            id=str(doc.get("id", "")),
            first_name=str(doc.get("first_name", "")),
            last_name=str(doc.get("last_name", "")),
            email=str(doc.get("email", "")),
            password_hash=str(doc.get("password_hash", "")),
            oauth_source=str(doc.get("oauth_source", "self")),
            included_data_sources=str(doc.get("included_data_sources", "")),
            excluded_data_sources=str(doc.get("excluded_data_sources", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "password_hash": self.password_hash,
            "oauth_source": self.oauth_source,
            "included_data_sources": self.included_data_sources,
            "excluded_data_sources": self.excluded_data_sources,
        }
