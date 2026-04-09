# Google Trends Scraper & Analyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-green.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-orange.svg)](https://playwright.dev/python/)

Scrape and analyze real Google Trends data using a Playwright-based browser automation. No API keys, no accounts, completely free.

Get interest-over-time scores, regional breakdowns, and multi-keyword comparisons — output as clean JSON ready for any pipeline, script, or AI assistant.

## How It Works

The scraper launches a headless Chromium browser, navigates to Google Trends, and intercepts the internal API responses (interest-over-time and interest-by-region). No HTML parsing or screen-scraping — it captures the actual data Google uses to render its charts.

## Installation

### Prerequisites

- **Python 3.9+** — [Download](https://www.python.org/downloads/) (check "Add to PATH" during install)

### Step 1: Install Playwright

```bash
pip install playwright
playwright install chromium
```

<details>
<summary>Troubleshooting</summary>

- `pip not found` — reinstall Python with PATH enabled, or use `python -m pip install playwright`
- `playwright install` hangs — try `playwright install --with-deps chromium`
- Permission errors on Linux/Mac — use `pip install --user playwright`

</details>

### Step 2: Clone the Repo

```bash
git clone https://github.com/judicael-s/google-trends-skill.git
cd google-trends-skill
```

### Step 3: Verify

```bash
python scripts/scraper.py "test" --geo US --outdir /tmp/trends-test
```

If you see `Saved: ...` lines, you're good to go.

## Usage

### CLI

```bash
# Single keyword
python scripts/scraper.py "artificial intelligence" --geo US --outdir ./results

# Multiple keywords (batch comparison)
python scripts/scraper.py "react" "vue" "angular" --geo US --outdir ./results

# Non-US country with matching language
python scripts/scraper.py "croissant" --geo FR --hl fr-FR --outdir ./results
```

### CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--geo CODE` | ISO country code | `US` |
| `--hl CODE` | Language code | `en-US` |
| `--outdir PATH` | Output directory for JSON files | `.` |
| `--visible` | Show browser window (reduces bot detection) | headless |
| `--retries N` | Max retries per keyword | `3` |

## Output Format

For each keyword, the scraper produces:

| File | Contents |
|------|----------|
| `trends_<keyword>_interest_over_time.json` | Weekly interest scores (0-100 scale) over 12 months |
| `trends_<keyword>_interest_by_region.json` | Interest breakdown by subregion (state, province, etc.) |
| `trends_summary.json` | Batch metadata: keywords, geo, timestamp, success/fail status |

### Interest Over Time

Each data point in `default.timelineData[]`:

```json
{
  "time": "1704067200",
  "formattedTime": "Jan 1, 2024",
  "value": [78],
  "formattedValue": ["78"]
}
```

- **100** = peak popularity in the selected period
- All other values are relative to that peak

### Interest By Region

Each entry in `default.geoMapData[]`:

```json
{
  "geoCode": "US-CA",
  "geoName": "California",
  "value": [100],
  "formattedValue": ["100"]
}
```

## Analysis Framework

When used with an AI assistant, the data supports analysis across six dimensions:

1. **Trend Direction** — Growing, declining, stable, or cyclical
2. **Momentum** — Recent data points vs period average
3. **Spikes** — Sudden jumps correlated with events
4. **Seasonality** — Repeating patterns (e.g., "home gym" spikes every January)
5. **Geographic Hotspots** — Top regions by interest
6. **Comparison** (multi-keyword) — Which leads, where they swap, convergence/divergence

## Use as a Claude Code Skill

This repo includes a `SKILL.md` file that turns it into a [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) skill with a full 4-phase workflow (parse, scrape, analyze, recommend).

```bash
# Copy to Claude Code skills directory
cp -r google-trends-skill ~/.claude/skills/google-trends
```

Once installed, just ask Claude naturally:

- *"What's trending for AI tools in the US?"*
- *"Compare React vs Vue vs Angular popularity"*
- *"How does interest in 'home gym' change throughout the year?"*
- *"What are people searching for about remote work in France?"*

Claude will automatically invoke the scraper, analyze the data, and deliver a structured report with recommendations.

## Limitations

- **Rate limits** — Google throttles repeated scrapes. Space out large batches (5+ keywords)
- **Time range** — Default is 12 months. Custom date ranges not currently supported
- **Data scope** — Captures interest-over-time and interest-by-region only (not related queries, YouTube, News, or Shopping breakdowns)
- **Anti-bot** — Headless mode may trigger CAPTCHAs after repeated use. Use `--visible` flag as workaround
- **Relative data** — Google Trends shows relative interest (0-100), not absolute search volume. Treat as directional intelligence

## Credits

The scraper is based on the open-source work by **[Bright Data](https://brightdata.com/)** (formerly Luminati Networks):

- **Original repo:** [luminati-io/google-trends-api](https://github.com/luminati-io/google-trends-api)
- **Enhanced with:** CLI arguments, retry logic, structured JSON output, and AI skill integration

Bright Data provides web data infrastructure and maintains the original Google Trends scraping approach. This project builds on their work with modifications for local CLI usage and AI-assisted analysis.

## License

MIT — see [LICENSE](LICENSE)

## Part of the Marketing Suite

This tool is part of a collection for marketing intelligence:

- **[google-trends-skill](https://github.com/judicael-s/google-trends-skill)** — Search trend analysis (this repo)
- **[google-analytics-skill](https://github.com/judicael-s/google-analytics-skill)** — GA4 reporting & audience insights
- **[google-search-console-skill](https://github.com/judicael-s/google-search-console-skill)** — SEO performance & query analysis
