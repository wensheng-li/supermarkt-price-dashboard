"""
Woolworths spider — Playwright-based browser automation.

STATUS: Functional architecture, blocked in practice by Akamai bot detection.
The scraper correctly intercepts Woolworths' internal Search/products API
(POST https://www.woolworths.com.au/apis/ui/Search/products) but cannot
establish a valid session without browser fingerprint spoofing tools.

For the live demo, data is sourced from Open Food Facts (see openfoodfacts.py)
with prices seeded via price_seeder.py.

Potential production fix: use Browserless.io or Zyte Smart Proxy Manager
to handle session and fingerprint requirements.
"""
import os
import json
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
from utils.helpers import parse_price, parse_unit, clean_text, random_delay
from utils.db import get_connection, upsert_store, upsert_product, insert_price
from dotenv import load_dotenv

load_dotenv()

# Woolworths store details are fetched via their internal API
# This endpoint is what their own website calls — not an official public API
WOOLWORTHS_SEARCH_URL = "https://www.woolworths.com.au/apis/ui/Search/products"

HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

def scrape_woolworths(product_query: str, store: dict):
    """
    Scrape Woolworths for a product query at a given store.
    Uses Playwright to load the page (handles JS rendering),
    then intercepts the API response directly.
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

        # Use a realistic browser context to reduce bot detection
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-AU",
            extra_http_headers={
                "Accept-Language": "en-AU,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
        )

        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            "window.navigator.chrome = { runtime: {} };"
        )

        # Capture Woolworths API responses and requests for debugging
        captured = []

        def handle_response(response):
            if response.status == 200 and "woolworths.com.au/apis" in response.url:
                print(f"    [intercepted] {response.url}")
            if "Search/products" in response.url and response.status == 200:
                try:
                    captured.append(response.json())
                except Exception:
                    print(f"    [intercepted] failed to parse JSON from {response.url}")

        page.on("response", handle_response)

        # Navigate to the search results page
        search_url = (
            f"https://www.woolworths.com.au/shop/search/products"
            f"?searchTerm={quote_plus(product_query)}"
        )

        print(f"  [Woolworths] Searching: {product_query}")
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            print("  [Woolworths] Page.goto timed out waiting for domcontentloaded")

        # Give the page additional time for JS to fire the search API
        page.wait_for_timeout(7000)

        if not captured:
            try:
                page.wait_for_response(
                    lambda response: (
                        response.status == 200
                        and "application/json" in response.headers.get("content-type", "")
                        and "Search/products" in response.url
                    ),
                    timeout=30000,
                )
            except Exception:
                print("  [Woolworths] Search products response did not appear in time")
        else:
            print(f"  [Woolworths] Already captured {len(captured)} Search/products responses during navigation")

        random_delay(float(os.getenv("SCRAPE_DELAY", 3)))

        context.close()
        browser.close()

    # Parse the intercepted JSON responses
    conn = get_connection()

    try:
        store_id = upsert_store(conn, store)

        for response_data in captured:
            # Top-level Products is a list of product groups
            product_groups = response_data.get("Products", [])

            for group in product_groups:
                # Each group has a nested Products list with the actual items
                items = group.get("Products", [])

                for info in items:
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