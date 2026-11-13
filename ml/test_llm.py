
"""
Test LLM helpers for brand classification and material extraction.

Run from project root:
    python -m ml.test_llm
"""

from .llm_helpers import (
    classify_unknown_brand,
    extract_material_composition,
)


def test_brand_classification():
    print("\n=== Brand Classification ===")

    domains = [
        "patagonia.com",
        "shein.com",
        "nike.com",
        "unknownbrand12345.com",
    ]

    valid_ratings = {"Good", "Average", "Bad", "Unknown"}

    for domain in domains:
        rating = classify_unknown_brand(domain)
        print(f"{domain} -> {rating}")

        assert rating in valid_ratings

    print("Brand classification tests passed!")


def test_material_extraction():
    print("\n=== Material Extraction ===")

    products = [
        {
            "material_text": "60% Cotton, 40% Polyester",
            "product_title": "Cotton Blend T-Shirt",
            "product_description": None,
        },
        {
            "material_text": "Sixty percent cotton and forty percent polyester",
            "product_title": "Everyday T-Shirt",
            "product_description": None,
        },
        {
            "material_text": None,
            "product_title": "100% Organic Cotton Hoodie",
            "product_description": None,
        },
        {
            "material_text": None,
            "product_title": "Women's Hoodie",
            "product_description": "Made with 80% cotton and 20% recycled polyester.",
        },
        {
            "material_text": "Cotton Blend",
            "product_title": "Casual Cotton Blend Hoodie",
            "product_description": None,
        },
        {
            "material_text": None,
            "product_title": "Black Hoodie",
            "product_description": None,
        },
        {
            "material_text": None,
            "product_title": None,
            "product_description": None,
        },
    ]

    for product in products:
        result = extract_material_composition(**product)

        print(f"\nProduct: {product['product_title']}")
        print(f"Material text: {product['material_text']}")
        print(f"Description: {product['product_description']}")
        print(f"Extracted: {result}")

        assert result is None or isinstance(result, dict)

        if result is not None:
            assert all(
                isinstance(name, str) and name == name.lower()
                for name in result
            )

            assert all(
                isinstance(percent, (int, float))
                and not isinstance(percent, bool)
                and 0 <= percent <= 100
                for percent in result.values()
            )

            assert sum(result.values()) <= 100.000001

    print("\nMaterial extraction tests passed!")


if __name__ == "__main__":
    test_brand_classification()
    test_material_extraction()
