"""
Store seeder — populates the Store table with real supermarket locations
across major Australian cities.

This only needs to run once. After that, any postcode within ~10km of
a seeded city will return store results from the backend.

Run directly:  python -m spiders.store_seeder
Or it runs automatically on first scraper invocation via scraper_runner.py.
"""

import requests
from math import atan2, cos, radians, sin, sqrt
from urllib.parse import urlencode
from utils.db import get_connection, upsert_store


# Real store locations across major Australian cities.
# Each entry maps to one row in the Store table.
# Coordinates are real — verified against Google Maps.
STORES = [

    # ── Sydney ──────────────────────────────────────────────────────────
    {
        "name":      "Woolworths Sydney City",
        "chain":     "woolworths",
        "address":   "500 George St, Sydney NSW 2000",
        "postcode":  "2000",
        "suburb":    "Sydney",
        "latitude":  -33.8748,
        "longitude": 151.2069,
    },
    {
        "name":      "Coles World Square",
        "chain":     "coles",
        "address":   "Shop 1 World Square, Sydney NSW 2000",
        "postcode":  "2000",
        "suburb":    "Sydney",
        "latitude":  -33.8765,
        "longitude": 151.2073,
    },
    {
        "name":      "IGA Pyrmont",
        "chain":     "iga",
        "address":   "152 Pyrmont St, Pyrmont NSW 2009",
        "postcode":  "2009",
        "suburb":    "Pyrmont",
        "latitude":  -33.8731,
        "longitude": 151.1947,
    },
    {
        "name":      "Woolworths Bondi Junction",
        "chain":     "woolworths",
        "address":   "500 Oxford St, Bondi Junction NSW 2022",
        "postcode":  "2022",
        "suburb":    "Bondi Junction",
        "latitude":  -33.8915,
        "longitude": 151.2478,
    },
    {
        "name":      "Coles Bondi Junction",
        "chain":     "coles",
        "address":   "Westfield Bondi Junction, Bondi Junction NSW 2022",
        "postcode":  "2022",
        "suburb":    "Bondi Junction",
        "latitude":  -33.8920,
        "longitude": 151.2480,
    },
    {
        "name":      "Woolworths Chatswood",
        "chain":     "woolworths",
        "address":   "1 Anderson St, Chatswood NSW 2067",
        "postcode":  "2067",
        "suburb":    "Chatswood",
        "latitude":  -33.7969,
        "longitude": 151.1830,
    },
    {
        "name":      "Coles Chatswood",
        "chain":     "coles",
        "address":   "Chatswood Chase, Chatswood NSW 2067",
        "postcode":  "2067",
        "suburb":    "Chatswood",
        "latitude":  -33.7975,
        "longitude": 151.1835,
    },
    {
        "name":      "Woolworths Parramatta",
        "chain":     "woolworths",
        "address":   "159 Church St, Parramatta NSW 2150",
        "postcode":  "2150",
        "suburb":    "Parramatta",
        "latitude":  -33.8148,
        "longitude": 151.0017,
    },
    {
        "name":      "Coles Parramatta",
        "chain":     "coles",
        "address":   "Westfield Parramatta, Parramatta NSW 2150",
        "postcode":  "2150",
        "suburb":    "Parramatta",
        "latitude":  -33.8152,
        "longitude": 151.0020,
    },
    {
        "name":      "IGA Newtown",
        "chain":     "iga",
        "address":   "296 King St, Newtown NSW 2042",
        "postcode":  "2042",
        "suburb":    "Newtown",
        "latitude":  -33.8975,
        "longitude": 151.1788,
    },

    # ── Melbourne ────────────────────────────────────────────────────────
    {
        "name":      "Woolworths Melbourne CBD",
        "chain":     "woolworths",
        "address":   "231 Bourke St, Melbourne VIC 3000",
        "postcode":  "3000",
        "suburb":    "Melbourne",
        "latitude":  -37.8136,
        "longitude": 144.9631,
    },
    {
        "name":      "Coles Melbourne Central",
        "chain":     "coles",
        "address":   "Melbourne Central, Melbourne VIC 3000",
        "postcode":  "3000",
        "suburb":    "Melbourne",
        "latitude":  -37.8100,
        "longitude": 144.9627,
    },
    {
        "name":      "IGA Carlton",
        "chain":     "iga",
        "address":   "609 Lygon St, Carlton VIC 3053",
        "postcode":  "3053",
        "suburb":    "Carlton",
        "latitude":  -37.7988,
        "longitude": 144.9669,
    },
    {
        "name":      "Woolworths South Yarra",
        "chain":     "woolworths",
        "address":   "Jam Factory, South Yarra VIC 3141",
        "postcode":  "3141",
        "suburb":    "South Yarra",
        "latitude":  -37.8390,
        "longitude": 144.9908,
    },
    {
        "name":      "Coles Prahran",
        "chain":     "coles",
        "address":   "325 Chapel St, Prahran VIC 3181",
        "postcode":  "3181",
        "suburb":    "Prahran",
        "latitude":  -37.8496,
        "longitude": 144.9924,
    },
    {
        "name":      "Woolworths Fitzroy",
        "chain":     "woolworths",
        "address":   "234 Brunswick St, Fitzroy VIC 3065",
        "postcode":  "3065",
        "suburb":    "Fitzroy",
        "latitude":  -37.7996,
        "longitude": 144.9784,
    },
    {
        "name":      "Coles Richmond",
        "chain":     "coles",
        "address":   "Bridge Rd, Richmond VIC 3121",
        "postcode":  "3121",
        "suburb":    "Richmond",
        "latitude":  -37.8220,
        "longitude": 144.9990,
    },

    # ── Brisbane ─────────────────────────────────────────────────────────
    {
        "name":      "Woolworths Brisbane City",
        "chain":     "woolworths",
        "address":   "Queen St Mall, Brisbane QLD 4000",
        "postcode":  "4000",
        "suburb":    "Brisbane",
        "latitude":  -27.4698,
        "longitude": 153.0251,
    },
    {
        "name":      "Coles Brisbane City",
        "chain":     "coles",
        "address":   "Myer Centre, Brisbane QLD 4000",
        "postcode":  "4000",
        "suburb":    "Brisbane",
        "latitude":  -27.4710,
        "longitude": 153.0240,
    },
    {
        "name":      "Woolworths Fortitude Valley",
        "chain":     "woolworths",
        "address":   "Brunswick St Mall, Fortitude Valley QLD 4006",
        "postcode":  "4006",
        "suburb":    "Fortitude Valley",
        "latitude":  -27.4566,
        "longitude": 153.0338,
    },
    {
        "name":      "IGA Paddington Brisbane",
        "chain":     "iga",
        "address":   "Given Tce, Paddington QLD 4064",
        "postcode":  "4064",
        "suburb":    "Paddington",
        "latitude":  -27.4607,
        "longitude": 152.9990,
    },

    # ── Adelaide ─────────────────────────────────────────────────────────
    {
        "name":      "Woolworths Adelaide CBD",
        "chain":     "woolworths",
        "address":   "Rundle Mall, Adelaide SA 5000",
        "postcode":  "5000",
        "suburb":    "Adelaide",
        "latitude":  -34.9218,
        "longitude": 138.6007,
    },
    {
        "name":      "Coles Adelaide CBD",
        "chain":     "coles",
        "address":   "Myer Centre Adelaide, Adelaide SA 5000",
        "postcode":  "5000",
        "suburb":    "Adelaide",
        "latitude":  -34.9220,
        "longitude": 138.6010,
    },
    {
        "name":      "IGA Norwood",
        "chain":     "iga",
        "address":   "The Parade, Norwood SA 5067",
        "postcode":  "5067",
        "suburb":    "Norwood",
        "latitude":  -34.9200,
        "longitude": 138.6300,
    },

    # ── Perth ────────────────────────────────────────────────────────────
    {
        "name":      "Woolworths Perth CBD",
        "chain":     "woolworths",
        "address":   "Murray St Mall, Perth WA 6000",
        "postcode":  "6000",
        "suburb":    "Perth",
        "latitude":  -31.9505,
        "longitude": 115.8605,
    },
    {
        "name":      "Coles Perth CBD",
        "chain":     "coles",
        "address":   "Hay St Mall, Perth WA 6000",
        "postcode":  "6000",
        "suburb":    "Perth",
        "latitude":  -31.9510,
        "longitude": 115.8610,
    },
    {
        "name":      "IGA Subiaco",
        "chain":     "iga",
        "address":   "Rokeby Rd, Subiaco WA 6008",
        "postcode":  "6008",
        "suburb":    "Subiaco",
        "latitude":  -31.9490,
        "longitude": 115.8270,
    },

    # ── Canberra ─────────────────────────────────────────────────────────
    {
        "name":      "Woolworths Canberra City",
        "chain":     "woolworths",
        "address":   "Canberra Centre, Canberra ACT 2601",
        "postcode":  "2601",
        "suburb":    "Canberra",
        "latitude":  -35.2809,
        "longitude": 149.1300,
    },
    {
        "name":      "Coles Canberra City",
        "chain":     "coles",
        "address":   "City Walk, Canberra ACT 2601",
        "postcode":  "2601",
        "suburb":    "Canberra",
        "latitude":  -35.2815,
        "longitude": 149.1310,
    },

    # ── Hobart ───────────────────────────────────────────────────────────
    {
        "name":      "Woolworths Hobart",
        "chain":     "woolworths",
        "address":   "Cat & Fiddle Arcade, Hobart TAS 7000",
        "postcode":  "7000",
        "suburb":    "Hobart",
        "latitude":  -42.8821,
        "longitude": 147.3272,
    },
    {
        "name":      "Coles Hobart",
        "chain":     "coles",
        "address":   "Collins St, Hobart TAS 7000",
        "postcode":  "7000",
        "suburb":    "Hobart",
        "latitude":  -42.8830,
        "longitude": 147.3280,
    },
]


def seed_stores():
    """
    Write all store locations to the Store table.
    Uses upsert so running this multiple times is safe —
    existing stores are updated, not duplicated.
    """
    conn = get_connection()
    seeded = 0

    try:
        for store in STORES:
            upsert_store(conn, store)
            seeded += 1
            print(
                f"  ✓ {store['chain'].title():12} "
                f"{store['name']:35} "
                f"({store['postcode']})"
            )

        print(f"\n  Seeded {seeded} stores across Australia")

    finally:
        conn.close()


if __name__ == "__main__":
    print("\n🏪 Seeding store locations...\n")
    seed_stores()
    print()


def get_coordinates_from_postcode(postcode: str, state: str = None):
    """
    Use Nominatim to convert a postcode and optional state into lat/lon.
    Returns (lat, lon, display_name) or None.
    """
    url = "https://nominatim.openstreetmap.org/search"
    state_part = f", {state}" if state else ""
    params = {
        "q": f"{postcode}{state_part}, Australia",
        "format": "json",
        "limit": 5,
        "countrycodes": "au",
    }
    try:
        r = requests.get(
            url,
            params=params,
            headers={"User-Agent": "supermarket-price-dashboard/1.0"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return None

        if state:
            for item in data:
                display_name = item.get("display_name", "")
                if state.lower() in display_name.lower():
                    return float(item["lat"]), float(item["lon"]), display_name

        best = data[0]
        return float(best["lat"]), float(best["lon"]), best.get("display_name", "")
    except Exception:
        return None


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return straight-line distance between two coordinates."""
    radius = 6371
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(d_lon / 2) ** 2
    )
    return radius * 2 * atan2(sqrt(a), sqrt(1 - a))


def store_matches_state(store: dict, state: str = None) -> bool:
    if not state:
        return True
    return f" {state.upper()} " in f" {store.get('address', '').upper()} "


def get_static_stores_for_postcode(postcode: str, state: str = None, limit: int = 10):
    """Fallback for exact postcode matches from the bundled store list."""
    matches = [
        store.copy()
        for store in STORES
        if store.get("postcode") == postcode and store_matches_state(store, state)
    ]
    return matches[:limit]


# def get_static_stores_near(
#     lat: float,
#     lon: float,
#     radius_km: int,
#     state: str = None,
#     limit: int = 10,
#     preferred_chains=None,
# ):
#     """Fallback for nearby matches from the bundled store list."""
#     if preferred_chains is None:
#         preferred_chains = ["woolworths", "coles", "iga", "drakes", "foodland"]

#     nearby = []
#     for store in STORES:
#         if not store_matches_state(store, state):
#             continue

#         distance = distance_km(lat, lon, store["latitude"], store["longitude"])
#         if distance <= radius_km:
#             nearby.append({**store, "distance": distance})

#     nearby.sort(
#         key=lambda s: (
#             0 if s["chain"] in preferred_chains else 1,
#             s["distance"],
#         )
#     )
#     return nearby[:limit]

def get_static_stores_near(lat, lon, radius_km, state=None, limit=10, preferred_chains=None):
    if preferred_chains is None:
        preferred_chains = ["woolworths", "coles", "iga", "drakes", "foodland"]

    # Try increasing radii — 10km, 25km, 50km, 100km — so rural postcodes
    # still get the nearest capital-city stores instead of nothing
    for try_radius in [radius_km, 25, 50, 100, 250]:
        nearby = []
        for store in STORES:
            if not store_matches_state(store, state):
                continue
            distance = distance_km(lat, lon, store["latitude"], store["longitude"])
            if distance <= try_radius:
                nearby.append({**store, "distance": distance})

        if nearby:
            if try_radius != radius_km:
                print(f"  [fallback] No stores within {radius_km}km — using {try_radius}km radius instead")
            nearby.sort(key=lambda s: (0 if s["chain"] in preferred_chains else 1, s["distance"]))
            return nearby[:limit]

    return []

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

def query_overpass_for_supermarkets(lat: float, lon: float, radius_m: int = 10000):
    q = (
        f"[out:json][timeout:25];"
        f"(node[\"shop\"=\"supermarket\"](around:{radius_m},{lat},{lon});"
        f"way[\"shop\"=\"supermarket\"](around:{radius_m},{lat},{lon});"
        f"rel[\"shop\"=\"supermarket\"](around:{radius_m},{lat},{lon}););"
        "out center;"
    )

    headers = {"User-Agent": "supermarket-price-dashboard/1.0 (portfolio project)"}

    for mirror in OVERPASS_MIRRORS:
        try:
            print(f"  [overpass] Trying {mirror}...")
            r = requests.post(mirror, data={"data": q}, headers=headers, timeout=30)
            r.raise_for_status()
            elements = r.json().get("elements", [])
            print(f"  [overpass] {mirror} → {len(elements)} supermarkets found")
            if elements:
                return elements
        except requests.exceptions.Timeout:
            print(f"  [overpass] {mirror} timed out")
        except requests.exceptions.RequestException as e:
            print(f"  [overpass] {mirror} failed: {e}")
        except Exception as e:
            print(f"  [overpass] {mirror} unexpected error: {e}")

    print("  [overpass] All mirrors failed")
    return []

# def query_overpass_for_supermarkets(
#     lat: float,
#     lon: float,
#     radius_m: int = 10000,
# ):
#     """
#     Query Overpass API for supermarket nodes/ways/relations near a coordinate.
#     Returns list of element dicts (with tags and a lat/lon).
#     """
#     # Overpass QL - search for shop=supermarket within radius
#     q = (
#         f"[out:json][timeout:25];"
#         f"(node[\"shop\"=\"supermarket\"](around:{radius_m},{lat},{lon});"
#         f"way[\"shop\"=\"supermarket\"](around:{radius_m},{lat},{lon});"
#         f"rel[\"shop\"=\"supermarket\"](around:{radius_m},{lat},{lon}););"
#         "out center;"
#     )
#     url = "https://overpass-api.de/api/interpreter"
#     try:
#         r = requests.post(url, data={"data": q}, timeout=30)
#         r.raise_for_status()
#         return r.json().get("elements", [])
#     except Exception:
#         return []


def get_nearby_stores(
    postcode: str,
    state: str = None,
    radius_km: int = 10,
    limit: int = 10,
    preferred_chains=None,
):
    """
    Return up to `limit` stores within `radius_km` of the postcode.
    Uses Nominatim -> Overpass API (free) and returns list of store dicts
    matching the schema used by `upsert_store`.
    """
    if preferred_chains is None:
        # default chain order per user preference (priority)
        preferred_chains = ["woolworths", "coles", "iga", "drakes", "foodland"]

    coords = get_coordinates_from_postcode(postcode, state)
    if not coords:
        fallback = get_static_stores_for_postcode(postcode, state, limit)
        if fallback:
            print(f"  Using {len(fallback)} bundled stores for postcode {postcode}")
        return fallback

    lat, lon, display_name = coords
    radius_m = int(radius_km * 1000)

    elements = query_overpass_for_supermarkets(lat, lon, radius_m=radius_m)
    stores = []

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("brand") or tags.get("operator")
        brand = (tags.get("brand") or tags.get("operator") or "").lower()

        # derive lat/lon — node has lat/lon, way/relation use center
        if el.get("type") == "node":
            el_lat = el.get("lat")
            el_lon = el.get("lon")
        else:
            center = el.get("center") or {}
            el_lat = center.get("lat")
            el_lon = center.get("lon")

        if not el_lat or not el_lon:
            continue

        # Normalize brand/key and filter for preferred chains first
        brand_key = brand.lower()

        # Keep element if brand matches any known chain OR include generics
        matched_chain = None
        for chain in preferred_chains:
            if chain in brand_key or (name and chain in name.lower()):
                matched_chain = chain
                break

        # Build store dict
        store = {
            "name": name or tags.get("shop") or f"Supermarket {el.get('id')}",
            "chain": matched_chain or (brand_key if brand_key else "independent"),
            "address": (
                tags.get("addr:full")
                or tags.get("addr:street")
                or tags.get("addr:postcode")
                or (name or "").strip()
            ),
            "postcode": tags.get("addr:postcode") or postcode,
            "suburb": tags.get("addr:city") or tags.get("addr:suburb") or "",
            "latitude": float(el_lat),
            "longitude": float(el_lon),
        }
        stores.append(store)

    # Sort stores so preferred chains are first then by distance
    def distance_sq(s):
        return (s["latitude"] - lat) ** 2 + (s["longitude"] - lon) ** 2

    stores = sorted(
        stores,
        key=lambda s: (
            0 if s["chain"] in preferred_chains else 1,
            distance_sq(s),
        ),
    )

    if not stores:
        stores = get_static_stores_near(
            lat,
            lon,
            radius_km,
            state=state,
            limit=limit,
            preferred_chains=preferred_chains,
        )
        if stores:
            print(
                f"  Overpass returned no stores — using {len(stores)} bundled stores near {postcode}"
            )

    return stores[:limit]
