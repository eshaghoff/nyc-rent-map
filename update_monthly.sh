#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# NYC Rent Heat Map — Quarterly Data Update
# ═══════════════════════════════════════════════════════════════════════
# Run this script quarterly to refresh all data from StreetEasy.
# Cron: 1st of Jan, Apr, Jul, Oct at 3am.
#
# What it does:
#   1. Scrapes active listings from StreetEasy (via Playwright)
#   2. Scrapes recently rented listings (trailing 4 months)
#   3. Regenerates the baseline heat map (dense grid, median rent)
#   4. Regenerates scenario S2 (dense grid, mean rent)
#   5. Regenerates scenario S3 (active + trailing 4 months rented)
#   6. Copies fresh data + updates region medians + listing count in HTML
#   7. Generates a tweet draft with latest stats
#   8. Commits and pushes to GitHub Pages
#
# Prerequisites:
#   - Python 3 with playwright installed: pip3 install playwright && playwright install
#   - Git configured with push access to the repo
#
# Usage:
#   cd /Users/SamuelEshaghoff1/Projects/nyc-rent-map
#   ./update_monthly.sh
# ═══════════════════════════════════════════════════════════════════════

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRAPER_DIR="/Users/SamuelEshaghoff1/Downloads/nyc-rent-scraper"
GENERATOR_DIR="$SCRIPT_DIR/generators"
DEPLOY_DIR="$SCRIPT_DIR"

MONTH_YEAR=$(date +"%b %Y")
LOG_FILE="$SCRIPT_DIR/update_log_$(date +%Y%m%d).txt"

echo "═══════════════════════════════════════════════════════" | tee "$LOG_FILE"
echo "NYC Rent Heat Map — Quarterly Update ($MONTH_YEAR)" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════════════════" | tee -a "$LOG_FILE"

# ─── Step 1: Scrape active listings ─────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 1/8: Scraping active listings..." | tee -a "$LOG_FILE"
cd "$SCRAPER_DIR"
python3 scrape_all.py 2>&1 | tee -a "$LOG_FILE"

ACTIVE_COUNT=$(python3 -c "import json; d=json.load(open('listings_raw.json')); print(len(d))")
echo "  Active listings: $ACTIVE_COUNT" | tee -a "$LOG_FILE"

# ─── Step 2: Scrape rented listings (trailing 4 months) ─────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 2/8: Scraping rented listings (trailing 4 months)..." | tee -a "$LOG_FILE"
python3 scrape_rented.py 2>&1 | tee -a "$LOG_FILE"

RENTED_COUNT=$(python3 -c "import json; d=json.load(open('rented_raw_v2.json')); print(len(d))")
echo "  Rented listings: $RENTED_COUNT" | tee -a "$LOG_FILE"

# ─── Step 3: Regenerate baseline (dense grid, median) ───────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 3/8: Generating baseline heat points..." | tee -a "$LOG_FILE"
BASELINE_OUTPUT=$(python3 "$GENERATOR_DIR/generate_baseline_v2.py" 2>&1)
echo "$BASELINE_OUTPUT" | tee -a "$LOG_FILE"
export BASELINE_OUTPUT

# ─── Step 4: Regenerate S2 (dense grid, mean) ───────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 4/8: Generating S2 (mean rent)..." | tee -a "$LOG_FILE"
python3 "$GENERATOR_DIR/generate_s2_dense_mean.py" 2>&1 | tee -a "$LOG_FILE"

# ─── Step 5: Regenerate S3 (active + trailing 4 months rented) ──────────
echo "" | tee -a "$LOG_FILE"
echo "Step 5/8: Generating S3 (active + rented 4mo)..." | tee -a "$LOG_FILE"
python3 "$GENERATOR_DIR/generate_s3_6month.py" 2>&1 | tee -a "$LOG_FILE"

# ─── Step 6: Copy data into deployment ───────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 6/8: Updating deployment files..." | tee -a "$LOG_FILE"

# Copy scenario files
cp /tmp/heat_points_s2_dense_mean.js "$DEPLOY_DIR/heat_points_s2.js"
cp /tmp/heat_points_s3_6month.js "$DEPLOY_DIR/heat_points_s3.js"

# Embed new baseline into index.html and update stats
python3 << PYEOF
import re, os, sys
import datetime

# Read baseline generator output (passed via env var)
baseline_output = os.environ.get("BASELINE_OUTPUT", "")

with open("index.html", "r") as f:
    html = f.read()

with open("/tmp/heat_points_baseline_v2.js", "r") as f:
    new_data = f.read()

# Change const to let for scenario switcher compatibility
new_data = new_data.replace("const HEAT_POINTS", "let HEAT_POINTS", 1)

# Replace the HEAT_POINTS block
pattern = r'(?:let|const) HEAT_POINTS = \[.*?\];'
html_new = re.sub(pattern, new_data.strip(), html, count=1, flags=re.DOTALL)

# Update the date in the subtitle
month_year = datetime.datetime.now().strftime("%b %Y")
html_new = re.sub(
    r'(1BR Listings &middot; StreetEasy &middot; )[^<]+',
    r'\g<1>' + month_year,
    html_new
)

# Update total listing count in subtitle
total_match = re.search(r'Total listings used: ([\d,]+)', baseline_output)
if total_match:
    total_str = total_match.group(1)
    html_new = re.sub(
        r'[\d,]+ (?:Market-Rate|Rented) 1BR Listings',
        total_str + ' Market-Rate 1BR Listings',
        html_new
    )
    print(f"Updated listing count: {total_str}")

# Update region medians in stats infobox
region_id_map = {
    "Lower Manhattan": "statLowerManhattan",
    "Upper Manhattan": "statUpperManhattan",
    "North Brooklyn": "statNorthBrooklyn",
    "South Brooklyn": "statSouthBrooklyn",
    "W. Queens": "statQueensWest",
    "Queens": "statQueens",
    "South Bronx": "statSouthBronx",
    "Bronx": "statBronx",
    "Staten Island": "statStatenIsland",
}
for line in baseline_output.split('\n'):
    line = line.strip()
    # Parse lines like "  Lower Manhattan: \$4,600 (n=15,273)"
    m = re.match(r'(\w[\w\s]+?):\s+\\\$([\d,]+)\s+\(n=', line)
    if not m:
        m = re.match(r'(\w[\w\s]+?):\s+\$([\d,]+)\s+\(n=', line)
    if m:
        region_name = m.group(1).strip()
        median_val = m.group(2)
        stat_id = region_id_map.get(region_name)
        if stat_id:
            html_new = re.sub(
                rf'(id="{stat_id}">)\$[\d,]+',
                rf'\g<1>\${median_val}',
                html_new
            )
            print(f"  Updated {region_name}: \${median_val}")

# Update NYC overall median
nyc_match = re.search(r'NYC overall median: \$([\d,]+)', baseline_output)
if nyc_match:
    nyc_med = nyc_match.group(1)
    html_new = re.sub(
        r'(id="statNYC">)\$[\d,]+',
        rf'\g<1>\${nyc_med}',
        html_new
    )
    print(f"  Updated NYC Overall: \${nyc_med}")

# Update the point counts in scenario buttons
baseline_lines = new_data.strip().split('\n')
baseline_pts = sum(1 for l in baseline_lines if l.strip().startswith('{lat:'))

with open("/tmp/heat_points_s2_dense_mean.js") as f:
    s2_lines = f.read().strip().split('\n')
    s2_pts = sum(1 for l in s2_lines if l.strip().startswith('{lat:'))

with open("/tmp/heat_points_s3_6month.js") as f:
    s3_lines = f.read().strip().split('\n')
    s3_pts = sum(1 for l in s3_lines if l.strip().startswith('{lat:'))

html_new = re.sub(
    r'(id="scenBtnS1">\s*<span class="sc-tag">S1</span>\s*<span class="sc-label">Baseline \(Median\)</span>\s*<span class="sc-pts">)\d+ pts',
    r'\g<1>' + str(baseline_pts) + ' pts',
    html_new
)
html_new = re.sub(
    r'(id="scenBtnS2">\s*<span class="sc-tag">S2</span>\s*<span class="sc-label">Mean Rent</span>\s*<span class="sc-pts">)\d+ pts',
    r'\g<1>' + str(s2_pts) + ' pts',
    html_new
)
html_new = re.sub(
    r'(id="scenBtnS3">\s*<span class="sc-tag">S3</span>\s*<span class="sc-label">Rented Past 6 Months</span>\s*<span class="sc-pts">)\d+ pts',
    r'\g<1>' + str(s3_pts) + ' pts',
    html_new
)

with open("index.html", "w") as f:
    f.write(html_new)

print(f"\nUpdated: S1={baseline_pts}pts, S2={s2_pts}pts, S3={s3_pts}pts, date={month_year}")
PYEOF

echo "  Files updated." | tee -a "$LOG_FILE"

# ─── Step 7: Generate tweet draft ──────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 7/8: Generating tweet draft..." | tee -a "$LOG_FILE"
python3 << 'TWEETEOF'
import re, os, datetime

output = os.environ.get("BASELINE_OUTPUT", "")

quarter_month = datetime.datetime.now().strftime("%b %Y")

# Parse region medians
medians = {}
for line in output.split('\n'):
    m = re.match(r'\s+(\w[\w\s]+?):\s+\$([\d,]+)\s+\(n=([\d,]+)\)', line.strip())
    if m:
        medians[m.group(1).strip()] = (m.group(2), m.group(3))

# Parse totals
total_match = re.search(r'Total listings used: ([\d,]+)', output)
nyc_match = re.search(r'NYC overall median: \$([\d,]+)', output)
total = total_match.group(1) if total_match else "?"
nyc_med = nyc_match.group(1) if nyc_match else "?"

draft = f"""# Tweet Thread Draft — NYC Rent Heat Map ({quarter_month})

## Tweet 1 (Hook + GIF)
Updated: NYC 1BR rent heat map for {quarter_month}.

{total} market-rate listings from StreetEasy, mapped by median rent across 9 regions.

🔗 eshaghoff.github.io/nyc-rent-map

[Attach: nyc-rent-heatmap-demo.gif]

## Tweet 2 (Key findings)
{quarter_month} median 1BR rents by region:

"""
# Sort by median descending
for region in ["Lower Manhattan", "North Brooklyn", "W. Queens", "South Bronx",
               "Upper Manhattan", "South Brooklyn", "Queens", "Bronx", "Staten Island"]:
    if region in medians:
        med_val, count = medians[region]
        draft += f"• {region}: ${med_val}\n"

draft += f"\nNYC Overall: ${nyc_med}\n"

draft += f"""
## Tweet 3 (CTA)
The map updates quarterly. Filter by region, toggle subway stations and violent crime data, zoom into any neighborhood.

All open source: github.com/eshaghoff/nyc-rent-map

🔗 eshaghoff.github.io/nyc-rent-map
"""

with open("tweet_draft.md", "w") as f:
    f.write(draft)

print(f"  Tweet draft written to tweet_draft.md")
TWEETEOF

# ─── Step 8: Commit and push ────────────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 8/8: Committing and pushing to GitHub..." | tee -a "$LOG_FILE"
cd "$DEPLOY_DIR"
git add index.html heat_points_s2.js heat_points_s3.js tweet_draft.md
git commit -m "Quarterly data update — $MONTH_YEAR

- $ACTIVE_COUNT active + $RENTED_COUNT rented listings (trailing 4-month lookback)
- Fresh heat map data from StreetEasy
- Auto-generated tweet draft" || echo "No changes to commit"
git push origin main 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "Update complete! $(date)" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
