# Data formats

What the backend needs from each scraper. If your output matches these formats, it plugs straight into scoring with no extra work.

- **Part A: Amazon scraper.** Product data for each item in the cart. Sent to the backend on every score request.
- **Part B: Sustainability scraper.** Facts about brands and materials. Saved as JSON files that the backend loads once.

General rules for both:

- **Send raw text, not cleaned or interpreted text.** If Amazon says `"60% Cotton, 40% Polyester"`, send exactly that. The backend does the parsing, so the logic lives in one place.
- **Use `null` when you don't know something.** Don't guess, and don't use an empty string.
- **`null` and `false` mean different things.** `null` means nobody checked. `false` means someone checked and the answer is no.

---

## Part A: Amazon scraper

### Where it goes

The extension sends this to `POST /score` (see [`backend/README.md`](../backend/README.md)). Call it from `background.js`, not `content.js`, or Chrome will block the request.

### Format

```json
{
  "items": [
    {
      "item_id": "B0C1234567",
      "title": "Amazon Essentials Men's Fleece Hoodie, Sage Green, Medium",
      "brand": "Amazon Essentials",
      "price": 24.90,
      "image_url": "https://m.media-amazon.com/images/I/....jpg",
      "product_url": "https://www.amazon.com/dp/B0C1234567",
      "material_text": "60% Cotton, 40% Polyester",
      "category": "Hoodies",
      "certifications": ["OEKO-TEX Standard 100"]
    }
  ]
}
```

| Field | Required | Where to find it on Amazon | Notes |
|---|---|---|---|
| `item_id` | **yes** | ASIN, in the product URL after `/dp/` | Unique per product |
| `title` | **yes** | Product title | Full title as shown |
| `brand` | no | Byline under the title: "Visit the ___ Store" or "Brand: ___" | Just the name. Remove "Visit the" and "Store" |
| `price` | no | Price on the cart or product page | A number: `24.90`, not `"$24.90"` |
| `image_url` | no | Main product image | Full URL |
| `product_url` | no | Product page link | `https://www.amazon.com/dp/<ASIN>` is enough |
| `material_text` | no | Product page → "Product details" → **"Fabric type"** (sometimes "Material composition") | **Exact raw text.** Usually only on the product page, not the cart page |
| `category` | no | Breadcrumb at the top of the product page | The most specific level, e.g. `"Hoodies"` |
| `certifications` | no | **"Climate Pledge Friendly"** badge on the product page → listed certifications | List of names exactly as shown, e.g. `["GOTS", "Fair Trade Certified"]`. Use `[]` if there's no badge |

Limit: 1–50 items per request. Only send clothing items.

### What I need from you now

**10–20 real examples** saved as `backend/tests/fixtures/amazon_samples.json`, in the format above. Pick a mix of:
- simple materials (`100% Cotton`)
- blends (`95% Cotton, 5% Spandex`)
- multi-part (`Shell: 100% Nylon; Lining: 100% Polyester`)
- items with no fabric info
- items with a Climate Pledge Friendly badge

I'll use these to test the material parser against what Amazon actually shows.

---

## Part B: Sustainability scraper

Two files, committed to `backend/data/`. **Collect facts, not scores.** The backend turns facts into points, so the team can change the scoring without re-scraping.

### `backend/data/brands.json`

```json
[
  {
    "name": "Patagonia",
    "aliases": ["patagonia"],
    "evidence": {
      "fti_score": null,
      "b_corp": true,
      "sbti_target": null,
      "certifications": ["Fair Trade Certified", "bluesign"]
    },
    "evidence_snippets": {
      "b_corp": "Patagonia is a certified B Corporation…",
      "Fair Trade Certified": "…sewn in Fair Trade Certified factories…"
    },
    "sources": [
      "https://www.bcorporation.net/...",
      "https://www.patagonia.com/..."
    ],
    "last_checked": "2026-10-23"
  }
]
```

| Field | Type | Notes |
|---|---|---|
| `name` | string | Brand name **as it appears on Amazon** |
| `aliases` | list of strings | Every lowercase spelling to match: `["levi's", "levis", "levi strauss"]`. Include the name itself |
| `evidence.fti_score` | number 0–100 or `null` | Fashion Transparency Index score. Get it from the WikiRate API rather than scraping. Use the latest edition the brand appears in |
| `evidence.b_corp` | `true` / `false` / `null` | From the B Corp directory |
| `evidence.sbti_target` | `true` / `false` / `null` | Validated target on the Science Based Targets initiative list |
| `evidence.certifications` | list of strings | Only certifications the brand **actually holds**, not ones it plans to get. Use the names in the list below |
| `evidence_snippets` | object | The sentence each fact came from, so a person can check it. Keyed by field name or certification |
| `sources` | list of URLs | Every page a fact came from |
| `last_checked` | `"YYYY-MM-DD"` | When it was scraped |

**Certification names to use** (spell them exactly like this, so the backend can match them):
`"Fair Trade Certified"`, `"bluesign"`, `"GOTS"`, `"OEKO-TEX Standard 100"`, `"Global Recycled Standard"`, `"Responsible Wool Standard"`, `"FSC"`. If you find one that isn't listed, add it and tell Wonjin.

**Which brands:** start with brands that are common on Amazon: Amazon Essentials, Hanes, Gildan, Fruit of the Loom, Champion, Levi's, Carhartt, Under Armour, Columbia, Calvin Klein, Patagonia. Then add a few fast-fashion brands. Aim for about 25.

### `backend/data/materials.json`

```json
[
  {
    "name": "spandex",
    "aliases": ["spandex", "elastane", "lycra"],
    "category": "synthetic",
    "recycled": false,
    "organic": false,
    "water_l_per_kg": null,
    "co2_kg_per_kg": null,
    "sources": {
      "water_l_per_kg": "",
      "co2_kg_per_kg": ""
    },
    "notes": ""
  }
]
```

| Field | Type | Notes |
|---|---|---|
| `name` | string | Lowercase |
| `aliases` | list of strings | All the ways Amazon writes it, lowercase: `"elastane"`, `"lycra"`, `"rayon"` / `"viscose"`, `"tencel"` / `"lyocell"` |
| `category` | `"natural"` / `"synthetic"` / `"semi-synthetic"` | |
| `recycled`, `organic` | `true` / `false` | `"recycled polyester"` is its own entry, with `recycled: true` |
| `water_l_per_kg` | number or `null` | Liters of water per kg of fiber |
| `co2_kg_per_kg` | number or `null` | kg of CO₂-equivalent per kg of fiber |
| `sources` | object | **A link for every number.** No source means leave it `null` |
| `notes` | string | Anything odd, e.g. "studies disagree; used the middle estimate" |

**Materials to cover:** cotton, organic cotton, recycled cotton, polyester, recycled polyester, nylon, recycled nylon, spandex, acrylic, wool, linen, hemp, viscose/rayon, lyocell, modal, silk.

### Scraping rules

- Check each site's robots.txt and terms of use before scraping it.
- About one request per second.
- Save the raw HTML once and parse from the saved copy.
- **Don't scrape Good On You.** Its ratings are a paid product.
- Scraper code goes in `scripts/`. Only the final, reviewed JSON goes in `backend/data/`.

---

## Questions

Ask Wonjin (backend). If a field doesn't fit what you're finding, say so before working around it. It's easier to change this doc than to fix the data later.
