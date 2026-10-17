from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ScoreRequest, ScoreResponse
from .scoring import mock_item_score, summarize_cart

app = FastAPI(title="Thred backend")

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
    """Score every item in a cart. Placeholder scores until step 3 (real scoring) lands."""
    items = [mock_item_score(item, i) for i, item in enumerate(req.items)]
    return ScoreResponse(items=items, cart=summarize_cart(items), mock=True)
