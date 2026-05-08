import re
from typing import Any


def normalize_string(s: str) -> str:
    """
    Normalize a string for comparison
    
    Examples:
    - "Smith, John" -> "smith john"
    - "Jane Doe" -> "jane doe"
    """
    if not s:
        return ""
    re_punctuation = re.compile(r"[–—\-,\.]+")
    s = re_punctuation.sub(" ", s.strip().lower())
    return " ".join(s.split())


def normalize_doi(raw: Any) -> str:
    """Normalize a DOI for comparison

    Examples:
    - "https://doi.org/10.1234/abc" -> "10.1234/abc"
    - "doi:10.1234/abc" -> "10.1234/abc"
    - "10.1234/abc.v2" -> "10.1234/abc"
    """
    if not raw:
        return ""
    s = str(raw).strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi: ", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    # strip version suffixes like ".v1", ".v2" (Figshare pattern)
    s = re.compile(r"\.v\d+$").sub("", s)
    return s


def normalize_orcid(raw: Any) -> str:
    """Normalize an ORCID for comparison

    Examples:
    - "https://orcid.org/0000-0001-2345-6789" -> "0000-0001-2345-6789"
    """
    if not raw:
        return ""
    s = str(raw).strip().lower()
    for prefix in ("https://orcid.org/", "http://orcid.org/"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s


def normalize_name(name: str) -> str:
    """
    Normalize a researcher name for comparison

    Examples:
    - "Dr. Jane Doe" -> "jane doe"
    - "Smith, John" -> "smith john"
    """
    if not name:
        return ""
    
    s = name.strip().lower()
    
    # remove titles like "Dr.", "Prof.", "Ing."
    re_title = re.compile(r"^(prof\.?\s+|dr\.?\s+|mr\.?\s+|mrs\.?\s+|ms\.?\s+|ing\.?\s+)+", re.IGNORECASE)
    s = re_title.sub("", s)
    
    s = s.replace(",", "")
    return " ".join(s.split())
