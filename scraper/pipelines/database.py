"""
Database pipeline — validates and persists scraped product and price data.

Spiders yield raw dicts; this pipeline cleans, validates, and writes
them to PostgreSQL via the utils.db helpers.
"""

from utils.db import get_connection, upsert_store, upsert_product, insert_price
from utils.helpers import clean_text, parse_price, parse_unit


class ProductPipeline:
    """Validates a product dict and writes it to the database."""

    REQUIRED_FIELDS = ["name", "category"]

    def process(self, product: dict, store: dict) -> str | None:
        """
        Validate and persist a product + its price at a given store.
        Returns the product ID on success, None if validation fails.
        """
        # Clean all string fields
        product["name"]     = clean_text(product.get("name", ""))
        product["brand"]    = clean_text(product.get("brand", ""))
        product["category"] = clean_text(product.get("category", "General"))

        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if not product.get(field):
                print(f"  [pipeline] Skipping — missing required field: {field}")
                return None

        # Infer unit from name if not provided
        if not product.get("unit"):
            product["unit"] = parse_unit(product["name"])

        conn = get_connection()
        try:
            store_id   = upsert_store(conn, store)
            product_id = upsert_product(conn, product)

            if product.get("price") is not None:
                insert_price(conn, {
                    "price":     product["price"],
                    "wasPrice":  product.get("wasPrice"),
                    "isOnSale":  product.get("isOnSale", False),
                    "productId": product_id,
                    "storeId":   store_id,
                })

            return product_id

        except Exception as e:
            print(f"  [pipeline] DB error for '{product['name']}': {e}")
            return None

        finally:
            conn.close()


class PricePipeline:
    """Validates a price record and writes it to the database."""

    def process(self, price: float, product_id: str, store_id: str,
                was_price: float | None = None) -> bool:
        """
        Persist a price record. Returns True on success.
        """
        if not isinstance(price, (int, float)) or price <= 0:
            print(f"  [pipeline] Skipping invalid price: {price}")
            return False

        conn = get_connection()
        try:
            insert_price(conn, {
                "price":     round(float(price), 2),
                "wasPrice":  round(float(was_price), 2) if was_price else None,
                "isOnSale":  was_price is not None,
                "productId": product_id,
                "storeId":   store_id,
            })
            return True

        except Exception as e:
            print(f"  [pipeline] Price insert error: {e}")
            return False

        finally:
            conn.close()