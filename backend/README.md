# backend

FastAPI service that scores the items in an Amazon cart.

**Status:** `/score` returns placeholder (mock) scores in the final response shape, so the extension can be wired up now. Real brand + material scoring comes next.

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
  "mock": true
}
```

- `items` come back in the same order they were sent.
- `verdict` is one of `good_choice`, `okay`, `consider_alternatives`. Use it for colors; show `verdict_label` as text.
- `impact` and each `summary` are the plain-language phrases for the panel. The `points` are for the expanded view.
- **History is not included.** The wardrobe lives in the extension's local storage, so the extension scores that part itself. `total` covers brand + material only.
- `mock: true` means the scores are placeholders.

### Calling it from the extension

Call the API from `background.js`, not `content.js`, and add the backend URL to `host_permissions` in `manifest.json` (e.g. `"http://localhost:8000/*"` for now). Content scripts run under amazon.com's origin, so their requests get blocked by CORS.
