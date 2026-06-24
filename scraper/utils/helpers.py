import re
import time
import random

def parse_price(price_str: str) -> float | None:
    """
    Extract a float from a price string.
    '$3.50' → 3.50,  '3.50 ea' → 3.50,  None if unparseable
    """
    if not price_str:
        return None
    match = re.search(r'[\d]+\.[\d]{2}', price_str.replace(',', ''))
    return float(match.group()) if match else None

def parse_unit(name: str) -> str | None:
    """
    Extract unit from a product name.
    'Full Cream Milk 2L' → '2L',  'Bread 700g' → '700g'
    """
    match = re.search(r'(\d+(\.\d+)?\s*(ml|l|g|kg|pk|pack|ct))', name, re.IGNORECASE)
    return match.group().strip() if match else None

def random_delay(base: float = 3.0):
    """
    Sleep for base ± 1 second to appear more human-like.
    This is important for avoiding bot detection.
    """
    time.sleep(base + random.uniform(-1, 1))

def clean_text(text: str) -> str:
    """Strip whitespace and normalise unicode characters."""
    if not text:
        return ''
    return ' '.join(text.split()).strip()