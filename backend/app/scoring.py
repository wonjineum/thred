"""Scoring logic: brand + material points from the catalog, with LLM fallbacks.

Flow for each item:
    brand    -> brands.json evidence -> points
                not in brands.json   -> LLM label (Good/Average/Bad) -> points
                still nothing        -> "unknown" default
    material -> material_parser      -> catalog match -> weighted points
                parser can't read it -> LLM extraction -> same
                still nothing        -> "unknown" default

All the numbers live in rubric.py.
"""

from dataclasses import dataclass

from . import llm_fallback, rubric
from .catalog import Brand, Catalog, Material
from .material_parser import parse_materials
from .schemas import (
    VERDICT_LABELS,
    CartItem,
    CartSummary,
    Component,
    ItemScore,
    Verdict,
)

BRAND_MAX = rubric.BRAND_MAX
MATERIAL_MAX = rubric.MATERIAL_MAX


def verdict_for(total: int) -> Verdict:
    if total >= rubric.GOOD_CHOICE_AT:
        return Verdict.good_choice
    if total >= rubric.OKAY_AT:
        return Verdict.okay
    return Verdict.consider_alternatives


def to_total(brand_points: int, material_points: int) -> int:
    """Scale brand + material (out of 67) to a 0-100 total.

    History is scored in the extension, so the backend's total covers only
    the two components it knows about.
    """
    return round((brand_points + material_points) / (BRAND_MAX + MATERIAL_MAX) * 100)


def score_item(item: CartItem, position: int, catalog: Catalog) -> ItemScore:
    """Score one cart item. `position` is unused; kept so callers don't change."""
    brand = brand_component(item.brand, catalog)
    material = material_component(item, catalog)
    total = to_total(brand.points, material.points)
    verdict = verdict_for(total)
    return ItemScore(
        item_id=item.item_id,
        total=total,
        verdict=verdict,
        verdict_label=VERDICT_LABELS[verdict],
        impact=material.impact,
        brand=Component(points=brand.points, max=BRAND_MAX, summary=brand.summary),
        material=Component(points=material.points, max=MATERIAL_MAX, summary=material.summary),
    )


# ---------------- Brand ----------------

@dataclass(frozen=True)
class BrandResult:
    points: int
    summary: str
    source: str  # "catalog", "llm", or "unknown"


def brand_component(brand_name: str | None, catalog: Catalog) -> BrandResult:
    if brand_name and brand_name.strip():
        match = catalog.match_brand(brand_name)
        if match is not None:
            points = brand_points_from_evidence(match)
            return BrandResult(points, _brand_summary(match, points), "catalog")

        label = llm_fallback.classify_brand(brand_name.strip())
        if label is not None:
            phrase = {"Good": "strong", "Average": "mixed", "Bad": "poor"}[label]
            return BrandResult(
                rubric.BRAND_LLM_POINTS[label],
                f"AI estimate: {phrase} sustainability record",
                "llm",
            )

    return BrandResult(rubric.BRAND_UNKNOWN_POINTS, "No sustainability information found", "unknown")


def brand_points_from_evidence(brand: Brand) -> int:
    points = rubric.BRAND_BASE
    if brand.fti_score is None:
        points += rubric.BRAND_FTI_MISSING
    else:
        points += brand.fti_score / 100 * rubric.BRAND_FTI_MAX
    if brand.b_corp:
        points += rubric.BRAND_B_CORP
    if brand.sbti_target:
        points += rubric.BRAND_SBTI
    if brand.certifications:
        cert_points = rubric.BRAND_FIRST_CERT + rubric.BRAND_EXTRA_CERT * (len(brand.certifications) - 1)
        points += min(cert_points, rubric.BRAND_CERT_MAX)
    return min(round(points), BRAND_MAX)


def _brand_summary(brand: Brand, points: int) -> str:
    if points >= rubric.BRAND_STRONG_AT:
        tier = "Strong sustainability record"
    elif points >= rubric.BRAND_MIXED_AT:
        tier = "Some sustainability commitments"
    else:
        tier = "Little public sustainability information"

    if brand.certifications:
        reason = ", ".join(brand.certifications[:2])
    elif brand.b_corp:
        reason = "B Corp certified"
    elif brand.sbti_target:
        reason = "validated climate target"
    elif brand.fti_score is not None:
        reason = f"transparency score {round(brand.fti_score)}/100"
    else:
        reason = ""
    return f"{tier}: {reason}" if reason else tier


# ---------------- Material ----------------

@dataclass(frozen=True)
class MaterialResult:
    points: int
    summary: str
    impact: str
    source: str  # "parser", "llm", or "unknown"


_UNKNOWN_MATERIAL = MaterialResult(
    rubric.MATERIAL_UNKNOWN_POINTS,
    "No material information found",
    "We couldn't find what this item is made of",
    "unknown",
)


def material_component(item: CartItem, catalog: Catalog) -> MaterialResult:
    composition = parse_materials(item.material_text)
    source = "parser"
    if not composition:
        composition = llm_fallback.extract_materials(item.material_text, item.title)
        source = "llm"
    if not composition:
        return _UNKNOWN_MATERIAL

    # Combine names that match the same material ("rayon" + "viscose").
    known: dict[str, tuple[Material, float]] = {}
    for name, pct in composition.items():
        material = catalog.match_material(name)
        if material is not None and material.name in rubric.MATERIAL_POINTS:
            previous = known.get(material.name, (material, 0))[1]
            known[material.name] = (material, previous + pct)

    known_share = sum(pct for _, pct in known.values())
    if known_share < rubric.MATERIAL_MIN_KNOWN_SHARE:
        return _UNKNOWN_MATERIAL

    weighted = sum(rubric.MATERIAL_POINTS[m.name] * pct for m, pct in known.values()) / known_share
    points = min(round(weighted), MATERIAL_MAX)

    ranked = sorted(known.values(), key=lambda mp: mp[1], reverse=True)
    summary = _material_summary(ranked, known_share)
    if source == "llm":
        summary = f"AI estimate: {summary[0].lower()}{summary[1:]}"
    return MaterialResult(points, summary, _impact_phrase(ranked, known_share), source)


def _material_summary(ranked: list[tuple[Material, float]], known_share: float) -> str:
    top, top_pct = ranked[0]
    if len(ranked) == 1 and top_pct >= 99.5:
        return f"100% {top.name}"
    if len(ranked) == 1 or top_pct / known_share >= 0.7:
        return f"Mostly {top.name}"
    return f"Blend of {top.name} and {ranked[1][0].name}"


# Plain-language impact lines, by the main fiber. Qualitative for now; switch
# to numbers ("uses about X% less water") once water/CO2 figures are sourced.
_IMPACT_BY_NAME = {
    "cotton": "Conventional cotton takes a lot of water to grow",
    "linen": "Linen needs little water or pesticide to grow",
    "hemp": "Hemp needs little water or pesticide to grow",
    "lyocell": "Lyocell is made in a closed-loop process that reuses its solvent",
    "viscose": "Viscose is made from wood pulp using heavy chemical processing",
}


def _impact_phrase(ranked: list[tuple[Material, float]], known_share: float) -> str:
    top, top_pct = ranked[0]
    if top_pct / known_share < 0.5:
        return "Mixed fibers, which are harder to recycle"
    if top.recycled:
        return "Made mostly from recycled fibers instead of new ones"
    if top.organic:
        return "Made mostly from organically grown fibers"
    if top.name in _IMPACT_BY_NAME:
        return _IMPACT_BY_NAME[top.name]
    if top.category == "synthetic":
        return "Mostly new synthetic fibers, which are made from fossil fuels"
    if top.category == "semi-synthetic":
        return "Mostly fibers made from processed wood pulp"
    return "Mostly natural fibers"


# ---------------- Cart ----------------

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
