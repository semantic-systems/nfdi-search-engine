# sources/static/gerit/updater.py
"""
GERiT updater — downloads the monthly institution export from gerit.org,
transforms it from .xlsx to a flat list of JSON records, and writes it
atomically to the shared data volume.

Run periodically (e.g. via cron) to keep the local data up to date:
    python -m sources.static.gerit.updater
"""
import logging
import os
import re

from io import BytesIO
from typing import Dict, List

import openpyxl

from sources.static.base import BaseUpdater

logger = logging.getLogger(__name__)

_DATA_DIR = os.getenv('STATIC_DATA_PATH', '/data')
DATA_PATH = os.path.join(_DATA_DIR, 'gerit.json')

DOWNLOAD_URL = 'https://www.gerit.org/downloads/institutionen_gerit.xlsx'


def _normalize_header(header: str) -> str:
    """
    Convert an xlsx column header to a lowercase snake_case key.
    e.g. 'Einrichtungstyp' -> 'einrichtungstyp'
         'GERiT-ID'        -> 'gerit_id'
         'PLZ / Ort'       -> 'plz_ort'
    """
    header = str(header).strip()
    header = re.sub(r'[^a-zA-Z0-9\u00C0-\u024F]+', '_', header)
    header = header.strip('_').lower()
    return header


class GERiTUpdater(BaseUpdater):

    DOWNLOAD_URL = DOWNLOAD_URL
    DATA_PATH = DATA_PATH
    SOURCE_NAME = 'GERiT'

    def transform(self, content: bytes) -> List[Dict]:
        """
        Parse the GERiT .xlsx file and return a list of normalized record dicts.

        Column headers are read from the first row and normalized to snake_case.
        Unknown columns are included as-is so that future additions to the xlsx
        are preserved without requiring a code change.
        """
        wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
        ws = wb.active

        rows = ws.iter_rows(values_only=True)

        raw_headers = next(rows, None)
        if not raw_headers:
            raise ValueError('xlsx file has no header row')

        headers = [_normalize_header(h) if h is not None else f'col_{i}'
                   for i, h in enumerate(raw_headers)]

        records = []
        for row in rows:
            record = {
                headers[i]: (str(cell).strip() if cell is not None else '')
                for i, cell in enumerate(row)
                if i < len(headers)
            }
            # Skip entirely empty rows
            if any(record.values()):
                records.append(record)

        wb.close()
        return records


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
    GERiTUpdater().run()


if __name__ == '__main__':
    main()
