"""
Price seeder — generates realistic prices for products fetched from Open Food Facts
and persists them across Woolworths, Coles, and IGA using the database pipeline.
"""

import random
from pipelines.database import ProductPipeline, PricePipeline
from utils.db import get_connection, upsert_store

STORES = [
    {
        "name":      "Woolworths",
        "chain":     "woolworths",
        "address":   "500 George St, Sydney NSW 2000",
        "postcode":  "2000",
        "suburb":    "Sydney",
        "latitude":  -33.8748,
        "longitude": 151.2069,
    },
    {
        "name":      "Coles",
        "chain":     "coles",
        "address":   "Shop 1 World Square, Sydney NSW 2000",
        "postcode":  "2000",
        "suburb":    "Sydney",
        "latitude":  -33.8765,
        "longitude": 151.2073,
    },
    {
        "name":      "IGA",
        "chain":     "iga",
        "address":   "152 Pyrmont St, Pyrmont NSW 2009",
        "postcode":  "2009",
        "suburb":    "Pyrmont",
        "latitude":  -33.8731,
        "longitude": 151.1947,
    },
]

# Realistic base price ranges by category
CATEGORY_PRICE_RANGES = {
    "Dairy":      (1.50, 6.00),
    "Bakery":     (2.00, 8.00),
    "Meat":       (5.00, 25.00),
    "Fruit":      (1.50, 10.00),
    "Vegetables": (1.00, 8.00),
    "Drinks":     (2.00, 5.00),
    "Pantry":     (1.50, 12.00),
    "General":    (2.00, 10.00),
}

# IGA is typically 5–15% pricier; Coles roughly matches Woolworths
STORE_PRICE_MULTIPLIERS = {
    "woolworths": 1.00,
    "coles":      random.uniform(0.97, 1.03),
    "iga":        random.uniform(1.05, 1.15),
}

product_pipeline = ProductPipeline()
price_pipeline   = PricePipeline()


def generate_price(base_price: float, chain: str) -> float:
    """Apply store multiplier and round to nearest 5c (realistic supermarket pricing)."""
    raw = base_price * STORE_PRICE_MULTIPLIERS.get(chain, 1.00)
    return round(round(raw / 0.05) * 0.05, 2)


def seed_prices_for_products(products: list):
    """
    Given a list of product dicts (from Open Food Facts),
    seed realistic prices at all three stores via the pipeline layer.
    """
    # Upsert all stores once upfront and cache their IDs
    conn = get_connection()
    store_ids = {}
    try:
        for store in STORES:
            store_ids[store["chain"]] = upsert_store(conn, store)
    finally:
        conn.close()

    seeded_count = 0

    for product in products:
        # Determine base price from category
        category    = product.get("category", "General")
        price_range = CATEGORY_PRICE_RANGES.get(category, (2.00, 10.00))
        base_price  = random.uniform(*price_range)

        for store in STORES:
            chain    = store["chain"]
            store_id = store_ids[chain]
            price    = generate_price(base_price, chain)

            # 20% chance of being on sale
            is_on_sale = random.random() < 0.20
            was_price  = round(price * random.uniform(1.10, 1.30), 2) if is_on_sale else None

            # Write product first via ProductPipeline (validates + upserts)
            product_id = product_pipeline.process(
                {**product, "price": price, "wasPrice": was_price, "isOnSale": is_on_sale},
                store,
            )

            if not product_id:
                # ProductPipeline already printed the reason — skip price
                continue

            # Write price separately via PricePipeline
            success = price_pipeline.process(
                price=price,
                product_id=product_id,
                store_id=store_id,
                was_price=was_price,
            )

            if success:
                seeded_count += 1
                sale_note = f" (was ${was_price})" if is_on_sale else ""
                print(f"    {store['name']:12} ${price:.2f}{sale_note}  — {product['name']}")

    print(f"\n  Seeded {seeded_count} price records across {len(STORES)} stores")