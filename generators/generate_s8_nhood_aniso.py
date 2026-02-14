#!/usr/bin/env python3
"""
S8: Neighborhood-weighted cells + gentle anisotropic smoothing.
Two fixes stacked:
  1. Cell means: each neighborhood contributes equally (from S7)
  2. Smoothing: neighbors with very different rents contribute less
     w = (1/dist) * exp(-rent_diff² / sigma²), sigma=$1,500
This fixes both the cell-mixing problem AND the smoothing-drag problem.
"""

import json
import math
import os
from collections import defaultdict, Counter
from statistics import median
from datetime import datetime, timedelta

# ─── Load data (active + trailing 4 months rented) ──────────────────────
cutoff_date = (datetime.now() - timedelta(days=4 * 30)).date()
CUTOFF_DATE = cutoff_date.strftime("%Y-%m-%d")

with open("/Users/SamuelEshaghoff1/Downloads/nyc-rent-scraper/rented_raw_v2.json") as f:
    rented_v2 = json.load(f)

rented_recent = [r for r in rented_v2 if r.get("rented_date", "") >= CUTOFF_DATE]

# Load active listings if available
listings_path = "/Users/SamuelEshaghoff1/Downloads/nyc-rent-scraper/listings_raw.json"
listings = []
if os.path.exists(listings_path):
    with open(listings_path) as f:
        listings = json.load(f)

all_raw = listings + rented_recent

if listings:
    print(f"Raw listings loaded: {len(listings)} active + {len(rented_recent)} rented (4mo) = {len(all_raw)} total")
else:
    print(f"Raw listings loaded: {len(rented_recent)} rented (4mo, no active listings available)")
print(f"Date range for subtitle: {datetime.now().strftime('%b %Y')}")

# ─── Step 1: Filter to 1BR only ─────────────────────────────────────────
one_br = [l for l in all_raw if l.get("beds") == 1]
print(f"1BR listings: {len(one_br)}")

# ─── Step 2: Remove bad data ────────────────────────────────────────────
BAD_TYPES = {"THREEFAMILY", "TWOFAMILY", "MIXED_USE", "TOWNHOUSE", "LAND",
             "FOURFAMILY", "MULTIFAMILY", "COMMERCIAL"}

removed_high_rent = 0
removed_bad_type = 0
removed_no_coords = 0
cleaned = []

for l in one_br:
    rent = l.get("rent", 0)
    ptype = (l.get("type") or "").upper()
    lat = l.get("lat")
    lng = l.get("lng")

    if not lat or not lng:
        removed_no_coords += 1
        continue
    if rent > 25000:
        removed_high_rent += 1
        continue
    if ptype in BAD_TYPES:
        removed_bad_type += 1
        continue
    if rent < 500:
        continue
    cleaned.append(l)

print(f"\nRemoved for bad data:")
print(f"  Rent > $25,000: {removed_high_rent}")
print(f"  Bad property type: {removed_bad_type}")
print(f"  No coordinates: {removed_no_coords}")
print(f"  Remaining after cleaning: {len(cleaned)}")

# ─── Step 3: Region assignment (9 custom regions) ────────────────────────
REGION_MAP = {
    # South Bronx (below 149th St)
    "Mott Haven": "South Bronx", "Melrose": "South Bronx", "Hunts Point": "South Bronx",
    "Longwood": "South Bronx", "Morrisania": "South Bronx", "Concourse": "South Bronx",
    "Highbridge": "South Bronx", "Crotona Park East": "South Bronx", "Woodstock": "South Bronx",
    # Bronx Main (above 149th St)
    "Bedford Park": "Bronx", "Belmont": "Bronx", "Bronxwood": "Bronx",
    "City Island": "Bronx", "Claremont": "Bronx", "Country Club": "Bronx",
    "East Tremont": "Bronx", "Fieldston": "Bronx", "Fordham": "Bronx",
    "Kingsbridge": "Bronx", "Kingsbridge Heights": "Bronx", "Laconia": "Bronx",
    "Locust Point": "Bronx", "Morris Heights": "Bronx", "Morris Park": "Bronx",
    "Mt. Hope": "Bronx", "Norwood": "Bronx", "Parkchester": "Bronx",
    "Pelham Bay": "Bronx", "Pelham Gardens": "Bronx", "Pelham Parkway": "Bronx",
    "Riverdale": "Bronx", "Schuylerville": "Bronx", "Soundview": "Bronx",
    "Spuyten Duyvil": "Bronx", "Throgs Neck": "Bronx", "Tremont": "Bronx",
    "University Heights": "Bronx", "Van Nest": "Bronx", "Wakefield": "Bronx",
    "West Farms": "Bronx", "Westchester Square": "Bronx", "Williamsbridge": "Bronx",
    # Lower Manhattan (below 96th East / 110th West)
    "Battery Park City": "Lower Manhattan", "Beekman": "Lower Manhattan",
    "Carnegie Hill": "Lower Manhattan", "Central Park South": "Lower Manhattan",
    "Chelsea": "Lower Manhattan", "Chinatown": "Lower Manhattan",
    "Civic Center": "Lower Manhattan", "East Village": "Lower Manhattan",
    "Financial District": "Lower Manhattan", "Flatiron": "Lower Manhattan",
    "Fulton/Seaport": "Lower Manhattan", "Gramercy Park": "Lower Manhattan",
    "Greenwich Village": "Lower Manhattan", "Hell's Kitchen": "Lower Manhattan",
    "Hudson Square": "Lower Manhattan", "Hudson Yards": "Lower Manhattan",
    "Kips Bay": "Lower Manhattan", "Lenox Hill": "Lower Manhattan",
    "Lincoln Square": "Lower Manhattan", "Little Italy": "Lower Manhattan",
    "Lower East Side": "Lower Manhattan", "Madison": "Lower Manhattan",
    "Manhattan Valley": "Lower Manhattan", "Midtown": "Lower Manhattan",
    "Midtown South": "Lower Manhattan", "Murray Hill": "Lower Manhattan",
    "NoMad": "Lower Manhattan", "Noho": "Lower Manhattan", "Nolita": "Lower Manhattan",
    "Roosevelt Island": "Lower Manhattan", "Soho": "Lower Manhattan",
    "Stuyvesant Town/PCV": "Lower Manhattan", "Sutton Place": "Lower Manhattan",
    "Tribeca": "Lower Manhattan", "Turtle Bay": "Lower Manhattan",
    "Two Bridges": "Lower Manhattan", "Upper Carnegie Hill": "Lower Manhattan",
    "Upper East Side": "Lower Manhattan", "Upper West Side": "Lower Manhattan",
    "West Chelsea": "Lower Manhattan", "West Village": "Lower Manhattan",
    "Yorkville": "Lower Manhattan",
    # Upper Manhattan (Harlem and above)
    "Central Harlem": "Upper Manhattan", "East Harlem": "Upper Manhattan",
    "Fort George": "Upper Manhattan", "Hamilton Heights": "Upper Manhattan",
    "Hudson Heights": "Upper Manhattan", "Inwood": "Upper Manhattan",
    "Manhattanville": "Upper Manhattan", "Marble Hill": "Upper Manhattan",
    "Morningside Heights": "Upper Manhattan", "South Harlem": "Upper Manhattan",
    "Washington Heights": "Upper Manhattan", "West Harlem": "Upper Manhattan",
    # North Brooklyn (above Empire Blvd / Prospect Expwy)
    "Bedford-Stuyvesant": "North Brooklyn", "Boerum Hill": "North Brooklyn",
    "Brooklyn Heights": "North Brooklyn", "Bushwick": "North Brooklyn",
    "Carroll Gardens": "North Brooklyn", "Clinton Hill": "North Brooklyn",
    "Cobble Hill": "North Brooklyn", "Columbia St Waterfront District": "North Brooklyn",
    "Crown Heights": "North Brooklyn", "DUMBO": "North Brooklyn",
    "Downtown Brooklyn": "North Brooklyn", "East Williamsburg": "North Brooklyn",
    "Fort Greene": "North Brooklyn", "Gowanus": "North Brooklyn",
    "Greenpoint": "North Brooklyn", "Ocean Hill": "North Brooklyn",
    "Park Slope": "North Brooklyn", "Prospect Heights": "North Brooklyn",
    "Red Hook": "North Brooklyn", "Stuyvesant Heights": "North Brooklyn",
    "Vinegar Hill": "North Brooklyn", "Weeksville": "North Brooklyn",
    "Williamsburg": "North Brooklyn", "Windsor Terrace": "North Brooklyn",
    # South Brooklyn (below Empire Blvd / Prospect Expwy)
    "Bath Beach": "South Brooklyn", "Bay Ridge": "South Brooklyn",
    "Bensonhurst": "South Brooklyn", "Bergen Beach": "South Brooklyn",
    "Borough Park": "South Brooklyn", "Brownsville": "South Brooklyn",
    "Canarsie": "South Brooklyn", "City Line": "South Brooklyn",
    "Coney Island": "South Brooklyn", "Cypress Hills": "South Brooklyn",
    "Ditmas Park": "South Brooklyn", "Dyker Heights": "South Brooklyn",
    "East Flatbush": "South Brooklyn", "East New York": "South Brooklyn",
    "Farragut": "South Brooklyn", "Fiske Terrace": "South Brooklyn",
    "Flatbush": "South Brooklyn", "Flatlands": "South Brooklyn",
    "Fort Hamilton": "South Brooklyn", "Gravesend": "South Brooklyn",
    "Greenwood": "South Brooklyn", "Homecrest": "South Brooklyn",
    "Kensington": "South Brooklyn", "Manhattan Beach": "South Brooklyn",
    "Mapleton": "South Brooklyn", "Marine Park": "South Brooklyn",
    "Midwood": "South Brooklyn", "Mill Basin": "South Brooklyn",
    "New Lots": "South Brooklyn", "Prospect Lefferts Gardens": "South Brooklyn",
    "Prospect Park South": "South Brooklyn", "Sheepshead Bay": "South Brooklyn",
    "Starrett City": "South Brooklyn", "Sunset Park": "South Brooklyn",
    "Wingate": "South Brooklyn",
    # Staten Island
    "Annadale": "Staten Island", "Arden Heights": "Staten Island",
    "Arrochar": "Staten Island", "Bulls Head": "Staten Island",
    "Castleton Corners": "Staten Island", "Clifton": "Staten Island",
    "Dongan Hills": "Staten Island", "Elm Park": "Staten Island",
    "Eltingville": "Staten Island", "Emerson Hill": "Staten Island",
    "Grant City": "Staten Island", "Graniteville": "Staten Island",
    "Grasmere": "Staten Island", "Great Kills": "Staten Island",
    "Grymes Hill": "Staten Island", "Huguenot": "Staten Island",
    "Mariners Harbor": "Staten Island", "Meiers Corners": "Staten Island",
    "Midland Beach": "Staten Island", "New Brighton": "Staten Island",
    "New Dorp": "Staten Island", "New Dorp Beach": "Staten Island",
    "New Springville": "Staten Island", "Oakwood": "Staten Island",
    "Park Hill": "Staten Island", "Port Richmond": "Staten Island",
    "Princes Bay": "Staten Island", "Richmondtown": "Staten Island",
    "Rosebank": "Staten Island", "Rossville": "Staten Island",
    "Saint George": "Staten Island", "Shore Acres": "Staten Island",
    "Silver Lake": "Staten Island", "South Beach": "Staten Island",
    "Stapleton": "Staten Island", "Tompkinsville": "Staten Island",
    "Tottenville": "Staten Island", "West Brighton": "Staten Island",
    "Westerleigh": "Staten Island", "Willowbrook": "Staten Island",
    "Woodrow": "Staten Island",
    # W. Queens (west of BQE)
    "Astoria": "W. Queens", "Ditmars-Steinway": "W. Queens",
    "Hunters Point": "W. Queens", "Long Island City": "W. Queens",
    "Sunnyside": "W. Queens", "Woodside": "W. Queens",
    # Queens Main (east of BQE)
    "Arverne": "Queens", "Auburndale": "Queens", "Bay Terrace": "Queens",
    "Bayside": "Queens", "Bayswater": "Queens", "Beechhurst": "Queens",
    "Briarwood": "Queens", "Brookville": "Queens", "College Point": "Queens",
    "Corona": "Queens", "Douglaston": "Queens", "East Elmhurst": "Queens",
    "East Flushing": "Queens", "Elmhurst": "Queens", "Far Rockaway": "Queens",
    "Flushing": "Queens", "Forest Hills": "Queens", "Fresh Meadows": "Queens",
    "Glen Oaks": "Queens", "Glendale": "Queens", "Hillcrest": "Queens",
    "Hollis": "Queens", "Jackson Heights": "Queens", "Jamaica": "Queens",
    "Jamaica Estates": "Queens", "Jamaica Hills": "Queens", "Kew Gardens": "Queens",
    "Kew Gardens Hills": "Queens", "Laurelton": "Queens", "Lindenwood": "Queens",
    "Little Neck": "Queens", "Malba": "Queens", "Maspeth": "Queens",
    "Middle Village": "Queens", "North Corona": "Queens", "North New York": "Queens",
    "Oakland Gardens": "Queens", "Old Howard Beach": "Queens", "Ozone Park": "Queens",
    "Pomonok": "Queens", "Queens": "Queens", "Queens Village": "Queens",
    "Ramblersville": "Queens", "Rego Park": "Queens", "Richmond Hill": "Queens",
    "Ridgewood": "Queens", "Rockaway Park": "Queens", "Rockwood Park": "Queens",
    "Rosedale": "Queens", "South Jamaica": "Queens", "South Ozone Park": "Queens",
    "Springfield Gardens": "Queens", "St. Albans": "Queens",
    "The Rockaways": "Queens", "Whitestone": "Queens", "Woodhaven": "Queens",
}

def get_region(listing):
    n = listing.get("neighborhood", "")
    if n in REGION_MAP:
        return REGION_MAP[n]
    lat = listing["lat"]
    lng = listing["lng"]
    # Staten Island
    if lat < 40.65 and lng < -74.04:
        return "Staten Island"
    # Bronx
    if lat > 40.85 or (lat > 40.80 and lng > -73.94):
        if lat < 40.818:
            return "South Bronx"
        return "Bronx"
    # Manhattan
    if -74.03 < lng < -73.90 and 40.70 < lat < 40.88:
        if lng > -73.96 or lat < 40.75:
            # East side: 96th St boundary (~40.785)
            # West side: 110th St boundary (~40.800)
            if lng > -73.96 and lat >= 40.785:
                return "Upper Manhattan"
            if lng <= -73.96 and lat >= 40.800:
                return "Upper Manhattan"
            return "Lower Manhattan"
    # Brooklyn
    if lat < 40.74 and lng < -73.83:
        if lat > 40.660:
            return "North Brooklyn"
        return "South Brooklyn"
    # Queens
    if lng > -73.95 and lng < -73.90 and lat > 40.73:
        return "W. Queens"
    return "Queens"

for l in cleaned:
    l["borough"] = get_region(l)

unknowns = [l for l in cleaned if l["borough"] == "Unknown"]
if unknowns:
    unknown_hoods = Counter(l.get("neighborhood", "?") for l in unknowns)
    print(f"\nUnknown region listings: {len(unknowns)}")
    for h, c in unknown_hoods.most_common(20):
        sample = next(l for l in unknowns if l.get("neighborhood") == h)
        print(f"  {h}: {c} (lat={sample['lat']}, lng={sample['lng']})")

# ─── Step 4: RS Filter ──────────────────────────────────────────────────
SPATIAL_GRID = 0.01
spatial_cells = defaultdict(list)
for l in cleaned:
    key = (round(l["lat"] / SPATIAL_GRID) * SPATIAL_GRID,
           round(l["lng"] / SPATIAL_GRID) * SPATIAL_GRID)
    spatial_cells[key].append(l["rent"])

spatial_medians = {}
for key, rents in spatial_cells.items():
    if len(rents) >= 3:
        spatial_medians[key] = median(rents)

def get_spatial_median(lat, lng):
    key = (round(lat / SPATIAL_GRID) * SPATIAL_GRID,
           round(lng / SPATIAL_GRID) * SPATIAL_GRID)
    return spatial_medians.get(key)

rs_flagged = 0
non_rs = []
for l in cleaned:
    rent = l["rent"]
    lat = l["lat"]
    lng = l["lng"]
    is_rs = False

    # Single RS rule: Below 60% of local spatial median
    sm = get_spatial_median(lat, lng)
    if sm and rent < sm * 0.60:
        is_rs = True

    if is_rs:
        rs_flagged += 1
    else:
        non_rs.append(l)

print(f"\nRS filter: flagged {rs_flagged} listings (below 60% of spatial median)")
print(f"After RS filter: {len(non_rs)} listings")

# ─── Step 5: Borough medians ────────────────────────────────────────────
borough_listings = defaultdict(list)
for l in non_rs:
    borough_listings[l["borough"]].append(l)

print(f"\nRegion means:")
borough_means = {}
for borough, lsts in sorted(borough_listings.items()):
    rents = [l["rent"] for l in lsts]
    avg = int(round(sum(rents) / len(rents)))
    borough_means[borough] = avg
    print(f"  {borough}: ${avg:,.0f} (n={len(rents)})")

# ─── Step 6: Dense adaptive grid heat points ────────────────────────────
def get_grid_size(lat, lng):
    if lat < 40.786 and lng > -74.02 and lng < -73.93:
        return 0.002
    if 40.68 < lat < 40.73 and -73.99 < lng < -73.93:
        return 0.002
    return 0.003

# FIX: Require >= 2 listings per cell to eliminate ghost points
MIN_CELL_COUNT = 2

grid_cells = defaultdict(list)
for l in non_rs:
    lat = l["lat"]
    lng = l["lng"]
    gs = get_grid_size(lat, lng)
    cell_lat = round(lat / gs) * gs
    cell_lng = round(lng / gs) * gs
    key = (round(cell_lat, 6), round(cell_lng, 6), gs)
    grid_cells[key].append(l)

heat_points = []
dropped_thin = 0
nhood_weighted_cells = 0
for (clat, clng, gs), lsts in grid_cells.items():
    if len(lsts) < MIN_CELL_COUNT:
        dropped_thin += 1
        continue
    # ─── KEY CHANGE: Neighborhood-weighted mean ─────────────────────
    # Group listings by neighborhood, compute mean per neighborhood,
    # then average across neighborhoods (each neighborhood = equal weight).
    by_nhood = defaultdict(list)
    for l in lsts:
        nhood = l.get("neighborhood", "Unknown")
        by_nhood[nhood].append(l["rent"])
    if len(by_nhood) > 1:
        # Multiple neighborhoods share this cell — weight equally
        nhood_means = []
        for nhood, rents in by_nhood.items():
            nhood_means.append(sum(rents) / len(rents))
        cell_rent = sum(nhood_means) / len(nhood_means)
        nhood_weighted_cells += 1
    else:
        # Single neighborhood — straight mean (no change from baseline)
        rents = [l["rent"] for l in lsts]
        cell_rent = sum(rents) / len(rents)
    heat_points.append({
        "lat": round(clat, 4),
        "lng": round(clng, 4),
        "rent": int(round(cell_rent)),
        "count": len(lsts),
    })
print(f"Neighborhood-weighted cells: {nhood_weighted_cells}/{len(heat_points)} cells had multiple neighborhoods")

# ─── Gentle anisotropic smoothing ──────────────────────────────────────
# w = (1/dist) * exp(-rent_diff² / sigma²)
# sigma=$1,500: a $1,500 gap → 37% influence, $3,000 gap → ~1%
SMOOTH_RADIUS = 0.008
RENT_SIGMA = 1500
RENT_SIGMA_SQ = RENT_SIGMA ** 2

smoothed_points = []
for i, hp in enumerate(heat_points):
    total_weight = 2.0
    weighted_rent = hp["rent"] * 2.0
    for j, other in enumerate(heat_points):
        if i == j:
            continue
        dlat = hp["lat"] - other["lat"]
        dlng = hp["lng"] - other["lng"]
        dist = math.sqrt(dlat**2 + dlng**2)
        if dist < SMOOTH_RADIUS and dist > 0:
            dist_w = 1.0 / dist
            rent_diff = hp["rent"] - other["rent"]
            rent_penalty = math.exp(-(rent_diff ** 2) / RENT_SIGMA_SQ)
            w = dist_w * rent_penalty
            total_weight += w
            weighted_rent += other["rent"] * w
    smoothed_rent = int(round(weighted_rent / total_weight))
    smoothed_points.append({
        "lat": hp["lat"],
        "lng": hp["lng"],
        "rent": smoothed_rent,
        "count": hp["count"],
    })
heat_points = smoothed_points
print(f"Anisotropic smoothing (radius={SMOOTH_RADIUS}, sigma=${RENT_SIGMA:,})")

# ─── Neighbor median clamping ────────────────────────────────────────────
# FIX: Relaxed from >= 2 neighbors to >= 1 to catch isolated outliers
CLAMP_RADIUS = 0.015
CLAMP_THRESHOLD = 1.50
CLAMP_MAX_N = 10
clamped_count = 0
for i, hp in enumerate(heat_points):
    if hp["count"] >= CLAMP_MAX_N:
        continue
    neighbors = []
    for j, other in enumerate(heat_points):
        if i == j:
            continue
        dlat = hp["lat"] - other["lat"]
        dlng = hp["lng"] - other["lng"]
        dist = math.sqrt(dlat**2 + dlng**2)
        if dist < CLAMP_RADIUS:
            neighbors.append(other["rent"])
    if len(neighbors) >= 1:
        neighbor_med = sorted(neighbors)[len(neighbors) // 2]
        if hp["rent"] > neighbor_med * CLAMP_THRESHOLD:
            old_rent = hp["rent"]
            hp["rent"] = neighbor_med
            clamped_count += 1
            if old_rent > neighbor_med * 2:
                print(f"  CLAMPED: ({hp['lat']},{hp['lng']}) ${old_rent:,} → ${neighbor_med:,} (n={hp['count']}, {len(neighbors)} neighbors)")
print(f"Neighbor median clamping: {clamped_count} points clamped (n<{CLAMP_MAX_N}, >{CLAMP_THRESHOLD:.0%} of neighbor median)")

heat_points.sort(key=lambda x: (-x["rent"], x["lat"]))
print(f"\nHeat points generated: {len(heat_points)} (dropped {dropped_thin} thin cells with <{MIN_CELL_COUNT} listings)")

# ─── Write output ────────────────────────────────────────────────────────
with open("/tmp/heat_points_s8_nhood_aniso.js", "w") as f:
    f.write("const HEAT_POINTS = [\n")
    for hp in heat_points:
        f.write(f"  {{lat:{hp['lat']},lng:{hp['lng']},rent:{hp['rent']},n:{hp['count']}}},\n")
    f.write("];\n")

print(f"\nOutput: /tmp/heat_points_s8_nhood_aniso.js")

# ─── Summary ─────────────────────────────────────────────────────────────
all_rents = [l["rent"] for l in non_rs]
nyc_mean = int(round(sum(all_rents) / len(all_rents)))
print(f"\nNYC overall mean: ${nyc_mean:,}")
print(f"Total listings used: {len(non_rs)}")

# Noho / Nolita diagnostic
print("\n--- Key micro-neighborhood check ---")
checks = {
    "Noho":          (40.724, 40.732, -73.996, -73.990),
    "Nolita":        (40.720, 40.726, -73.998, -73.992),
    "Hudson Square": (40.724, 40.730, -74.008, -74.002),
    "Tribeca":       (40.714, 40.722, -74.010, -74.002),
    "Chinatown":     (40.714, 40.720, -73.998, -73.992),
    "East Village":  (40.724, 40.732, -73.990, -73.982),
    "West Village":  (40.728, 40.738, -74.006, -73.998),
}
for name, (lat_lo, lat_hi, lng_lo, lng_hi) in checks.items():
    cells = [hp for hp in heat_points if lat_lo <= hp["lat"] <= lat_hi and lng_lo <= hp["lng"] <= lng_hi]
    if cells:
        rents = [c["rent"] for c in cells]
        print(f"  {name:>14}: {len(cells)} cells, ${min(rents):,}-${max(rents):,}, avg ${sum(rents)//len(rents):,}")
    else:
        print(f"  {name:>14}: no cells")
