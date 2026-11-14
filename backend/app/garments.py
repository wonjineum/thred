"""Figure out what kind of garment an item is, from a fixed list.

Alternatives are only suggested within the same garment type, so the Amazon item
and every listing in alternatives.json must use these exact names.
"""

import re

GARMENT_TYPES = [
    "t-shirt", "shirt", "sweater", "hoodie", "jacket", "dress", "skirt",
    "jeans", "pants", "shorts", "leggings", "shoes", "bag",
]

# Words that show up in titles -> garment type. Plurals are handled automatically.
_KEYWORDS = {
    "t-shirt": ["t-shirt", "tshirt", "tee", "tank top", "tank", "camisole", "crop top"],
    "shirt": ["shirt", "blouse", "button-down", "button down", "polo", "henley", "flannel"],
    "sweater": ["sweater", "cardigan", "pullover", "jumper", "knit top", "turtleneck"],
    "hoodie": ["hoodie", "hooded sweatshirt", "sweatshirt", "crewneck sweatshirt", "zip-up", "fleece"],
    "jacket": ["jacket", "coat", "parka", "puffer", "blazer", "windbreaker", "vest", "anorak", "raincoat"],
    "dress": ["dress", "jumpsuit", "romper"],
    "skirt": ["skirt"],
    "jeans": ["jeans", "jean", "denim pant"],
    "pants": ["pants", "pant", "trousers", "trouser", "chinos", "chino", "joggers", "jogger", "sweatpants", "cargo pant"],
    "shorts": ["shorts", "short"],
    "leggings": ["leggings", "legging", "tights", "yoga pant"],
    "shoes": ["shoes", "shoe", "sneakers", "sneaker", "boots", "boot", "sandals", "sandal", "loafers", "heels", "slippers"],
    "bag": ["bag", "backpack", "tote", "purse", "handbag", "crossbody"],
}

_PATTERNS = [
    (garment, re.compile(r"(?<![a-z])" + re.escape(word) + r"s?(?![a-z])"))
    for garment, words in _KEYWORDS.items()
    for word in words
]


def garment_type_from_text(*texts: str | None) -> str | None:
    """The garment type named in the text, or None.

    Product titles usually put the garment noun last ("Women's Stretch Pant",
    "Denim Jacket"), so when several words match, the one that appears last wins.
    Each text is tried in order: pass the most reliable one (the title) first.
    """
    for text in texts:
        if not text:
            continue
        lowered = text.lower()
        # Amazon titles put size/color after the first comma; look before it first.
        for part in (lowered.split(",")[0], lowered):
            found = _last_match(part)
            if found:
                return found
    return None


def _last_match(text: str) -> str | None:
    best: tuple[int, int, str] | None = None  # (end position, length, garment)
    for garment, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            candidate = (m.end(), m.end() - m.start(), garment)
            if best is None or candidate > best:
                best = candidate
    return best[2] if best else None
