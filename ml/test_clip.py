"""Quick manual tests for the CLIP helpers. Run from the REPO ROOT (the folder that contains ml/):
 
    python -m ml.test_clip                       # built-in sanity checks, no photos needed
    python -m ml.test_clip a.jpg b.jpg           # tag a.jpg, then compare a.jpg with b.jpg
 
The first run downloads the CLIP weights, so it can take a minute. Later runs are faster.
"""
import argparse
import json
 
from PIL import Image
 
from .clip_helpers import image_similarity, tag_image
 
# Labels to choose from when tagging a garment photo. Keep "other" so CLIP has an escape hatch.
GARMENTS = ["t-shirt", "hoodie", "dress", "jeans", "jacket", "shoes", "bag", "other"]
 
 
def sanity_checks():
    """Checks that don't need any photos: we make tiny solid-color images ourselves."""
    red = Image.new("RGB", (224, 224), (220, 30, 30))
    blue = Image.new("RGB", (224, 224), (30, 30, 220))
 
    # 1. An image compared with itself should be (almost exactly) 1.0.
    same = image_similarity(red, red)
    diff = image_similarity(red, blue)
    print(f"similarity red vs red : {same:.4f}  (expect ~1.0)")
    print(f"similarity red vs blue: {diff:.4f}  (expect lower than red vs red)")
    assert same > 0.99, "an image should match itself"
    assert diff < same, "different images should score lower than identical ones"
 
    # 2. Tag scores are probabilities, so they must add up to 1.
    result = tag_image(red, ["red", "blue", "green"])
    print(f"tag a red square      : {result['best']}  {result['scores']}  (expect 'red', not guaranteed)")
    assert abs(sum(result["scores"].values()) - 1) < 1e-4, "scores should sum to 1"
    print("sanity checks passed")
 
 
def try_photos(paths):
    """Tag the first photo with garment labels; if a second is given, compare the two."""
    result = tag_image(paths[0], GARMENTS)
    top = sorted(result["scores"].items(), key=lambda kv: -kv[1])[:3]
    print(f"{paths[0]} -> best: {result['best']}   top 3: {[(k, round(v, 3)) for k, v in top]}")
    if len(paths) > 1:
        print(f"similarity {paths[0]} vs {paths[1]}: {image_similarity(paths[0], paths[1]):.4f}")
 
 
def try_samples(path, limit):
    """Tag the scraped products' image_url and print it next to the product title."""
    data = json.load(open(path, encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    for item in [i for i in items if i.get("image_url")][:limit]:
        try:
            result = tag_image(item["image_url"], GARMENTS)
            print(f"{item['title'][:55]:55} -> {result['best']} ({result['scores'][result['best']]:.2f})")
        except Exception as e:  # one bad image URL shouldn't stop the rest
            print(f"{item['title'][:55]:55} -> FAILED: {e}")
 
 
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("photos", nargs="*", help="one or two image files or URLs")
    ap.add_argument("--samples", help="path to amazon_samples.json")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()
 
    if args.samples:
        try_samples(args.samples, args.limit)
    elif args.photos:
        try_photos(args.photos)
    else:
        sanity_checks()
 