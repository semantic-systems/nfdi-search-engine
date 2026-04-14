from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class SearchSettings:
    data_sources: Dict[str, Dict[str, Any]]
    max_workers: int = 16
    first_page_n: int = 20
    lazy_load_n: int = 20
    results_ttl_s: int = 15 * 60  # 15 minutes

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "SearchSettings":
        return cls(
            data_sources=cfg["DATA_SOURCES"],
            max_workers=16,
            first_page_n=int(
                cfg.get("NUMBER_OF_RECORDS_TO_SHOW_ON_PAGE_LOAD", 20)),
            lazy_load_n=int(
                cfg.get("NUMBER_OF_RECORDS_TO_APPEND_ON_LAZY_LOAD", 20)),
            results_ttl_s=int(cfg.get("SEARCH_RESULTS_TTL_SECONDS", 15 * 60)),
        )
