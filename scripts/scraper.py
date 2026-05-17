#!/usr/bin/env python3
"""
Google Trends Scraper — CLI wrapper around Playwright-based scraping.

Based on: https://github.com/luminati-io/google-trends-api
Enhanced with CLI args, retry logic, and structured output.

Usage:
    python scraper.py "keyword" --geo US --hl en-US --outdir ./results
    python scraper.py "keyword1" "keyword2" "keyword3" --geo US --outdir ./results
    python scraper.py "keyword1" "keyword2" --compare --geo US --outdir ./results
    python scraper.py "keyword" --timeframe 5y --geo US --outdir ./results
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: Playwright is not installed.")
    print("Run:  pip install playwright && playwright install chromium")
    sys.exit(1)


TIMEFRAME_PRESETS = {
    "1m": "today%201-m",
    "3m": "today%203-m",
    "12m": "today%2012-m",
    "5y": "today%205-y",
    "all": "all",
}


def _detect_captcha(page) -> bool:
    """Check if Google is showing a CAPTCHA / bot-detection page."""
    try:
        title = page.title().lower()
        content = page.content().lower()
        for signal in ("unusual traffic", "captcha", "verify"):
            if signal in title or signal in content:
                return True
    except Exception:
        pass
    return False


def _build_trends_url(keywords: list[str], geo: str, hl: str, timeframe: str | None) -> str:
    """Build a Google Trends explore URL with properly encoded parameters."""
    q_value = ",".join(quote_plus(kw) for kw in keywords)
    url = f"https://trends.google.com/trends/explore?geo={geo}&q={q_value}&hl={hl}"
    if timeframe and timeframe != "12m":
        date_param = TIMEFRAME_PRESETS.get(timeframe, timeframe)
        url += f"&date={date_param}"
    return url


def scrape_keyword(
    keyword: str,
    geo: str,
    hl: str,
    headless: bool,
    max_retries: int = 3,
    timeframe: str | None = None,
) -> dict:
    """
    Scrape Google Trends data for a single keyword.

    Returns dict with keys: 'interest_over_time', 'interest_by_region'
    Each value is the parsed JSON from Google Trends API, or None if not captured.
    """
    captured_data = {}
    error_info = {"attempts": 0, "error": None, "last_error_message": None}

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

        trends_url = _build_trends_url([keyword], geo, hl, timeframe)

        for attempt in range(1, max_retries + 1):
            captured_data.clear()
            error_info["attempts"] = attempt
            print(f"  Attempt {attempt}/{max_retries} for '{keyword}' (geo={geo})...")

            try:
                page.goto(trends_url, wait_until="networkidle", timeout=30000)
                time.sleep(6)

                if _detect_captcha(page):
                    error_info["error"] = "captcha_suspected"
                    error_info["last_error_message"] = "Google CAPTCHA / bot detection triggered"
                    print(f"  CAPTCHA detected on attempt {attempt}", file=sys.stderr)
                    if attempt < max_retries:
                        time.sleep(2)
                    continue

                # Scroll to trigger lazy-loaded widgets
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                if captured_data:
                    error_info["error"] = None
                    break

                # Retry via page reload
                print(f"  No data yet, refreshing...")
                page.reload(wait_until="networkidle", timeout=30000)
                time.sleep(6)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                if captured_data:
                    error_info["error"] = None
                    break

                error_info["error"] = "no_data"
                error_info["last_error_message"] = "No API responses captured after reload"

            except Exception as e:
                err_msg = str(e)
                if "timeout" in err_msg.lower():
                    error_info["error"] = "timeout"
                else:
                    error_info["error"] = "network_error"
                error_info["last_error_message"] = err_msg
                print(f"  Error on attempt {attempt}: {e}", file=sys.stderr)
                if attempt < max_retries:
                    time.sleep(2)

        browser.close()

    return {"data": captured_data, "error_info": error_info}


def scrape_comparison(
    keywords: list[str],
    geo: str,
    hl: str,
    headless: bool,
    max_retries: int = 3,
    timeframe: str | None = None,
) -> dict:
    """
    Scrape Google Trends comparison data for multiple keywords in a single query.

    Google Trends normalizes keywords against each other only when they appear
    in the same URL (comma-separated in the q parameter).

    Returns dict with keys: 'interest_over_time', 'interest_by_region'
    """
    captured_data = {}
    error_info = {"attempts": 0, "error": None, "last_error_message": None}

    def handle_response(response):
        url = response.url
        if "trends/api/widgetdata/multiline" in url or "trends/api/widgetdata/comparedgeo" in url:
            try:
                text = response.text()
                if not text:
                    return
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

        trends_url = _build_trends_url(keywords, geo, hl, timeframe)
        label = ", ".join(keywords)

        for attempt in range(1, max_retries + 1):
            captured_data.clear()
            error_info["attempts"] = attempt
            print(f"  Attempt {attempt}/{max_retries} for comparison [{label}] (geo={geo})...")

            try:
                page.goto(trends_url, wait_until="networkidle", timeout=30000)
                time.sleep(6)

                if _detect_captcha(page):
                    error_info["error"] = "captcha_suspected"
                    error_info["last_error_message"] = "Google CAPTCHA / bot detection triggered"
                    print(f"  CAPTCHA detected on attempt {attempt}", file=sys.stderr)
                    if attempt < max_retries:
                        time.sleep(2)
                    continue

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                if captured_data:
                    error_info["error"] = None
                    break

                print(f"  No data yet, refreshing...")
                page.reload(wait_until="networkidle", timeout=30000)
                time.sleep(6)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                if captured_data:
                    error_info["error"] = None
                    break

                error_info["error"] = "no_data"
                error_info["last_error_message"] = "No API responses captured after reload"

            except Exception as e:
                err_msg = str(e)
                if "timeout" in err_msg.lower():
                    error_info["error"] = "timeout"
                else:
                    error_info["error"] = "network_error"
                error_info["last_error_message"] = err_msg
                print(f"  Error on attempt {attempt}: {e}", file=sys.stderr)
                if attempt < max_retries:
                    time.sleep(2)

        browser.close()

    return {"data": captured_data, "error_info": error_info}


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
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare keywords in a single query (Google normalizes them against each other)",
    )
    parser.add_argument(
        "--timeframe",
        default="12m",
        help="Time range: 1m, 3m, 12m (default), 5y, all, or custom date string",
    )

    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    headless = not args.visible
    all_results = {}
    error_report = {"failed_keywords": [], "successful_keywords": []}

    # --- Comparison mode ---
    if args.compare:
        if len(args.keywords) < 2:
            print("ERROR: --compare requires at least 2 keywords.", file=sys.stderr)
            sys.exit(1)

        print(f"\nComparing: {', '.join(args.keywords)}")
        result = scrape_comparison(
            args.keywords, args.geo, args.hl, headless, args.retries, args.timeframe
        )
        data = result["data"]
        err = result["error_info"]

        if data:
            for endpoint, payload in data.items():
                filepath = outdir / f"trends_comparison_{endpoint}.json"
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                print(f"  Saved: {filepath}")
            for kw in args.keywords:
                error_report["successful_keywords"].append(kw)
        else:
            label = ", ".join(args.keywords)
            print(f"  WARNING: No data captured for comparison [{label}]")
            for kw in args.keywords:
                error_report["failed_keywords"].append({
                    "keyword": kw,
                    "error": err.get("error", "no_data"),
                    "attempts": err.get("attempts", args.retries),
                    "last_error_message": err.get("last_error_message", "No data captured"),
                })

        # Write summary for comparison
        summary_path = outdir / "trends_summary.json"
        summary = {
            "meta": {
                "geo": args.geo,
                "hl": args.hl,
                "keywords": args.keywords,
                "mode": "comparison",
                "timeframe": args.timeframe,
                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "results": {
                "comparison": {
                    "has_data": bool(data),
                    "endpoints": list(data.keys()) if data else [],
                }
            },
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSummary: {summary_path}")

        # Write error report
        if error_report["failed_keywords"]:
            error_path = outdir / "trends_errors.json"
            with open(error_path, "w", encoding="utf-8") as f:
                json.dump(error_report, f, indent=2)
            print(f"Error report: {error_path}")
            print(f"\nFailed keywords: {', '.join(kw for kw in args.keywords)}", file=sys.stderr)
            sys.exit(1)

        return

    # --- Sequential (independent) mode ---
    for keyword in args.keywords:
        print(f"\nScraping: '{keyword}'")
        result = scrape_keyword(keyword, args.geo, args.hl, headless, args.retries, args.timeframe)
        data = result["data"]
        err = result["error_info"]

        if data:
            all_results[keyword] = data
            error_report["successful_keywords"].append(keyword)
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
            error_report["failed_keywords"].append({
                "keyword": keyword,
                "error": err.get("error", "no_data"),
                "attempts": err.get("attempts", args.retries),
                "last_error_message": err.get("last_error_message", "No data captured"),
            })

    # Write combined summary
    summary_path = outdir / "trends_summary.json"
    summary = {
        "meta": {
            "geo": args.geo,
            "hl": args.hl,
            "keywords": args.keywords,
            "mode": "independent",
            "timeframe": args.timeframe,
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

    # Write error report
    failed = [kw for kw, d in all_results.items() if d is None]
    if error_report["failed_keywords"]:
        error_path = outdir / "trends_errors.json"
        with open(error_path, "w", encoding="utf-8") as f:
            json.dump(error_report, f, indent=2)
        print(f"Error report: {error_path}")

    if failed:
        print(f"\nFailed keywords: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
