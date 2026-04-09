from dataclasses import dataclass


@dataclass(frozen=True)
class DetailsSettings:
    data_sources: dict
    mapping_preference: dict
    max_workers: int = 16
    formatting_timeout: int = 10

    @classmethod
    def from_config(cls, cfg: dict) -> "DetailsSettings":
        return cls(
            data_sources=cfg["DATA_SOURCES"],
            mapping_preference=cfg["MAPPING_PREFERENCE"],
            max_workers=int(cfg.get("DETAILS_MAX_WORKERS", 16)),
            formatting_timeout=int(cfg.get("DETAILS_FORMATTING_TIMEOUT", 10)),
        )
