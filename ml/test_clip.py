import torch
from PIL import Image
from clip_model import model, processor, CLIP_MODEL

image = Image.new("RGB", (224, 224), "black")
inputs = processor(images=image, return_tensors="pt")

with torch.no_grad():
    vision_out = model.vision_model(pixel_values=inputs["pixel_values"])
    emb = model.visual_projection(vision_out.pooler_output)

print("Model:", CLIP_MODEL)
print("Embedding shape:", emb.shape)