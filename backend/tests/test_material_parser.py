import pytest

from app.material_parser import parse_materials


@pytest.mark.parametrize(
    "text, expected",
    [
        # Simple
        ("100% Cotton", {"cotton": 100}),
        ("100% cotton", {"cotton": 100}),
        ("60% Cotton, 40% Polyester", {"cotton": 60, "polyester": 40}),
        # Different separators and spacing
        ("95% Cotton/5% Spandex", {"cotton": 95, "spandex": 5}),
        ("95%Cotton 5%Spandex", {"cotton": 95, "spandex": 5}),
        ("80% Cotton; 20% Polyester", {"cotton": 80, "polyester": 20}),
        ("60% cotton and 40% polyester", {"cotton": 60, "polyester": 40}),
        ("52% Cotton | 48% Polyester", {"cotton": 52, "polyester": 48}),
        # Multi-word fibers keep their full name
        ("100% Recycled Polyester", {"recycled polyester": 100}),
        ("70% Organic Cotton, 30% Recycled Polyester", {"organic cotton": 70, "recycled polyester": 30}),
        # Name before the number
        ("Cotton 60%, Polyester 40%", {"cotton": 60, "polyester": 40}),
        # Decimals
        ("57.5% Cotton, 42.5% Polyester", {"cotton": 57.5, "polyester": 42.5}),
        # Filler words get dropped
        ("100% Polyester Fabric", {"polyester": 100}),
        # Amazon noise around the materials
        ("100% Cotton, Imported", {"cotton": 100}),
        ("100% Cotton Machine Wash", {"cotton": 100}),
        ("Fabric Type: 100% Cotton", {"cotton": 100}),
        ("100 % Cotton", {"cotton": 100}),
    ],
)
def test_parses_common_formats(text, expected):
    assert parse_materials(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        # Labeled parts: use the main fabric, not the lining or trim
        ("Shell: 100% Nylon; Lining: 100% Polyester", {"nylon": 100}),
        ("Lining: 100% Polyester; Shell: 100% Nylon", {"nylon": 100}),
        ("Body: 100% Cotton; Rib: 98% Cotton, 2% Spandex", {"cotton": 100}),
        ("Outer Shell: 100% Polyester, Filling: 100% Polyester", {"polyester": 100}),
        # Unlabeled main part, then a labeled extra
        ("60% Cotton, 40% Polyester; Pocket Lining: 100% Cotton", {"cotton": 60, "polyester": 40}),
        # Unlabeled multiple parts: first one is the main fabric
        ("100% Cotton; 100% Polyester", {"cotton": 100}),
        ("95% Cotton, 5% Spandex; 100% Polyester", {"cotton": 95, "spandex": 5}),
        # Period instead of semicolon between parts
        ("Shell: 100% Polyester. Lining: 100% Nylon", {"polyester": 100}),
        # Label without a colon after the main part
        ("Main: 65% Polyester, 35% Viscose, Lining 100% Polyester", {"polyester": 65, "viscose": 35}),
        # Different fabric per color: uses the first one listed (known limit)
        ("Solid colors: 100% Cotton; Heathers: 60% Cotton, 40% Polyester", {"cotton": 100}),
    ],
)
def test_picks_main_fabric(text, expected):
    assert parse_materials(text) == expected


@pytest.mark.parametrize(
    "text",
    [None, "", "Cotton Blend", "Cotton", "Imported", "Polyester, Spandex"],
)
def test_returns_none_without_percentages(text):
    # No percentages -> None. The LLM handles these later.
    assert parse_materials(text) is None


def test_same_fiber_listed_twice_is_added_up():
    assert parse_materials("50% Cotton, 30% Polyester, 20% Cotton") == {"cotton": 70, "polyester": 30}


def test_partial_composition_is_kept_as_is():
    # Doesn't invent the missing 40%; scoring treats it as unknown.
    assert parse_materials("60% Cotton") == {"cotton": 60}
