# Thred

A browser extension that scores clothing sustainability at the point of purchase, factoring in brand practices, material composition, and your own purchase/wardrobe history.

## Repo layout

```
thred/
├── extension/   Chrome extension (Manifest V3, TypeScript, React, Tailwind)
├── backend/     FastAPI service (brand/material scoring, CNN + CLIP inference)
├── ml/          Model training scripts, notebooks, saved weights
└── docs/        Research, problem statement, roadmap
```

## Getting started

Each folder has its own README with setup instructions once that piece is built out. See `docs/` for the project background, scoring model, and roadmap.

## Team workflow

- `main` stays stable and working.
- Branch per task: `yourname/short-description` (e.g. `alex/cnn-training`).
- Open a PR into `main` when a piece works. Don't push directly to `main`.
- Keep commits small and scoped to one thing at a time.

## Current phase

See `docs/roadmap.md` for the full plan. We're starting frontend-first: extension skeleton and score badge UI with mocked data, before wiring up the real backend/ML pipeline.
