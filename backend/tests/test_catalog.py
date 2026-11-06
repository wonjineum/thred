import json

import pytest

from app.catalog import CatalogError, clear_catalog_cache, load_catalog


@pytest.fixture
def catalog_dir(tmp_path):
    brands = [
        {
            "name": "Patagonia",
            "aliases": ["patagonia inc"],
            "evidence": {
                "fti_score": None,
                "b_corp": True,
                "sbti_target": False,
                "certifications": ["Fair Trade Certified"],
            },
            "evidence_snippets": {"b_corp": "Verified source"},
            "sources": ["https://example.test/brand"],
            "last_checked": "2026-01-01",
        }
    ]
    materials = [
        {
            "name": "spandex",
            "aliases": ["elastane", "lycra"],
            "category": "synthetic",
            "recycled": False,
            "organic": False,
            "water_l_per_kg": None,
            "co2_kg_per_kg": 5.0,
            "sources": {"co2_kg_per_kg": "https://example.test/material"},
            "notes": "",
        }
    ]
    (tmp_path / "brands.json").write_text(json.dumps(brands))
    (tmp_path / "materials.json").write_text(json.dumps(materials))
    clear_catalog_cache()
    return tmp_path


def test_loads_records_and_matches_aliases(catalog_dir):
    catalog = load_catalog(catalog_dir)
    assert catalog.match_brand(" PATAGONIA INC ") is catalog.brands[0]
    material = catalog.match_material("ELASTANE")
    assert material is catalog.materials[0]
    assert material.recycled is False
    assert material.water_l_per_kg is None


def test_missing_files_are_empty_and_unknown_matches_are_none(tmp_path):
    catalog = load_catalog(tmp_path)
    assert catalog.brands == ()
    assert catalog.materials == ()
    assert catalog.match_brand("Unknown") is None
    assert catalog.match_material("Unknown") is None


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("brands.json", {"name": "not an array"}),
        ("materials.json", [{"name": "cotton", "category": "unknown"}]),
    ],
)
def test_malformed_catalog_raises_catalog_error(tmp_path, filename, payload):
    (tmp_path / filename).write_text(json.dumps(payload))
    with pytest.raises(CatalogError):
        load_catalog(tmp_path)
