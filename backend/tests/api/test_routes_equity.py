import pytest
from fastapi.testclient import TestClient

from pokerpete.main import app

client = TestClient(app)


def test_hand_vs_hand_equity() -> None:
    response = client.post(
        "/equity/calculate",
        json={"hero": "AsAd", "villain": "KsKd", "iterations": 20000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["equity"] == pytest.approx(0.821, abs=0.02)
    assert body["win"] + body["tie"] + body["lose"] == pytest.approx(1.0)


def test_range_vs_range_equity() -> None:
    response = client.post(
        "/equity/calculate",
        json={"hero": "AA", "villain": "KK", "iterations": 4000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["equity"] > 0.6


def test_equity_with_board() -> None:
    response = client.post(
        "/equity/calculate",
        json={"hero": "2c3c", "villain": "4d5d", "board": "As Ks Qs Js Ts"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["win"] == 0.0
    assert body["tie"] == 1.0


def test_equity_rejects_overlapping_cards() -> None:
    response = client.post("/equity/calculate", json={"hero": "AsAd", "villain": "AsKd"})
    assert response.status_code == 422


def test_equity_rejects_malformed_notation() -> None:
    response = client.post("/equity/calculate", json={"hero": "not a hand", "villain": "AA"})
    assert response.status_code == 422
