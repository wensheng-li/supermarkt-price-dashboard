import requests
from utils.helpers import parse_price, parse_unit, clean_text
from utils.db import get_connection, upsert_store, upsert_product, insert_price

# This is Woolworths' public-facing search API used by their SSR pages
WW_API = "https://www.woolworths.com.au/apis/ui/Search/products"

STORE = {
    "name":      "Woolworths",
    "chain":     "woolworths",
    "address":   "500 George St, Sydney NSW 2000",
    "postcode":  "2000",
    "suburb":    "Sydney",
    "latitude":  -33.8748,
    "longitude": 151.2069,
}

def fetch_woolworths_prices(query: str) -> list:
    results = []

    try:
        response = requests.post(
            WW_API,
            json={
                "Filters":            [],
                "IsSpecial":          False,
                "Location":           f"/shop/search/products?searchTerm={query}",
                "PageNumber":         1,
                "PageSize":           36,
                "SearchTerm":         query,
                "SortType":           "TraderRelevance",
            },
            headers={
                "Content-Type":  "application/json",
                "User-Agent":    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer":       f"https://www.woolworths.com.au/shop/search/products?searchTerm={query}",
                "Origin":        "https://www.woolworths.com.au",
                "Accept":        "application/json",
            },
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"  [Woolworths] Request failed: {e}")
        return []

    if response.status_code != 200:
        print(f"  [Woolworths] Status {response.status_code} — may be blocked")
        return []

    data = response.json()

    # Validate we got actual search results
    if "Products" not in data or "SearchResultsCount" not in data:
        print("  [Woolworths] Unexpected response shape")
        return []

    conn = get_connection()
    try:
        store_id = upsert_store(conn, STORE)

        for group in data.get("Products", []):
            for info in group.get("Products", []):
                name  = clean_text(info.get("DisplayName", ""))
                price = parse_price(str(info.get("Price", "")))

                if not name or not price:
                    continue

                was_price_raw = info.get("WasPrice")
                was_price     = parse_price(str(was_price_raw)) if was_price_raw else None

                product_data = {
                    "name":     name,
                    "brand":    clean_text(info.get("Brand", "")),
                    "category": clean_text(
                        info.get("Departments", [{}])[0].get("Name", "General")
                        if info.get("Departments") else "General"
                    ),
                    "unit":     parse_unit(name),
                    "barcode":  str(info.get("Barcode", "")) if info.get("Barcode") else "",
                    "imageUrl": info.get("MediumImageFile", ""),
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