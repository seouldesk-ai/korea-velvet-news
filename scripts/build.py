"""
build.py — Daily build pipeline

Steps:
  1. Process submitted URLs (status=submitted → pending_review)
  2. Translate approved articles (status=approved → translated)
  3. Generate HTML main page
  4. Deploy to gh-pages
  5. Mark translated articles as published in Airtable

Triggered by build.yml daily at KST 07:00 and workflow_dispatch.
"""

from dotenv import load_dotenv
load_dotenv()

from src.airtable.client import get_records, batch_update_records
from src.form_processor.process import process_submitted_urls
from src.publisher.deploy import deploy
from src.publisher.generate import generate_html
from src.translator.translator import translate_article


def run():
    # Step 1: Process submitted URLs
    process_submitted_urls()

    # Step 2: Translate approved articles
    approved = get_records(
        "Articles",
        filter_formula="{status}='approved'",
        fields=["url", "title_ko", "body_ko"],
    )
    print(f"Translating {len(approved)} approved articles...")
    translate_updates = []
    for record in approved:
        f = record["fields"]
        result = translate_article({
            "id": record["id"],
            "title_ko": f.get("title_ko", ""),
            "body_ko": f.get("body_ko", ""),
        })
        if result.get("status") == "translate_failed":
            translate_updates.append({"id": record["id"], "fields": {"status": "translate_failed"}})
            print(f"  Translate failed: {record['id']}")
        else:
            translate_updates.append({
                "id": record["id"],
                "fields": {
                    "title_en": result["title_en"],
                    "body_en": result["body_en"],
                    "status": "translated",
                },
            })
            print(f"  Translated: {record['id']}")

    if translate_updates:
        batch_update_records("Articles", translate_updates)

    # Step 3: Generate HTML
    generate_html()

    # Step 4: Deploy
    deploy()

    # Step 5: Mark translated articles as published
    translated = get_records(
        "Articles",
        filter_formula="{status}='translated'",
        fields=["url"],
    )
    if translated:
        publish_updates = [{"id": r["id"], "fields": {"status": "published"}} for r in translated]
        batch_update_records("Articles", publish_updates)
        print(f"Marked {len(translated)} articles as published.")

    print("Build complete.")


if __name__ == "__main__":
    run()
