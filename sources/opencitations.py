import re
from typing import List
from requests import get
from objects import Person, Article, thing, Organization
from config import Config

_RX_DOI = re.compile(r"10\.\d{4,9}/\S+", re.I)
_RX_ORCID = re.compile(r"orcid:([\d\-Xx]{15,19})")
_RX_CROSSREF = re.compile(r"crossref:(\d+)")
_RX_OMID = re.compile(r"omid:([\w\/]+)")

API_CITATION  = "https://opencitations.net/index/api/v2/citations/doi:"
API_REFERENCE = "https://opencitations.net/index/api/v2/references/doi:"
API_METADATA  = "https://opencitations.net/meta/api/v1/metadata/doi:"

def fetch_citations(doi: str, access_token: str = None):

    # add the access_token to the headers if provided
    access_token = Config.OPENCITATIONS_API_KEY
    HTTP_HEADERS = {}
    if not (access_token is None or access_token == ""):
        HTTP_HEADERS["authorization"] = access_token

    search_url = API_CITATION + doi

    r = get(search_url, timeout=30, headers=HTTP_HEADERS)
    r.raise_for_status()

    return r.json()

def fetch_references(doi: str, access_token: str = None):

    # add the access_token to the headers if provided
    access_token = Config.OPENCITATIONS_API_KEY
    HTTP_HEADERS = {}
    if not (access_token is None or access_token == ""):
        HTTP_HEADERS["authorization"] = access_token

    search_url = API_REFERENCE + doi

    r = get(search_url, timeout=30, headers=HTTP_HEADERS)
    r.raise_for_status()
    return r.json()

def fetch_metadata(dois: list[str], access_token: str = None):
    """
    Request the metadata for a list of DOIs from OpenCitations.

    Args:
        dois (list[str]): A list of DOIs to fetch metadata for.
    """

    if len(dois) == 0:
        return []
    
    # request in batches of 25 if too large
    if len(dois) > 10:
        batches = [dois[i:i + 10] for i in range(0, len(dois), 10)]
        results = []
        for batch in batches:
            results.extend(fetch_metadata(batch, access_token))
        return results

    # add the access_token to the headers if provided
    access_token = Config.OPENCITATIONS_API_KEY
    HTTP_HEADERS = {}
    if not (access_token is None or access_token == ""):
        HTTP_HEADERS["authorization"] = access_token        

    search_url = API_METADATA + "__doi:".join(dois)

    r = get(search_url, timeout=30, headers=HTTP_HEADERS)
    r.raise_for_status()

    return r.json()


def _extract_doi(id_field: str) -> str:
    m = _RX_DOI.search(id_field)
    return m.group(0).lower() if m else ""

def _parse_authors(raw: str) -> List[Person]:
    people: List[Person] = []
    for fragment in (p.strip() for p in raw.split(";") if p.strip()):
        if " [" in fragment:
            name_part, meta_part = fragment.split(" [", 1)
            meta_part = meta_part.rstrip("]")
        else:
            name_part, meta_part = fragment, ""
        if "," in name_part:
            family, given = (t.strip() for t in name_part.split(",", 1))
        else:
            given, family = name_part.strip(), ""
        orcid_match = _RX_ORCID.search(meta_part)
        omid_match = _RX_OMID.search(meta_part)  # currently unused
        identifier = orcid_match.group(1) if orcid_match else ''
        people.append(
            Person(
                name=f"{given} {family}".strip(),
                givenName=given,
                familyName=family,
                identifier=identifier,
            )
        )
    return people

def _parse_publisher(raw: str) -> Organization | None:
    if not raw:
        return None
    if " [" in raw:
        name_part, meta_part = raw.split(" [", 1)
        meta_part = meta_part.rstrip("]")
    else:
        name_part, meta_part = raw, ""
    crossref_match = _RX_CROSSREF.search(meta_part)
    omid_match = _RX_OMID.search(meta_part)             # currently unused
    identifier = crossref_match
    return Organization(name=name_part.strip(), identifier=identifier)

def metadata_to_articles(records: List[dict]) -> List[Article]:

    articles: List[Article] = []

    for rec in records:

        article = Article()
        article.identifier = _extract_doi(rec.get("id", ""))
        article.name = rec.get("title", "")
        article.datePublished = rec.get("pub_date", "")
        article.additionalType = rec.get("type", "")
        article.publication = rec.get("venue", "")

        pages = rec.get("page", "")
        if pages:
            if "-" in pages:
                article.pageStart, article.pageEnd = pages.split("-", 1)
            article.pagination = pages
        
        article.publisher = _parse_publisher(rec.get("publisher", ""))
        article.author = _parse_authors(rec.get("author", ""))
        
        _source = thing()
        _source.name = "OpenCitations"
        _source.identifier = article.identifier
        article.source.append(_source)

        articles.append(article)

    return articles

def get_citations_for_publication(source: str, doi: str, access_token: str = None) -> List[Article]:
    """
    Fetches the citation data for a given DOI from OpenCitations.

    Args:
        doi (str): The DOI of the article to fetch citations for.
        access_token (str, optional): Access token for OpenCitations API.

    Returns:
        List[Article]: A list of Article objects containing citation data.
    """
    citations = fetch_citations(doi, access_token)
    dois = [_extract_doi(citation["citing"]) for citation in citations if _extract_doi(citation["citing"])]
    metadata = fetch_metadata(dois, access_token)
    objects = metadata_to_articles(metadata) if metadata else []
    
    return objects

def get_publication_references(source: str, doi: str, access_token: str = None) -> List[Article]:
    """
    Fetches the references for a given DOI from OpenCitations.

    Args:
        doi (str): The DOI of the article to fetch references for.
        access_token (str, optional): Access token for OpenCitations API.

    Returns:
        List[Article]: A list of Article objects containing reference data.
    """

    article_metadata = fetch_metadata([doi], access_token)
    article = metadata_to_articles(article_metadata)[0]

    refs = fetch_references(doi, access_token)
    dois = [_extract_doi(ref["cited"]) for ref in refs if _extract_doi(ref["cited"])]
    metadata = fetch_metadata(dois, access_token)
    objects = metadata_to_articles(metadata) if metadata else []

    article.reference = objects

    return article