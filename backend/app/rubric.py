"""Every number the scoring uses, in one place.

These are the team's judgment calls, not facts. Change them here, and the tests
in tests/test_scoring.py show what moves. Explained in docs/scoring-model.md.
"""

BRAND_MAX = 34
MATERIAL_MAX = 33

# ---------- Brand: brands in brands.json, scored from their evidence ----------

# Every brand we have documented starts here; evidence adds to it.
BRAND_BASE = 8
# Fashion Transparency Index (0-100) is scaled into this many points.
BRAND_FTI_MAX = 10
# Used when the brand isn't in the FTI (often small brands). Neutral, not a penalty.
BRAND_FTI_MISSING = 3
BRAND_B_CORP = 8
BRAND_SBTI = 5
# First certification is worth more than each additional one.
BRAND_FIRST_CERT = 5
BRAND_EXTRA_CERT = 3
BRAND_CERT_MAX = 8

# ---------- Brand: not in brands.json ----------

# Points for each label the LLM can return (ml/llm_helpers.classify_unknown_brand).
BRAND_LLM_POINTS = {"Good": 26, "Average": 17, "Bad": 6}
# No match and no LLM answer. Kept close to the weakest documented brands, so
# being unknown never beats being documented-but-weak.
BRAND_UNKNOWN_POINTS = 10

# Thresholds for the brand phrase shown in the panel.
BRAND_STRONG_AT = 22
BRAND_MIXED_AT = 12

# ---------- Material ----------

# Points for a garment made entirely of that fiber (out of MATERIAL_MAX).
# Blends get the percentage-weighted average. Keys are catalog material names.
MATERIAL_POINTS = {
    "recycled cotton": 30,
    "hemp": 30,
    "organic cotton": 28,
    "linen": 28,
    "recycled wool": 28,
    "lyocell": 26,
    "recycled polyester": 20,
    "recycled nylon": 20,
    "modal": 20,
    "wool": 18,
    "silk": 16,
    "cotton": 15,
    "viscose": 12,
    "polyester": 6,
    "nylon": 6,
    "spandex": 6,
    "acrylic": 3,
}
# No usable material information.
MATERIAL_UNKNOWN_POINTS = 12
# Score the known part of a blend only if it covers at least this share.
MATERIAL_MIN_KNOWN_SHARE = 50

# ---------- Alternatives ----------

# Added to a secondhand listing's total (out of 100): buying used avoids making
# a new garment, which brand + material alone don't capture.
SECONDHAND_BONUS = 15

# Only suggest listings at least "Okay" (see OKAY_AT below).
ALTERNATIVE_MIN_TOTAL = 40

# ---------- Verdict (total out of 100) ----------

GOOD_CHOICE_AT = 65
OKAY_AT = 40
