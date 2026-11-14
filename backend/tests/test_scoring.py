import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import llm_fallback, rubric
from app.catalog import load_catalog
from app.main import app
from app.schemas import CartItem
from app.scoring import brand_component, material_component, score_item

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CATALOG = load_catalog(DATA_DIR)


def item(**fields):
    return CartItem(item_id=fields.pop("item_id", "x"), title=fields.pop("title", "Shirt"), **fields)


@pytest.fixture
def no_llm(monkeypatch):
    """Fail the test if scoring calls the LLM when it shouldn't."""
    def boom(*args, **kwargs):
        raise AssertionError("LLM should not be called here")
    monkeypatch.setattr(llm_fallback, "classify_brand", boom)
    monkeypatch.setattr(llm_fallback, "extract_materials", boom)


@pytest.fixture
def catalog(tmp_path):
    brands = [
        {"name": "Plain Co", "aliases": [], "evidence": {"fti_score": None, "b_corp": None, "sbti_target": None, "certifications": []}},
        {"name": "Open Co", "aliases": [], "evidence": {"fti_score": 50, "b_corp": False, "sbti_target": True, "certifications": []}},
        {"name": "Best Co", "aliases": ["best"], "evidence": {"fti_score": 100, "b_corp": True, "sbti_target": True, "certifications": ["GOTS", "bluesign", "Fair Trade Certified"]}},
    ]
    (tmp_path / "brands.json").write_text(json.dumps(brands))
    (tmp_path / "materials.json").write_text((DATA_DIR / "materials.json").read_text())
    return load_catalog(tmp_path)


# ---------- Brand ----------

def test_brand_points_come_from_evidence(catalog, no_llm):
    # base 8 + neutral FTI 3
    assert brand_component("Plain Co", catalog).points == 11
    # base 8 + FTI 50% of 10 + SBTi 5
    assert brand_component("Open Co", catalog).points == 18
    # every signal maxed out is capped at 34
    assert brand_component("best", catalog).points == 34


def test_brand_summary_names_the_evidence(catalog, no_llm):
    assert brand_component("Open Co", catalog).summary == "Some sustainability commitments: validated climate target"
    assert brand_component("Best Co", catalog).summary.startswith("Strong sustainability record: GOTS, bluesign")


def test_unknown_brand_without_llm_gets_default():
    result = brand_component("Totally Unknown Brand", CATALOG)
    assert result.points == rubric.BRAND_UNKNOWN_POINTS
    assert result.summary == "No sustainability information found"
    assert result.source == "unknown"


def test_missing_brand_gets_default_without_calling_llm(no_llm):
    assert brand_component(None, CATALOG).source == "unknown"
    assert brand_component("   ", CATALOG).source == "unknown"


@pytest.mark.parametrize("label, points", [("Good", 26), ("Average", 17), ("Bad", 6)])
def test_unknown_brand_uses_llm_label(monkeypatch, label, points):
    monkeypatch.setattr(llm_fallback, "classify_brand", lambda name: label)
    result = brand_component("Some Small Label", CATALOG)
    assert result.points == points
    assert result.summary.startswith("AI estimate:")
    assert result.source == "llm"


def test_unknown_never_beats_documented_brands():
    weakest = min(brand_component(b.name, CATALOG).points for b in CATALOG.brands)
    assert rubric.BRAND_UNKNOWN_POINTS <= weakest + 2


def test_every_real_brand_scores_in_range(no_llm):
    for brand in CATALOG.brands:
        assert 0 <= brand_component(brand.name, CATALOG).points <= rubric.BRAND_MAX


# ---------- Material ----------

def test_single_fiber(no_llm):
    result = material_component(item(material_text="100% Polyester"), CATALOG)
    assert result.points == rubric.MATERIAL_POINTS["polyester"]
    assert result.summary == "100% polyester"
    assert "fossil fuels" in result.impact


def test_blend_is_weighted_by_percentage(no_llm):
    result = material_component(item(material_text="60% Cotton, 40% Polyester"), CATALOG)
    expected = (rubric.MATERIAL_POINTS["cotton"] * 60 + rubric.MATERIAL_POINTS["polyester"] * 40) / 100
    assert result.points == round(expected)
    assert result.summary == "Blend of cotton and polyester"


def test_aliases_match_catalog_materials(no_llm):
    result = material_component(item(material_text="92% Viscose rayon, 8% Elastane"), CATALOG)
    assert result.summary == "Mostly viscose"
    assert result.source == "parser"


def test_organic_and_recycled_score_higher_than_conventional(no_llm):
    def points(text):
        return material_component(item(material_text=text), CATALOG).points
    assert points("100% Organic Cotton") > points("100% Cotton")
    assert points("100% Recycled Polyester") > points("100% Polyester")


def test_mostly_unrecognized_fibers_count_as_unknown(no_llm):
    result = material_component(item(material_text="70% Mysteryfiber, 30% Cotton"), CATALOG)
    assert result.points == rubric.MATERIAL_UNKNOWN_POINTS
    assert result.source == "unknown"


def test_llm_reads_text_the_parser_cannot(monkeypatch):
    monkeypatch.setattr(llm_fallback, "extract_materials", lambda text, title: {"cotton": 80, "recycled polyester": 20})
    result = material_component(item(material_text="Made with eighty percent cotton"), CATALOG)
    assert result.source == "llm"
    assert result.summary == "AI estimate: mostly cotton"


def test_no_material_info_without_llm():
    result = material_component(item(material_text=None), CATALOG)
    assert result.points == rubric.MATERIAL_UNKNOWN_POINTS
    assert result.summary == "No material information found"


def test_parser_result_skips_llm(no_llm):
    material_component(item(material_text="100% Cotton"), CATALOG)


# ---------- Data files stay in sync with the rubric ----------

def test_every_material_has_points_and_every_rubric_entry_has_data():
    names = {m.name for m in CATALOG.materials}
    assert names == set(rubric.MATERIAL_POINTS)


# ---------- End to end ----------

def test_score_endpoint_returns_real_scores():
    client = TestClient(app)
    body = client.post(
        "/score",
        json={"items": [
            {"item_id": "a", "title": "Tee", "brand": "Puma", "material_text": "100% Organic Cotton"},
            {"item_id": "b", "title": "Tee", "brand": "Forever 21", "material_text": "100% Polyester"},
        ]},
    ).json()
    assert body["mock"] is False
    good, bad = body["items"]
    assert good["total"] > bad["total"]
    assert good["verdict"] == "good_choice"
    assert bad["verdict"] == "consider_alternatives"


def test_real_amazon_sample_scores():
    samples = json.loads((Path(__file__).parent / "amazon_samples.json").read_text())["items"]
    for sample in samples:
        result = score_item(CartItem(**sample), 0, CATALOG)
        assert 0 <= result.total <= 100
        assert result.material.summary != "No material information found"
