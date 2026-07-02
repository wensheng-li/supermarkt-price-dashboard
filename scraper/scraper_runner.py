from spiders.store_seeder import get_nearby_stores
from spiders.openfoodfacts import fetch_products_openfoodfacts, get_fallback_products
from spiders.prices_seeder import seed_prices_for_products
from utils.db import get_connection, upsert_store


def run(product_query: str, postcode: str = None, state: str = None):
    print(f"\n🔍 Fetching data for: '{product_query}' @ {postcode} {state or ''}\n")

    nearby = []
    if postcode:
        print(
            f"→ Discovering nearby stores for postcode {postcode}"
            + (f" ({state})" if state else ""),
        )
        nearby = get_nearby_stores(postcode, radius_km=10, limit=10, state=state)
        if nearby:
            conn = get_connection()
            try:
                for s in nearby:
                    upsert_store(conn, s)
            finally:
                conn.close()
            print("PROGRESS:10", flush=True)
        else:
            print("  No nearby stores found via Overpass.")

    print("→ Step 1: Fetching products from Open Food Facts")
    products = fetch_products_openfoodfacts(product_query)
    print("PROGRESS:40", flush=True)

    if not products:
        print("  OFF unavailable — using local fallback products")
        products = get_fallback_products(product_query)

    print(f"  Found {len(products)} products\n")
    print("PROGRESS:60", flush=True)

    if not products:
        print("No products found — try a different search term.")
        return

    print("→ Step 2: Seeding realistic prices for nearby stores")
    seed_prices_for_products(products, nearby if postcode else None)

    # Update progress after price seeding
    print("PROGRESS:90", flush=True)

    print(f"\n✅ Done — {len(products)} products with prices across Australia\n")
    print("PROGRESS:100", flush=True)
    print("RESULT:completed", flush=True)


if __name__ == "__main__":
    import sys

    product_query = sys.argv[1] if len(sys.argv) > 1 else None
    postcode = sys.argv[2] if len(sys.argv) > 2 else None
    state = sys.argv[3] if len(sys.argv) > 3 else None

    if not product_query:
        print("ERROR: product_query is required", file=sys.stderr)
        sys.exit(1)

    try:
        run(product_query, postcode, state)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
