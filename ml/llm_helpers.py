
from .llm import client, LLM_MODEL
import json
import math

VALID_RATINGS = {"Good", "Average", "Bad", "Unknown"}


def classify_unknown_brand(domain: str) -> str:
    """Classify a clothing brand's sustainability using its domain."""

    if not domain or not domain.strip():
        return "Unknown"

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You classify clothing brands by their sustainability "
                        "practices. Return exactly one label: "
                        "Good, Average, Bad, or Unknown. "
                        "Use Good for brands with strong, well-supported "
                        "sustainability practices; Average for mixed practices; "
                        "Bad for brands with well-supported poor practices. "
                        "If the brand cannot be identified or reliable "
                        "information is insufficient, return Unknown. "
                        "Do not guess or include explanations."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Classify the clothing brand associated with domain: {domain.strip()}",
                },
            ],
            temperature=0,
            max_tokens=20,
        )

        content = response.choices[0].message.content

        if not content:
            return "Unknown"

        rating = content.strip().title()

        return rating if rating in VALID_RATINGS else "Unknown"

    except Exception:
        return "Unknown"




def extract_material_composition(
    material_text: str | None,
    product_title: str | None = None,
    product_description: str | None = None,
) -> dict[str, float] | None:
    """
    LLM fallback for material composition extraction.

    Inputs:
        material_text: Raw material information from the scraper.
        product_title: Product title (optional).
        product_description: Product description (optional).

    Returns:
        {"cotton": 60, "polyester": 40}
        None if exact percentages cannot be determined.

    Only call when the existing material parser returns None.
    """

    if not any(
        isinstance(value, str) and value.strip()
        for value in (material_text, product_title, product_description)
    ):
        return None

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract clothing material composition from "
                        "product information. "
                        "Use the material text, product title, and description "
                        "to identify the garment's MAIN fabric composition. "
                        "Return ONLY a JSON object mapping lowercase material "
                        "names to numeric percentages. "
                        'Example: {"cotton": 60, "polyester": 40}. '
                        "Only use percentages explicitly supported by the "
                        "provided information. Never guess percentages. "
                        "Do not confuse lining, trim, or filling with the "
                        "main fabric. "
                        "If the main fabric composition cannot be determined "
                        "without guessing, return null. "
                        "Do not include explanations or markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Material text: {material_text or 'Not available'}\n"
                        f"Product title: {product_title or 'Not available'}\n"
                        f"Product description: "
                        f"{product_description or 'Not available'}"
                    ),
                },
            ],
            temperature=0,
            max_tokens=200,
        )

        content = response.choices[0].message.content

        if not content:
            return None

        materials = json.loads(content.strip())

        if not isinstance(materials, dict) or not materials:
            return None

        cleaned = {}

        for material, percentage in materials.items():
            if not isinstance(material, str):
                return None

            name = material.strip().lower()

            if not name:
                return None

            if (
                isinstance(percentage, bool)
                or not isinstance(percentage, (int, float))
                or not math.isfinite(percentage)
                or not 0 <= percentage <= 100
            ):
                return None

            if name in cleaned:
                return None

            cleaned[name] = percentage

        if sum(cleaned.values()) > 100.000001:
            return None

        return cleaned

    except Exception:
        return None
