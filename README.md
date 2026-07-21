# PokerPete

A local-first study tool for heads-up No-Limit Hold'em cash game players:
range work, equity calculation, preflop solving, postflop analysis, hand
history review, and a trainer/quiz mode.

See [`docs/architecture.md`](docs/architecture.md) for the full architecture,
schema, and phased roadmap.

## Development

Requirements: [`uv`](https://docs.astral.sh/uv/) (Python) and Node.js.

```sh
./scripts/dev.sh
```

This boots the backend (FastAPI, http://localhost:8000) and frontend (Vite,
http://localhost:5173) together. Data is stored locally in
`~/.pokerpete/pokerpete.db` (SQLite).

### Backend only

```sh
cd backend
uv run alembic upgrade head   # apply migrations
uv run uvicorn pokerpete.main:app --reload --port 8000
uv run pytest                 # tests
uv run ruff check .           # lint
```

### Frontend only

```sh
cd frontend
npm run dev                   # dev server
npm run build                 # typecheck + build
npm run lint                  # lint
npm run gen:api                # regenerate API types from the running backend
```
