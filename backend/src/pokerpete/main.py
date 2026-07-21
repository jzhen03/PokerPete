from fastapi import FastAPI

app = FastAPI(title="PokerPete")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
