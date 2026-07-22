from fastapi import FastAPI

app = FastAPI(title="Thred backend")


@app.get("/health")
def health():
    return {"status": "ok"}


# Phase 3: implement real logic
@app.get("/brand-score")
def brand_score(domain: str):
    """Look up a brand's tier/score by domain. Curated list first, LLM fallback for unknown domains."""
    return {"domain": domain, "tier": "unknown", "score": 17}


@app.post("/material-score")
def material_score(composition: dict):
    """Score a material composition dict, e.g. {'cotton': 60, 'polyester': 40}."""
    return {"score": 0}


@app.post("/classify-image")
def classify_image():
    """Run the trained CNN (type) and CLIP (embedding) on a product image."""
    return {"type": None, "embedding": None}
