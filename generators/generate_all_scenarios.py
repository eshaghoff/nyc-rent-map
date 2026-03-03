#!/usr/bin/env python3
"""
Unified generator: produces 6 heat map datasets (1BR/2BR/3BR × mean/median).
Reads from the Q1 2026 archive on the Mac Mini.
Outputs /tmp/all_scenarios.js with all data arrays + metadata.
"""

import json
import math
import os
from collections import defaultdict, Counter
from statistics import median as stat_median
from datetime import datetime, timedelta

DATA_DIR = "/Users/samueleshaghoff/projects/Projects/nyc-rent-map/data/archive/2026-Q1/raw"

# ─── Data files by bed count ────────────────────────────────────────────
BED_FILES = {
    "1br": {
        "active": os.path.join(DATA_DIR, "listings_raw.json"),
        "rented": os.path.join(DATA_DIR, "rented_raw_v2.json"),
    },
    "2br": {
        "active": os.path.join(DATA_DIR, "listings_raw_2br.json"),
        "rented": os.path.join(DATA_DIR, "rented_raw_v2_2br.json"),
    },
    "3br": {
        "active": os.path.join(DATA_DIR, "listings_raw_3br.json"),
        "rented": os.path.join(DATA_DIR, "rented_raw_v2_3br.json"),
    },
}

# Only remove genuinely non-residential types
BAD_TYPES = {"LAND", "COMMERCIAL", "MIXED_USE"}

cutoff_date = (datetime.now() - timedelta(days=4 * 30)).date()
CUTOFF_DATE = cutoff_date.strftime("%Y-%m-%d")

# ─── Region map ──────────────────────────────────────────────────────────
REGION_MAP = {
    "Mott Haven": "South Bronx", "Melrose": "South Bronx", "Hunts Point": "South Bronx",
    "Longwood": "South Bronx", "Morrisania": "South Bronx", "Concourse": "South Bronx",
    "Highbridge": "South Bronx", "Crotona Park East": "South Bronx", "Woodstock": "South Bronx",
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
    "Central Harlem": "Upper Manhattan", "East Harlem": "Upper Manhattan",
    "Fort George": "Upper Manhattan", "Hamilton Heights": "Upper Manhattan",
    "Hudson Heights": "Upper Manhattan", "Inwood": "Upper Manhattan",
    "Manhattanville": "Upper Manhattan", "Marble Hill": "Upper Manhattan",
    "Morningside Heights": "Upper Manhattan", "South Harlem": "Upper Manhattan",
    "Washington Heights": "Upper Manhattan", "West Harlem": "Upper Manhattan",
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
    "Astoria": "W. Queens", "Ditmars-Steinway": "W. Queens",
    "Hunters Point": "W. Queens", "Long Island City": "W. Queens",
    "Sunnyside": "W. Queens", "Woodside": "W. Queens",
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
    if lat < 40.65 and lng < -74.04:
        return "Staten Island"
    if lat > 40.85 or (lat > 40.80 and lng > -73.94):
        if lat < 40.818:
            return "South Bronx"
        return "Bronx"
    if -74.03 < lng < -73.90 and 40.70 < lat < 40.88:
        if lng > -73.96 or lat < 40.75:
            if lng > -73.96 and lat >= 40.785:
                return "Upper Manhattan"
            if lng <= -73.96 and lat >= 40.800:
                return "Upper Manhattan"
            return "Lower Manhattan"
    if lat < 40.74 and lng < -73.83:
        if lat > 40.660:
            return "North Brooklyn"
        return "South Brooklyn"
    if lng > -73.95 and lng < -73.90 and lat > 40.73:
        return "W. Queens"
    return "Queens"


def get_grid_size(lat, lng):
    if lat < 40.786 and lng > -74.02 and lng < -73.93:
        return 0.002
    if 40.68 < lat < 40.73 and -73.99 < lng < -73.93:
        return 0.002
    return 0.003


def generate_heat_points(listings, agg_func):
    """Generate heat points from cleaned listings using given aggregation (mean or median)."""
    # RS filter: remove listings below 60% of spatial median
    SPATIAL_GRID = 0.01
    spatial_cells = defaultdict(list)
    for l in listings:
        key = (round(l["lat"] / SPATIAL_GRID) * SPATIAL_GRID,
               round(l["lng"] / SPATIAL_GRID) * SPATIAL_GRID)
        spatial_cells[key].append(l["rent"])

    spatial_medians = {}
    for key, rents in spatial_cells.items():
        if len(rents) >= 3:
            spatial_medians[key] = stat_median(rents)

    non_rs = []
    for l in listings:
        rent = l["rent"]
        key = (round(l["lat"] / SPATIAL_GRID) * SPATIAL_GRID,
               round(l["lng"] / SPATIAL_GRID) * SPATIAL_GRID)
        sm = spatial_medians.get(key)
        if sm and rent < sm * 0.60:
            continue
        non_rs.append(l)

    # Grid cells
    MIN_CELL_COUNT = 2
    grid_cells = defaultdict(list)
    for l in non_rs:
        lat, lng = l["lat"], l["lng"]
        gs = get_grid_size(lat, lng)
        cell_lat = round(lat / gs) * gs
        cell_lng = round(lng / gs) * gs
        key = (round(cell_lat, 6), round(cell_lng, 6), gs)
        grid_cells[key].append(l)

    heat_points = []
    for (clat, clng, gs), lsts in grid_cells.items():
        if len(lsts) < MIN_CELL_COUNT:
            continue
        rents = [l["rent"] for l in lsts]
        if agg_func == "mean":
            agg_rent = sum(rents) / len(rents)
        else:
            agg_rent = stat_median(rents)
        heat_points.append({
            "lat": round(clat, 4),
            "lng": round(clng, 4),
            "rent": int(round(agg_rent)),
            "count": len(lsts),
        })

    # Spatial smoothing
    SMOOTH_RADIUS = 0.008
    smoothed = []
    for i, hp in enumerate(heat_points):
        total_weight = 2.0
        weighted_rent = hp["rent"] * 2.0
        for j, other in enumerate(heat_points):
            if i == j:
                continue
            dist = math.sqrt((hp["lat"] - other["lat"])**2 + (hp["lng"] - other["lng"])**2)
            if 0 < dist < SMOOTH_RADIUS:
                w = 1.0 / dist
                total_weight += w
                weighted_rent += other["rent"] * w
        smoothed.append({
            "lat": hp["lat"],
            "lng": hp["lng"],
            "rent": int(round(weighted_rent / total_weight)),
            "count": hp["count"],
        })
    heat_points = smoothed

    # Neighbor clamping
    CLAMP_RADIUS = 0.015
    CLAMP_THRESHOLD = 1.50
    CLAMP_MAX_N = 10
    for i, hp in enumerate(heat_points):
        if hp["count"] >= CLAMP_MAX_N:
            continue
        neighbors = []
        for j, other in enumerate(heat_points):
            if i == j:
                continue
            dist = math.sqrt((hp["lat"] - other["lat"])**2 + (hp["lng"] - other["lng"])**2)
            if dist < CLAMP_RADIUS:
                neighbors.append(other["rent"])
        if len(neighbors) >= 1:
            neighbor_med = sorted(neighbors)[len(neighbors) // 2]
            if hp["rent"] > neighbor_med * CLAMP_THRESHOLD:
                hp["rent"] = neighbor_med

    heat_points.sort(key=lambda x: (-x["rent"], x["lat"]))
    return heat_points, non_rs


def load_and_clean(bed_key):
    """Load active + rented data for a bed count, clean, assign regions."""
    files = BED_FILES[bed_key]
    with open(files["active"]) as f:
        active = json.load(f)
    with open(files["rented"]) as f:
        rented_all = json.load(f)
    rented = [r for r in rented_all if r.get("rented_date", "") >= CUTOFF_DATE]
    all_raw = active + rented
    print(f"\n{'='*60}")
    print(f"  {bed_key.upper()}: {len(active)} active + {len(rented)} rented = {len(all_raw)} total")

    # Filter to correct bed count (active files are pre-filtered, but rented may not be)
    target_beds = 1 if bed_key == "1br" else (2 if bed_key == "2br" else 3)
    if bed_key == "3br":
        filtered = [l for l in all_raw if l.get("beds", 0) >= 3]
    else:
        filtered = [l for l in all_raw if l.get("beds") == target_beds]

    # Clean
    cleaned = []
    for l in filtered:
        rent = l.get("rent", 0)
        ptype = (l.get("type") or "").upper()
        lat = l.get("lat")
        lng = l.get("lng")
        if not lat or not lng:
            continue
        if rent > 25000 or rent < 500:
            continue
        if ptype in BAD_TYPES:
            continue
        cleaned.append(l)

    # Assign regions
    for l in cleaned:
        l["borough"] = get_region(l)

    print(f"  After cleaning: {len(cleaned)} listings")
    return cleaned


# ─── Main ────────────────────────────────────────────────────────────────
REGION_ORDER = [
    "Lower Manhattan", "Upper Manhattan", "North Brooklyn", "South Brooklyn",
    "W. Queens", "Queens", "South Bronx", "Bronx", "Staten Island"
]
REGION_JS_KEYS = {
    "Lower Manhattan": "LowerManhattan",
    "Upper Manhattan": "UpperManhattan",
    "North Brooklyn": "NorthBrooklyn",
    "South Brooklyn": "SouthBrooklyn",
    "W. Queens": "QueensWest",
    "Queens": "Queens",
    "South Bronx": "SouthBronx",
    "Bronx": "Bronx",
    "Staten Island": "StatenIsland",
}

results = {}  # results[bed_key][stat] = heat_points list
region_stats = {}  # region_stats[bed_key][stat] = { region_js_key: "$X,XXX", ... }
listing_counts = {}
bed_medians = {}

for bed_key in ["1br", "2br", "3br"]:
    cleaned = load_and_clean(bed_key)
    listing_counts[bed_key] = len(cleaned)
    results[bed_key] = {}
    region_stats[bed_key] = {}

    for stat in ["mean", "median"]:
        heat_points, non_rs = generate_heat_points(cleaned, stat)
        results[bed_key][stat] = heat_points
        print(f"  {bed_key} {stat}: {len(heat_points)} heat points")

        # Region stats
        region_rents = defaultdict(list)
        for l in non_rs:
            region_rents[l["borough"]].append(l["rent"])

        stats = {}
        for region in REGION_ORDER:
            rents = region_rents.get(region, [])
            if rents:
                if stat == "mean":
                    val = int(round(sum(rents) / len(rents)))
                else:
                    val = int(round(stat_median(rents)))
                stats[REGION_JS_KEYS[region]] = f"${val:,}"
            else:
                stats[REGION_JS_KEYS[region]] = "$0"

        # NYC overall
        all_rents = [l["rent"] for l in non_rs]
        if stat == "mean":
            nyc_val = int(round(sum(all_rents) / len(all_rents)))
        else:
            nyc_val = int(round(stat_median(all_rents)))
        stats["NYC"] = f"${nyc_val:,}"
        region_stats[bed_key][stat] = stats

        # Save Manhattan median and NYC median for info panel
        if stat == "median":
            manhattan_rents = region_rents.get("Lower Manhattan", [])
            manhattan_med = int(round(stat_median(manhattan_rents))) if manhattan_rents else 0
            bed_medians[bed_key] = {"manhattan": manhattan_med, "nyc": nyc_val}

# ─── Write output ────────────────────────────────────────────────────────
output_path = "/tmp/all_scenarios.js"
with open(output_path, "w") as f:
    # Write each data array
    var_names = {
        ("1br", "mean"): "MEAN_1BR",
        ("1br", "median"): "MEDIAN_1BR",
        ("2br", "mean"): "MEAN_2BR",
        ("2br", "median"): "MEDIAN_2BR",
        ("3br", "mean"): "MEAN_3BR",
        ("3br", "median"): "MEDIAN_3BR",
    }

    for (bed, stat), var_name in var_names.items():
        pts = results[bed][stat]
        f.write(f"const {var_name} = [\n")
        for hp in pts:
            f.write(f"  {{lat:{hp['lat']},lng:{hp['lng']},rent:{hp['rent']},n:{hp['count']}}},\n")
        f.write("];\n\n")

    # Write metadata
    f.write("// --- Metadata (listing counts, region stats, medians) ---\n")
    f.write(f"const LISTING_COUNTS = {json.dumps({k: f'{v:,}' for k, v in listing_counts.items()})};\n\n")
    f.write(f"const REGION_STATS = {json.dumps(region_stats, indent=2)};\n\n")
    f.write(f"const BED_MEDIANS = {json.dumps(bed_medians)};\n")

print(f"\n{'='*60}")
print(f"Output: {output_path}")
for bed_key in ["1br", "2br", "3br"]:
    print(f"  {bed_key}: {listing_counts[bed_key]:,} listings, mean={len(results[bed_key]['mean'])} pts, median={len(results[bed_key]['median'])} pts")
print(f"{'='*60}")
