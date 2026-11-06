from app.catalog import load_catalog
from app.schemas import CartItem
from app.scoring import score_item


def test_material_parser_and_catalog_matching_feed_existing_score_shape(tmp_path):
    (tmp_path / "brands.json").write_text("[]")
    (tmp_path / "materials.json").write_text(
        '[{"name":"spandex","aliases":["elastane"],"category":"synthetic",'
        '"recycled":false,"organic":false,"water_l_per_kg":null,'
        '"co2_kg_per_kg":null,"sources":{},"notes":""}]'
    )
    result = score_item(
        CartItem(item_id="1", title="Top", material_text="95% Polyester, 5% Elastane"),
        0,
        load_catalog(tmp_path),
    )
    assert result.item_id == "1"
    assert result.brand.max == 34
    assert result.material.max == 33
