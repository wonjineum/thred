"""Scoring logic.

Step 1 (now): `mock_item_score` returns placeholder scores so the extension can
be wired up against the real API shape.
Step 3 (next): replace it with real brand + material scoring from the data tables.
"""

from .schemas import (
    VERDICT_LABELS,
    CartItem,
    CartSummary,
    Component,
    ItemScore,
    Verdict,
)

BRAND_MAX = 34
MATERIAL_MAX = 33


def verdict_for(total: int) -> Verdict:
    if total >= 65:
        return Verdict.good_choice
    if total >= 40:
        return Verdict.okay
    return Verdict.consider_alternatives


def to_total(brand_points: int, material_points: int) -> int:
    """Scale brand + material (out of 67) to a 0-100 total.

    History is scored in the extension, so the backend's total covers only
    the two components it knows about.
    """
    return round((brand_points + material_points) / (BRAND_MAX + MATERIAL_MAX) * 100)


# Two canned profiles so the extension can test both the good and the low styling.
_MOCK_PROFILES = [
    {
        "brand": (28, "Some verified sustainability practices"),
        "material": (25, "Mostly lower-impact fibers"),
        "impact": "Uses roughly 40% less water than a typical item like this",
    },
    {
        "brand": (8, "No sustainability information found"),
        "material": (11, "Mostly virgin polyester"),
        "impact": "A lower-impact alternative is likely available",
    },
]


def mock_item_score(item: CartItem, position: int) -> ItemScore:
    # Alternate profiles by cart position so any cart with 2+ items shows both styles.
    profile = _MOCK_PROFILES[position % len(_MOCK_PROFILES)]
    brand_pts, brand_summary = profile["brand"]
    mat_pts, mat_summary = profile["material"]
    total = to_total(brand_pts, mat_pts)
    verdict = verdict_for(total)
    return ItemScore(
        item_id=item.item_id,
        total=total,
        verdict=verdict,
        verdict_label=VERDICT_LABELS[verdict],
        impact=profile["impact"],
        brand=Component(points=brand_pts, max=BRAND_MAX, summary=brand_summary),
        material=Component(points=mat_pts, max=MATERIAL_MAX, summary=mat_summary),
    )


def summarize_cart(scores: list[ItemScore]) -> CartSummary:
    average = round(sum(s.total for s in scores) / len(scores))
    verdict = verdict_for(average)
    low = sum(1 for s in scores if s.verdict == Verdict.consider_alternatives)
    if low:
        headline = f"{low} of {len(scores)} items have a lower-impact alternative"
    else:
        headline = "Nice! Every item in your cart is a solid choice"
    return CartSummary(
        item_count=len(scores),
        average_total=average,
        verdict=verdict,
        verdict_label=VERDICT_LABELS[verdict],
        headline=headline,
    )
