from fastapi.testclient import TestClient

from pokerpete.main import app

client = TestClient(app)


def test_predict_route_returns_classes_and_stages() -> None:
    response = client.post(
        "/ranges/predict",
        json={"position": "SB", "action": "open", "player_type": "balanced"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classes"]
    assert body["combo_count"] > 0
    assert [stage["name"] for stage in body["stages"]] == ["position", "player_type", "bet_sizing"]


def test_predict_route_defaults_reliability_from_player_type() -> None:
    response = client.post(
        "/ranges/predict",
        json={"position": "BB", "action": "threebet", "player_type": "tight_aggressive"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reliability_used"] == 55
    assert body["reliability_default"] == 55
    assert body["reliability_is_customized"] is False


def test_predict_route_honors_explicit_reliability_override() -> None:
    response = client.post(
        "/ranges/predict",
        json={
            "position": "SB",
            "action": "open",
            "player_type": "loose_aggressive",
            "sizing_bucket": "large",
            "reliability": 90,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reliability_used"] == 90
    assert body["reliability_is_customized"] is True


def test_predict_route_rejects_invalid_position() -> None:
    response = client.post(
        "/ranges/predict",
        json={"position": "UTG", "action": "open", "player_type": "balanced"},
    )
    assert response.status_code == 422


def test_predict_route_rejects_invalid_action() -> None:
    response = client.post(
        "/ranges/predict",
        json={"position": "SB", "action": "shove", "player_type": "balanced"},
    )
    assert response.status_code == 422


def test_predict_route_rejects_invalid_player_type() -> None:
    response = client.post(
        "/ranges/predict",
        json={"position": "SB", "action": "open", "player_type": "maniac"},
    )
    assert response.status_code == 422


def test_predict_route_rejects_out_of_range_reliability() -> None:
    response = client.post(
        "/ranges/predict",
        json={"position": "SB", "action": "open", "player_type": "balanced", "reliability": 150},
    )
    assert response.status_code == 422
