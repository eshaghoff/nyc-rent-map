#!/usr/bin/env python3
"""
New Baseline: Dense grid (0.002°/0.003°), median rent, MIN_CELL_COUNT=2
Fixes Mill Basin ghost points by requiring >= 2 listings per cell
and relaxing clamping neighbor requirement to >= 1.
"""

import json
import math
from collections import defaultdict, Counter
from statistics import median

# ─── Load data ───────────────────────────────────────────────────────────
with open("/Users/SamuelEshaghoff1/Downloads/nyc-rent-scraper/listings_raw.json") as f:
    listings = json.load(f)
with open("/Users/SamuelEshaghoff1/Downloads/nyc-rent-scraper/rented_raw.json") as f:
    rented = json.load(f)

all_raw = listings + rented
print(f"Raw listings loaded: {len(listings)} active + {len(rented)} rented = {len(all_raw)} total")

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

# ─── Step 3: Borough assignment ──────────────────────────────────────────
BOROUGH_MAP = {
    "Battery Park City": "Manhattan", "Beekman": "Manhattan", "Carnegie Hill": "Manhattan",
    "Central Harlem": "Manhattan", "Central Park South": "Manhattan", "Chelsea": "Manhattan",
    "Chinatown": "Manhattan", "Civic Center": "Manhattan", "East Harlem": "Manhattan",
    "East Village": "Manhattan", "Financial District": "Manhattan", "Flatiron": "Manhattan",
    "Fort George": "Manhattan", "Fulton/Seaport": "Manhattan", "Gramercy Park": "Manhattan",
    "Greenwich Village": "Manhattan", "Hamilton Heights": "Manhattan", "Hell's Kitchen": "Manhattan",
    "Hudson Heights": "Manhattan", "Hudson Square": "Manhattan", "Hudson Yards": "Manhattan",
    "Inwood": "Manhattan", "Kips Bay": "Manhattan", "Lenox Hill": "Manhattan",
    "Lincoln Square": "Manhattan", "Little Italy": "Manhattan", "Lower East Side": "Manhattan",
    "Madison": "Manhattan", "Manhattan Beach": "Brooklyn", "Manhattan Valley": "Manhattan",
    "Manhattanville": "Manhattan", "Marble Hill": "Manhattan", "Midtown": "Manhattan",
    "Midtown South": "Manhattan", "Morningside Heights": "Manhattan", "Murray Hill": "Manhattan",
    "NoMad": "Manhattan", "Noho": "Manhattan", "Nolita": "Manhattan",
    "Roosevelt Island": "Manhattan", "Soho": "Manhattan", "South Harlem": "Manhattan",
    "Stuyvesant Town/PCV": "Manhattan", "Sutton Place": "Manhattan", "Tribeca": "Manhattan",
    "Turtle Bay": "Manhattan", "Two Bridges": "Manhattan", "Upper Carnegie Hill": "Manhattan",
    "Upper East Side": "Manhattan", "Upper West Side": "Manhattan", "Washington Heights": "Manhattan",
    "West Chelsea": "Manhattan", "West Harlem": "Manhattan", "West Village": "Manhattan",
    "Yorkville": "Manhattan",
    "Bath Beach": "Brooklyn", "Bay Ridge": "Brooklyn", "Bedford-Stuyvesant": "Brooklyn",
    "Bensonhurst": "Brooklyn", "Bergen Beach": "Brooklyn", "Boerum Hill": "Brooklyn",
    "Borough Park": "Brooklyn", "Brooklyn Heights": "Brooklyn", "Brownsville": "Brooklyn",
    "Bushwick": "Brooklyn", "Canarsie": "Brooklyn", "Carroll Gardens": "Brooklyn",
    "City Line": "Brooklyn", "Clinton Hill": "Brooklyn", "Cobble Hill": "Brooklyn",
    "Columbia St Waterfront District": "Brooklyn", "Coney Island": "Brooklyn",
    "Crown Heights": "Brooklyn", "Cypress Hills": "Brooklyn", "DUMBO": "Brooklyn",
    "Ditmars-Steinway": "Queens",
    "Ditmas Park": "Brooklyn", "Downtown Brooklyn": "Brooklyn", "Dyker Heights": "Brooklyn",
    "East Flatbush": "Brooklyn", "East New York": "Brooklyn", "East Williamsburg": "Brooklyn",
    "Farragut": "Brooklyn", "Fiske Terrace": "Brooklyn", "Flatbush": "Brooklyn",
    "Flatlands": "Brooklyn", "Fort Greene": "Brooklyn", "Fort Hamilton": "Brooklyn",
    "Gowanus": "Brooklyn", "Gravesend": "Brooklyn", "Greenpoint": "Brooklyn",
    "Greenwood": "Brooklyn", "Homecrest": "Brooklyn", "Kensington": "Brooklyn",
    "Mapleton": "Brooklyn", "Marine Park": "Brooklyn", "Midwood": "Brooklyn",
    "Mill Basin": "Brooklyn", "New Lots": "Brooklyn", "Ocean Hill": "Brooklyn",
    "Park Slope": "Brooklyn", "Prospect Heights": "Brooklyn",
    "Prospect Lefferts Gardens": "Brooklyn", "Prospect Park South": "Brooklyn",
    "Red Hook": "Brooklyn", "Sheepshead Bay": "Brooklyn", "Starrett City": "Brooklyn",
    "Stuyvesant Heights": "Brooklyn", "Sunset Park": "Brooklyn", "Vinegar Hill": "Brooklyn",
    "Weeksville": "Brooklyn", "Williamsburg": "Brooklyn", "Windsor Terrace": "Brooklyn",
    "Wingate": "Brooklyn",
    "Arverne": "Queens", "Astoria": "Queens", "Auburndale": "Queens", "Bay Terrace": "Queens",
    "Bayside": "Queens", "Bayswater": "Queens", "Beechhurst": "Queens", "Briarwood": "Queens",
    "Brookville": "Queens", "College Point": "Queens", "Corona": "Queens",
    "Douglaston": "Queens", "East Elmhurst": "Queens", "East Flushing": "Queens",
    "Elmhurst": "Queens", "Far Rockaway": "Queens", "Flushing": "Queens",
    "Forest Hills": "Queens", "Fresh Meadows": "Queens", "Glen Oaks": "Queens",
    "Glendale": "Queens", "Hillcrest": "Queens", "Hollis": "Queens",
    "Hunters Point": "Queens", "Jackson Heights": "Queens", "Jamaica": "Queens",
    "Jamaica Estates": "Queens", "Jamaica Hills": "Queens", "Kew Gardens": "Queens",
    "Kew Gardens Hills": "Queens", "Laurelton": "Queens", "Lindenwood": "Queens",
    "Little Neck": "Queens", "Long Island City": "Queens", "Malba": "Queens",
    "Maspeth": "Queens", "Middle Village": "Queens", "North Corona": "Queens",
    "North New York": "Queens", "Oakland Gardens": "Queens", "Old Howard Beach": "Queens",
    "Ozone Park": "Queens", "Pomonok": "Queens", "Queens": "Queens",
    "Queens Village": "Queens", "Rego Park": "Queens", "Richmond Hill": "Queens",
    "Ridgewood": "Queens", "Rockaway Park": "Queens", "Rockwood Park": "Queens",
    "Rosedale": "Queens", "South Jamaica": "Queens", "South Ozone Park": "Queens",
    "Springfield Gardens": "Queens", "St. Albans": "Queens", "Sunnyside": "Queens",
    "The Rockaways": "Queens", "Whitestone": "Queens", "Woodhaven": "Queens",
    "Woodside": "Queens",
    "Bedford Park": "Bronx", "Belmont": "Bronx", "Bronxwood": "Bronx",
    "City Island": "Bronx", "Claremont": "Bronx", "Concourse": "Bronx",
    "Country Club": "Bronx", "Crotona Park East": "Bronx", "East Tremont": "Bronx",
    "Fieldston": "Bronx", "Fordham": "Bronx", "Highbridge": "Bronx",
    "Hunts Point": "Bronx", "Kingsbridge": "Bronx", "Kingsbridge Heights": "Bronx",
    "Laconia": "Bronx", "Locust Point": "Bronx", "Longwood": "Bronx",
    "Melrose": "Bronx", "Morris Heights": "Bronx", "Morris Park": "Bronx",
    "Morrisania": "Bronx", "Mott Haven": "Bronx", "Mt. Hope": "Bronx",
    "Norwood": "Bronx", "Parkchester": "Bronx", "Pelham Bay": "Bronx",
    "Pelham Gardens": "Bronx", "Pelham Parkway": "Bronx", "Riverdale": "Bronx",
    "Schuylerville": "Bronx", "Soundview": "Bronx", "Spuyten Duyvil": "Bronx",
    "Throgs Neck": "Bronx", "Tremont": "Bronx", "University Heights": "Bronx",
    "Van Nest": "Bronx", "Wakefield": "Bronx", "West Farms": "Bronx",
    "Westchester Square": "Bronx", "Williamsbridge": "Bronx", "Woodstock": "Bronx",
    "Annadale": "Staten Island", "Arden Heights": "Staten Island", "Arrochar": "Staten Island",
    "Bulls Head": "Staten Island", "Castleton Corners": "Staten Island", "Clifton": "Staten Island",
    "Dongan Hills": "Staten Island", "Elm Park": "Staten Island", "Eltingville": "Staten Island",
    "Emerson Hill": "Staten Island", "Grant City": "Staten Island", "Graniteville": "Staten Island",
    "Grasmere": "Staten Island", "Great Kills": "Staten Island", "Grymes Hill": "Staten Island",
    "Huguenot": "Staten Island", "Mariners Harbor": "Staten Island",
    "Meiers Corners": "Staten Island", "Midland Beach": "Staten Island",
    "New Brighton": "Staten Island", "New Dorp": "Staten Island",
    "New Dorp Beach": "Staten Island", "New Springville": "Staten Island",
    "Oakwood": "Staten Island", "Park Hill": "Staten Island", "Port Richmond": "Staten Island",
    "Princes Bay": "Staten Island", "Ramblersville": "Queens",
    "Richmondtown": "Staten Island", "Rosebank": "Staten Island", "Rossville": "Staten Island",
    "Saint George": "Staten Island", "Shore Acres": "Staten Island",
    "Silver Lake": "Staten Island", "South Beach": "Staten Island",
    "Stapleton": "Staten Island", "Tompkinsville": "Staten Island",
    "Tottenville": "Staten Island", "West Brighton": "Staten Island",
    "Westerleigh": "Staten Island", "Willowbrook": "Staten Island",
    "Woodrow": "Staten Island",
}

def get_borough(listing):
    n = listing.get("neighborhood", "")
    if n in BOROUGH_MAP:
        return BOROUGH_MAP[n]
    lat = listing["lat"]
    lng = listing["lng"]
    if -74.03 < lng < -73.90 and 40.70 < lat < 40.88:
        if lng > -73.96 or lat < 40.75:
            return "Manhattan"
    if lat < 40.65 and lng < -74.04:
        return "Staten Island"
    if lat > 40.80 and lng > -73.94:
        return "Bronx"
    if lat > 40.85:
        return "Bronx"
    if lat < 40.74:
        if lng < -73.92:
            return "Brooklyn"
        else:
            return "Queens"
    if lng > -73.92:
        return "Queens"
    return "Unknown"

for l in cleaned:
    l["borough"] = get_borough(l)

unknowns = [l for l in cleaned if l["borough"] == "Unknown"]
if unknowns:
    unknown_hoods = Counter(l.get("neighborhood", "?") for l in unknowns)
    print(f"\nUnknown borough listings: {len(unknowns)}")
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
rs_by_rule = Counter()
non_rs = []
for l in cleaned:
    rent = l["rent"]
    lat = l["lat"]
    lng = l["lng"]
    is_rs = False
    rule = None

    # Rule 1: Non-round rents below $2,500 — these are DHCR legal rent amounts
    if rent < 2500 and rent % 5 != 0:
        is_rs = True
        rule = "odd_under_2500"

    # Rule 2: Below 50% of local spatial median — catches RS in any neighborhood
    if not is_rs:
        sm = get_spatial_median(lat, lng)
        if sm and rent < sm * 0.50:
            is_rs = True
            rule = "below_50pct_spatial_median"

    if is_rs:
        rs_flagged += 1
        rs_by_rule[rule] += 1
    else:
        non_rs.append(l)

print(f"\nRS filter: flagged {rs_flagged} listings")
for rule, count in rs_by_rule.most_common():
    print(f"  {rule}: {count}")
print(f"After RS filter: {len(non_rs)} listings")

# ─── Step 5: Borough medians ────────────────────────────────────────────
borough_listings = defaultdict(list)
for l in non_rs:
    borough_listings[l["borough"]].append(l)

print(f"\nBorough medians:")
borough_medians = {}
for borough, lsts in sorted(borough_listings.items()):
    rents = [l["rent"] for l in lsts]
    if len(rents) >= 1000:
        sorted_rents = sorted(rents)
        n = len(sorted_rents)
        med = sorted_rents[n // 2]
    else:
        med = median(rents)
    borough_medians[borough] = med
    print(f"  {borough}: ${med:,.0f} (n={len(rents)})")

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
for (clat, clng, gs), lsts in grid_cells.items():
    if len(lsts) < MIN_CELL_COUNT:
        dropped_thin += 1
        continue
    rents = sorted([l["rent"] for l in lsts])
    med_rent = rents[len(rents) // 2]
    heat_points.append({
        "lat": round(clat, 4),
        "lng": round(clng, 4),
        "rent": int(med_rent),
        "count": len(lsts),
    })

# ─── Spatial smoothing pass ─────────────────────────────────────────────
SMOOTH_RADIUS = 0.008
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
            w = 1.0 / dist
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
print(f"Spatial smoothing applied (radius={SMOOTH_RADIUS}deg, ~800m)")

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
with open("/tmp/heat_points_baseline_v2.js", "w") as f:
    f.write("const HEAT_POINTS = [\n")
    for hp in heat_points:
        f.write(f"  {{lat:{hp['lat']},lng:{hp['lng']},rent:{hp['rent']},n:{hp['count']}}},\n")
    f.write("];\n")

print(f"\nOutput: /tmp/heat_points_baseline_v2.js")

# ─── Summary ─────────────────────────────────────────────────────────────
all_rents = sorted([l["rent"] for l in non_rs])
nyc_med = all_rents[len(all_rents) // 2]
print(f"\nNYC overall median: ${nyc_med:,}")
print(f"Total listings used: {len(non_rs)}")

# Check Mill Basin area
print("\n--- Mill Basin check ---")
mb = [hp for hp in heat_points if 40.59 <= hp["lat"] <= 40.62 and -73.94 <= hp["lng"] <= -73.90]
if mb:
    for hp in mb:
        print(f"  ${hp['rent']:>6,}  lat={hp['lat']}, lng={hp['lng']}  n={hp['count']}")
else:
    print("  No heat points in Mill Basin ✓")
