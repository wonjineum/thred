"""API contract between the extension and the backend.

The extension sends the items in an Amazon cart; the backend sends back a score
for each item plus a summary for the whole cart. Keep this file and
backend/README.md in sync — the extension is built against them.
"""

from enum import Enum

from pydantic import BaseModel, Field


# ---------- Request (what the extension sends) ----------

class CartItem(BaseModel):
    item_id: str = Field(description="Amazon ASIN, or any ID unique within the cart")
    title: str
    brand: str | None = None
    price: float | None = Field(default=None, ge=0)
    image_url: str | None = None
    product_url: str | None = None
    material_text: str | None = Field(
        default=None,
        description="Raw material text from the product page, e.g. '60% Cotton, 40% Polyester'",
    )
    category: str | None = Field(default=None, description="Most specific breadcrumb level, e.g. 'Hoodies'")
    certifications: list[str] = Field(
        default_factory=list,
        description="Certifications from the product's Climate Pledge Friendly badge, e.g. ['GOTS']",
    )


class ScoreRequest(BaseModel):
    items: list[CartItem] = Field(min_length=1, max_length=50)


# ---------- Response (what the extension gets back) ----------

class Verdict(str, Enum):
    good_choice = "good_choice"
    okay = "okay"
    consider_alternatives = "consider_alternatives"


VERDICT_LABELS = {
    Verdict.good_choice: "Good choice",
    Verdict.okay: "Okay",
    Verdict.consider_alternatives: "Consider alternatives",
}


class Component(BaseModel):
    points: int
    max: int
    summary: str = Field(description="Short phrase shown in the panel, e.g. 'Mostly organic cotton'")


class ItemScore(BaseModel):
    item_id: str
    total: int = Field(ge=0, le=100)
    verdict: Verdict
    verdict_label: str
    impact: str = Field(description="One plain-language impact line for the badge")
    brand: Component
    material: Component
    # Purchase/wardrobe history is stored locally in the extension, so the
    # extension computes that part itself. It is not part of this response.


class CartSummary(BaseModel):
    item_count: int
    average_total: int
    verdict: Verdict
    verdict_label: str
    headline: str


class ScoreResponse(BaseModel):
    items: list[ItemScore]
    cart: CartSummary
    mock: bool = Field(description="True while the backend returns placeholder scores")
