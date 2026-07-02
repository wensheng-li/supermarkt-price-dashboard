"""
Price seeder — generates realistic prices for products fetched from Open Food Facts
and persists them across Woolworths, Coles, and IGA using the database pipeline.
"""

import random
from pipelines.database import ProductPipeline, PricePipeline
from utils.db import get_connection, upsert_store

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

# Probability that a store stocks any given product
# IGA stocks ~70% of what the majors carry — smaller range
STORE_STOCK_PROBABILITY = {
    "woolworths": 0.95,
    "coles":      0.95,
    "iga":        0.70,
}

product_pipeline = ProductPipeline()
price_pipeline   = PricePipeline()


def generate_price(base_price: float, chain: str) -> float:
    """Apply store multiplier and round to nearest 5c (realistic supermarket pricing)."""
    raw = base_price * STORE_PRICE_MULTIPLIERS.get(chain, 1.00)
    return round(round(raw / 0.05) * 0.05, 2)


def seed_prices_for_products(products: list, stores: list = None):
    """
    Given a list of product dicts (from Open Food Facts),
    seed realistic prices at the supplied stores via the pipeline layer.
    """
    if not stores:
        print("No stores available for seeding prices.")
        return

    # Ensure every store has an address for a stable upsert key.
    for store in stores:
        if not store.get("address"):
            store["address"] = f"{store.get('name', 'store')}|{store.get('postcode', '')}".strip()

    # Upsert all stores once upfront and cache their IDs by stable store key.
    conn = get_connection()
    store_ids = {}
    try:
        for store in stores:
            key = store["address"]
            store_ids[key] = upsert_store(conn, store)
    finally:
        conn.close()

    seeded_count = 0
    skipped_count = 0

    for product in products:
        category = product.get("category", "General")
        price_range = CATEGORY_PRICE_RANGES.get(category, (2.00, 10.00))
        base_price = random.uniform(*price_range)

        for store in stores:
            chain = store.get("chain", "independent").lower()
            stock_probability = STORE_STOCK_PROBABILITY.get(chain, 0.80)
            if random.random() > stock_probability:
                skipped_count += 1
                print(
                    f"    {store['name']:12} —  not stocked  — {product['name']}"
                )
                continue

            store_key = store.get("address") or f"{store.get('name')}|{store.get('postcode')}"
            store_id = store_ids.get(store_key)
            if not store_id:
                print(f"    Skipping store without ID: {store}")
                continue

            price = generate_price(base_price, chain)
            is_on_sale = random.random() < 0.20
            was_price = (
                round(price * random.uniform(1.10, 1.30), 2)
                if is_on_sale
                else None
            )

            product_id = product_pipeline.process(
                {**product, "price": price, "wasPrice": was_price, "isOnSale": is_on_sale},
                store,
            )

            if not product_id:
                continue

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

    print(f"\n  Seeded {seeded_count} price records across {len(stores)} stores")
    print(f"  Skipped {skipped_count} store/product combinations (not stocked)")