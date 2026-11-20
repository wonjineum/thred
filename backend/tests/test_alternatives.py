import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import alternatives, clip_similarity, rubric
from app.alternatives import AlternativesError, find_alternatives, load_index
from app.catalog import load_catalog
from app.garments import garment_type_from_text
from app.main import app
from app.schemas import CartItem

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CATALOG = load_catalog(DATA_DIR)

# The real Amazon sample (Banana Republic viscose pants, scores 33).
PANTS = CartItem(**json.loads((Path(__file__).parent / "amazon_samples.json").read_text())["items"][0])
PANTS_TOTAL = 33


def listing(alt_id, **overrides):
    """A made-up listing for tests. Real listings come from alternatives.json."""
    record = {
        "alt_id": alt_id,
        "title": "Organic Cotton Wide Leg Pants",
        "brand": None,
        "price": 40.0,
        "currency": "USD",
        "image_url": f"https://example.com/{alt_id}.jpg",
        "listing_url": f"https://example.com/listing/{alt_id}",
        "source": "Test",
        "condition": "Very good",
        "secondhand": True,
        "garment_type": "pants",
        "material_text": "100% Organic Cotton",
    }
    record.update(overrides)
    return record


@pytest.fixture(autouse=True)
def fresh_cache():
    alternatives.clear_cache()
    clip_similarity.clear_cache()
    yield
    alternatives.clear_cache()


def write(tmp_path, records, embeddings=None):
    (tmp_path / "alternatives.json").write_text(json.dumps(records))
    if embeddings is not None:
        (tmp_path / "alternative_embeddings.json").write_text(json.dumps({"model": "test", "embeddings": embeddings}))
    return load_index(CATALOG, tmp_path)


# ---------- Garment type ----------

@pytest.mark.parametrize(
    "title, expected",
    [
        ("Banana Republic Women's High-Rise Modern Straight City Stretch Pant", "pants"),
        ("Amazon Essentials Men's Fleece Hoodie, Sage Green, Medium", "hoodie"),
        ("Levi's Men's 505 Regular Fit Jeans", "jeans"),
        ("Levi's Trucker Jean Jacket", "jacket"),
        ("Hanes Men's Short Sleeve T-Shirt, 4-Pack", "t-shirt"),
        ("T-Shirt Dress", "dress"),
        ("Champion Reverse Weave Crewneck Sweatshirt", "hoodie"),
        ("Women's Short Sleeve Blouse", "shirt"),
        ("Wireless Earbuds", None),
    ],
)
def test_garment_type_from_title(title, expected):
    assert garment_type_from_text(title) == expected


def test_garment_type_falls_back_to_category():
    assert garment_type_from_text("Banana Republic Classic", "Jeans") == "jeans"


# ---------- Finding alternatives ----------

def test_returns_better_scoring_same_type_alternatives(tmp_path):
    index = write(tmp_path, [
        listing("good"),
        listing("too-expensive", price=500.0),
        listing("wrong-type", garment_type="jeans", title="Organic Cotton Jeans"),
        listing("worse", material_text="100% Acrylic", secondhand=False),
    ])
    result = find_alternatives(PANTS, CATALOG, index)
    assert result.status == "ok"
    assert result.garment_type == "pants"
    assert [a.alt_id for a in result.alternatives] == ["good"]
    best = result.alternatives[0]
    assert best.total > result.item_total
    assert best.similarity is None  # no CLIP in tests


def test_never_suggests_a_low_scoring_listing(tmp_path):
    # 100% polyester from a weak brand: higher than the pants (33) only thanks to
    # the secondhand bonus, but still below "Okay".
    index = write(tmp_path, [listing("weak", brand="Forever 21", material_text="100% Polyester")])
    weak_total = index.listings[0].total
    assert PANTS_TOTAL < weak_total < rubric.ALTERNATIVE_MIN_TOTAL
    assert find_alternatives(PANTS, CATALOG, index).status == "no_match"


def test_secondhand_bonus_is_added(tmp_path):
    index = write(tmp_path, [listing("used"), listing("new", secondhand=False)])
    totals = {l.data["alt_id"]: l.total for l in index.listings}
    assert totals["used"] - totals["new"] == rubric.SECONDHAND_BONUS


def test_visual_similarity_decides_between_similar_listings(tmp_path, monkeypatch):
    index = write(
        tmp_path,
        [listing("looks-different"), listing("looks-same")],
        embeddings={"looks-different": [0.0, 1.0], "looks-same": [1.0, 0.0]},
    )
    monkeypatch.setattr(clip_similarity, "embed_image", lambda url: [1.0, 0.0])
    result = find_alternatives(PANTS, CATALOG, index)
    assert [a.alt_id for a in result.alternatives] == ["looks-same", "looks-different"]
    assert result.alternatives[0].similarity == 1.0


def test_limit(tmp_path):
    index = write(tmp_path, [listing(f"alt-{i}") for i in range(6)])
    assert len(find_alternatives(PANTS, CATALOG, index, limit=2).alternatives) == 2
    assert len(find_alternatives(PANTS, CATALOG, index).alternatives) == 3


def test_item_without_price_is_not_filtered_on_price(tmp_path):
    index = write(tmp_path, [listing("pricey", price=500.0)])
    no_price = PANTS.model_copy(update={"price": None})
    assert [a.alt_id for a in find_alternatives(no_price, CATALOG, index).alternatives] == ["pricey"]


def test_no_catalog(tmp_path):
    result = find_alternatives(PANTS, CATALOG, load_index(CATALOG, tmp_path))
    assert result.status == "no_catalog"
    assert result.alternatives == []
    assert result.message


def test_unknown_garment_type(tmp_path):
    index = write(tmp_path, [listing("good")])
    earbuds = CartItem(item_id="e", title="Wireless Earbuds")
    assert find_alternatives(earbuds, CATALOG, index).status == "unknown_type"


def test_no_match(tmp_path):
    index = write(tmp_path, [listing("jeans-only", garment_type="jeans")])
    result = find_alternatives(PANTS, CATALOG, index)
    assert result.status == "no_match"
    assert "pants" in result.message


# ---------- Data validation ----------

@pytest.mark.parametrize(
    "bad",
    [
        listing("x", garment_type="trousers"),
        listing("x", price="40"),
        listing("x", price=None),
        listing("x", listing_url=""),
        {"alt_id": "x"},
        "not an object",
    ],
)
def test_bad_listing_is_skipped_and_the_rest_still_load(tmp_path, bad):
    index = write(tmp_path, [bad, listing("good")])
    assert [l.data["alt_id"] for l in index.listings] == ["good"]


def test_duplicate_ids_keep_the_first(tmp_path):
    index = write(tmp_path, [listing("same", title="First Pants"), listing("same", title="Second Pants")])
    assert [l.data["title"] for l in index.listings] == ["First Pants"]


def test_broken_json_file_raises(tmp_path):
    (tmp_path / "alternatives.json").write_text("{not json")
    with pytest.raises(AlternativesError):
        load_index(CATALOG, tmp_path)


def test_accepts_the_vinted_scraper_format(tmp_path):
    # scripts/vinted_altneratives.py writes item_id / product_url and no source.
    scraped = {
        "item_id": "vinted_123",
        "title": "Organic Cotton Wide Leg Pants",
        "brand": None,
        "price": 30.0,
        "image_url": "https://example.com/v.jpg",
        "product_url": "https://example.com/items/123",
        "material_text": "100% Organic Cotton",
        "category": None,
        "certifications": None,
        "garment_type": "pants",
    }
    index = write(tmp_path, [scraped])
    result = find_alternatives(PANTS, CATALOG, index)
    alt = result.alternatives[0]
    assert (alt.alt_id, alt.source, alt.listing_url, alt.product_url, alt.secondhand) == (
        "vinted_123", "Vinted", "https://example.com/items/123", "https://example.com/items/123", True,
    )


@pytest.mark.parametrize(
    "embeddings_file, expected",
    [
        ({}, {}),
        ({"model": "clip", "embeddings": {"good": [1, 0]}}, {"good": (1.0, 0.0)}),
        ({"good": [1, 0]}, {"good": (1.0, 0.0)}),
        ({"good": "oops", "fine": [0, 1]}, {"fine": (0.0, 1.0)}),
    ],
)
def test_embedding_file_shapes(tmp_path, embeddings_file, expected):
    (tmp_path / "alternatives.json").write_text(json.dumps([listing("good"), listing("fine")]))
    (tmp_path / "alternative_embeddings.json").write_text(json.dumps(embeddings_file))
    index = load_index(CATALOG, tmp_path)
    assert {l.data["alt_id"]: l.embedding for l in index.listings if l.embedding} == expected


# ---------- Endpoint ----------

def test_alternatives_endpoint_with_real_amazon_sample():
    body = TestClient(app).post("/alternatives", json={"item": PANTS.model_dump()}).json()
    assert body["item_id"] == PANTS.item_id
    assert body["garment_type"] == "pants"
    assert body["status"] in {"ok", "no_catalog", "no_match"}


def test_alternatives_endpoint_validates_limit():
    res = TestClient(app).post("/alternatives", json={"item": PANTS.model_dump(), "limit": 0})
    assert res.status_code == 422


# ---------- Alternatives inside /score (what the extension popup reads) ----------

def test_score_includes_alternatives_per_item(tmp_path, monkeypatch):
    import app.main as main_module

    index = write(tmp_path, [listing("good")])
    monkeypatch.setattr(main_module, "load_index", lambda catalog: index)
    body = TestClient(app).post("/score", json={"items": [PANTS.model_dump()]}).json()
    alts = body["items"][0]["alternatives"]
    assert [a["alt_id"] for a in alts] == ["good"]
    assert alts[0]["product_url"] == alts[0]["listing_url"]


def test_score_still_works_when_alternatives_break(monkeypatch):
    import app.main as main_module

    def broken(catalog):
        raise AlternativesError("bad file")

    monkeypatch.setattr(main_module, "load_index", broken)
    res = TestClient(app).post("/score", json={"items": [PANTS.model_dump()]})
    assert res.status_code == 200
    assert res.json()["items"][0]["alternatives"] == []
