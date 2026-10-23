import os
from dotenv import load_dotenv
from transformers import CLIPModel, CLIPProcessor

load_dotenv()

CLIP_MODEL = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")

model = CLIPModel.from_pretrained(CLIP_MODEL)
processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
model.eval()  # inference mode, nothing gets trained