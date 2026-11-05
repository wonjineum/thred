
from .llm import client, LLM_MODEL

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
