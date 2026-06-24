"""
Coles spider — Playwright-based browser automation.

STATUS: Blocked by bot detection (returns 404/challenge page on headless requests).
Coles uses DataDome or similar enterprise bot protection that detects
headless Chromium even with stealth patches applied.

For the live demo, data is sourced from Open Food Facts (see openfoodfacts.py)
with prices seeded via price_seeder.py.

Potential production fix: residential proxy rotation + Playwright stealth plugin,
or a commercial scraping API like Zyte or ScraperAPI.
"""

import os
import json
import re
import requests
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
from utils.helpers import parse_price, parse_unit, clean_text, random_delay
from utils.db import get_connection, upsert_store, upsert_product, insert_price
from dotenv import load_dotenv

load_dotenv()

COLES_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
window.navigator.chrome = { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['en-AU', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
"""

HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"


def is_bot_challenge(html: str) -> bool:
    if not html:
        return False
    return any(
        phrase in html
        for phrase in [
            "Pardon Our Interruption",
            "please enable JavaScript",
            "we think you were a bot",
            "noindex, nofollow",
        ]
    )


def extract_coles_search_payload(data):
    if not isinstance(data, dict):
        return None

    if "results" in data and isinstance(data["results"], list):
        return data
    if "searchResults" in data and isinstance(data["searchResults"], dict):
        return data["searchResults"]
    if "products" in data and isinstance(data["products"], list):
        return data
    return None


def scrape_coles(product_query: str, store: dict):
    """
    Scrape Coles for a product query.
    Coles renders via React, so we intercept their internal
    product search API response rather than parsing HTML.
    """
    results  = []
    captured = []

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

        # Create browser context and set default navigation timeout
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-AU",
            timezone_id="Australia/Sydney",
            extra_http_headers={
                "Accept-Language": "en-AU,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not A(Brand)";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            },
        )
        # Set default navigation timeout globally
        context.set_default_navigation_timeout(60000)

        page = context.new_page()
        page.add_init_script(COLES_STEALTH_JS)

        # ⚠️ Intercept Coles' internal search API
        seen_responses = []

        def handle_response(response):
            try:
                url = response.url
                ct = response.headers.get("content-type", "")
                if response.status == 200 and "application/json" in ct:
                    data = response.json()
                    payload = extract_coles_search_payload(data)
                    # Only store if it actually has results
                    if payload and payload.get("results"):
                        print(f"    [captured] {url}")
                        captured.append(payload)
            except Exception:
                pass

        page.on("response", handle_response)

        search_url = (
            f"https://www.coles.com.au/search/products?"
            f"q={quote_plus(product_query)}"
        )

        try:
            page.goto("https://www.coles.com.au/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
        except Exception as exc:
            print(f"  [Coles] Warning: homepage initialization failed: {exc}")

        print(f"  [Coles] Searching: {product_query}")
        try:
            # page.goto(search_url, wait_until="load", timeout=45000)
            page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(8000)  # give XHRs time to fire after DOM loads
        except Exception:
            print("  [Coles] Page.goto timed out waiting for load")

        # Give the page additional time for JS to execute and fire XHRs
        page.wait_for_timeout(5000)

        # Extract Next.js embedded JSON payload if available
        page_content = page.content()
        match = re.search(
            r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
            page_content,
            re.DOTALL,
        )

        if match:
            try:
                next_data = json.loads(match.group(1))
                page_props = next_data.get("props", {}).get("pageProps", {})
                search_results = page_props.get("searchResults")
                if isinstance(search_results, dict):
                    captured.append(search_results)
            except Exception as exc:
                print(f"  [Coles] Failed to parse __NEXT_DATA__ JSON: {exc}")

        try:
            page.wait_for_response(
                lambda response: (
                    response.status == 200
                    and "application/json" in response.headers.get("content-type", "")
                ),
                timeout=30000,
            )
        except Exception:
            pass

        # Scroll to trigger lazy-loaded responses and page content
        for _ in range(4):
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(1500)

        try:
            page.wait_for_selector("[data-testid='product-tile']", timeout=15000)
        except Exception:
            print("  [Coles] Product tiles didn't appear — page may have changed structure")

        page_html = page.content()
        if is_bot_challenge(page_html):
            print("  [Coles] Bot challenge detected on search page — search is blocked.")

        # Fallback: fetch the search page directly using requests if no JSON was captured.
        if not captured:
            try:
                cookies = context.cookies()
                cookie_header = "; ".join(
                    f"{cookie['name']}={cookie['value']}" for cookie in cookies
                )

                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-AU,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Upgrade-Insecure-Requests": "1",
                    "Referer": "https://www.coles.com.au/",
                }
                if cookie_header:
                    headers["Cookie"] = cookie_header

                fallback_html = requests.get(
                    search_url,
                    headers=headers,
                    timeout=30,
                ).text

                fallback_match = re.search(
                    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                    fallback_html,
                    re.DOTALL,
                )
                if fallback_match:
                    next_data = json.loads(fallback_match.group(1))
                    page_props = next_data.get("props", {}).get("pageProps", {})
                    search_results = extract_coles_search_payload(page_props)
                    if search_results is not None:
                        captured.append(search_results)
                        print("  [Coles] Captured searchResults from direct request fallback")
            except Exception as exc:
                print(f"  [Coles] Direct request fallback failed: {exc}")

        random_delay(float(os.getenv("SCRAPE_DELAY", 3)))

        # If no API responses were captured, print recent API calls for debugging
        if not captured:
            print("  [Coles] No captured JSON responses — recent responses:")
            for r in seen_responses[-12:]:
                print(f"    - {r['status']} {r['url']} (content-type: {r['contentType']})")

        context.close()
        browser.close()

    conn = get_connection()

    try:
        store_id = upsert_store(conn, store)

        for response_data in captured:
            # Coles nests results under 'results' → 'products'
            products = response_data.get("results", [])

            for item in products:
                pricing = item.get("pricing", {})
                name    = clean_text(item.get("name", ""))
                price   = parse_price(str(pricing.get("now", "")))

                if not name or not price:
                    continue

                was_price_raw = pricing.get("was")
                was_price     = parse_price(str(was_price_raw)) if was_price_raw else None

                category = "General"
                cat_value = item.get("category")
                if isinstance(cat_value, list) and cat_value:
                    first_cat = cat_value[0]
                    if isinstance(first_cat, dict):
                        category = first_cat.get("name", "General")
                    elif isinstance(first_cat, str):
                        category = first_cat
                elif isinstance(cat_value, dict):
                    category = cat_value.get("name", "General")
                elif isinstance(cat_value, str):
                    category = cat_value
                elif item.get("merchandiseHeir"):
                    category = item.get("merchandiseHeir", {}).get("category", "General")

                image_url = None
                image_uris = item.get("imageUris")
                if isinstance(image_uris, list) and image_uris:
                    first_image = image_uris[0]
                    if isinstance(first_image, dict):
                        image_url = first_image.get("uri")
                    elif isinstance(first_image, str):
                        image_url = first_image

                barcode = item.get("barcode")
                if barcode is None:
                    barcode = item.get("id")
                barcode = str(barcode) if barcode is not None else ""

                product_data = {
                    "name":     name,
                    "brand":    clean_text(item.get("brand", "")),
                    "category": clean_text(category),
                    "unit":     parse_unit(name),
                    "barcode":  barcode,
                    "imageUrl": image_url,
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