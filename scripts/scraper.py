#!/usr/bin/env python3
"""
Google Trends Scraper — CLI wrapper around Playwright-based scraping.

Based on: https://github.com/luminati-io/google-trends-api
Enhanced with CLI args, retry logic, and structured output.

Usage:
    python scraper.py "keyword" --geo US --hl en-US --outdir ./results
    python scraper.py "keyword1" "keyword2" "keyword3" --geo US --outdir ./results
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: Playwright is not installed.")
    print("Run:  pip install playwright && playwright install chromium")
    sys.exit(1)


def scrape_keyword(keyword: str, geo: str, hl: str, headless: bool, max_retries: int = 3) -> dict:
    """
    Scrape Google Trends data for a single keyword.

    Returns dict with keys: 'interest_over_time', 'interest_by_region'
    Each value is the parsed JSON from Google Trends API, or None if not captured.
    """
    captured_data = {}

    def handle_response(response):
        url = response.url
        if "trends/api/widgetdata/multiline" in url or "trends/api/widgetdata/comparedgeo" in url:
            try:
                text = response.text()
                if not text:
                    return
                # Google prefixes JSON with )]}' — strip it
                if text.startswith(")]}'"):
                    text = text[4:].lstrip(",")
                data = json.loads(text)
                endpoint = "interest_over_time" if "multiline" in url else "interest_by_region"
                captured_data[endpoint] = data
            except Exception as e:
                print(f"  Warning: failed to parse response: {e}", file=sys.stderr)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.on("response", handle_response)

        trends_url = f"https://trends.google.com/trends/explore?geo={geo}&q={keyword}&hl={hl}"

        for attempt in range(1, max_retries + 1):
            captured_data.clear()
            print(f"  Attempt {attempt}/{max_retries} for '{keyword}' (geo={geo})...")

            try:
                page.goto(trends_url, wait_until="networkidle", timeout=30000)
                time.sleep(6)

                # Scroll to trigger lazy-loaded widgets
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                if captured_data:
                    break

                # Retry via page reload
                print(f"  No data yet, refreshing...")
                page.reload(wait_until="networkidle", timeout=30000)
                time.sleep(6)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                if captured_data:
                    break

            except Exception as e:
                print(f"  Error on attempt {attempt}: {e}", file=sys.stderr)
                if attempt < max_retries:
                    time.sleep(2)

        browser.close()

    return captured_data


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Google Trends data for one or more keywords."
    )
    parser.add_argument("keywords", nargs="+", help="Search keyword(s)")
    parser.add_argument("--geo", default="US", help="Country code (default: US)")
    parser.add_argument("--hl", default="en-US", help="Language code (default: en-US)")
    parser.add_argument("--outdir", default=".", help="Output directory for JSON files")
    parser.add_argument("--visible", action="store_true", help="Run browser visibly (reduces detection)")
    parser.add_argument("--retries", type=int, default=3, help="Max retries per keyword (default: 3)")

    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    headless = not args.visible
    all_results = {}

    for keyword in args.keywords:
        print(f"\nScraping: '{keyword}'")
        data = scrape_keyword(keyword, args.geo, args.hl, headless, args.retries)

        if data:
            all_results[keyword] = data
            # Save per-keyword files
            safe_name = keyword.replace(" ", "_").replace("/", "_")
            for endpoint, payload in data.items():
                filepath = outdir / f"trends_{safe_name}_{endpoint}.json"
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                print(f"  Saved: {filepath}")
        else:
            print(f"  WARNING: No data captured for '{keyword}'")
            all_results[keyword] = None

    # Write combined summary
    summary_path = outdir / "trends_summary.json"
    summary = {
        "meta": {
            "geo": args.geo,
            "hl": args.hl,
            "keywords": args.keywords,
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "results": {}
    }
    for kw, data in all_results.items():
        summary["results"][kw] = {
            "has_data": data is not None,
            "endpoints": list(data.keys()) if data else [],
        }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary: {summary_path}")

    # Return non-zero if any keyword failed
    failed = [kw for kw, d in all_results.items() if d is None]
    if failed:
        print(f"\nFailed keywords: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
