
"""
python -m ml.test_recommendation

Test the 3-NN recommendation helper.

Tests:
- Same-category filtering
- Higher sustainability score requirement
- Price filtering
- Cosine similarity ranking
- Top 3 recommendations
- No eligible alternatives

Run from project root:
    python -m ml.test_recommendation
"""

from .recommendation_helpers import recommend_alternatives


# Mock cosine similarity (no CLIP needed)
def mock_similarity(embedding_a, embedding_b):
    return sum(a * b for a, b in zip(embedding_a, embedding_b))


# Original product
product = {
    "item_id": "original_001",
    "title": "Black Hoodie",
    "category": "hoodie",
    "price": 40.0,
    "sustainability_score": 35,
    "embedding": [1.0, 0.0],
}


# Curated alternatives
alternatives = [
    {
        "item_id": "alt_001",
        "title": "Organic Cotton Hoodie",
        "category": "hoodie",
        "price": 45.0,
        "sustainability_score": 85,
        "embedding": [0.95, 0.3122499],
    },
    {
        "item_id": "alt_002",
        "title": "Recycled Hoodie",
        "category": "hoodie",
        "price": 50.0,
        "sustainability_score": 75,
        "embedding": [0.90, 0.4358899],
    },
    {
        "item_id": "alt_003",
        "title": "Sustainable Hoodie",
        "category": "hoodie",
        "price": 38.0,
        "sustainability_score": 65,
        "embedding": [0.85, 0.5267827],
    },
    {
        "item_id": "alt_004",
        "title": "Eco Hoodie",
        "category": "hoodie",
        "price": 55.0,
        "sustainability_score": 90,
        "embedding": [0.80, 0.60],
    },
    {
        "item_id": "alt_005",
        "title": "Sustainable Jeans",
        "category": "jeans",
        "price": 35.0,
        "sustainability_score": 95,
        "embedding": [0.99, 0.1410674],
    },
    {
        "item_id": "alt_006",
        "title": "Expensive Hoodie",
        "category": "hoodie",
        "price": 100.0,
        "sustainability_score": 95,
        "embedding": [0.99, 0.1410674],
    },
    {
        "item_id": "alt_007",
        "title": "Low Score Hoodie",
        "category": "hoodie",
        "price": 30.0,
        "sustainability_score": 20,
        "embedding": [0.98, 0.1989975],
    },
]


def test_recommendations():
    results = recommend_alternatives(
        product=product,
        alternatives=alternatives,
        similarity_fn=mock_similarity,
    )

    print("\n=== Recommendation Results ===")

    for i, item in enumerate(results, start=1):
        print(
            f"{i}. {item['title']} | "
            f"Price: ${item['price']:.2f} | "
            f"Sustainability: {item['sustainability_score']} | "
            f"Similarity: {item['similarity']:.3f} | "
            f"Ranking: {item['ranking_score']:.3f}"
        )

    # Top 3 returned
    assert len(results) == 3

    # Sorted by ranking score
    assert all(
        results[i]["ranking_score"] >= results[i + 1]["ranking_score"]
        for i in range(len(results) - 1)
    )

    # All recommendations satisfy filtering rules
    for item in results:
        assert item["category"] == product["category"]
        assert item["sustainability_score"] > product["sustainability_score"]
        assert item["price"] <= product["price"] * 1.5

    # Invalid alternatives excluded
    excluded_ids = {"alt_005", "alt_006", "alt_007"}

    assert all(
        item["item_id"] not in excluded_ids
        for item in results
    )

    print("\nAll recommendation tests passed!")


def test_no_matches():
    results = recommend_alternatives(
        product=product,
        alternatives=[],
        similarity_fn=mock_similarity,
    )

    assert results == []
    print("Empty alternatives test passed!")


if __name__ == "__main__":
    test_recommendations()
    test_no_matches()
