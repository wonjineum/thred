# ml

Training scripts and notebooks. This is where the CNN gets trained and CLIP gets tested — separate from `backend/`, which only loads the final saved weights and serves inference.

- `notebooks/` — exploration, training runs
- `weights/` — saved model weights (`.pt` files are gitignored — see root `.gitignore`; use Git LFS or share weights separately if they get large)

## Phase 1 tasks
- Train a small CNN on Fashion MNIST for garment type classification, save weights to `weights/`
- Load a pretrained CLIP checkpoint (`open_clip_torch`, ViT-B/32 to start), test cosine similarity on a handful of real product photos to confirm it behaves as expected before wiring into the backend
