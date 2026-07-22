import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from pokerpete.db.models import Base, SolverResult
from pokerpete.db.solver_cache import get_or_solve_tree
from pokerpete.engine.preflop_equity_matrix import DEFAULT_DATA_PATH

requires_real_matrix = pytest.mark.skipif(
    not DEFAULT_DATA_PATH.exists(),
    reason="preflop equity matrix artifact not built; run scripts/build_preflop_equity_matrix.py",
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@requires_real_matrix
def test_cache_miss_then_hit_return_the_same_solution(db_session: Session) -> None:
    first = get_or_solve_tree(db_session, 20.0, iterations=20)
    second = get_or_solve_tree(db_session, 20.0, iterations=20)
    assert first.sb_root == second.sb_root
    assert first.iterations == second.iterations == 20
    assert db_session.query(SolverResult).count() == 1


@requires_real_matrix
def test_cache_row_records_solver_version_and_raw_params(db_session: Session) -> None:
    get_or_solve_tree(db_session, 15.0, iterations=20)
    row = db_session.query(SolverResult).one()
    assert row.solver_version
    assert '"stack_bb": 15.0' in row.tree_params_json


@requires_real_matrix
def test_different_stack_depths_produce_separate_cache_entries(db_session: Session) -> None:
    get_or_solve_tree(db_session, 15.0, iterations=20)
    get_or_solve_tree(db_session, 25.0, iterations=20)
    assert db_session.query(SolverResult).count() == 2


@requires_real_matrix
def test_different_iteration_counts_do_not_collide(db_session: Session) -> None:
    # A different iteration count is a different tree_params_json, so it
    # must not be served from a differently-configured cache entry.
    get_or_solve_tree(db_session, 20.0, iterations=20)
    get_or_solve_tree(db_session, 20.0, iterations=30)
    assert db_session.query(SolverResult).count() == 2
