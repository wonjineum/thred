# Sustainability score

Total score: 1–100, made of three components.

| Component | Points | What it covers |
|---|---|---|
| Brand Score | 0–34 | Domain lookup: Good / Average / Unknown / Bad brand tier |
| Material Score | 0–33 | Composition rubric (organic cotton vs. polyester, etc.) |
| User History Score | 0–33 | Duplicate purchase check (30-day window) + wardrobe similarity (CLIP embeddings) |

Weighting is currently even (34/33/33) as a starting default — open question whether Material should be weighted higher, since research interviews suggested sustainability should be about "longevity and material."

## Brand tiers
- Good Brand: full points
- Average / Unknown Brand: half points (unknown brands get classified via an LLM call the first time they're seen, then cached)
- Bad / Fast-Fashion Brand: 0 points

## User History scoring
- No identical repurchase from the same store in 30 days: full points
- Low wardrobe overlap (color/type/pattern via CLIP similarity): full points
- Partial overlap: partial deduction
- Near-duplicate of something already owned: heavy deduction

See `docs/roadmap.md` for build order and `docs/problem-statement.md` for the research this is based on.
