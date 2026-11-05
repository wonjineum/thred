""" python -m ml.test_llm """ 

from .llm_helpers import classify_unknown_brand

domains = [
    "patagonia.com",
    "shein.com",
    "nike.com",
    "unknownbrand12345.com",
]

for domain in domains:
    rating = classify_unknown_brand(domain)
    print(f"{domain} -> {rating}")