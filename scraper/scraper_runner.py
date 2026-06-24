import sys
from spiders.openfoodfacts import fetch_products_openfoodfacts,get_fallback_products
from spiders.prices_seeder  import seed_prices_for_products

def run(product_query: str):
    print(f"\n🔍 Fetching data for: '{product_query}'\n")

    print("→ Step 1: Fetching products from Open Food Facts")
    products = fetch_products_openfoodfacts(product_query)

    if not products:
        print("  OFF unavailable — using local fallback products")
        products = get_fallback_products(product_query)
        
    print(f"  Found {len(products)} products\n")

    if not products:
        print("No products found — try a different search term.")
        return

    print("→ Step 2: Seeding realistic prices for Woolworths, Coles, IGA")
    seed_prices_for_products(products)

    print(f"\n✅ Done — {len(products)} products with prices at 3 stores\n")

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "full cream milk"
    run(query)