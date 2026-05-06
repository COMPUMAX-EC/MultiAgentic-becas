from __future__ import annotations

from urllib.parse import urlsplit


OFFICIAL_DOMAIN_SUFFIXES = (
    ".edu",
    ".edu.au",
    ".edu.co",
    ".edu.mx",
    ".edu.sg",
    ".edu.cn",
    ".ac.uk",
    ".ac.jp",
    ".gov",
    ".gov.au",
    ".gov.br",
    ".gov.ca",
    ".gov.co",
    ".gov.uk",
    ".gouv.fr",
)

SUSPICIOUS_DOMAIN_TERMS = (
    "blogspot",
    "wordpress",
    "substack",
    "medium",
    "linkedin",
    "facebook",
    "reddit",
    "pinterest",
    "applyonline",
    "visa",
    "job",
)


def extract_domain(url: str) -> str | None:
    try:
        parsed_url = urlsplit(url.strip())
    except ValueError:
        return None

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return None

    return normalize_domain(parsed_url.netloc)


def normalize_domain(domain: str) -> str:
    normalized_domain = domain.strip().lower()
    if normalized_domain.startswith("www."):
        normalized_domain = normalized_domain[4:]
    return normalized_domain.split(":")[0]


def is_probably_official_domain(url: str) -> bool:
    domain = extract_domain(url)
    if domain is None:
        return False

    return domain.endswith(OFFICIAL_DOMAIN_SUFFIXES)


def has_suspicious_domain(url: str) -> bool:
    domain = extract_domain(url)
    if domain is None:
        return True

    return any(term in domain for term in SUSPICIOUS_DOMAIN_TERMS)
