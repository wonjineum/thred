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
import logging
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
REQUIRED_FIELDS = ("alt_id", "title", "price", "image_url", "listing_url", "garment_type")


log = logging.getLogger("thred.alternatives")


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
    """Valid listings from alternatives.json. Bad listings are skipped with a warning."""
    if not path.exists():
        return []
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AlternativesError(f"Unable to read valid JSON from {path}") from exc
    if not isinstance(records, list):
        raise AlternativesError(f"{path} must contain a JSON array")

    listings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw in enumerate(records):
        record = _normalize(raw) if isinstance(raw, dict) else None
        problem = _problem(record, seen)
        if problem:
            log.warning("Skipping listing %s in %s: %s", i, path.name, problem)
            continue
        seen.add(record["alt_id"])
        listings.append(record)
    return listings


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept the spec's field names and the scraper's (item_id, product_url)."""
    record = dict(raw)
    record["alt_id"] = raw.get("alt_id") or raw.get("item_id")
    record["listing_url"] = raw.get("listing_url") or raw.get("product_url")
    if not record.get("source"):
        prefix = str(record["alt_id"] or "").split("_")[0].split("-")[0]
        record["source"] = prefix.capitalize() if prefix else "Secondhand"
    if record.get("secondhand") is None:
        record["secondhand"] = True
    record.setdefault("currency", "USD")
    return record


def _problem(record: dict[str, Any] | None, seen: set[str]) -> str | None:
    if record is None:
        return "not an object"
    missing = [f for f in REQUIRED_FIELDS if record.get(f) in (None, "")]
    if missing:
        return f"missing {', '.join(missing)}"
    if record["garment_type"] not in GARMENT_TYPES:
        return f"garment_type must be one of {GARMENT_TYPES}"
    price = record["price"]
    if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
        return "price must be a non-negative number"
    if record["alt_id"] in seen:
        return f"duplicate alt_id {record['alt_id']}"
    return None


def _read_embeddings(path: Path) -> dict[str, tuple[float, ...]]:
    """Accepts {"model": ..., "embeddings": {alt_id: [...]}}, a flat {alt_id: [...]}, or {}."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AlternativesError(f"Unable to read valid JSON from {path}") from exc
    if not isinstance(data, dict):
        raise AlternativesError(f"{path} must contain a JSON object")
    vectors = data.get("embeddings", data)
    if not isinstance(vectors, dict):
        raise AlternativesError(f"{path}: 'embeddings' must map alt_id to a list of numbers")
    result: dict[str, tuple[float, ...]] = {}
    for alt_id, vector in vectors.items():
        if alt_id == "model":
            continue
        try:
            result[alt_id] = tuple(float(x) for x in vector)
        except (TypeError, ValueError):
            log.warning("Skipping embedding for %s: not a list of numbers", alt_id)
    return result


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
        product_url=record["listing_url"],
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
