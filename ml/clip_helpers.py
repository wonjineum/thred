"""CLIP helpers: tag a photo with the best-fitting label, and compare two photos.
 
HOW CLIP WORKS (the one idea behind both functions)
    CLIP was trained on hundreds of millions of (image, caption) pairs. It learned to turn
    an image OR a piece of text into a list of numbers (an "embedding", or vector) so that
    a photo and a caption that describe the same thing land close together in the same
    "space". That gives us two tricks with no extra training:
      - tag_image:        compare one photo's vector to the vectors of several text labels
                          and see which label is closest.
      - image_similarity: compare two photos' vectors; the closer they are, the more alike.
 
The model itself is loaded in clip_init.py (once, when that file is first imported), and this
file reuses it. Keeping loading separate means there is only one copy of the model in memory.
 
Needs: torch, pillow, requests (plus transformers and python-dotenv for clip_init.py).
 
An "image" argument can be a PIL image, raw bytes, a local file path, or an http(s) URL
(so you can pass the image_url from the scraper straight in).
"""
import io
from pathlib import Path
 
import requests
import torch
from PIL import Image
 
# The already-loaded model and processor from clip_init.py (no second download or second copy).
# model:     the neural network. processor: turns raw images/text into what the model expects
#            (for images it resizes and normalizes pixels the way CLIP was trained; for text
#            it splits words into tokens).
from .clip_model import model, processor
 
 
def _open(image) -> Image.Image:
    """Turn whatever we were given (PIL image, bytes, URL, or file path) into an RGB PIL image.
    Why: the rest of the code only wants one type of input, and callers have several (the
    scraper gives a URL, the extension may send bytes, tests use files). Doing the conversion
    in one place keeps every other function simple.
    Why convert("RGB"): CLIP expects 3 color channels, but PNGs can have transparency (RGBA),
    and some images are grayscale; converting avoids a shape error and gives consistent input.
    """
    if isinstance(image, Image.Image):  # already an image object
        return image.convert("RGB")
    if isinstance(image, (bytes, bytearray)):  # raw file contents, e.g. an upload
        return Image.open(io.BytesIO(image)).convert("RGB")
    if isinstance(image, str) and image.startswith(("http://", "https://")):  # a web address
        resp = requests.get(image, timeout=15)  # timeout so a dead link can't hang the server
        resp.raise_for_status()  # raise a clear error on 404/403 instead of failing later
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    return Image.open(Path(image)).convert("RGB")  # otherwise treat it as a local file path
 
 
def tag_image(image, options: list[str], template: str = "a photo of {}") -> dict:
    """1 photo + a list of text options -> which option fits best.
 
    Returns {"best": "hoodie", "scores": {"hoodie": 0.91, "dress": 0.05, ...}} (scores sum to 1).
    Scores are relative to your list: include an "other" option if none might fit.
 
    Why it works: this is "zero-shot" classification. CLIP already knows how to match images
    to text, so we never train a classifier. We just describe each possible label in words,
    and CLIP tells us which description the photo is closest to.
    """
    # Wrap each label in a sentence ("a photo of hoodie"). CLIP learned from captions, which are
    # sentences, so this phrasing matches its training and is usually more accurate than a
    # bare word like "hoodie".
    # The processor tokenizes the text and resizes/normalizes the image in one step.
    # padding=True makes all the labels the same length so they can be processed together.
    inputs = processor(
        text=[template.format(o) for o in options],
        images=_open(image),
        return_tensors="pt",  # return PyTorch tensors, which the model needs
        padding=True,
    )
    # no_grad: we only need the answer, not the data used for training, so skipping gradient
    # tracking saves memory and time.
    with torch.no_grad():
        # logits_per_image = how well the photo matches each label (higher means closer),
        # scaled by a value CLIP learned during training. softmax converts those raw scores
        # into probabilities that add up to 1, so 0.91 reads as "91% of the match goes here".
        probs = model(**inputs).logits_per_image.softmax(dim=1)[0].tolist()
    scores = dict(zip(options, probs))  # pair each label with its probability
    return {"best": max(scores, key=scores.get), "scores": scores}  # best = highest probability
 
 
def _embed_image(image):
    """Turn one photo into a single unit-length vector that describes what it looks like.
 
    Why unit length: if every vector has length 1, comparing two of them with a dot product
    gives exactly their cosine similarity (the angle between them). That compares what the
    images look like, not how bright or large the raw numbers happen to be.
    """
    # Only the image side: resize/normalize into a tensor of pixel values.
    pixel_values = processor(images=_open(image), return_tensors="pt")["pixel_values"]
    with torch.no_grad():  # inference only, no gradient tracking
        # vision_model reads the pixels; pooler_output is one vector summarizing the whole image.
        pooled = model.vision_model(pixel_values=pixel_values).pooler_output
        # visual_projection maps that vector into the shared image-and-text space. This is the
        # step that makes the numbers comparable with CLIP's text vectors.
        feats = model.visual_projection(pooled)
    return feats / feats.norm(dim=-1, keepdim=True)  # divide by its length -> length exactly 1
 
 
def image_similarity(image_a, image_b) -> float:
    """2 photos -> similarity from -1 to 1 (closer to 1 means more alike).
 
    Why it works: both photos become unit-length vectors in the same space. The dot product of
    two unit vectors is the cosine of the angle between them: 1.0 means pointing the same way
    (looks the same), near 0 means unrelated, negative means opposite.
    Use for the duplicate check: the same item photographed twice scores very close to 1.
    Choose the cutoff for "duplicate" by testing on pairs you know are the same or different;
    don't guess a number.
    """
    # (1 x N) @ (N x 1) = a single 1x1 value; .item() pulls out the plain number; float() makes
    # it a normal Python float so FastAPI/JSON can return it.
    return float((_embed_image(image_a) @ _embed_image(image_b).T).item())