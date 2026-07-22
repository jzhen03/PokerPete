from fastapi.testclient import TestClient

from pokerpete.main import app

client = TestClient(app)


def test_parse_range() -> None:
    response = client.post("/ranges/parse", json={"notation": "AA,AKs"})
    assert response.status_code == 200
    body = response.json()
    assert body["classes"] == {"AA": 1.0, "AKs": 1.0}
    assert body["combo_count"] == 10.0


def test_parse_invalid_range_notation() -> None:
    response = client.post("/ranges/parse", json={"notation": "not a range!!!"})
    assert response.status_code == 422
