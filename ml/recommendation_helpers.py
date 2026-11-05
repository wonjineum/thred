
from typing import Callable
"""
Recommendation System Helper (3-NN)

Takes in:
- Original product: embedding, category, price, sustainability score.
- Curated alternatives: list of products with the same information.
- similarity_fn: existing cosine similarity function from clip_helpers.py.

How it works:
1. Filter alternatives by matching category, higher sustainability
   score, and reasonable price (max 1.5x original price).
2. Use similarity_fn(original_embedding, alternative_embedding)
   to calculate cosine similarity for each eligible alternative.
3. Rank using 60% similarity, 30% sustainability, and 10% price.
4. Return the top 3 highest-ranked alternatives.

Example:
    Original: Black hoodie, $40, sustainability score 35

    Alternatives:
    - Hoodie A: $45, score 85, cosine similarity 0.92
    - Hoodie B: $50, score 70, cosine similarity 0.88
    - Jeans C:  $30, score 90, cosine similarity 0.95

    Jeans C is filtered out (wrong category).
    Hoodies A and B are ranked by their combined scores.

Returns:
    List of up to 3 alternative product dictionaries containing
    product metadata, cosine similarity, and final ranking score.
    Returns [] if no alternatives qualify.

Note:
    No CLIP inference, embedding generation, or database calls.
    Embeddings are already computed before this helper runs.
"""

def recommend_alternatives(
    product: dict,
    alternatives: list[dict],
    similarity_fn: Callable,
    top_k: int = 3,
    max_price_multiplier: float = 1.5,
    similarity_weight: float = 0.6,
    sustainability_weight: float = 0.3,
    price_weight: float = 0.1,
) -> list[dict]:
    """
    Rank curated alternatives for a product.

    Assumes:
    - embeddings are already computed
    - alternatives are already fetched from the database
    - sustainability scores range from 0 to 100
    - similarity_fn returns cosine similarity
    """

    if top_k <= 0:
        return []

    if product["price"] < 0:
        raise ValueError("Product price cannot be negative")

    if not 0 <= product["sustainability_score"] <= 100:
        raise ValueError("Invalid sustainability score")

    if max_price_multiplier <= 0:
        raise ValueError("Price multiplier must be positive")

    weights = (
        similarity_weight
        + sustainability_weight
        + price_weight
    )

    if abs(weights - 1.0) > 1e-9:
        raise ValueError("Ranking weights must sum to 1")

    ranked = []

    for item in alternatives:
        # 1. Same category
        if item["category"] != product["category"]:
            continue

        # 2. Higher sustainability score
        score = item["sustainability_score"]

        if not 0 <= score <= 100:
            continue

        if score <= product["sustainability_score"]:
            continue

        # 3. Reasonable price
        price = item["price"]

        if price < 0:
            continue

        if price > product["price"] * max_price_multiplier:
            continue

        # 4. Embedding similarity
        similarity = float(
            similarity_fn(
                product["embedding"],
                item["embedding"],
            )
        )

        # Convert cosine similarity from [-1, 1] to [0, 1]
        normalized_similarity = max(
            0.0, min(1.0, (similarity + 1) / 2)
        )

        # 5. Normalize sustainability
        normalized_sustainability = score / 100

        # 6. Price preference: cheaper is better
        price_score = (
            min(1.0, product["price"] / price)
            if price > 0
            else 1.0
        )

        # 7. Combined ranking
        ranking_score = (
            similarity_weight * normalized_similarity
            + sustainability_weight * normalized_sustainability
            + price_weight * price_score
        )

        ranked.append({
            **item,
            "similarity": similarity,
            "ranking_score": ranking_score,
        })

    # 8. Sort and return top K
    ranked.sort(
        key=lambda item: item["ranking_score"],
        reverse=True,
    )

    return ranked[:top_k]
