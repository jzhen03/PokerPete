import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from pokerpete.db.models import Base
from pokerpete.db.session import get_db
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


@pytest.fixture
def isolated_db():
    """Override get_db with a throwaway in-memory database, so solver-cache
    writes in these tests never touch the real local app database."""
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


def test_preflop_tree_solve(isolated_db) -> None:
    response = client.post("/solver/preflop-tree", json={"stack_bb": 20})
    assert response.status_code == 200
    body = response.json()
    assert body["stack_bb"] == 20
    assert body["open_size_bb"] == 2.5
    assert body["sb_root"]["AA"]["fold"] == pytest.approx(0.0, abs=0.1)
    assert len(body["sb_root"]) == 169
    assert "postflop" in body["caveat"]


def test_preflop_tree_rejects_non_positive_stack(isolated_db) -> None:
    response = client.post("/solver/preflop-tree", json={"stack_bb": -5})
    assert response.status_code == 422
