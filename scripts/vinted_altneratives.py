"""
Vinted alternatives scraper for Thred.  
  * raw text only, no cleaning (material_text is sent exactly as shown)
  * null when unknown, never an empty string or a guess
  * seller description is never read or saved
  * raw HTML is saved once and parsed from the saved copy
  * robots.txt checked, about one request per second

Setup
    pip install playwright beautifulsoup4 requests
    playwright install chromium
Run (from repo root)
    python scripts/vinted_scraper.py --per-type 5
"""

import argparse
import json
import random
import re
import time
from pathlib import Path
from urllib import robotparser

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE = "https://www.vinted.com"
OUT_PATH = Path("backend/data/alternatives.json")
RAW_DIR = Path("scripts/raw/vinted")
UA = "ThredResearchBot/0.1 (student project)"

# Must match the backend's fixed garment_type list. Ask Wonjin for the exact values.
GARMENT_QUERIES = {
    "hoodie": "hoodie",
    "jeans": "jeans",
    "pants": "pants",
    "sweater": "sweater",
    "jacket": "jacket",
    "t-shirt": "t-shirt",
    "dress": "dress",
    "skirt": "skirt",
}


def nullify(value):
    """Part A rule: null for unknown, never an empty string."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def polite_sleep():
    time.sleep(random.uniform(1.0, 2.0))


def robots_ok(url: str) -> bool:
    rp = robotparser.RobotFileParser()
    rp.set_url(f"{BASE}/robots.txt")
    rp.read()
    return rp.can_fetch(UA, url)


def fetch_html(page, url: str, cache_name: str) -> str | None:
    """Save raw HTML once, then always read from the saved copy."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{cache_name}.html"
    if not path.exists():
        if not robots_ok(url):
            print(f"robots.txt disallows {url}")
            return None
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        path.write_text(page.content(), encoding="utf-8")
        polite_sleep()
    return path.read_text(encoding="utf-8")


def item_urls_from_search(html: str, limit: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    seen, urls = set(), []
    for a in soup.select("a[href*='/items/']"):
        href = a["href"].split("?")[0]
        if href.startswith("/"):
            href = BASE + href
        if re.search(r"/items/\d+", href) and href not in seen:
            seen.add(href)
            urls.append(href)
        if len(urls) >= limit:
            break
    return urls


def detail_value(soup: BeautifulSoup, label: str):
    node = soup.find(string=re.compile(rf"^\s*{label}\s*$", re.I))
    if not node or not node.find_parent():
        return None
    sibling = node.find_parent().find_next_sibling()
    return sibling.get_text(" ", strip=True) if sibling else None


def parse_item(html: str, url: str, garment_type: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    product = None
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        for entry in data if isinstance(data, list) else [data]:
            if isinstance(entry, dict) and entry.get("@type") == "Product":
                product = entry
    if not product:
        return None

    brand = product.get("brand")
    brand = brand.get("name") if isinstance(brand, dict) else brand
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    image = product.get("image")
    image = image[0] if isinstance(image, list) and image else image
    try:
        price = float(offers.get("price"))
    except (TypeError, ValueError):
        price = None
    match = re.search(r"/items/(\d+)", url)
    if not match:
        return None

    return {
        "item_id": f"vinted_{match.group(1)}",
        "title": nullify(product.get("name")),
        "brand": nullify(brand),
        "price": price,
        "image_url": nullify(image),
        "product_url": url,
        "material_text": nullify(detail_value(soup, "Material")),
        "category": nullify(detail_value(soup, "Category")),
        "certifications": None,  # nobody checked on Vinted, so null, not []
        "garment_type": garment_type,
    }


def valid(item: dict) -> bool:
    if not item["title"] or not item["image_url"]:
        return False
    try:
        h = {"User-Agent": UA}
        r = requests.head(item["product_url"], headers=h, timeout=10, allow_redirects=True)
        i = requests.head(item["image_url"], headers=h, timeout=10, allow_redirects=True)
        return r.status_code < 400 and i.status_code == 200 and i.headers.get(
            "content-type", ""
        ).startswith("image/")
    except requests.RequestException:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-type", type=int, default=5)
    args = ap.parse_args()

    catalog = {}
    if OUT_PATH.exists():
        catalog = {i["item_id"]: i for i in json.loads(OUT_PATH.read_text())}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        for garment_type, query in GARMENT_QUERIES.items():
            search_url = f"{BASE}/catalog?search_text={query}&order=relevance"
            html = fetch_html(page, search_url, f"search_{garment_type}")
            if not html:
                continue
            for url in item_urls_from_search(html, args.per_type):
                item_html = fetch_html(page, url, re.search(r"/items/(\d+)", url).group(1))
                item = parse_item(item_html, url, garment_type) if item_html else None
                if item and valid(item):
                    catalog[item["item_id"]] = item
                    print(f"saved {item['item_id']} ({garment_type})")
                else:
                    print(f"skipped {url}")
        browser.close()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(list(catalog.values()), indent=2), encoding="utf-8")
    print(f"wrote {len(catalog)} listings to {OUT_PATH}")


if __name__ == "__main__":
    main()
