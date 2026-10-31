"""
Thred brand sustainability scraper (Part B of docs/data-formats).

What it does
------------
Starts from the hand-researched file backend/data/brands.json and re-checks
three facts for every brand automatically:

  * fti_score     -> Fashion Transparency Index, from the WikiRate API
  * sbti_target   -> SBTi's official "companies" spreadsheet
  * bluesign      -> bluesign's official System Partner list (PDF)

It also re-checks B Corp status for brands whose B Lab directory page is known.
Anything it can't find is left exactly as it was in brands.json.

It follows the scraping rules in the data-formats doc:
  * checks robots.txt before fetching from a site
  * waits about 1 second between requests
  * saves every raw download once in scripts/raw/ and parses from that copy
  * never uses Good On You
  * collects facts, not scores

Output (for review, NOT written into backend/data automatically):
  scripts/output/brands_scraped.json   same format as brands.json
  scripts/output/changes.txt           every value the scraper changed, and why

Setup
-----
  pip install requests openpyxl pypdf wikirate4py

WikiRate needs a free API key. Make an account at wikirate.org, get your key,
then set it before running:
  export WIKIRATE_API_KEY="your-key"        (Mac/Linux)
  set WIKIRATE_API_KEY=your-key             (Windows)
Without a key, the FTI step is skipped and FTI scores stay as they are.

Run (from the repo root)
------------------------
  python scripts/scrape_brands.py              # download + parse
  python scripts/scrape_brands.py --offline    # only re-parse files already in scripts/raw/
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent   # scripts/ at the repo root
REPO_ROOT = SCRIPTS_DIR.parent
BASE_FILE = REPO_ROOT / "backend" / "data" / "brands.json"
RAW_DIR = SCRIPTS_DIR / "raw"
OUT_DIR = SCRIPTS_DIR / "output"

USER_AGENT = "ThredResearchBot/1.0 (student project; contact via GitHub repo)"
REQUEST_DELAY_SECONDS = 1.0

SBTI_URL = "https://files.sciencebasedtargets.org/production/files/companies-excel.xlsx"
BLUESIGN_URL = ("https://www.bluesign.com/wp-content/uploads/2026/08/"
                "bluesign-System-Partner-list_2026.08.01.pdf")
BLAB_PAGE = "https://www.bcorporation.net/en-us/find-a-b-corp/company/{slug}/"

# Newest edition first. 2024 and 2025 are climate-only special editions, so the
# team agreed to use 2023 (the last full edition) and fall back to older ones.
FTI_YEARS = [2023, 2022, 2021, 2020, 2019]
FTI_DESIGNER = "Fashion Revolution"

# How each brand is named in each source. Parent companies are used where the
# source only lists the parent (e.g. Calvin Klein's SBTi target belongs to PVH).
#   wikirate : name to search for on WikiRate (partial match is OK)
#   sbti     : company name in the SBTi spreadsheet
#   bluesign : exact entry text on the bluesign partner list
#   blab     : slug of the brand's B Lab directory page, if it has one
SOURCES = {
    "Amazon Essentials": {"wikirate": "Amazon", "sbti": "Amazon", "bluesign": "Amazon"},
    "Hanes": {"wikirate": "Hanesbrands", "sbti": "Hanesbrands", "bluesign": "Hanesbrands"},
    "Gildan": {"wikirate": "Gildan", "sbti": "Gildan Activewear", "bluesign": "Gildan"},
    "Fruit of the Loom": {"wikirate": "Fruit of the Loom", "sbti": "Fruit of the Loom", "bluesign": "Fruit of the Loom"},
    "Levi's": {"wikirate": "Levi Strauss", "sbti": "Levi Strauss", "bluesign": "Levi Strauss"},
    "Carhartt": {"wikirate": "Carhartt", "sbti": "Carhartt", "bluesign": "Carhartt",
                 "blab": "carhartt-inc-developed-market"},
    "Under Armour": {"wikirate": "Under Armour", "sbti": "Under Armour", "bluesign": "Under Armour, Inc"},
    "Columbia": {"wikirate": "Columbia Sportswear", "sbti": "Columbia Sportswear", "bluesign": "Columbia Sportswear"},
    "Calvin Klein": {"wikirate": "Calvin Klein", "sbti": "PVH", "bluesign": "PVH"},
    "adidas": {"wikirate": "adidas", "sbti": "adidas", "bluesign": "adidas AG"},
    "Nike": {"wikirate": "Nike", "sbti": "Nike", "bluesign": "Nike"},
    "Puma": {"wikirate": "Puma", "sbti": "Puma", "bluesign": "Puma SE"},
    "New Balance": {"wikirate": "New Balance", "sbti": "New Balance", "bluesign": "New Balance"},
    "Tommy Hilfiger": {"wikirate": "Tommy Hilfiger", "sbti": "PVH", "bluesign": "PVH"},
    "Wrangler": {"wikirate": "Wrangler", "sbti": "Kontoor Brands", "bluesign": "Kontoor"},
    "Gap": {"wikirate": "Gap", "sbti": "Gap", "bluesign": "Gap Inc"},
    "Pact": {"sbti": "Pact", "bluesign": "Wear Pact"},
    "The Drop": {"wikirate": "Amazon", "sbti": "Amazon", "bluesign": "Amazon"},
    "The North Face": {"wikirate": "North Face", "sbti": "VF Corporation", "bluesign": "VF Outdoor, LLC"},
    "ASICS": {"wikirate": "ASICS", "sbti": "ASICS", "bluesign": "ASICS Corporation"},
    "Guess": {"wikirate": "Guess", "sbti": "Guess", "bluesign": "Guess"},
    "Reebok": {"wikirate": "Reebok", "sbti": "Authentic Brands", "bluesign": "Reebok"},
    "Skechers": {"wikirate": "Skechers", "sbti": "Skechers", "bluesign": "Skechers"},
    "Allbirds": {"sbti": "Allbirds", "bluesign": "Allbirds", "blab": "allbirds-inc"},
    "Forever 21": {"wikirate": "Forever 21", "sbti": "Forever 21", "bluesign": "Forever 21"},
}


# ---------------------------------------------------------------------------
# Polite fetching: robots.txt, rate limit, raw cache
# ---------------------------------------------------------------------------

_robots_cache = {}
_last_request = [0.0]


def allowed_by_robots(url):
    """Return True if robots.txt lets our user agent fetch this URL."""
    import requests

    parts = urlparse(url)
    host = f"{parts.scheme}://{parts.netloc}"
    if host not in _robots_cache:
        parser = urllib.robotparser.RobotFileParser()
        try:
            wait_politely()
            resp = requests.get(host + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=20)
            # No robots.txt (404) means everything is allowed; 401/403 means stay out.
            if resp.status_code in (401, 403):
                parser.parse(["User-agent: *", "Disallow: /"])
            else:
                parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
        except requests.RequestException:
            parser.parse([])
        _robots_cache[host] = parser
    return _robots_cache[host].can_fetch(USER_AGENT, url)


def wait_politely():
    """Keep at least REQUEST_DELAY_SECONDS between requests."""
    gap = time.time() - _last_request[0]
    if gap < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - gap)
    _last_request[0] = time.time()


def fetch_once(url, filename, offline, log):
    """Download url into scripts/raw/filename once; afterwards reuse the saved copy.

    Returns the saved file's path, or None if it isn't available.
    """
    path = RAW_DIR / filename
    if path.exists():
        return path
    if offline:
        log.append(f"[skip] {filename} not in scripts/raw/ and --offline is set")
        return None
    if not allowed_by_robots(url):
        log.append(f"[skip] robots.txt disallows {url}")
        return None

    import requests

    wait_politely()
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    except requests.RequestException as err:
        log.append(f"[error] could not download {url}: {err}")
        return None
    if resp.status_code != 200:
        log.append(f"[error] {url} returned HTTP {resp.status_code}")
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(resp.content)
    return path


# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------

_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
             "llc", "ag", "se", "sa", "plc", "group", "holdings", "the"}


def normalize(name):
    """'Levi Strauss & Co.' -> 'levi strauss'. Used to compare company names.

    Text in brackets is dropped too: 'Calvin Klein (part of PVH)' -> 'calvin klein'.
    """
    name = re.sub(r"\([^)]*\)", " ", name.lower())
    words = re.sub(r"[^a-z0-9 ]", " ", name.replace("&", " ")).split()
    return " ".join(w for w in words if w not in _SUFFIXES)


def names_match(wanted, candidate):
    """True if candidate is the wanted company once 'Inc', 'Corp', etc. are ignored.

    Matching is exact on purpose: 'Puma' must not match 'Puma Chemicals GmbH'.
    If a company isn't found, the log says so; fix its name in SOURCES.
    """
    w, c = normalize(wanted), normalize(candidate)
    return bool(w) and c in (w, w + " com")  # 'Amazon.com, Inc.' -> 'amazon com'


# ---------------------------------------------------------------------------
# Source 1: SBTi companies spreadsheet
# ---------------------------------------------------------------------------

def load_sbti(offline, log):
    """Return a list of (company_name, status_text) rows from SBTi's spreadsheet."""
    path = fetch_once(SBTI_URL, "sbti_companies.xlsx", offline, log)
    if not path:
        return None
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))

    # Find the header row and the columns we need. SBTi has renamed columns
    # before, so match loosely and print what we found.
    for h, row in enumerate(rows[:15]):
        headers = [str(c or "").strip().lower() for c in row]
        name_col = next((i for i, x in enumerate(headers) if "company" in x and "name" in x), None)
        status_cols = [i for i, x in enumerate(headers) if "status" in x]
        near = [i for i in status_cols if "near" in headers[i]]
        status_col = (near or status_cols or [None])[0]
        if name_col is not None and status_col is not None:
            log.append(f"[sbti] using columns '{row[name_col]}' and '{row[status_col]}'")
            return [(str(r[name_col] or ""), str(r[status_col] or ""))
                    for r in rows[h + 1:] if r and r[name_col]]
    log.append("[error] SBTi file: couldn't find company-name and status columns; "
               "open scripts/raw/sbti_companies.xlsx and update load_sbti()")
    return None


def sbti_value(status):
    """Map SBTi's status text to true/false. Unknown text -> None."""
    s = status.lower()
    if "targets set" in s or "target set" in s or "validated" in s:
        return True
    if "committed" in s or "removed" in s or "expired" in s:
        return False
    return None


# ---------------------------------------------------------------------------
# Source 2: bluesign System Partner list (PDF)
# ---------------------------------------------------------------------------

def load_bluesign_text(offline, log):
    path = fetch_once(BLUESIGN_URL, "bluesign_partners.pdf", offline, log)
    if not path:
        return None
    from pypdf import PdfReader

    try:
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    except Exception as err:  # broken or non-PDF download
        log.append(f"[error] couldn't read bluesign PDF: {err}")
        return None


def bluesign_entry(text, entry_name):
    """Return the matching line from the partner list, or None."""
    pattern = re.compile(r"(?<![a-z])" + re.escape(entry_name.lower()) + r"(?![a-z])")
    for line in text.splitlines():
        if pattern.search(line.lower()):
            return line.strip()
    return None


# ---------------------------------------------------------------------------
# Source 3: WikiRate API (Fashion Transparency Index)
# ---------------------------------------------------------------------------

def wikirate_fti(brand, company, api, offline, log):
    """Return (score_0_to_100, year, value_as_shown, company_name, url) or None.

    WikiRate stores FTI on a 0-10 scale (6.04 = 60.4%), so we multiply by 10.
    Each brand's API answers are cached in scripts/raw/wikirate/<brand>.json.
    """
    cache = RAW_DIR / "wikirate" / (re.sub(r"[^a-z0-9]+", "_", brand.lower()) + ".json")
    if cache.exists():
        answers = json.loads(cache.read_text())
    elif offline or api is None:
        return None
    else:
        answers = []
        for year in FTI_YEARS:
            wait_politely()
            try:
                found = api.get_answers(metric_name=f"Fashion Transparency Index {year}",
                                        metric_designer=FTI_DESIGNER,
                                        company_name=company, year=year, limit=20)
            except Exception as err:
                log.append(f"[error] WikiRate request failed for {brand} {year}: {err}")
                found = []
            answers += [{"company": str(a.company), "value": a.value, "year": a.year, "url": a.url,
                         "edition": year} for a in found]
            if any(names_match(company, a["company"]) and a["value"] not in (None, "", "Unknown")
                   for a in answers):
                break  # newest edition with data found
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(answers, indent=2))

    for a in sorted(answers, key=lambda a: -int(a.get("edition") or a.get("year") or 0)):
        if not names_match(company, a["company"]):
            continue
        text = str(a["value"]).strip()
        try:
            raw = float(text.rstrip("%").strip())
        except ValueError:
            continue
        # WikiRate's FTI answers are 0-10 (e.g. 6.3). A "%" value is already 0-100.
        score = round(raw) if text.endswith("%") or raw > 10 else round(raw * 10)
        if not 0 <= score <= 100:
            log.append(f"[keep] {brand}: odd WikiRate FTI value {text!r}, ignored")
            continue
        shown = text if text.endswith("%") else f"{text} / 10"
        return score, a.get("edition") or a.get("year"), shown, a["company"], a.get("url")
    return None


# ---------------------------------------------------------------------------
# Source 4: B Lab directory pages (only for brands with a known page)
# ---------------------------------------------------------------------------

def blab_certified(slug, offline, log):
    path = fetch_once(BLAB_PAGE.format(slug=slug), f"blab_{slug}.html", offline, log)
    if not path:
        return None
    return "certified b corporation" in path.read_text(errors="ignore").lower()


# ---------------------------------------------------------------------------
# Merge scraped facts into the hand-researched data
# ---------------------------------------------------------------------------

def add_source(entry, url):
    if url and url not in entry["sources"]:
        entry["sources"].append(url)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--offline", action="store_true", help="only use files already in scripts/raw/")
    args = parser.parse_args()

    if not BASE_FILE.exists():
        sys.exit(f"Can't find {BASE_FILE}. Run this from the repo after brands.json is in backend/data/.")
    brands = json.loads(BASE_FILE.read_text(encoding="utf-8"))
    log, changes = [], []
    today = datetime.date.today().isoformat()

    api = None
    key = os.environ.get("WIKIRATE_API_KEY")
    if key and not args.offline:
        from wikirate4py import API
        api = API(key)
    elif not args.offline:
        log.append("[skip] WIKIRATE_API_KEY not set, so FTI scores were not re-checked")

    sbti_rows = load_sbti(args.offline, log)
    bluesign_text = load_bluesign_text(args.offline, log)

    for entry in brands:
        name = entry["name"]
        src = SOURCES.get(name)
        if src is None:
            log.append(f"[skip] {name}: no entry in SOURCES, left unchanged")
            continue
        ev, snip = entry["evidence"], entry["evidence_snippets"]
        touched = False

        def record(field, old, new, why):
            nonlocal touched
            touched = True
            if old != new:
                changes.append(f"{name}: {field} {json.dumps(old)} -> {json.dumps(new)}  ({why})")

        # FTI
        if "wikirate" in src:
            got = wikirate_fti(name, src["wikirate"], api, args.offline, log)
            if got:
                score, year, raw, company, url = got
                record("fti_score", ev["fti_score"], score, f"WikiRate FTI {year}: {raw} for {company}")
                ev["fti_score"] = score
                snip["fti_score"] = f"Fashion Transparency Index {year} on WikiRate ({company}): {raw}"
                add_source(entry, url)
            elif api is not None:
                log.append(f"[keep] {name}: no FTI answer found on WikiRate")

        # SBTi
        if sbti_rows is not None and "sbti" in src:
            hits = [(c, s) for c, s in sbti_rows if names_match(src["sbti"], c)]
            values = {sbti_value(s) for _, s in hits} - {None}
            if len(values) == 1:
                company, status = next(h for h in hits if sbti_value(h[1]) in values)
                new = values.pop()
                record("sbti_target", ev["sbti_target"], new, f"SBTi file: {company} = {status}")
                ev["sbti_target"] = new
                snip["sbti_target"] = f"SBTi companies list: {company} - {status}"
                add_source(entry, SBTI_URL)
            elif len(values) > 1:
                log.append(f"[keep] {name}: SBTi rows disagree {hits}; check by hand")
            else:
                log.append(f"[keep] {name}: '{src['sbti']}' not found in SBTi file")

        # bluesign
        if bluesign_text is not None and "bluesign" in src:
            line = bluesign_entry(bluesign_text, src["bluesign"])
            had = "bluesign" in ev["certifications"]
            if line and not had:
                ev["certifications"].append("bluesign")
            if not line and had:
                ev["certifications"].remove("bluesign")
                snip.pop("bluesign", None)
            if line:
                snip["bluesign"] = line
            record("bluesign", had, bool(line), "bluesign System Partner list")
            add_source(entry, BLUESIGN_URL)

        # B Corp (only brands with a known directory page)
        if "blab" in src:
            certified = blab_certified(src["blab"], args.offline, log)
            if certified is not None:
                record("b_corp", ev["b_corp"], certified, f"B Lab page {src['blab']}")
                ev["b_corp"] = certified
                snip["b_corp"] = ("Certified B Corporation" if certified else
                                  f"B Lab page no longer shows 'Certified B Corporation' ({today})")
                add_source(entry, BLAB_PAGE.format(slug=src["blab"]))

        if touched:
            entry["last_checked"] = today

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "brands_scraped.json"
    out_json.write_text(json.dumps(brands, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = ["CHANGES vs backend/data/brands.json:"] + (changes or ["(none)"]) + ["", "LOG:"] + log
    (OUT_DIR / "changes.txt").write_text("\n".join(report) + "\n", encoding="utf-8")

    print("\n".join(report))
    print(f"\nWrote {out_json.relative_to(REPO_ROOT)}. Review it, then copy it over "
          f"backend/data/brands.json if it looks right.")


if __name__ == "__main__":
    main()
