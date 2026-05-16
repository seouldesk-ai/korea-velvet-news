import os
from pyairtable import Api

_token = os.environ.get("AIRTABLE_TOKEN")
_base_id = os.environ.get("AIRTABLE_BASE_ID")

if not _token or not _base_id:
    raise RuntimeError(
        "Missing required environment variables: AIRTABLE_TOKEN and/or AIRTABLE_BASE_ID. "
        "Set them in your .env file or GitHub Secrets."
    )

_api = Api(_token)


def _table(name: str):
    return _api.table(_base_id, name)


def get_records(table_name: str, filter_formula: str = None, fields: list = None) -> list[dict]:
    """Return all records from a table, with optional formula filter and field subset."""
    kwargs = {}
    if filter_formula:
        kwargs["formula"] = filter_formula
    if fields:
        kwargs["fields"] = fields
    return _table(table_name).all(**kwargs)


def create_record(table_name: str, fields: dict) -> dict:
    """Create a single record and return the created record dict."""
    return _table(table_name).create(fields)


def update_record(table_name: str, record_id: str, fields: dict) -> dict:
    """Update fields of a specific record and return the updated record dict."""
    return _table(table_name).update(record_id, fields)


def batch_update_records(table_name: str, updates: list[dict]) -> list[dict]:
    """Update multiple records. Each item: {"id": record_id, "fields": {...}}."""
    return _table(table_name).batch_update(updates)


def url_exists(url: str) -> bool:
    """Return True if the URL already exists in the Articles table."""
    formula = f"{{url}} = '{url}'"
    records = get_records("Articles", filter_formula=formula, fields=["url"])
    return len(records) > 0


def get_active_keywords() -> list[str]:
    """Return list of keyword strings where is_active is True."""
    records = get_records("Keywords", filter_formula="{is_active} = 1", fields=["keyword"])
    return [r["fields"]["keyword"] for r in records if "keyword" in r["fields"]]


def get_active_glossary() -> list[dict]:
    """Return list of {term_ko, term_en} for active Glossary records."""
    records = get_records(
        "Glossary",
        filter_formula="{is_active} = 1",
        fields=["term_ko", "term_en"],
    )
    return [
        {"term_ko": r["fields"].get("term_ko", ""), "term_en": r["fields"].get("term_en", "")}
        for r in records
        if r["fields"].get("term_ko") and r["fields"].get("term_en")
    ]
