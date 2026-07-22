import pytest
from fastapi.testclient import TestClient

from pokerpete.main import app

client = TestClient(app)


def test_push_fold_solve() -> None:
    response = client.post("/solver/push-fold", json={"stack_bb": 12})
    assert response.status_code == 200
    body = response.json()
    assert body["stack_bb"] == 12
    assert body["sb_shove_frequency"]["AA"] == pytest.approx(1.0, abs=0.1)
    assert body["bb_call_frequency"]["AA"] == pytest.approx(1.0, abs=0.1)
    assert len(body["sb_shove_frequency"]) == 169


def test_push_fold_rejects_non_positive_stack() -> None:
    response = client.post("/solver/push-fold", json={"stack_bb": 0})
    assert response.status_code == 422
