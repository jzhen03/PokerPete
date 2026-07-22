from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SolverResult(Base):
    """Cache of expensive preflop solves (e.g. the open/3bet/shove tree),
    keyed by a hash of the solver version and its tree parameters so that
    algorithm changes never silently serve a stale result."""

    __tablename__ = "solver_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(unique=True, index=True)
    solver_version: Mapped[str]
    tree_params_json: Mapped[str]
    result_json: Mapped[str]
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
