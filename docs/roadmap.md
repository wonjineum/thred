# Roadmap

Revised order: frontend-first, so there's something demoable early.

## Phase 1 — Extension skeleton
- Manifest V3 setup
- Popup UI (React + Tailwind)
- Score badge + "why this score" breakdown, built against hardcoded/fake data

## Phase 2 — Content script scraping
- Scrape brand domain, product image, material listing, price from real product pages
- Log scraped data to console — nothing to send it to yet

## Phase 3 — Backend + ML
- Curated `brands` table (Good/Average/Bad)
- `materials` rubric table with point values
- Train CNN on Fashion MNIST (type classification)
- Set up CLIP, confirm embeddings work on real product photos
- Lock scoring weights (Brand/Material/User History)

## Phase 4 — Wire frontend to backend
- Replace fake data in the extension with real API calls
- Handle edge cases: null fields, missing material data, slow responses

## Phase 5 — Alternatives & extras
- Curated alternative-brand suggestions
- Manual "add to wardrobe" button
- Score history/trends view (local only)

## Phase 6 — Polish & edge cases
- Graceful fallback for missing/vague material listings
- Cold-start wardrobe handling
- Slow/failed backend calls shouldn't hang the page

## Phase 7 — Testing & demo prep
- Test scraping across real retailer sites (expect breakage — every site's HTML differs)
- Prepare demo flow
- Finalize docs for submission
