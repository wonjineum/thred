"""Connects alternatives to Labi's CLIP helpers in ml/clip_helpers.py.

CLIP needs torch + transformers (several GB), so it's optional:
    pip install -r ../ml/requirements.txt
Without it (or with THRED_USE_CLIP=0), embed_image returns None and alternatives
are ranked on sustainability and price only, without visual similarity.

The first call loads the model (and downloads it the very first time), which
takes a while. Embeddings are cached in memory by image URL.
"""

from functools import lru_cache
import math
import os
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[2]


def clip_enabled() -> bool:
    return os.getenv("THRED_USE_CLIP", "1") != "0"


@lru_cache(maxsize=1)
def _helpers():
    if not clip_enabled():
        return None
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    try:
        from ml import clip_helpers  # noqa: PLC0415  (loads the model)
    except Exception:  # torch/transformers not installed, model download failed, etc.
        return None
    return clip_helpers


@lru_cache(maxsize=2048)
def _embed_cached(image_url: str) -> tuple[float, ...] | None:
    helpers = _helpers()
    if helpers is None:
        return None
    try:
        vector = helpers._embed_image(image_url)
    except Exception:  # dead link, not an image, timeout
        return None
    return tuple(float(x) for x in vector.reshape(-1).tolist())


def embed_image(image_url: str | None) -> list[float] | None:
    """Unit-length CLIP embedding of the image at this URL, or None."""
    if not image_url:
        return None
    result = _embed_cached(image_url)
    return list(result) if result else None


def tag_garment(image_url: str | None, options: list[str]) -> str | None:
    """Best-matching garment type for the photo, or None if CLIP is unsure."""
    helpers = _helpers()
    if helpers is None or not image_url:
        return None
    try:
        result = helpers.tag_image(image_url, [*options, "other"])
    except Exception:
        return None
    best = result["best"]
    if best == "other" or result["scores"][best] < 0.5:
        return None
    return best


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine similarity, -1 to 1. 0 when either embedding is missing."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def clear_cache() -> None:
    _helpers.cache_clear()
    _embed_cached.cache_clear()
