---
name: google-trends
description: "Scrape and analyze Google Trends data using a free Playwright-based scraper. Use this skill whenever the user asks about search trends, trending topics, keyword popularity, seasonal interest, search volume over time, regional interest, Google Trends data, or wants to compare how popular different search terms are. Also trigger when the user mentions market research involving search trends, content timing based on search interest, or wants to know when/where something is trending. Even if the user doesn't say 'Google Trends' explicitly — if they're asking about what people are searching for or how interest in a topic changes over time, this skill applies."
license: MIT
---

# Google Trends Scraper & Analyzer

Scrape real Google Trends data, analyze patterns, and deliver actionable recommendations — single keywords or batches. No API keys, no accounts, completely free.

**Source:** [luminati-io/google-trends-api](https://github.com/luminati-io/google-trends-api) — enhanced with CLI arguments, retry logic, and structured JSON output.

## Installation

This skill includes a bundled Python scraper that uses Playwright to automate a real browser visit to Google Trends. First-time setup takes about 2 minutes.

**Step 1: Verify Python**
```bash
python --version  # needs 3.9+
```
If Python is missing: install from [python.org](https://www.python.org/downloads/). Check "Add to PATH" during install.

**Step 2: Install Playwright**
```bash
pip install playwright
playwright install chromium
```

**Troubleshooting:**
- `pip not found` — reinstall Python with PATH enabled, or use `python -m pip install playwright`
- `playwright install` hangs — try `playwright install --with-deps chromium`
- Permission errors on Linux/Mac — use `pip install --user playwright`

**Step 3: Verify the scraper runs**
```bash
python ~/.claude/skills/google-trends/scripts/scraper.py "test" --geo US --outdir /tmp/trends-test
```
If you see "Saved: ..." lines, you're good. Delete the test output when done.

## How It Works

The scraper launches a headless Chromium browser, navigates to Google Trends, intercepts the internal API responses (interest-over-time and interest-by-region), and saves them as clean JSON files. No screen-scraping or HTML parsing — it captures the actual data Google uses to render its charts.

## Workflow

Follow these four phases in order for every request.

### Phase 1: Parse the Request

Extract these parameters from what the user said:

| Parameter | Default | How to infer |
|-----------|---------|--------------|
| **Keywords** | *(required)* | The topic(s) they're asking about |
| **Country** | `US` | Look for country names, codes, or language cues |
| **Language** | `en-US` | Match the country — `fr-FR` for France, `de-DE` for Germany, etc. |

"Compare X and Y" or "X vs Y" means multiple keywords — scrape them all and compare results.

Don't ask clarifying questions if the defaults are reasonable. Just scrape and note what you assumed.

### Phase 2: Scrape

The scraper lives at `~/.claude/skills/google-trends/scripts/scraper.py`.

```bash
# Single keyword
python ~/.claude/skills/google-trends/scripts/scraper.py "artificial intelligence" \
  --geo US --outdir ./trends-results

# Multiple keywords (batched sequentially)
python ~/.claude/skills/google-trends/scripts/scraper.py "react" "vue" "angular" \
  --geo US --outdir ./trends-results

# Non-US country with matching language
python ~/.claude/skills/google-trends/scripts/scraper.py "croissant" \
  --geo FR --hl fr-FR --outdir ./trends-results
```

**CLI flags:**

| Flag | What it does |
|------|-------------|
| `--geo CODE` | ISO country code (default: US) |
| `--hl CODE` | Language code (default: en-US) |
| `--outdir PATH` | Where to save JSON output (default: current dir) |
| `--visible` | Show the browser — helps avoid anti-bot detection |
| `--retries N` | Max retries per keyword (default: 3) |

**Output files per keyword:**
- `trends_<keyword>_interest_over_time.json`
- `trends_<keyword>_interest_by_region.json`
- `trends_summary.json` (metadata for the batch)

**If scraping fails:**
1. Retry with `--visible` (non-headless reduces detection)
2. Wait 60 seconds between batches
3. If persistent blocks: suggest trying from a different network or VPN
4. Last resort: mention the [Bright Data paid API](https://github.com/luminati-io/google-trends-api#bright-data-enterprise-solution) as an alternative

### Phase 3: Analyze

Read the JSON files and build a structured analysis. Here's where the data lives inside each file:

**Interest Over Time** — `default.timelineData[]`:
- `time` (unix timestamp), `formattedTime`, `value[0]` (0-100 scale), `formattedValue[0]`
- 100 = peak popularity in the selected period; everything else is relative to that peak

**Interest By Region** — `default.geoMapData[]`:
- `geoCode`, `geoName`, `value[0]`, `formattedValue[0]`, `hasData[0]`
- Values show relative interest by subregion (state, province, etc.)

**Analysis framework — answer these questions:**

1. **Trend Direction** — Growing, declining, stable, or cyclical? Over what timeframe?
2. **Momentum** — Are recent data points above or below the period average? Accelerating or decelerating?
3. **Spikes** — Any sudden jumps? Try to correlate with known events (launches, news, holidays)
4. **Seasonality** — Repeating patterns? (e.g., "home gym" spikes every January)
5. **Geographic Hotspots** — Top 5 regions by interest. Any surprises?
6. **Comparison** *(multi-keyword only)* — Which leads overall? Where do they swap? Converging or diverging?

### Phase 4: Recommend

Tailor recommendations to the user's context. Read between the lines of their request:

**Content creators / marketers:**
- Best timing to publish (ride the rising wave, don't chase the peak)
- Geographic targeting for ads or localization
- Which keyword variant has momentum (e.g., "AI tools" vs "ChatGPT")
- Content angles suggested by spike triggers

**Product / business:**
- Market entry signals — interest growing in a target region?
- Competitive positioning — which terms are gaining on yours?
- Seasonal planning — when to ramp inventory, campaigns, hiring

**Researchers / analysts:**
- Trend lifecycle stage (emerging / peaking / mature / declining)
- Correlation hooks with external datasets
- Confidence and data quality notes

**Always include these caveats:**
- Google Trends shows *relative* interest (0-100 scale), not absolute search volume
- Data is sampled — small fluctuations may be noise, not signal
- Regional data can be sparse for niche topics in small countries
- This is a snapshot — trends shift; re-scrape for updates

## Output Format

Present your analysis using this template:

```
## Google Trends: [keyword(s)] — [country]

### Key Findings
- [2-3 bullets with the most important takeaways]

### Trend Over Time
[Direction, momentum, notable spikes or dips]
[Include a mini data table for key months if it helps tell the story]

### Regional Interest
| Rank | Region | Interest Score |
|------|--------|---------------|
| 1    | ...    | ...           |
[Top 5 regions + any geographic pattern worth noting]

### Comparison (multi-keyword only)
[Head-to-head: which leads, where, and by how much]

### Recommendations
[3-5 actionable items matched to the user's context]

### Data Files
- `trends_<keyword>_interest_over_time.json`
- `trends_<keyword>_interest_by_region.json`
```

## Limitations

- **Rate limits:** Google throttles repeated scrapes. Space out large batches (5+ keywords).
- **Time range:** Default is 12 months. The scraper doesn't currently support custom date ranges (the Bright Data API does).
- **Data types:** Only captures interest-over-time and interest-by-region. Does not capture related queries, related topics, or YouTube/News/Shopping breakdowns.
- **Anti-bot:** Headless mode may trigger CAPTCHAs after repeated use. Use `--visible` flag as a workaround.
- **Accuracy:** Google Trends data is normalized and sampled. Treat it as directional intelligence, not precision metrics.
