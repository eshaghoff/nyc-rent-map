#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# NYC Rent Heat Map — Monthly Data Update
# ═══════════════════════════════════════════════════════════════════════
# Run this script once a month to refresh all data from StreetEasy.
#
# What it does:
#   1. Scrapes active listings from StreetEasy (via Playwright)
#   2. Scrapes recently rented listings (past 6 months)
#   3. Regenerates the baseline heat map (dense grid, median rent)
#   4. Regenerates scenario S2 (dense grid, mean rent)
#   5. Regenerates scenario S3 (6-month rented only)
#   6. Copies fresh data into the deployment directory
#   7. Updates the date in the HTML
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
echo "NYC Rent Heat Map — Monthly Update ($MONTH_YEAR)" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════════════════" | tee -a "$LOG_FILE"

# ─── Step 1: Scrape active listings ─────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 1/7: Scraping active listings..." | tee -a "$LOG_FILE"
cd "$SCRAPER_DIR"
python3 scrape_all.py 2>&1 | tee -a "$LOG_FILE"

ACTIVE_COUNT=$(python3 -c "import json; d=json.load(open('listings_raw.json')); print(len(d))")
echo "  Active listings: $ACTIVE_COUNT" | tee -a "$LOG_FILE"

# ─── Step 2: Scrape rented listings ─────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 2/7: Scraping rented listings (past 6 months)..." | tee -a "$LOG_FILE"
python3 scrape_rented.py 2>&1 | tee -a "$LOG_FILE"

RENTED_COUNT=$(python3 -c "import json; d=json.load(open('rented_raw_v2.json')); print(len(d))")
echo "  Rented listings: $RENTED_COUNT" | tee -a "$LOG_FILE"

# ─── Step 3: Regenerate baseline (dense grid, median) ───────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 3/7: Generating baseline heat points..." | tee -a "$LOG_FILE"
python3 "$GENERATOR_DIR/generate_baseline_v2.py" 2>&1 | tee -a "$LOG_FILE"

# ─── Step 4: Regenerate S2 (dense grid, mean) ───────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 4/7: Generating S2 (mean rent)..." | tee -a "$LOG_FILE"
python3 "$GENERATOR_DIR/generate_s2_dense_mean.py" 2>&1 | tee -a "$LOG_FILE"

# ─── Step 5: Regenerate S3 (6-month rented) ──────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 5/7: Generating S3 (rented past 6 months)..." | tee -a "$LOG_FILE"
python3 "$GENERATOR_DIR/generate_s3_6month.py" 2>&1 | tee -a "$LOG_FILE"

# ─── Step 6: Copy data into deployment ───────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 6/7: Updating deployment files..." | tee -a "$LOG_FILE"

# Copy scenario files
cp /tmp/heat_points_s2_dense_mean.js "$DEPLOY_DIR/heat_points_s2.js"
cp /tmp/heat_points_s3_6month.js "$DEPLOY_DIR/heat_points_s3.js"

# Embed new baseline into index.html
# Extract the HEAT_POINTS array from the generated file
BASELINE_DATA=$(cat /tmp/heat_points_baseline_v2.js)

# Use Python to do the replacement safely
python3 << 'PYEOF'
import re

with open("index.html", "r") as f:
    html = f.read()

with open("/tmp/heat_points_baseline_v2.js", "r") as f:
    new_data = f.read()

# Change const to let for scenario switcher compatibility
new_data = new_data.replace("const HEAT_POINTS", "let HEAT_POINTS", 1)

# Replace the HEAT_POINTS block
pattern = r'let HEAT_POINTS = \[.*?\];'
html_new = re.sub(pattern, new_data.strip(), html, count=1, flags=re.DOTALL)

# Update the date in the subtitle
import datetime
month_year = datetime.datetime.now().strftime("%b %Y")
html_new = re.sub(
    r'(Market-Rate 1BR Listings &middot; StreetEasy &middot; )\w+ \d{4}',
    r'\g<1>' + month_year,
    html_new
)

# Update the point counts in scenario buttons
import json

# Count baseline points
baseline_lines = new_data.strip().split('\n')
baseline_pts = sum(1 for l in baseline_lines if l.strip().startswith('{lat:'))

with open("/tmp/heat_points_s2_dense_mean.js") as f:
    s2_lines = f.read().strip().split('\n')
    s2_pts = sum(1 for l in s2_lines if l.strip().startswith('{lat:'))

with open("/tmp/heat_points_s3_6month.js") as f:
    s3_lines = f.read().strip().split('\n')
    s3_pts = sum(1 for l in s3_lines if l.strip().startswith('{lat:'))

# Update S1 pts
html_new = re.sub(
    r'(id="scenBtnS1">\s*<span class="sc-tag">S1</span>\s*<span class="sc-label">Baseline \(Median\)</span>\s*<span class="sc-pts">)\d+ pts',
    r'\g<1>' + str(baseline_pts) + ' pts',
    html_new
)
# Update S2 pts
html_new = re.sub(
    r'(id="scenBtnS2">\s*<span class="sc-tag">S2</span>\s*<span class="sc-label">Mean Rent</span>\s*<span class="sc-pts">)\d+ pts',
    r'\g<1>' + str(s2_pts) + ' pts',
    html_new
)
# Update S3 pts
html_new = re.sub(
    r'(id="scenBtnS3">\s*<span class="sc-tag">S3</span>\s*<span class="sc-label">Rented Past 6 Months</span>\s*<span class="sc-pts">)\d+ pts',
    r'\g<1>' + str(s3_pts) + ' pts',
    html_new
)

with open("index.html", "w") as f:
    f.write(html_new)

print(f"Updated: S1={baseline_pts}pts, S2={s2_pts}pts, S3={s3_pts}pts, date={month_year}")
PYEOF

echo "  Files updated." | tee -a "$LOG_FILE"

# ─── Step 7: Commit and push ────────────────────────────────────────────
echo "" | tee -a "$LOG_FILE"
echo "Step 7/7: Committing and pushing to GitHub..." | tee -a "$LOG_FILE"
cd "$DEPLOY_DIR"
git add index.html heat_points_s2.js heat_points_s3.js
git commit -m "Monthly data update — $MONTH_YEAR

- $ACTIVE_COUNT active listings
- $RENTED_COUNT rented listings (6-month lookback)
- Fresh heat map data from StreetEasy" || echo "No changes to commit"
git push origin main 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "Update complete! $(date)" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
