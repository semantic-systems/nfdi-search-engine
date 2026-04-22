# sources/static/base.py
import json
import logging
import os
import requests

from abc import abstractmethod
from typing import Any, Dict, Iterable, List

from config import Config
from sources.base import BaseSource

logger = logging.getLogger('nfdi_search_engine')


class BaseStaticSource(BaseSource):
    """
    Base class for sources backed by a local JSON file rather than a live API.

    Subclasses must define:
      - DATA_PATH: str           path to the local JSON file
      - map_hit(hit) -> object   map a record dict to a domain object
      - search(...)              append mapped objects to the correct results bucket

    Subclasses may override:
      - filter_record(record, search_term) -> bool
        Default performs a case-insensitive substring scan across all string values.
        Override with targeted field matching for better precision and performance.
    """

    DATA_PATH: str = ''

    def fetch(self, search_term: str, failed_sources: list) -> List[Dict] | None:
        """Load the full dataset from the local JSON file."""
        try:
            with open(self.DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning('%s - Data file not found at %s. Has the updater run?', self.__class__.__name__, self.DATA_PATH)
            if failed_sources is not None:
                failed_sources.append(self.__class__.__name__)
            return None
        except Exception as e:
            logger.error('%s - Failed to load data file: %s', self.__class__.__name__, e)
            if failed_sources is not None:
                failed_sources.append(self.__class__.__name__)
            return None

    def filter_record(self, record: Dict, search_term: str) -> bool:
        """
        Return True if the record matches the search term.
        Default: case-insensitive substring check across all non-empty string values.
        Subclasses should override for targeted field matching.
        """
        term = search_term.lower()
        return any(term in str(v).lower() for v in record.values() if v)

    def extract_hits(self, raw: List[Dict], search_term: str = '') -> Iterable[Dict]:
        """Filter the full dataset to records matching the search term."""
        if not raw:
            return []
        if not search_term:
            return raw
        return [record for record in raw if self.filter_record(record, search_term)]

    @abstractmethod
    def map_hit(self, hit: Dict[str, Any]):
        """Map a single record dict to a domain object (e.g. Organization)."""
        ...

    @abstractmethod
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        ...


class BaseUpdater:
    """
    Base class for updaters that download a remote file, transform it into a
    list of record dicts, and write the result atomically to a local JSON file.

    Subclasses must define:
      - DOWNLOAD_URL: str        URL to fetch the source file from
      - DATA_PATH: str           path to write the output JSON file
      - SOURCE_NAME: str         human-readable name used in log messages
      - transform(content: bytes) -> List[Dict]   parse raw bytes into records

    The run() method handles download → transform → atomic write. It is the
    intended entrypoint for the cron job.
    """

    DOWNLOAD_URL: str = ''
    DATA_PATH: str = ''
    SOURCE_NAME: str = ''

    @abstractmethod
    def transform(self, content: bytes) -> List[Dict]:
        """Parse raw file content and return a list of normalized record dicts."""
        ...

    def run(self) -> None:
        logger.info('%s - Starting update from %s', self.SOURCE_NAME, self.DOWNLOAD_URL)

        try:
            response = requests.get(
                self.DOWNLOAD_URL,
                timeout=int(Config.REQUEST_TIMEOUT),
                headers={'User-Agent': Config.REQUEST_HEADER_USER_AGENT},
            )
            response.raise_for_status()
        except Exception as e:
            logger.error('%s - Download failed: %s', self.SOURCE_NAME, e)
            return

        try:
            records = self.transform(response.content)
        except Exception as e:
            logger.error('%s - Transform failed: %s', self.SOURCE_NAME, e)
            return

        tmp_path = self.DATA_PATH + '.tmp'
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.DATA_PATH)), exist_ok=True)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.DATA_PATH)
            logger.info('%s - Successfully wrote %d records to %s', self.SOURCE_NAME, len(records), self.DATA_PATH)
        except Exception as e:
            logger.error('%s - Write failed: %s', self.SOURCE_NAME, e)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
