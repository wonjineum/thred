"""Load and match sustainability reference catalogs.

The scraper owns producing these JSON files. This module only validates and
indexes reviewed records; it never creates or fills production data.
"""

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATERIAL_CATEGORIES = {"natural", "synthetic", "semi-synthetic"}


class CatalogError(ValueError):
    """Raised when a catalog file exists but does not follow the data contract."""


@dataclass(frozen=True)
class Brand:
    name: str
    aliases: tuple[str, ...]
    fti_score: float | None
    b_corp: bool | None
    sbti_target: bool | None
    certifications: tuple[str, ...]
    evidence_snippets: dict[str, str]
    sources: tuple[str, ...]
    last_checked: str | None


@dataclass(frozen=True)
class Material:
    name: str
    aliases: tuple[str, ...]
    category: str
    recycled: bool
    organic: bool
    water_l_per_kg: float | None
    co2_kg_per_kg: float | None
    sources: dict[str, str]
    notes: str


@dataclass(frozen=True)
class Catalog:
    brands: tuple[Brand, ...]
    materials: tuple[Material, ...]
    _brands_by_alias: dict[str, Brand]
    _materials_by_alias: dict[str, Material]

    def match_brand(self, name: str | None) -> Brand | None:
        return self._brands_by_alias.get(normalize_name(name)) if name else None

    def match_material(self, name: str | None) -> Material | None:
        return self._materials_by_alias.get(normalize_name(name)) if name else None

    def match_materials(self, names: list[str]) -> dict[str, Material | None]:
        return {name: self.match_material(name) for name in names}


def normalize_name(value: str) -> str:
    """Normalize names for case-insensitive, whitespace-tolerant matching."""
    return " ".join(value.casefold().replace("’", "'").split())


def load_catalog(data_dir: Path | str = DEFAULT_DATA_DIR) -> Catalog:
    """Load a catalog once per directory and return indexed records.

    Missing files are treated as unavailable reference data and result in empty
    catalogs. Existing malformed files raise ``CatalogError`` at application
    startup instead of silently degrading scoring.
    """
    return _load_catalog_cached(str(Path(data_dir).resolve()))


def clear_catalog_cache() -> None:
    """Clear cached catalogs for tests or an explicit data refresh."""
    _load_catalog_cached.cache_clear()


@lru_cache(maxsize=8)
def _load_catalog_cached(data_dir: str) -> Catalog:
    directory = Path(data_dir)
    brands_data = _read_array(directory / "brands.json")
    materials_data = _read_array(directory / "materials.json")
    brands = tuple(_parse_brand(value, index) for index, value in enumerate(brands_data))
    materials = tuple(_parse_material(value, index) for index, value in enumerate(materials_data))
    return Catalog(
        brands=brands,
        materials=materials,
        _brands_by_alias=_index_aliases(brands, "brand"),
        _materials_by_alias=_index_aliases(materials, "material"),
    )


def _read_array(path: Path) -> list[Any]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"Unable to read valid JSON from {path}") from exc
    if not isinstance(value, list):
        raise CatalogError(f"{path} must contain a JSON array")
    return value


def _parse_brand(value: Any, index: int) -> Brand:
    if not isinstance(value, dict):
        raise CatalogError(f"Brand at index {index} must be an object")
    name = _required_string(value, "name", "brand", index)
    aliases = _string_list(value, "aliases", "brand", index)
    evidence = value.get("evidence", {})
    if not isinstance(evidence, dict):
        raise CatalogError(f"Brand evidence at index {index} must be an object")
    fti_score = _nullable_number(evidence, "fti_score", "brand", index)
    if fti_score is not None and not 0 <= fti_score <= 100:
        raise CatalogError(f"Brand fti_score at index {index} must be between 0 and 100")
    return Brand(
        name=name,
        aliases=tuple(normalize_name(alias) for alias in aliases),
        fti_score=fti_score,
        b_corp=_nullable_bool(evidence, "b_corp", "brand", index),
        sbti_target=_nullable_bool(evidence, "sbti_target", "brand", index),
        certifications=tuple(_string_list(evidence, "certifications", "brand", index)),
        evidence_snippets=_optional_string_dict(value, "evidence_snippets", "brand", index),
        sources=tuple(_string_list(value, "sources", "brand", index)),
        last_checked=_optional_string(value, "last_checked", "brand", index),
    )


def _parse_material(value: Any, index: int) -> Material:
    if not isinstance(value, dict):
        raise CatalogError(f"Material at index {index} must be an object")
    name = _required_string(value, "name", "material", index)
    category = _required_string(value, "category", "material", index)
    if category not in MATERIAL_CATEGORIES:
        raise CatalogError(f"Material category at index {index} is invalid")
    return Material(
        name=name,
        aliases=tuple(normalize_name(alias) for alias in _string_list(value, "aliases", "material", index)),
        category=category,
        recycled=_required_bool(value, "recycled", "material", index),
        organic=_required_bool(value, "organic", "material", index),
        water_l_per_kg=_nullable_number(value, "water_l_per_kg", "material", index),
        co2_kg_per_kg=_nullable_number(value, "co2_kg_per_kg", "material", index),
        sources=_optional_string_dict(value, "sources", "material", index),
        notes=_optional_string(value, "notes", "material", index) or "",
    )


def _index_aliases(records: tuple[Any, ...], kind: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for record in records:
        for alias in (record.name, *record.aliases):
            normalized = normalize_name(alias)
            existing = result.get(normalized)
            if existing is not None and existing != record:
                raise CatalogError(f"Duplicate {kind} alias: {alias}")
            result[normalized] = record
    return result


def _required_string(value: dict[str, Any], field: str, kind: str, index: int) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise CatalogError(f"{kind} {field} at index {index} must be a non-empty string")
    return normalize_name(result)


def _optional_string(value: dict[str, Any], field: str, kind: str, index: int) -> str | None:
    result = value.get(field)
    if result is None:
        return None
    if not isinstance(result, str):
        raise CatalogError(f"{kind} {field} at index {index} must be a string or null")
    return result


def _string_list(value: dict[str, Any], field: str, kind: str, index: int) -> list[str]:
    result = value.get(field, [])
    if not isinstance(result, list) or any(not isinstance(item, str) for item in result):
        raise CatalogError(f"{kind} {field} at index {index} must be a list of strings")
    return result


def _optional_string_dict(value: dict[str, Any], field: str, kind: str, index: int) -> dict[str, str]:
    result = value.get(field, {})
    if not isinstance(result, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in result.items()):
        raise CatalogError(f"{kind} {field} at index {index} must be an object of strings")
    return dict(result)


def _required_bool(value: dict[str, Any], field: str, kind: str, index: int) -> bool:
    result = value.get(field)
    if not isinstance(result, bool):
        raise CatalogError(f"{kind} {field} at index {index} must be true or false")
    return result


def _nullable_bool(value: dict[str, Any], field: str, kind: str, index: int) -> bool | None:
    result = value.get(field)
    if result is not None and not isinstance(result, bool):
        raise CatalogError(f"{kind} {field} at index {index} must be true, false, or null")
    return result


def _nullable_number(value: dict[str, Any], field: str, kind: str, index: int) -> float | None:
    result = value.get(field)
    if result is None:
        return None
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise CatalogError(f"{kind} {field} at index {index} must be a number or null")
    return float(result)
