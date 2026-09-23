# Weekly job to download the GERiT institution excel file and save the content as a JSON file.

from __future__ import annotations

import json
import logging
import os
import re

from io import BytesIO
from typing import Any, Dict, List

import openpyxl
from celery.signals import worker_ready
from requests import RequestException

from config import Config
from nfdi_search_engine.infra.jobs.celery_app import celery_app
from sources.http_client import HttpClient

log = logging.getLogger(__name__)

SOURCE = "GERiT"

# the export has German column headers, which become the record keys
UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})

# the source reads these, so the export has to keep providing them
REQUIRED_COLUMNS = (
    "dfg_inst_id",
    "name_deutsch",
    "name_englisch",
    "ort",
    "einrichtungsart_englisch",
    "url_gerit_nachweis",
)


def _config(key: str) -> Any:
    return Config.DATA_SOURCES[SOURCE].get(key)


def _normalize_header(header: Any) -> str:
    """
    Turn a column header into a record key, e.g. DESTATIS Fächergruppe
    englisch into destatis_faechergruppe_englisch.
    """
    key = str(header).strip().lower().translate(UMLAUTS)
    return re.sub(r"[^a-z0-9]+", "_", key).strip("_")


def _transform(content: bytes) -> List[Dict[str, str]]:
    """
    Read the institution sheet of the xlsx export into records.
    """
    workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        rows = workbook.active.iter_rows(values_only=True)
        headers = [_normalize_header(header) for header in next(rows, ())]

        missing = [column for column in REQUIRED_COLUMNS if column not in headers]
        if missing:
            raise ValueError(f"{SOURCE} - the export is missing the columns {missing}")

        # every column is kept, so an added one needs no code change
        records = [
            {
                header: str(cell).strip() if cell is not None else ""
                for header, cell in zip(headers, row)
            }
            for row in rows
        ]
    finally:
        workbook.close()

    return [record for record in records if any(record.values())]


def _write(records: List[Dict[str, str]], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temp_path = f"{path}.tmp"

    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False)

    # swapped in one step, so a search never reads a half written file
    os.replace(temp_path, path)


@celery_app.task(
    name="gerit.refresh",
    autoretry_for=(RequestException,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def refresh() -> None:
    """
    Download the GERiT institution export and store it as the JSON file that
    sources/gerit.py reads.
    """
    path = _config("local-path")

    http = HttpClient(timeout=_config("request-timeout"))
    records = _transform(http.get_bytes(_config("download-url")))
    _write(records, path)

    log.info("%s - wrote %d records to %s", SOURCE, len(records), path)


@worker_ready.connect
def _refresh_if_missing(**kwargs) -> None:
    """
    Fill the JSON file on a fresh deployment, rather than leaving the source
    empty until the weekly job runs.
    """
    if not os.path.exists(_config("local-path")):
        log.info("%s - no local data, queueing a refresh", SOURCE)
        refresh.delay()
