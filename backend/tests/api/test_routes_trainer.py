from fastapi.testclient import TestClient

from pokerpete.engine.preflop_equity_matrix import canonical_hand_classes
from pokerpete.main import app

client = TestClient(app)


def test_get_spot_is_well_formed() -> None:
    response = client.get("/trainer/push-fold/spot")
    assert response.status_code == 200
    body = response.json()
    assert body["hero_class"] in canonical_hand_classes()
    assert 2 <= body["stack_bb"] <= 40
    assert len(body["hero_combo"]) == 4


def test_grade_premium_shove_is_correct() -> None:
    response = client.post(
        "/trainer/push-fold/grade",
        json={"stack_bb": 20, "hero_class": "AA", "action": "shove"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["correct_action"] == "shove"


def test_grade_rejects_unknown_hand_class() -> None:
    response = client.post(
        "/trainer/push-fold/grade",
        json={"stack_bb": 20, "hero_class": "ZZ", "action": "shove"},
    )
    assert response.status_code == 422
