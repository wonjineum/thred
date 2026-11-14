import os

# Tests never call the real LLM or load CLIP. Tests that need them patch
# app.llm_fallback / app.clip_similarity directly.
os.environ["THRED_USE_LLM"] = "0"
os.environ["THRED_USE_CLIP"] = "0"
