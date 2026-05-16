"""
process.py — Handle articles submitted via the Airtable URL form.

Submitted articles have status='submitted' and only a URL field.
This processor:
  1. Fetches all submitted articles
  2. Extracts body text (trafilatura → newspaper)
  3. Updates status to pending_review (skips classification — form submissions are trusted)
  4. Updates status to extract_failed if extraction fails
"""

from src.airtable.client import get_records, batch_update_records
from src.extractor.crawl import extract_body


def process_submitted_urls():
    """Process all articles with status='submitted'."""
    submitted = get_records(
        "Articles",
        filter_formula="{status}='submitted'",
        fields=["url", "title_ko"],
    )
    if not submitted:
        return

    print(f"Processing {len(submitted)} submitted URLs...")
    updates = []
    for record in submitted:
        url = record["fields"].get("url", "")
        if not url:
            updates.append({"id": record["id"], "fields": {"status": "extract_failed"}})
            continue

        body, method = extract_body(url)
        if body:
            updates.append({
                "id": record["id"],
                "fields": {
                    "body_ko": body,
                    "source_type": "form",
                    "status": "pending_review",
                },
            })
            print(f"  Extracted ({method}): {record['id']}")
        else:
            updates.append({"id": record["id"], "fields": {"status": "extract_failed"}})
            print(f"  Extract failed: {record['id']}")

    if updates:
        batch_update_records("Articles", updates)
    print("Form processing complete.")
