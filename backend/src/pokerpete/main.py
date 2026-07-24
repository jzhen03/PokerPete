from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pokerpete.api import (
    routes_equity,
    routes_range_predictor,
    routes_ranges,
    routes_solver,
    routes_trainer,
)

app = FastAPI(title="PokerPete")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_ranges.router)
app.include_router(routes_range_predictor.router)
app.include_router(routes_equity.router)
app.include_router(routes_solver.router)
app.include_router(routes_trainer.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
