import re
from typing import Any, Dict, Iterable, List, Optional

from nfdi_search_engine.common.models.objects import Article, Author, Organization, thing
from sources import data_retriever
from config import Config

from sources.base import BaseSource

_ORCID_PATH_RE = re.compile(
    r"^(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$", re.IGNORECASE
)


def _normalize_orcid_path(orcid: str) -> Optional[str]:
    """Return canonical ORCID path (e.g. 0000-0002-1825-0097) or None if invalid."""
    s = (orcid or "").strip().lower()
    for prefix in ("https://orcid.org/", "http://orcid.org/"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
    s = s.strip().strip("/")
    m = _ORCID_PATH_RE.match(s)
    return m.group(1).upper() if m else None


def _leaf_value(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict) and "value" in node:
        v = node.get("value")
        return str(v) if v is not None else ""
    return str(node)


def _doi_from_work_summary(ws: Dict[str, Any]) -> str:
    ext = (ws.get("external-ids") or {}).get("external-id") or []
    if isinstance(ext, dict):
        ext = [ext]
    for item in ext:
        if not isinstance(item, dict):
            continue
        if (item.get("external-id-type") or "").lower() != "doi":
            continue
        val = (item.get("external-id-value") or "").strip()
        if val:
            return val.lower()
    return ""


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


class ORCID(BaseSource):

    SOURCE = 'ORCID'

    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(
            base_url=Config.DATA_SOURCES[self.SOURCE].get('search-endpoint', ''),
            search_term=search_term,
        )

        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        if raw is None:
            return []

        records_found = raw.get('num-found', 0)
        authors = raw.get('expanded-result', None)
        
        if records_found > 0 and authors:
            self.log_event(type="info", message=f"{self.SOURCE} - {records_found} records matched; pulled top {len(authors)}")
            return authors
        
        return []

    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        authorObj = Author()
        authorObj.identifier = hit.get('orcid-id', '')
        given_names = hit.get('given-names', '')
        family_names = hit.get('family-names', '')
        authorObj.name = given_names + " " + family_names
        authorObj.additionalType = 'Person'
        
        institution = hit.get('institution-name', [])
        for inst in institution:
            authorObj.affiliation.append(Organization(name=inst))
        
        authorObj.works_count = ''
        authorObj.cited_by_count = ''

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get('orcid-id', '')
        _source.url = 'https://orcid.org/' + hit.get('orcid-id', '')
        authorObj.source.append(_source)

        return authorObj

    def get_researcher(self, orcid: str, researchers: List[Any]) -> None:
        """
        Load a public ORCID record (v3.0) and map it to an Author.
        Used when OpenAlex has no author for this ORCID but the registry does.
        """
        orcid_path = _normalize_orcid_path(orcid)
        if not orcid_path:
            return

        base = Config.DATA_SOURCES[self.SOURCE].get("get-researcher-endpoint", "")
        if not str(base).strip():
            return

        record = data_retriever.retrieve_object(
            base_url=base,
            identifier=f"{orcid_path}/record",
            quote=False,
        )

        if not record or not isinstance(record, dict):
            return

        oid = record.get("orcid-identifier") or {}
        path = _leaf_value(oid.get("path")) or orcid_path

        person = record.get("person") or {}
        name_block = person.get("name") or {}
        given = _leaf_value(name_block.get("given-names"))
        family = _leaf_value(name_block.get("family-name"))
        display_name = f"{given} {family}".strip() or _leaf_value(name_block.get("credit-name"))

        author = Author()
        author.additionalType = "Person"
        author.identifier = path
        author.url = f"https://orcid.org/{path}"
        author.name = display_name

        for on in _as_list((person.get("other-names") or {}).get("other-name")):
            if isinstance(on, dict):
                c = on.get("content")
                if isinstance(c, str) and c.strip():
                    author.alternateName.append(c.strip())

        bio = person.get("biography") or {}
        if isinstance(bio.get("content"), str) and bio["content"].strip():
            author.about = bio["content"].strip()

        for kw in _as_list((person.get("keywords") or {}).get("keyword")):
            if isinstance(kw, dict):
                c = kw.get("content")
                if isinstance(c, str) and c.strip():
                    author.researchAreas.append(c.strip())

        activities = record.get("activities-summary") or {}
        emp_root = activities.get("employments") or {}
        for group in _as_list(emp_root.get("affiliation-group")):
            if not isinstance(group, dict):
                continue
            for item in _as_list(group.get("summaries")):
                if not isinstance(item, dict):
                    continue
                es = item.get("employment-summary") or {}
                if not isinstance(es, dict):
                    continue
                org = es.get("organization") or {}
                if not isinstance(org, dict):
                    continue
                org_name = (org.get("name") or "").strip()
                if not org_name:
                    continue
                o = Organization()
                o.name = org_name
                sd, ed = es.get("start-date") or {}, es.get("end-date") or {}
                y_start = _leaf_value(sd.get("year")) if isinstance(sd, dict) else ""
                y_end = _leaf_value(ed.get("year")) if isinstance(ed, dict) else ""
                if y_start and y_end:
                    o.keywords.append(f"{y_end}-{y_start}")
                elif y_start:
                    o.keywords.append(y_start)
                author.affiliation.append(o)

        works_root = activities.get("works") or {}
        seen: set[str] = set()
        for group in _as_list(works_root.get("group")):
            if not isinstance(group, dict):
                continue
            summaries = _as_list(group.get("work-summary"))
            if not summaries:
                continue
            ws = summaries[0]
            if not isinstance(ws, dict):
                continue
            title_block = ws.get("title") or {}
            title_obj = title_block.get("title") if isinstance(title_block, dict) else None
            title = _leaf_value(title_obj) if title_obj is not None else ""
            doi = _doi_from_work_summary(ws)
            dedupe_key = doi or str(ws.get("path") or ws.get("put-code") or title)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            art = Article(
                name=title or "(untitled)",
                identifier=doi,
            )
            author.works.append(art)

        author.works_count = str(len(author.works)) if author.works else ""

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = path
        _source.url = author.url
        author.source.append(_source)

        researchers.append(author)

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term)

        if raw is None:
            return

        hits = self.extract_hits(raw)

        for hit in hits:
            authorObj = self.map_hit(hit)
            results['researchers'].append(authorObj)


def search(search_term: str, results, tracking=None):
    """
    Entrypoint to search ORCID researchers.
    """
    ORCID(tracking).search(search_term, results)


def get_researcher(orcid: str, researchers: list, tracking=None):
    """
    Entrypoint to load one researcher from the public ORCID record API.
    """
    ORCID(tracking).get_researcher(orcid, researchers)
