import time
import requests
from utils.helpers import clean_text, parse_unit
from utils.db import get_connection, upsert_product

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"

def fetch_products_openfoodfacts(query: str, retries: int = 3) -> list:
    results  = []
    response = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                BASE_URL,
                params={
                    "search_terms":   query,
                    "search_simple":  1,
                    "action":         "process",
                    "json":           1,
                    "page_size":      20, # Fetch up 20 products
                    "countries_tags": "australia",
                    "fields": "product_name,brands,categories_tags,quantity,code,image_url",
                },
                headers={
                    "User-Agent": "SupermarketPriceDashboard/1.0 (portfolio project)"
                },
                timeout=20,
            )

            if response.status_code == 200:
                break  # success — exit retry loop

            print(f"  [OFF] Attempt {attempt}/{retries} — status {response.status_code}, retrying...")
            time.sleep(3 * attempt)  # wait 3s, then 6s, then 9s

        except requests.RequestException as e:
            print(f"  [OFF] Attempt {attempt}/{retries} — error: {e}")
            time.sleep(3 * attempt)

    if not response or response.status_code != 200:
        print(f"  [OFF] All {retries} attempts failed — skipping Open Food Facts")
        return []

    data     = response.json()
    products = data.get("products", [])

    conn = get_connection()
    try:
        for item in products:
            # Normalise the product names
            name = clean_text(item.get("product_name", "")).title()
            if not name:
                continue

            raw_cats = item.get("categories_tags", [])
            category = "General"
            for cat in raw_cats:
                cleaned = cat.replace("en:", "").replace("-", " ").title()
                if len(cleaned) > 2:
                    category = cleaned
                    break

            product_data = {
                "name":     name,
                # Normalise the brand names
                "brand":    clean_text(item.get("brands", "")).title(),
                "category": category,
                "unit":     parse_unit(item.get("quantity", "") or name),
                "barcode":  item.get("code", ""),
                "imageUrl": item.get("image_url", ""),
            }

            upsert_product(conn, product_data)
            results.append(product_data)
            print(f"    ✓ {name}")

    finally:
        conn.close()

    return results

FALLBACK_PRODUCTS = [
    {"name": "Full Cream Milk 2L",   "brand": "Woolworths", "category": "Dairy",  "unit": "2L",   "barcode": "9300633308025", "imageUrl": None},
    {"name": "Full Cream Milk 1L",   "brand": "Coles",      "category": "Dairy",  "unit": "1L",   "barcode": "9300633308018", "imageUrl": None},
    {"name": "Full Cream Milk 3L",   "brand": "Pauls",      "category": "Dairy",  "unit": "3L",   "barcode": "9300633308032", "imageUrl": None},
    {"name": "Skim Milk 2L",         "brand": "Devondale",  "category": "Dairy",  "unit": "2L",   "barcode": "9310085010015", "imageUrl": None},
    {"name": "Sourdough Bread 700g", "brand": "Coles",      "category": "Bakery", "unit": "700g", "barcode": "9300633400018", "imageUrl": None},
]

def get_fallback_products(query: str) -> list:
    """Return fallback products matching the query when OFF is unavailable."""
    q = query.lower()
    return [p for p in FALLBACK_PRODUCTS if q in p["name"].lower()]