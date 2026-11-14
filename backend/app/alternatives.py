"""Suggest lower-impact alternatives for a cart item.

Data:
    backend/data/alternatives.json            listings (Samira), see docs/data-formats.md Part C
    backend/data/alternative_embeddings.json  CLIP embeddings per listing (Labi), optional

Ranking is Labi's ml/recommendation_helpers.recommend_alternatives: same garment
type, higher sustainability score, at most 1.5x the price, then ranked by
60% visual similarity, 30% sustainability, 10% price.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any

from . import clip_similarity, rubric
from .catalog import Catalog
from .garments import GARMENT_TYPES, garment_type_from_text
from .schemas import VERDICT_LABELS, Alternative, AlternativesResponse, CartItem
from .scoring import score_item, verdict_for

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FIELDS = ("alt_id", "title", "price", "image_url", "listing_url", "source", "garment_type")


class AlternativesError(ValueError):
    """alternatives.json exists but doesn't follow the data format."""


@dataclass(frozen=True)
class Listing:
    data: dict[str, Any]  # the raw record from alternatives.json
    total: int  # sustainability score 0-100, including the secondhand bonus
    embedding: tuple[float, ...] | None


@dataclass(frozen=True)
class AlternativesIndex:
    listings: tuple[Listing, ...]


# ---------------- Loading ----------------

_INDEX_CACHE: dict[tuple[str, int], AlternativesIndex] = {}


def load_index(catalog: Catalog, data_dir: Path | str = DEFAULT_DATA_DIR) -> AlternativesIndex:
    """Load and score every listing once; cached until clear_cache()."""
    key = (str(Path(data_dir).resolve()), id(catalog))
    if key not in _INDEX_CACHE:
        directory = Path(key[0])
        records = _read_listings(directory / "alternatives.json")
        embeddings = _read_embeddings(directory / "alternative_embeddings.json")
        _INDEX_CACHE[key] = AlternativesIndex(tuple(
            Listing(data=r, total=_score_listing(r, catalog), embedding=embeddings.get(r["alt_id"]))
            for r in records
        ))
    return _INDEX_CACHE[key]


def clear_cache() -> None:
    _INDEX_CACHE.clear()


def _read_listings(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AlternativesError(f"Unable to read valid JSON from {path}") from exc
    if not isinstance(records, list):
        raise AlternativesError(f"{path} must contain a JSON array")
    seen: set[str] = set()
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            raise AlternativesError(f"Listing {i} must be an object")
        missing = [f for f in REQUIRED_FIELDS if r.get(f) in (None, "")]
        if missing:
            raise AlternativesError(f"Listing {i} is missing {', '.join(missing)}")
        if r["garment_type"] not in GARMENT_TYPES:
            raise AlternativesError(f"Listing {i} garment_type must be one of {GARMENT_TYPES}")
        if isinstance(r["price"], bool) or not isinstance(r["price"], (int, float)) or r["price"] < 0:
            raise AlternativesError(f"Listing {i} price must be a non-negative number")
        if r["alt_id"] in seen:
            raise AlternativesError(f"Duplicate alt_id: {r['alt_id']}")
        seen.add(r["alt_id"])
    return records


def _read_embeddings(path: Path) -> dict[str, tuple[float, ...]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: tuple(float(x) for x in v) for k, v in data["embeddings"].items()}
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError) as exc:
        raise AlternativesError(f"{path} must look like {{\"model\": ..., \"embeddings\": {{alt_id: [numbers]}}}}") from exc


def _score_listing(record: dict[str, Any], catalog: Catalog) -> int:
    as_item = CartItem(
        item_id=record["alt_id"],
        title=record["title"],
        brand=record.get("brand"),
        material_text=record.get("material_text"),
    )
    total = score_item(as_item, 0, catalog).total
    if record.get("secondhand", True):
        total += rubric.SECONDHAND_BONUS
    return min(total, 100)


# ---------------- Finding alternatives ----------------

def _recommend():
    """Labi's ranking function (pure Python, no heavy dependencies)."""
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    from ml.recommendation_helpers import recommend_alternatives  # noqa: PLC0415

    return recommend_alternatives


def find_alternatives(item: CartItem, catalog: Catalog, index: AlternativesIndex, limit: int = 3) -> AlternativesResponse:
    item_total = score_item(item, 0, catalog).total
    garment = garment_type_from_text(item.title, item.category) or clip_similarity.tag_garment(item.image_url, GARMENT_TYPES)

    def respond(status: str, message: str, alternatives: list[Alternative] | None = None) -> AlternativesResponse:
        return AlternativesResponse(
            item_id=item.item_id,
            item_total=item_total,
            garment_type=garment,
            status=status,
            message=message,
            alternatives=alternatives or [],
        )

    if not index.listings:
        return respond("no_catalog", "Alternatives aren't available yet.")
    if garment is None:
        return respond("unknown_type", "We couldn't tell what kind of item this is.")

    item_embedding = clip_similarity.embed_image(item.image_url)
    product = {
        "category": garment,
        # No price -> don't filter or rank on price (inf passes every price check).
        "price": item.price if item.price is not None else float("inf"),
        "sustainability_score": item_total,
        "embedding": item_embedding,
    }
    candidates = []
    for listing in index.listings:
        # Never suggest something the panel itself would label "Consider alternatives".
        if listing.total < rubric.ALTERNATIVE_MIN_TOTAL:
            continue
        embedding = listing.embedding
        if embedding is None and item_embedding is not None:
            embedding = clip_similarity.embed_image(listing.data["image_url"])
        candidates.append({
            **listing.data,
            "category": listing.data["garment_type"],
            "sustainability_score": listing.total,
            "embedding": list(embedding) if embedding else None,
        })

    ranked = _recommend()(product, candidates, clip_similarity.cosine, top_k=limit)
    if not ranked:
        return respond("no_match", f"No better-scoring {garment} alternatives in a similar price range yet.")

    used_similarity = item_embedding is not None
    return respond("ok", "", [_to_alternative(r, used_similarity) for r in ranked])


def _to_alternative(record: dict[str, Any], used_similarity: bool) -> Alternative:
    total = record["sustainability_score"]
    verdict = verdict_for(total)
    return Alternative(
        alt_id=record["alt_id"],
        title=record["title"],
        brand=record.get("brand"),
        price=record["price"],
        currency=record.get("currency", "USD"),
        image_url=record["image_url"],
        listing_url=record["listing_url"],
        source=record["source"],
        condition=record.get("condition"),
        secondhand=record.get("secondhand", True),
        garment_type=record["garment_type"],
        total=total,
        verdict=verdict,
        verdict_label=VERDICT_LABELS[verdict],
        similarity=round(record["similarity"], 4) if used_similarity and record.get("embedding") else None,
        ranking_score=round(record["ranking_score"], 4),
    )
