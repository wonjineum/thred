"""Connects scoring to Labi's LLM helpers in ml/llm_helpers.py.

Only used when the normal path fails: a brand that isn't in brands.json, or
material text the parser can't read. If the LLM isn't available (no API key,
package not installed, THRED_USE_LLM=0, or the call fails), these return None
and scoring falls back to its "unknown" defaults instead of crashing.

Results are cached in memory, so each brand or text is only sent to the LLM once
per server run.
"""

from functools import lru_cache
import os
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[2]


def llm_enabled() -> bool:
    if os.getenv("THRED_USE_LLM", "1") == "0":
        return False
    return bool(os.getenv("OPENROUTER_API_KEY")) or (_REPO_ROOT / "ml" / ".env").exists() or (_REPO_ROOT / ".env").exists()


def _helpers():
    """Import ml.llm_helpers lazily, so the backend still starts without it."""
    if not llm_enabled():
        return None
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    try:
        from ml import llm_helpers  # noqa: PLC0415
    except Exception:  # missing package, missing key (ml/llm.py raises KeyError), etc.
        return None
    return llm_helpers


@lru_cache(maxsize=1024)
def classify_brand(brand_name: str) -> str | None:
    """'Good' / 'Average' / 'Bad', or None if the LLM is unavailable or doesn't know."""
    helpers = _helpers()
    if helpers is None:
        return None
    label = helpers.classify_unknown_brand(brand_name)
    return label if label in ("Good", "Average", "Bad") else None


@lru_cache(maxsize=1024)
def _extract_materials_cached(material_text: str | None, title: str | None) -> tuple | None:
    helpers = _helpers()
    if helpers is None:
        return None
    result = helpers.extract_material_composition(material_text, product_title=title)
    return tuple(sorted(result.items())) if result else None


def extract_materials(material_text: str | None, title: str | None) -> dict[str, float] | None:
    """{fiber: percent} from text the parser couldn't read, or None."""
    result = _extract_materials_cached(material_text, title)
    return dict(result) if result else None


def clear_cache() -> None:
    classify_brand.cache_clear()
    _extract_materials_cached.cache_clear()
