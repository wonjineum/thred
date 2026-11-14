# Sustainability score

Total score: 0–100. The backend scores **brand** and **material**; the extension scores **user history**, because the wardrobe lives in the browser.

| Component | Points | Scored by | What it covers |
|---|---|---|---|
| Brand | 0–34 | backend | Public evidence about the brand |
| Material | 0–33 | backend | What the garment is made of |
| User History | 0–33 | extension | Duplicate purchases + wardrobe similarity |

The backend's `total` is brand + material scaled to 100. Verdicts: **65+ Good choice**, **40–64 Okay**, **under 40 Consider alternatives**.

Every number below lives in [`backend/app/rubric.py`](../backend/app/rubric.py). These are team judgment calls; change them there and run `pytest` to see what moves.

## Brand (0–34)

### Brands in `backend/data/brands.json`

Points come from the evidence, not a hand-typed score:

| Evidence | Points |
|---|---|
| Base (we have documented the brand) | 8 |
| Fashion Transparency Index score (0–100) | up to 10, scaled. Not in the index: 3 (neutral) |
| B Corp certified | +8 |
| Validated Science Based Targets climate target | +5 |
| Certifications (Fair Trade, bluesign, GOTS…) | +5 for the first, +3 each after, up to 8 |

Capped at 34. Phrase shown in the panel: **22+** "Strong sustainability record", **12–21** "Some sustainability commitments", **under 12** "Little public sustainability information", followed by the main piece of evidence.

Current spread across the 25 brands: The North Face 25, adidas 24 … Pact / Allbirds / Levi's 19 … Amazon Essentials 11 … Reebok 8.

### Brands not in the list

1. Ask the LLM (`ml/llm_helpers.classify_unknown_brand`): **Good 26 / Average 17 / Bad 6**, shown as "AI estimate: …".
2. No answer, or LLM unavailable: **10**, "No sustainability information found".

Unknown is set at 10 on purpose: close to the weakest documented brands, so a brand never scores higher by being unknown than by being documented-but-weak.

## Material (0–33)

1. Parse the fabric text (`material_parser.py`): `"60% Cotton, 40% Polyester"` → `{"cotton": 60, "polyester": 40}`.
2. If it can't, ask the LLM (`ml/llm_helpers.extract_material_composition`), shown as "AI estimate: …".
3. Match each fiber to `backend/data/materials.json` using aliases (`"elastane"` → spandex).
4. Score = the percentage-weighted average of each fiber's points. If less than half the composition is recognized, it counts as unknown (**12**).

| Fiber | Points | | Fiber | Points |
|---|---|---|---|---|
| recycled cotton, hemp | 30 | | wool | 18 |
| organic cotton, linen, recycled wool | 28 | | silk | 16 |
| lyocell | 26 | | cotton | 15 |
| recycled polyester, recycled nylon, modal | 20 | | viscose | 12 |
| | | | polyester, nylon, spandex | 6 |
| | | | acrylic | 3 |

**Impact line:** a plain-language sentence about the main fiber (e.g. "Made mostly from recycled fibers instead of new ones"). These are qualitative for now. Once water and CO₂ figures in `materials.json` are sourced, they can become numbers ("uses about X% less water").

## User History (0–33, extension)

- No identical repurchase from the same store in 30 days: full points
- Low wardrobe overlap (color/type/pattern via CLIP similarity): full points
- Partial overlap: partial deduction
- Near-duplicate of something already owned: heavy deduction

## Open questions

- Should Material be weighted higher than Brand? Research interviews suggested sustainability is about "longevity and material."
- Product-level certifications from Amazon's Climate Pledge Friendly badge (`certifications` in the request) aren't scored yet.
