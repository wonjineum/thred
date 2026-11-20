import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from tests.scrape_amazon import fetch, parse_product


from .alternatives import AlternativesError, find_alternatives, load_index
from .schemas import AlternativesRequest, AlternativesResponse, CartItem, ItemScore, ScoreRequest, ScoreResponse
from .catalog import load_catalog
from .scoring import score_item, summarize_cart

app = FastAPI(title="Thred backend")
CATALOG = load_catalog()

# The extension should call the API from background.js (with the backend URL in
# the manifest's host_permissions), which skips CORS. This also allows calls from
# extension pages and the local dashboard during development.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://[a-z]+|http://localhost(:\d+)?)$",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    """Score every item in a cart: brand + material from the catalog, LLM fallback."""
    items = [
        _with_alternatives(score_item(item, i, CATALOG), item)
        for i, item in enumerate(req.items)
    ]
    return ScoreResponse(items=items, cart=summarize_cart(items), mock=False)


log = logging.getLogger("thred")


def _with_alternatives(scored: ItemScore, item: CartItem) -> ItemScore:
    """Attach up to 3 alternatives. Never lets an alternatives problem break scoring."""
    try:
        found = find_alternatives(item, CATALOG, load_index(CATALOG))
    except (AlternativesError, Exception):  # noqa: BLE001 - scoring must still return
        log.exception("Alternatives failed for %s; returning the score without them", item.item_id)
        return scored
    return scored.model_copy(update={"alternatives": found.alternatives})


@app.post("/alternatives", response_model=AlternativesResponse)
def alternatives(req: AlternativesRequest) -> AlternativesResponse:
    """Up to `limit` lower-impact alternatives for one cart item."""
    return find_alternatives(req.item, CATALOG, load_index(CATALOG), limit=req.limit)



class AmazonCartRequest(BaseModel):
    asins: list[str]



@app.post("/scrape/amazon")
def scrape_amazon_cart(request: AmazonCartRequest):
    products = []

    for asin in request.asins:
        html = fetch(asin)

        if not html:
            continue

        product = parse_product(html, asin)
        products.append(product)

    return {"products": products}


class AmazonHTMLRequest(BaseModel):
    asin: str
    html: str


@app.post("/scrape/amazon-html")
def scrape_amazon_html(request: AmazonHTMLRequest):
    product = parse_product(request.html, request.asin)
    return {"product": product}
