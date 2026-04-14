# sources/static/gerit/gerit.py
import logging

from typing import Any, Dict, Iterable, List

from config import Config
from nfdi_search_engine.common.models.objects import Organization, thing
from sources.static.base import BaseStaticSource

logger = logging.getLogger('nfdi_search_engine')


class GERiT(BaseStaticSource):
    """
    Source for GERiT - German Research Institutions.

    Data is provided as a monthly .xlsx download from gerit.org and converted
    to a local JSON file by the gerit updater service. This class reads that
    file and exposes it through the standard BaseSource search interface.
    """

    SOURCE = 'GERiT'
    DATA_PATH = Config.DATA_SOURCES['GERiT']['data-path']

    def filter_record(self, record: Dict, search_term: str) -> bool:
        """Match on institution name (German and English), city, and institution type."""
        term = search_term.lower()
        return any(
            term in (record.get(field) or '').lower()
            for field in ('name_deutsch', 'name_englisch', 'ort', 'einrichtungsart', 'einrichtungsart_englisch')
        )

    def extract_hits(self, raw: List[Dict], search_term: str = '') -> Iterable[Dict]:
        if not raw:
            return []
        if not search_term:
            return raw
        hits = [record for record in raw if self.filter_record(record, search_term)]
        self.log_event(type="info", message=f"{self.SOURCE} - {len(raw)} records total; {len(hits)} matched '{search_term}'")
        return hits

    def map_hit(self, hit: Dict[str, Any]) -> Organization:
        org = Organization()

        org.identifier = hit.get('dfg_inst_id', '')
        org.name = hit.get('name_deutsch', '')
        org.additionalType = hit.get('einrichtungsart_englisch', '') or hit.get('einrichtungsart', '')
        org.url = hit.get('url_der_einrichtung', '')

        english_name = hit.get('name_englisch', '')
        if english_name:
            org.alternateName.append(english_name)

        street = ' '.join(filter(None, [hit.get('adresse', ''), hit.get('hausnummer', '')]))
        postal_city = ' '.join(filter(None, [hit.get('postleitzahl_vor_ort', ''), hit.get('ort', '')]))
        org.address = ', '.join(filter(None, [street, postal_city]))

        seen = set()
        for field in ('destatis_fächergruppe_englisch', 'destatis_lehr_forschungsbereich_englisch', 'destatis_fachgebiet_englisch'):
            val = hit.get(field, '')
            if val and val not in seen:
                org.keywords.append(val)
                seen.add(val)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = org.identifier
        _source.url = hit.get('url_gerit_nachweis', '')
        org.source.append(_source)

        return org

    def search(self, search_term: str, results: dict) -> None:
        raw = self.fetch(search_term, failed_sources=None)
        if raw is None:
            return
        hits = list(self.extract_hits(raw, search_term))
        for hit in hits:
            org = self.map_hit(hit)
            if org:
                results['organizations'].append(org)


def search(search_term: str, results: dict, tracking=None) -> None:
    """Entrypoint to search GERiT institutions."""
    GERiT(tracking).search(search_term, results)
