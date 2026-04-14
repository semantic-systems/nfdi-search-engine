from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class RequestMeta:
    url: str
    host: str
    client_ip: str
    url_root: str
    base_url: str
    path: str
    user_email: str
    session_id: str
    visitor_id: str
