from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

HOODIE = {
    "item_id": "B0HOODIE01",
    "title": "Oversized Hoodie, Sage Green",
    "brand": "Example Brand",
    "price": 49.99,
    "material_text": "60% Cotton, 40% Polyester",
}
JEANS = {"item_id": "B0JEANS002", "title": "Straight Leg Jeans"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_score_returns_one_result_per_item_in_order():
    res = client.post("/score", json={"items": [HOODIE, JEANS]})
    assert res.status_code == 200
    body = res.json()
    assert [i["item_id"] for i in body["items"]] == ["B0HOODIE01", "B0JEANS002"]
    assert body["cart"]["item_count"] == 2
    for item in body["items"]:
        assert 0 <= item["total"] <= 100
        assert item["brand"]["max"] == 34 and item["material"]["max"] == 33


def test_same_item_gets_same_score():
    a = client.post("/score", json={"items": [HOODIE]}).json()
    b = client.post("/score", json={"items": [HOODIE]}).json()
    assert a == b


def test_only_title_and_id_are_required():
    assert client.post("/score", json={"items": [JEANS]}).status_code == 200


def test_empty_cart_is_rejected():
    assert client.post("/score", json={"items": []}).status_code == 422


def test_cors_allows_extension_origin():
    res = client.options(
        "/score",
        headers={
            "Origin": "chrome-extension://abcdefghijklmnop",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "chrome-extension://abcdefghijklmnop"
