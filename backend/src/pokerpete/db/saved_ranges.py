import json

from sqlalchemy.orm import Session

from pokerpete.db.models import SavedRange


def create_saved_range(
    db: Session,
    *,
    name: str,
    source: str,
    classes: dict[str, float],
    notation: str | None = None,
    position: str | None = None,
    tags: list[str] | None = None,
    factors: dict | None = None,
) -> SavedRange:
    row = SavedRange(
        name=name,
        source=source,
        classes_json=json.dumps(classes),
        notation=notation,
        position=position,
        tags=",".join(tags) if tags else None,
        factors_json=json.dumps(factors) if factors is not None else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_saved_ranges(db: Session) -> list[SavedRange]:
    return list(db.query(SavedRange).order_by(SavedRange.created_at.desc()).all())


def get_saved_range(db: Session, range_id: int) -> SavedRange | None:
    return db.get(SavedRange, range_id)
