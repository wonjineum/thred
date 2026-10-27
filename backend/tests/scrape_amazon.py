"""
Amazon product scraper for the sustainability extension.

Outputs the Part A format: raw text, null when unknown, [] for no certifications.

Usage
    pip install requests beautifulsoup4
    python scripts/scrape_amazon.py B0C1234567 B0XXXXXXXX
    python scripts/scrape_amazon.py --file asins.txt
    python scripts/scrape_amazon.py --from-html raw_html/   (parse saved pages only)

Writes backend/tests/fixtures/amazon_samples.json and saves raw HTML to raw_html/
so you only hit Amazon once per product.
"""

import argparse
import json
import random
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT_PATH = Path("backend/tests/fixtures/amazon_samples.json")
RAW_DIR = Path("raw_html")
DELAY_SECONDS = 1.5  # keep at roughly one request per second or slower

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

# Labels in the "Product details" tables that hold fabric info, in priority order
MATERIAL_LABELS = ["fabric type", "material composition", "material"]


def clean(text):
    # Collapse whitespace and strip invisible unicode marks Amazon inserts.
    if text is None:
        return None
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def meta_content(soup, **attrs):
    node = soup.find("meta", attrs=attrs)
    return clean(node.get("content")) if node and node.get("content") else None


def get_detail(soup, labels):
    # Look up a labeled value across the several Amazon detail table layouts.
    wanted = [l.lower() for l in labels]
    found = {}
    for row in soup.select("table tr"):
        th, td = row.find("th"), row.find("td")
        if th and td:
            key = clean(th.get_text(" "))
            if key:
                found.setdefault(key.lower().rstrip(":"), clean(td.get_text(" ")))
    for li in soup.select("#detailBullets_feature_div li"):
        spans = li.select("span.a-text-bold")
        if spans:
            key = clean(spans[0].get_text(" "))
            if key:
                key = key.rstrip(":").strip().lower()
                full = clean(li.get_text(" "))
                val = clean(full.split(":", 1)[1]) if full and ":" in full else None
                found.setdefault(key, val)
    for row in soup.select("div.po-attribute, tr.po-brand, tr.po-material, tr.po-fabric_type"):
        label = row.select_one("span.po-break-word")
        key = row.select_one("span.a-color-secondary, td.a-span3")
        if label and key:
            k = clean(key.get_text(" "))
            if k:
                found.setdefault(k.lower().rstrip(":"), clean(label.get_text(" ")))
    for w in wanted:
        if found.get(w):
            return found[w]
    return None


def extract_asin(soup, fallback):
    node = soup.find("input", {"id": "ASIN"})
    if node and node.get("value"):
        return node["value"]
    canon = soup.find("link", {"rel": "canonical"})
    if canon and canon.get("href"):
        m = re.search(r"/dp/([A-Z0-9]{10})", canon["href"])
        if m:
            return m.group(1)
    return fallback


def extract_title(soup):
    node = soup.find(id="productTitle")
    if node:
        return clean(node.get_text(" "))
    return meta_content(soup, property="og:title")


def strip_brand(text):
    text = clean(text)
    if not text:
        return None
    text = re.sub(r"^Visit the\s+", "", text, flags=re.I)
    text = re.sub(r"\s+Store$", "", text, flags=re.I)
    text = re.sub(r"^Brand:\s*", "", text, flags=re.I)
    return text.strip() or None


def extract_brand(soup):
    # 1. the byline under the title, as text or as a logo image with alt text
    for sel in ["#bylineInfo", "#bylineInfo_feature_div a", "a#brand", "#brand"]:
        node = soup.select_one(sel)
        if node:
            text = clean(node.get_text(" "))
            if not text:
                img = node.find("img")
                text = clean(img.get("alt")) if img else None
            text = strip_brand(text)
            if text:
                return text
    # 2. any link that reads "Visit the ___ Store"
    for a in soup.find_all("a"):
        t = clean(a.get_text(" "))
        if t and re.match(r"^Visit the .+ Store$", t, re.I):
            return strip_brand(t)
    # 3. a brand logo image
    for img in soup.select("#brandBannerFeatureGroup img, #brand-logo img, #bylineInfo_feature_div img"):
        alt = strip_brand(img.get("alt"))
        if alt:
            return alt
    # 4. the Brand row in the product details
    return strip_brand(get_detail(soup, ["brand"]))


def to_float(text):
    if not text:
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def extract_price(soup, html=""):
    selectors = [
        "#corePrice_feature_div span.a-price:not(.a-text-price) span.a-offscreen",
        "#corePriceDisplay_desktop_feature_div span.a-price:not(.a-text-price) span.a-offscreen",
        "span.priceToPay span.a-offscreen",
        "#apex_desktop span.a-price:not(.a-text-price) span.a-offscreen",
        "span.a-price:not(.a-text-price) span.a-offscreen",
        "#price_inside_buybox",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#tp_price_block_total_price_ww span.a-offscreen",
    ]
    for sel in selectors:
        for node in soup.select(sel):
            val = to_float(node.get_text())
            if val:
                return val
    # whole and fraction spans, like 120 and 00
    whole = soup.select_one("span.a-price-whole")
    if whole:
        w = re.sub(r"\D", "", whole.get_text())
        frac = soup.select_one("span.a-price-fraction")
        f = re.sub(r"\D", "", frac.get_text()) if frac else ""
        if w:
            return float(f"{w}.{f or '00'}")
    # hidden inputs and embedded JSON
    node = soup.select_one("#twister-plus-price-data-price")
    if node and node.get("value"):
        val = to_float(node["value"])
        if val:
            return val
    for pat in [r'"priceAmount"\s*:\s*([\d.]+)', r'"displayPrice"\s*:\s*"\$?([\d,.]+)"',
                r'"price"\s*:\s*"\$?([\d,.]+)"']:
        m = re.search(pat, html or "")
        if m:
            val = to_float(m.group(1))
            if val:
                return val
    return to_float(meta_content(soup, property="product:price:amount"))


def extract_image(soup):
    img = soup.find(id="landingImage") or soup.find(id="imgBlkFront") or soup.select_one("#imgTagWrapperId img")
    if img:
        hi = img.get("data-old-hires")
        if hi:
            return hi
        dyn = img.get("data-a-dynamic-image")
        if dyn:
            try:
                return next(iter(json.loads(dyn)))
            except (ValueError, StopIteration):
                pass
        if img.get("src"):
            return img["src"]
    return meta_content(soup, property="og:image")


def extract_category(soup):
    for sel in ["#wayfinding-breadcrumbs_feature_div li a", "#wayfinding-breadcrumbs_container a"]:
        texts = [clean(a.get_text(" ")) for a in soup.select(sel)]
        texts = [t for t in texts if t]
        if texts:
            return texts[-1]
    return None


def extract_certifications(soup):
    # Names exactly as shown under the Climate Pledge Friendly badge. [] if none.
    badge = soup.select_one("#climatePledgeFriendly, #climatePledgeFriendlyBadge_feature_div")
    if not badge:
        return []
    certs = []
    for el in badge.select("span, a, li"):
        t = clean(el.get_text(" "))
        if t and t.lower() not in ("climate pledge friendly", "learn more") and len(t) < 80:
            certs.append(t)
    return list(dict.fromkeys(certs))


def parse_product(html, fallback_asin):
    soup = BeautifulSoup(html, "html.parser")
    asin = extract_asin(soup, fallback_asin)
    return {
        "item_id": asin,
        "title": extract_title(soup),
        "brand": extract_brand(soup),
        "price": extract_price(soup, html),
        "image_url": extract_image(soup),
        "product_url": f"https://www.amazon.com/dp/{asin}" if asin else None,
        "material_text": get_detail(soup, MATERIAL_LABELS),
        "category": extract_category(soup),
        "certifications": extract_certifications(soup),
    }


def is_blocked(html):
    low = html.lower()
    return "captcha" in low or "api-services-support@amazon.com" in low or "robot check" in low


def fetch(asin):
    RAW_DIR.mkdir(exist_ok=True)
    cache = RAW_DIR / f"{asin}.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    resp = requests.get(f"https://www.amazon.com/dp/{asin}", headers=HEADERS, timeout=20)
    resp.raise_for_status()
    html = resp.text
    if is_blocked(html):
        raise RuntimeError(f"Amazon served a captcha for {asin}. Slow down or use saved HTML.")
    cache.write_text(html, encoding="utf-8")
    time.sleep(DELAY_SECONDS + random.random())
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asins", nargs="*", help="ASINs or amazon.com/dp/ URLs")
    ap.add_argument("--file", help="text file with one ASIN or URL per line")
    ap.add_argument("--from-html", help="folder of saved .html files named <ASIN>.html")
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    items = []

    if args.from_html:
        for path in sorted(Path(args.from_html).glob("*.html")):
            items.append(parse_product(path.read_text(encoding="utf-8"), path.stem))
    else:
        raw = list(args.asins)
        if args.file:
            raw += [l.strip() for l in Path(args.file).read_text().splitlines() if l.strip()]
        for entry in raw:
            m = re.search(r"([A-Z0-9]{10})", entry)
            if not m:
                print(f"skip, no ASIN found in {entry}")
                continue
            asin = m.group(1)
            try:
                items.append(parse_product(fetch(asin), asin))
                print(f"ok {asin}")
            except Exception as e:
                print(f"fail {asin} {e}")

    # item_id and title are required, drop anything missing them
    items = [i for i in items if i["item_id"] and i["title"]]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"items": items}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(items)} items to {out}")


if __name__ == "__main__":
    main()
