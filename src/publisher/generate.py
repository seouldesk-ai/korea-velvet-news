"""
generate.py — Build the main page HTML from Airtable data.

Loads all translated/published articles for the current month,
renders current_month.html via Jinja2, and writes index.html to /output/.
"""

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.airtable.client import get_records

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
_OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
_FORM_URL = "https://airtable.com/appovMgZeAduoscP0/shr96xJ5xmOAtucFS"


def _format_date(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' to '9 May 2026'."""
    try:
        d = date.fromisoformat(date_str)
        return f"{d.day} {d.strftime('%B')} {d.year}"
    except Exception:
        return date_str


def _get_current_month_articles() -> list[dict]:
    """Fetch translated + published articles for the current month from Airtable."""
    today = date.today()
    month_key = today.strftime("%Y-%m")
    formula = (
        f"AND("
        f"OR({{status}}='translated', {{status}}='published'), "
        f"{{month_key}}='{month_key}'"
        f")"
    )
    records = get_records("Articles", filter_formula=formula)
    articles = []
    for r in records:
        f = r["fields"]
        attachments = f.get("image_attachments") or []
        articles.append({
            "id": r["id"],
            "title_en": f.get("title_en", ""),
            "body_en": f.get("body_en", ""),
            "published_date": f.get("published_date", ""),
            "source_name": f.get("source_name", ""),
            "url": f.get("url", ""),
            "image_url": f.get("image_url", ""),
            "image_attachments": attachments,
        })
    # Sort by published_date descending
    articles.sort(key=lambda a: a["published_date"], reverse=True)
    return articles


def generate_html(output_path: Path = None) -> Path:
    """Render index.html and write to output_path (default: /output/index.html)."""
    if output_path is None:
        output_path = _OUTPUT_DIR / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    articles = _get_current_month_articles()
    today = date.today()

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)
    # Register date formatter as a filter
    env.filters["format_date"] = _format_date

    template = env.get_template("current_month.html")
    html = template.render(
        as_of_date=_format_date(str(today)),
        month_label=today.strftime("%B %Y"),
        articles=articles,
        form_url=_FORM_URL,
    )

    output_path.write_text(html, encoding="utf-8")
    print(f"Generated: {output_path} ({len(articles)} articles)")
    return output_path
