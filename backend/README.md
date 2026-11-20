# backend

FastAPI service that scores the items in an Amazon cart.

**Status:** `/score` returns real brand + material scores (`"mock": false`). How scores are calculated: [`docs/scoring-model.md`](../docs/scoring-model.md). The numbers are in `app/rubric.py`.

### LLM fallback (optional)

Unknown brands and fabric text the parser can't read go to the LLM helpers in `ml/llm_helpers.py`. To turn that on, put your key in `ml/.env`:

```
OPENROUTER_API_KEY=your-key-here
```

Without a key, the backend still runs; those items just get the "unknown" score. Set `THRED_USE_LLM=0` to switch it off. Tests never call the real LLM.

## Run it locally

From the `backend/` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate        # run this every time you open a new terminal
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs to see the API and try requests in the browser.

If you use conda and your prompt shows `(base)`, run `conda deactivate` first so the venv's Python is the one being used.

Run the tests:

```bash
pytest
```

## API contract

### `POST /score`

The extension sends every clothing item in the cart. Only `item_id` and `title` are required; send whatever else you can scrape.

```json
{
  "items": [
    {
      "item_id": "B0HOODIE01",
      "title": "Oversized Hoodie, Sage Green",
      "brand": "Example Brand",
      "price": 49.99,
      "image_url": "https://m.media-amazon.com/images/...",
      "product_url": "https://www.amazon.com/dp/B0HOODIE01",
      "material_text": "60% Cotton, 40% Polyester",
      "category": "Hoodies",
      "certifications": ["OEKO-TEX Standard 100"]
    }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `item_id` | yes | The ASIN is ideal |
| `title` | yes | |
| `brand` | no | |
| `price` | no | Number, no `$` |
| `image_url` | no | |
| `product_url` | no | |
| `material_text` | no | Raw text, e.g. from "Fabric type" on the product page. The cart page usually doesn't show materials. |
| `category` | no | Most specific breadcrumb level, e.g. `"Hoodies"` |
| `certifications` | no | From the product's Climate Pledge Friendly badge. List of strings, `[]` if none |

Limit: 1–50 items per request. Where to find each field on Amazon: see [`docs/data-formats.md`](../docs/data-formats.md).

### Response

```json
{
  "items": [
    {
      "item_id": "B0HOODIE01",
      "total": 79,
      "verdict": "good_choice",
      "verdict_label": "Good choice",
      "impact": "Uses roughly 40% less water than a typical item like this",
      "brand":    { "points": 28, "max": 34, "summary": "Some verified sustainability practices" },
      "material": { "points": 25, "max": 33, "summary": "Mostly lower-impact fibers" }
    }
  ],
  "cart": {
    "item_count": 1,
    "average_total": 79,
    "verdict": "good_choice",
    "verdict_label": "Good choice",
    "headline": "Nice! Every item in your cart is a solid choice"
  },
  "mock": false
}
```

- `items` come back in the same order they were sent.
- Each item also has `alternatives`: up to 3 better-scoring secondhand listings, same fields as in `/alternatives` below. It's `[]` when there are none or no listings are loaded. If anything goes wrong finding alternatives, `/score` still returns the scores.
- `verdict` is one of `good_choice`, `okay`, `consider_alternatives`. Use it for colors; show `verdict_label` as text.
- `impact` and each `summary` are the plain-language phrases for the panel. The `points` are for the expanded view.
- **History is not included.** The wardrobe lives in the extension's local storage, so the extension scores that part itself. `total` covers brand + material only.
- `mock` is `false` now that scoring is real.

### `POST /alternatives`

Up to 3 lower-impact alternatives for one cart item: same garment type, a better score that is at least "Okay", at most 1.5x the price, ranked by visual similarity (CLIP), score, and price.

```json
{ "item": { "item_id": "B0H34KR2DX", "title": "Banana Republic Women's Stretch Pant", "price": 120.0, "image_url": "https://...", "brand": "BANANA REPUBLIC", "material_text": "92% Viscose rayon, 8% Elastane" }, "limit": 3 }
```

`item` is the same shape as one item in `/score`. `limit` is optional (1–10, default 3).

```json
{
  "item_id": "B0H34KR2DX",
  "item_total": 33,
  "garment_type": "pants",
  "status": "ok",
  "message": "",
  "alternatives": [
    {
      "alt_id": "vinted-4829173",
      "title": "Patagonia Organic Cotton Wide Leg Pants",
      "brand": "Patagonia",
      "price": 32.0,
      "currency": "USD",
      "image_url": "https://...",
      "listing_url": "https://...",
      "source": "Vinted",
      "condition": "Very good",
      "secondhand": true,
      "garment_type": "pants",
      "total": 82,
      "verdict": "good_choice",
      "verdict_label": "Good choice",
      "similarity": 0.84,
      "ranking_score": 0.88
    }
  ]
}
```

| `status` | Meaning | What the panel can do |
|---|---|---|
| `ok` | Found alternatives | Show them |
| `no_catalog` | No listings loaded yet | Hide the section, or show `message` |
| `unknown_type` | Couldn't tell what garment it is | Show `message` |
| `no_match` | Nothing better in that type and price range | Show `message` |

`similarity` is `null` when CLIP isn't installed on the server.

### Visual similarity (optional)

CLIP needs torch + transformers (several GB), so it's not in `requirements.txt`. To turn it on:

```bash
pip install -r ../ml/requirements.txt
```

The first `/alternatives` request then loads the model (and downloads it the first time). Without it, alternatives are ranked on score and price only. Set `THRED_USE_CLIP=0` to switch it off.

### Calling it from the extension

Call the API from `background.js`, not `content.js`, and add the backend URL to `host_permissions` in `manifest.json` (e.g. `"http://localhost:8000/*"` for now). Content scripts run under amazon.com's origin, so their requests get blocked by CORS.
