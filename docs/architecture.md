# PokerPete — HU NLHE Study Tool: Architecture & Roadmap

## Context

Greenfield project (empty directory). Goal: a professional-grade study tool for
heads-up No-Limit Hold'em cash game players — range work, equity calculation,
preflop solving, postflop analysis, hand history review, and a trainer/quiz
mode with progress tracking. This document is the architecture, schema, module
design, and phased roadmap to review and approve before any code is written.

Confirmed decisions (from user):
- **Stack:** Python backend (FastAPI) + TypeScript/React frontend (Vite).
- **Deployment:** single-user, local-first. No auth/accounts. SQLite. Runs
  entirely on localhost (two dev processes), no cloud dependency.
- **Engine scope:** hybrid — exact preflop solving (push/fold Nash +
  abstracted deeper-stack solve) + Monte Carlo equity + heuristic (not fully
  solved) postflop analysis. Explicitly **not** building a full postflop CFR
  solver — out of scope for now.

This design was reviewed by an architecture-critique pass; its findings
(algorithm choice for push/fold, evaluator library choice, package layout,
cache-key versioning) are incorporated below rather than listed separately.

---

## Product Requirements Analysis

**Primary user:** a HU NLHE cash player studying between sessions.

**Core capabilities, roughly in order of value:**
1. Range construction/editing (13×13 grid, weighted combos, standard notation).
2. Preflop GTO-ish guidance: push/fold at shallow stacks (exact), open/3bet/
   4bet ranges at deeper stacks (abstracted solve).
3. Equity calculation: hand-vs-range, range-vs-range, given a board.
4. Postflop spot analysis: pot odds, bet-sizing EV, range/nut advantage —
   heuristic, grounded in real equity numbers, not a full solve.
5. Hand history import & review, tied back to the above analysis.
6. Trainer/quiz mode with grading and progress tracking over time.

**Explicit non-goals for now:** multi-user/cloud, tournament ICM, full
postflop solver, mobile app.

---

## Architecture Overview

Local client-server, two processes on localhost, no network dependency:

- **Backend:** FastAPI app. Poker logic lives in a framework-free `engine`
  package (unit-testable in isolation, no FastAPI/DB imports). API routes are
  a thin layer translating HTTP ⇄ engine calls. SQLAlchemy + Alembic + SQLite
  for persistence (WAL mode, `PRAGMA foreign_keys=ON`).
- **Frontend:** React + TypeScript + Vite. Server state via React Query;
  local UI state via Zustand/context. **API types are generated from FastAPI's
  OpenAPI schema** (`openapi-typescript`) rather than hand-duplicated — wired
  up in Phase 1 so it's never a manual-sync problem.
- **Hand evaluation:** use an existing C/Cython-accelerated library
  (`eval7`) rather than a hand-rolled evaluator. A naive Python evaluator
  cannot hit interactive speed for range-vs-range Monte Carlo (millions of
  evaluations); a bespoke perfect-hash evaluator is a possible future
  optimization but not needed to start, and eval7 gives us headroom.
- **Preflop solving is two distinct algorithms, not one:**
  - Push/fold (shallow stacks): 2-player shove/call is a small fixed-point
    game solved via iterative best-response / fictitious play over a 169×169
    payoff matrix. This is not a CFR problem — using CFR here would be
    overkill and slower to converge.
  - Deeper-stack open/3bet/4bet/allin trees: abstracted CFR over hand-class
    buckets (169 starting hands, not 1326 combos — this loses blocker
    information for bluff-combo selection, a documented MVP limitation),
    numpy-vectorized regret matching, solved offline/cached per stack-depth
    grid rather than on-demand per request.

---

## Folder Structure

```
PokerPete/
  backend/
    src/
      pokerpete/
        main.py                    # FastAPI app entrypoint
        api/
          routes_ranges.py
          routes_equity.py
          routes_solver.py
          routes_hands.py
          routes_trainer.py
          routes_sessions.py
        engine/                    # framework-free poker logic
          cards.py                 # bitmask Card/Deck/Board primitives
          evaluator.py             # thin wrapper over eval7
          ranges.py                # notation parser + range algebra
          equity.py                # Monte Carlo + exact equity calc
          preflop_equity_matrix.py # offline-built 169x169 all-in equities
          preflop_solver.py        # push/fold FP solver + abstracted CFR
          postflop_heuristics.py   # pot odds, EV, range/nut advantage
          handhistory/
            base.py                # pluggable parser interface
            parsers/
              generic.py
          trainer.py                # spot generation + grading
        db/
          models.py                 # SQLAlchemy models
          session.py
          migrations/                # alembic
        schemas/                     # Pydantic request/response models
          ranges.py
          equity.py
          hands.py
          trainer.py
        core/
          config.py
          exceptions.py
    scripts/
      build_preflop_equity_matrix.py  # offline batch job → data artifact
    tests/
      engine/
        test_evaluator.py
        test_ranges.py
        test_equity.py
        test_preflop_solver.py        # validated vs. published push/fold charts
      api/
    pyproject.toml
    alembic.ini
  frontend/
    src/
      api/                # generated types (openapi-typescript) + client
      components/
        RangeGrid/
        EquityPanel/
        Trainer/
        HandReplayer/
      pages/
      state/
      App.tsx
      main.tsx
    tests/
    package.json
    vite.config.ts
  docs/
    architecture.md        # this document, committed for future reference
  scripts/
    dev.sh                 # boots both servers
  README.md
```

---

## Database Schema (SQLite via SQLAlchemy)

- **`sessions`** — id, started_at, ended_at, mode, notes.
- **`ranges`** — id, name, notation, position, stack_depth, tags, created_at.
  Saved/named ranges only; combos are *derived at runtime* from notation
  (in-process `lru_cache`d), never stored — keeps the DB small and avoids
  derived-data drift.
- **`hands`** — id, source, raw_text, played_at, hero_position, hero_cards,
  board (full run-out string), stakes, pot_size, result.
- **`hand_actions`** — id, hand_id (FK), street, actor, action_type, amount,
  sequence. Board-per-street is reconstructed from `hands.board` + `street`
  at replay time, not duplicated per action.
- **`trainer_spots`** — id, spot_type (preflop/postflop), scenario_json,
  correct_action_json, created_at.
- **`trainer_attempts`** — id, spot_id (FK), session_id (FK), user_action_json,
  correct, ev_loss, attempted_at.
- **`solver_results`** — cache for expensive preflop solves. id, cache_key
  (hash of **`solver_version` + tree_params_json** — versioned so algorithm
  changes don't serve stale results), solver_version, tree_params_json (raw,
  kept for debuggability), result_json, computed_at.

---

## Poker Engine: Module Interactions

1. `ranges.py` parses notation (`"AA-TT, AKs, AQo+, 76s"`) → weighted combo
   set; range algebra (union/intersect/blocker-removal) lives here. Combo
   expansion is `lru_cache`d — it's hit repeatedly by equity/solver/trainer.
2. `equity.py` runs Monte Carlo (or exact enumeration when combo count is
   small, e.g. river) equity between hands/ranges given a board, using
   `evaluator.py` (eval7) per iteration. **Deterministic seeding** so trainer
   grading doesn't flake against re-sampled noise.
3. `preflop_equity_matrix.py` is an **offline, separate concern** from
   solving: batch-computes the 169×169 all-in matchup equity table via
   `equity.py`, serialized as a data artifact by
   `scripts/build_preflop_equity_matrix.py`. Kept separate so
   `preflop_solver.py` can be unit-tested against a small mocked matrix.
4. `preflop_solver.py` consumes that matrix. Push/fold: fictitious
   play/iterative best-response, converges in tens–low-hundreds of
   iterations. Deeper-stack trees: abstracted CFR, numpy-vectorized,
   precomputed per stack-depth grid, results cached in `solver_results`.
   **Validated in tests against published push/fold charts** as ground truth.
5. `postflop_heuristics.py` takes board + ranges + pot/stack, uses
   `equity.py` for range equity, computes pot odds and bet-size EV estimates,
   outputs a recommendation with rationale — explicitly heuristic, not solved.
6. `handhistory/parsers/*.py` parse raw text → structured `Hand`/`HandAction`
   → persisted via `db/models.py`. Pluggable interface (`base.py`) so more
   site formats can be added without touching callers.
7. `trainer.py` generates spots from solver output or imported hand-history
   decision points, grades user actions against solver/heuristic output, logs
   `trainer_attempts`. Caches equity/solver calls rather than recomputing
   per-grade.
8. FastAPI routes are thin translators between HTTP/Pydantic and the engine;
   expensive solves run as background tasks (progress via polling or
   WebSocket), never blocking the request thread.

---

## Phased Roadmap

**Phase 0 — Foundations.** Repo scaffold (backend `src`-layout, frontend
Vite+TS), tooling (uv/poetry, pytest, ruff/black, eslint/prettier), SQLAlchemy
+ Alembic + SQLite base setup, `scripts/dev.sh`.

**Phase 1 — Core primitives.** `cards.py` (bitmask), `evaluator.py` (eval7
wrapper), `ranges.py` (notation parser + algebra + lru_cache), `equity.py`
(Monte Carlo + exact, deterministic seeding). Full unit test coverage against
known-correct hand rankings and published equity benchmarks. Wire up
openapi-typescript codegen even though there's little API yet.

**Phase 2 — Push/fold preflop solver.** `preflop_equity_matrix.py` +
build script; `preflop_solver.py` (fictitious play for shove/call).
Tests validate output against published push/fold charts.

**Phase 3 — First usable vertical slice.** FastAPI routes for
ranges/equity/push-fold solver. React: range grid, equity panel, push/fold
trainer quiz mode with grading. This is the first milestone a user can
actually study with.

**Phase 4 — Deeper-stack preflop.** Abstracted CFR for open/3bet/4bet/allin
trees, numpy-vectorized, precomputed per stack-depth grid, `solver_results`
cache with `solver_version`. Frontend: broaden trainer beyond push/fold.

**Phase 5 — Postflop heuristics.** `postflop_heuristics.py` + frontend
postflop spot viewer (equity + pot odds + bet-size EV + rationale).

**Phase 6 — Hand history import & review.** One well-defined format first,
pluggable parser interface, storage, replayer UI tied to decision-point
analysis from Phases 2–5.

**Phase 7 — Trainer polish.** Leak-weighted spot selection, session stats /
progress dashboard, EV-loss tracking over time.

**Phase 8+ — Stretch.** More HH parsers, larger CFR scope if ever justified,
range export/sharing, desktop packaging (Tauri), optional multi-user mode.

---

## Risks, Assumptions, Dependencies

**Risks**
- 169-hand (not 1326-combo) abstraction in the deeper-stack solver loses
  blocker information for bluff-combo selection — documented limitation, not
  silently accepted.
- **Confirmed (Phase 4), not just anticipated:** the open/3bet/shove tree
  solver's 100%-equity-realization assumption (a plain call is scored as an
  immediate showdown on the pot as it stands, with no postflop skill or
  implied-odds value) makes its equilibria lean heavily toward maximal
  aggression once ahead — verified by hand-checking terminal EVs, not a bug.
  BB's response to an open is very often a shove rather than a smaller
  3bet, and SB's response to a 3bet is very often a shove rather than a
  flat call, well beyond what real HU cash players would do. This is a real
  consequence of not modeling postflop play, not an implementation error;
  the API and frontend surface an explicit caveat on every tree-solver
  response so it's never mistaken for real GTO strategy at these stacks.
- Postflop analysis is heuristic, not a true solve — must be UI-labeled as
  such so it's never mistaken for solver-grade output.
- Hand history parsing is fragile per site format — MVP scopes to one format
  behind a pluggable interface.

**Assumptions**
- Single user, single machine, no auth needed.
- HU NLHE **cash game** focus, not tournament ICM (different solver math) —
  flagged explicitly since it changes push/fold EV calculations.
- eval7 (or equivalent accelerated evaluator) is an acceptable dependency
  rather than a fully bespoke evaluator.

**Dependencies**
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, pytest, numpy, eval7,
  uvicorn.
- Frontend: React, TypeScript, Vite, React Query, openapi-typescript.
- No external services or API keys — fully local.

---

## Verification Approach (once implementation starts)

- Phase 1: `pytest` on evaluator (known hand rankings), range parser
  (notation round-trips), equity calc (compare against published equity
  tables for well-known matchups, e.g. AA vs KK preflop ≈ 82/18).
- Phase 2: solver output compared against published push/fold charts at
  several stack depths; convergence/exploitability tracked in tests.
- Phase 3: manual end-to-end pass — run `scripts/dev.sh`, exercise range
  grid → equity panel → push/fold trainer in the browser.
- Each subsequent phase adds tests for new engine logic plus a manual
  UI pass for the new frontend surface, per the "one milestone at a time,
  test as you go" working style already agreed for this project.
