"""Turn Amazon's raw fabric text into fiber percentages.

    parse_materials("60% Cotton, 40% Polyester")  ->  {"cotton": 60, "polyester": 40}

This only reads the text. It doesn't know which fibers exist; matching names like
"elastane" to a catalog entry happens later, in scoring, using the aliases in
backend/data/materials.json. Text with no percentages ("Cotton Blend") returns None,
and the LLM handles those cases later.
"""

import re

# Labels Amazon uses for the parts of a garment. The first group is the main fabric.
_MAIN_LABELS = ["outer shell", "shell", "outer", "body", "main", "self", "fabric"]
_OTHER_LABELS = [
    "pocket lining", "lining", "trim", "rib", "ribbing", "contrast", "filling", "fill",
    "insulation", "lace", "mesh", "waistband", "sleeves", "sleeve", "hood lining",
]
_LABEL_RE = re.compile(
    r"\b(" + "|".join(sorted(_MAIN_LABELS + _OTHER_LABELS, key=len, reverse=True)) + r")\s*:",
)

_NUM = r"(\d+(?:\.\d+)?)"
# "60% cotton"  (name stops at a digit or a separator)
_FORWARD_RE = re.compile(_NUM + r"\s*%\s*([a-z][a-z\s\-']*)")
# "cotton 60%"
_REVERSE_RE = re.compile(r"([a-z][a-z\s\-']*?)\s*" + _NUM + r"\s*%")

# Words that appear next to fiber names but aren't part of them.
_FILLER_WORDS = {"fabric", "fiber", "fibers", "fibre", "fibres", "material", "materials", "of", "and", "with"}
# Amazon noise that isn't about materials at all.
_NOISE_RE = re.compile(r"\b(imported|made in [a-z ]+|machine wash[a-z ]*|hand wash[a-z ]*)\b")


def parse_materials(text: str | None) -> dict[str, float] | None:
    """Return {fiber: percent} for the garment's main fabric, or None if there are no percentages."""
    if not text:
        return None

    cleaned = _normalize(text)
    section = _main_section(cleaned)
    pairs = _find_pairs(section)
    if not pairs:
        return None

    return _first_full_composition(pairs)


def _normalize(text: str) -> str:
    text = text.lower().replace("％", "%").replace(" ", " ")
    text = _NOISE_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _main_section(text: str) -> str:
    """Pick the main-fabric part of multi-part text like 'Shell: ...; Lining: ...'."""
    matches = list(_LABEL_RE.finditer(text))
    if not matches:
        return text

    sections: list[tuple[str, str]] = []
    before_first_label = text[: matches[0].start()]
    if _find_pairs(before_first_label):
        sections.append(("", before_first_label))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((m.group(1), text[m.end():end]))

    for label in _MAIN_LABELS:
        for name, body in sections:
            if name == label and _find_pairs(body):
                return body
    # Unlabeled text first, then any section with percentages.
    for name, body in sections:
        if name not in _OTHER_LABELS and _find_pairs(body):
            return body
    for _, body in sections:
        if _find_pairs(body):
            return body
    return text


def _find_pairs(text: str) -> list[tuple[str, float]]:
    pairs = [(_clean_name(name), float(num)) for num, name in _FORWARD_RE.findall(text)]
    pairs = [(n, p) for n, p in pairs if n]
    if not pairs:
        pairs = [(_clean_name(name), float(num)) for name, num in _REVERSE_RE.findall(text)]
        pairs = [(n, p) for n, p in pairs if n]
    return pairs


def _clean_name(name: str) -> str:
    # "cotton and " -> "cotton";  "polyester fabric" -> "polyester"
    name = re.split(r"\band\b|\bwith\b", name)[0]
    words = [w.strip("-'") for w in name.split()]
    words = [w for w in words if w and w not in _FILLER_WORDS]
    return " ".join(words)


def _first_full_composition(pairs: list[tuple[str, float]]) -> dict[str, float]:
    """Add fibers in order until they reach ~100%.

    Handles unlabeled multi-part text like '100% Cotton; 100% Polyester', where
    the first part is almost always the main fabric.
    """
    result: dict[str, float] = {}
    total = 0.0
    for name, pct in pairs:
        if total >= 99.5:
            break
        result[name] = result.get(name, 0) + pct
        total += pct
    return {name: _tidy(pct) for name, pct in result.items()}


def _tidy(pct: float) -> float:
    return int(pct) if pct == int(pct) else pct
