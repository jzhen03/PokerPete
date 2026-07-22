import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from pokerpete.db.models import Base
from pokerpete.db.session import get_db
from pokerpete.engine.preflop_equity_matrix import canonical_hand_classes
from pokerpete.main import app

client = TestClient(app)


@pytest.fixture
def isolated_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)()

    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    yield test_session
    app.dependency_overrides.pop(get_db, None)
    test_session.close()


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


def test_get_tree_spot_is_well_formed() -> None:
    response = client.get("/trainer/preflop-tree/spot")
    assert response.status_code == 200
    body = response.json()
    assert body["hero_class"] in canonical_hand_classes()
    assert 15 <= body["stack_bb"] <= 100
    assert len(body["hero_combo"]) == 4


def test_grade_tree_premium_open_is_correct(isolated_db) -> None:
    response = client.post(
        "/trainer/preflop-tree/grade",
        json={"stack_bb": 40, "hero_class": "AA", "action": "open"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["correct_action"] in ("open", "shove")
    assert "postflop" in body["caveat"]


def test_grade_tree_rejects_unknown_hand_class(isolated_db) -> None:
    response = client.post(
        "/trainer/preflop-tree/grade",
        json={"stack_bb": 40, "hero_class": "ZZ", "action": "fold"},
    )
    assert response.status_code == 422
