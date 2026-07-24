import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from pokerpete.db.models import Base
from pokerpete.db.session import get_db
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


@pytest.fixture
def isolated_db():
    """Override get_db with a throwaway in-memory database, so saved-range
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


def test_save_and_list_and_get_range(isolated_db) -> None:
    create_response = client.post(
        "/ranges",
        json={
            "name": "SB open vs LAG",
            "source": "predictor",
            "classes": {"AA": 1.0, "76s": 0.5},
            "position": "SB",
            "factors": {"position": "SB", "action": "open", "player_type": "loose_aggressive"},
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "SB open vs LAG"

    list_response = client.get("/ranges")
    assert list_response.status_code == 200
    summaries = list_response.json()
    assert any(row["id"] == created["id"] for row in summaries)

    get_response = client.get(f"/ranges/{created['id']}")
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["classes"] == {"AA": 1.0, "76s": 0.5}
    assert detail["combo_count"] == pytest.approx(1.0 * 6 + 0.5 * 4)
    assert detail["factors"] == {
        "position": "SB",
        "action": "open",
        "player_type": "loose_aggressive",
    }


def test_get_missing_range_returns_404(isolated_db) -> None:
    response = client.get("/ranges/999999")
    assert response.status_code == 404
