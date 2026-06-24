# Database utilities for the scraper.
# This connects the scraper directly to the PostgreSQL to write prices

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Return a live PostgreSQL connection."""
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )

def upsert_store(conn, store: dict) -> str:
    """
    Insert a store if it doesn't exist, return its ID.
    Uses the store address as the unique key.
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO "Store" (id, name, chain, address, postcode, suburb, latitude, longitude, "createdAt")
            VALUES (gen_random_uuid()::text, %(name)s, %(chain)s, %(address)s,
                    %(postcode)s, %(suburb)s, %(latitude)s, %(longitude)s, NOW())
            ON CONFLICT (address) DO UPDATE
                SET name = EXCLUDED.name,
                    chain = EXCLUDED.chain
            RETURNING id
        """, store)
        conn.commit()
        return cur.fetchone()['id']

def upsert_product(conn, product: dict) -> str:
    with conn.cursor() as cur:
        # If barcode is empty/None, use name+unit as fallback unique key
        if not product.get('barcode'):
            cur.execute("""
                INSERT INTO "Product" (id, name, brand, category, unit, "imageUrl", "createdAt", "updatedAt")
                VALUES (gen_random_uuid()::text, %(name)s, %(brand)s, %(category)s,
                        %(unit)s, %(imageUrl)s, NOW(), NOW())
                ON CONFLICT DO NOTHING
                RETURNING id
            """, product)
            row = cur.fetchone()
            if not row:
                # Already exists — fetch it
                cur.execute("""
                    SELECT id FROM "Product" WHERE name = %(name)s AND unit = %(unit)s LIMIT 1
                """, product)
                row = cur.fetchone()
        else:
            cur.execute("""
                INSERT INTO "Product" (id, name, brand, category, unit, barcode, "imageUrl", "createdAt", "updatedAt")
                VALUES (gen_random_uuid()::text, %(name)s, %(brand)s, %(category)s,
                        %(unit)s, %(barcode)s, %(imageUrl)s, NOW(), NOW())
                ON CONFLICT (barcode) DO UPDATE
                    SET name       = EXCLUDED.name,
                        "imageUrl" = EXCLUDED."imageUrl",
                        "updatedAt" = NOW()
                RETURNING id
            """, product)
            row = cur.fetchone()

        conn.commit()
        return row['id']

def insert_price(conn, price: dict):
    """Insert a new price record (always a new row — builds price history)."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO "Price" (id, price, "wasPrice", "isOnSale", "scrapedAt", "productId", "storeId")
            VALUES (gen_random_uuid()::text, %(price)s, %(wasPrice)s,
                    %(isOnSale)s, NOW(), %(productId)s, %(storeId)s)
        """, price)
        conn.commit()