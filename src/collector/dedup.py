from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from src.airtable.client import url_exists

_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "referer",
}


def normalise_url(url: str) -> str:
    """Strip tracking params and normalise scheme/netloc."""
    parsed = urlparse(url)
    params = {k: v for k, v in parse_qs(parsed.query).items() if k not in _TRACKING_PARAMS}
    clean_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower().replace("www.", ""),
        parsed.path.rstrip("/"),
        "",
        clean_query,
        "",
    ))


def deduplicate(articles: list[dict]) -> list[dict]:
    """
    Remove articles whose normalised URL already exists in Airtable or appeared
    earlier in this batch. Mutates each article's 'url' field to the normalised form.
    """
    seen = set()
    unique = []
    for article in articles:
        norm = normalise_url(article["url"])
        if norm in seen:
            continue
        seen.add(norm)
        if url_exists(norm):
            continue
        article["url"] = norm
        unique.append(article)
    return unique
