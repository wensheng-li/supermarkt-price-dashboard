import requests
from utils.helpers import parse_price, parse_unit, clean_text
from utils.db import get_connection, upsert_store, upsert_product, insert_price
from urllib.parse import quote_plus

COLES_API = "https://www.coles.com.au/api/2.0/product/search/collection"

STORE = {
    "name":      "Coles",
    "chain":     "coles",
    "address":   "Shop 1 World Square, Sydney NSW 2000",
    "postcode":  "2000",
    "suburb":    "Sydney",
    "latitude":  -33.8765,
    "longitude": 151.2073,
}

def fetch_coles_prices(query: str) -> list:
    results = []

    try:
        response = requests.get(
            COLES_API,
            params={
                "slug":     quote_plus(query),
                "page":     1,
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept":     "application/json",
                "Referer":    f"https://www.coles.com.au/search/products?q={quote_plus(query)}",
                "Origin":     "https://www.coles.com.au",
            },
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"  [Coles] Request failed: {e}")
        return []

    if response.status_code != 200:
        print(f"  [Coles] Status {response.status_code} — may be blocked")
        return []

    data     = response.json()
    products = data.get("results", [])

    if not products:
        print("  [Coles] No results in response")
        return []

    conn = get_connection()
    try:
        store_id = upsert_store(conn, STORE)

        for item in products:
            pricing = item.get("pricing", {})
            name    = clean_text(item.get("name", ""))
            price   = parse_price(str(pricing.get("now", "")))

            if not name or not price:
                continue

            was_price_raw = pricing.get("was")
            was_price     = parse_price(str(was_price_raw)) if was_price_raw else None

            barcode = str(item.get("barcode") or item.get("id") or "")

            product_data = {
                "name":     name,
                "brand":    clean_text(item.get("brand", "")),
                "category": clean_text(item.get("category", "General"))
                            if isinstance(item.get("category"), str)
                            else "General",
                "unit":     parse_unit(name),
                "barcode":  barcode,
                "imageUrl": (item.get("imageUris") or [None])[0],
            }

            product_id = upsert_product(conn, product_data)
            insert_price(conn, {
                "price":     price,
                "wasPrice":  was_price,
                "isOnSale":  was_price is not None,
                "productId": product_id,
                "storeId":   store_id,
            })

            results.append({"name": name, "price": price})
            print(f"    ✓ {name} — ${price}")

    finally:
        conn.close()

    return results