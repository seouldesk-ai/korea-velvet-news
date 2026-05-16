"""
collect.py — Phase A collection pipeline

Steps:
  1. Load active keywords from Airtable Keywords table
  2. Search Naver + Google News for each keyword
  3. Normalise and deduplicate against existing Airtable records
  4. Create new articles in Airtable (status=collected)
  5. Extract body text for each new article (trafilatura → newspaper → Naver description fallback)
  6. Classify extracted articles in batches (Haiku)
  7. Update Airtable: status=classified or extract_failed

Triggered by collect.yml on Mon/Wed/Fri KST 07:00 and workflow_dispatch.
"""

import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

from src.airtable.client import create_record, update_record, batch_update_records
from src.classifier.classifier import classify_articles
from src.collector.dedup import deduplicate
from src.collector.google_news import search_google_news
from src.collector.naver import search_naver
from src.extractor.crawl import extract_body


def run():
    from src.airtable.client import get_active_keywords
    keywords = get_active_keywords()
    if not keywords:
        print("No active keywords found. Exiting.")
        return

    print(f"Keywords: {keywords}")

    # Collect from Naver + Google News
    raw_articles = []
    for kw in keywords:
        print(f"  Naver: {kw}")
        raw_articles.extend(search_naver(kw))
        print(f"  Google News: {kw}")
        raw_articles.extend(search_google_news(kw))

    print(f"Raw results: {len(raw_articles)}")

    # Deduplicate against Airtable and within batch
    new_articles = deduplicate(raw_articles)
    print(f"New after dedup: {len(new_articles)}")

    if not new_articles:
        print("No new articles. Done.")
        return

    # Create records in Airtable (status=collected)
    created = []
    for article in new_articles:
        record = create_record("Articles", {
            "url": article["url"],
            "title_ko": article.get("title_ko", ""),
            "source_name": article.get("source_name", ""),
            "published_date": article.get("published_date") or str(date.today()),
            "source_type": "auto",
            "status": "collected",
        })
        created.append({
            "id": record["id"],
            "url": article["url"],
            "title_ko": article.get("title_ko", ""),
            "description": article.get("description", ""),
        })
    print(f"Created in Airtable: {len(created)}")

    # Extract body text
    extractable = []
    extract_updates = []
    for article in created:
        body, method = extract_body(article["url"], article.get("description", ""))
        if body:
            extract_updates.append({"id": article["id"], "fields": {"body_ko": body, "status": "extracted"}})
            extractable.append({**article, "body_ko": body})
            print(f"  Extracted ({method}): {article['id']}")
        else:
            extract_updates.append({"id": article["id"], "fields": {"status": "extract_failed"}})
            print(f"  Extract failed: {article['id']}")

    if extract_updates:
        batch_update_records("Articles", extract_updates)

    if not extractable:
        print("No extractable articles for classification. Done.")
        return

    # Classify
    print(f"Classifying {len(extractable)} articles...")
    classifications = classify_articles(extractable)

    classify_updates = []
    for cls in classifications:
        score = cls.get("relevance_score", 3)
        # Phase A: all articles go to pending_review (auto-exclude disabled for first month)
        status = "pending_review"
        classify_updates.append({
            "id": cls["id"],
            "fields": {
                "relevance_score": score,
                "recommendation": cls.get("recommendation", ""),
                "tags_internal": cls.get("tags_internal", []),
                "status": status,
            },
        })

    if classify_updates:
        batch_update_records("Articles", classify_updates)

    print(f"Collection complete. {len(classify_updates)} articles queued for review.")


if __name__ == "__main__":
    run()
