import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models.digest import DailySummary

router = APIRouter(tags=["digest"])


def _row_to_dict(row: DailySummary) -> dict:
    return {
        'date': row.date, 'event_count': row.event_count,
        'top_projects': json.loads(row.top_projects) if row.top_projects else [],
        'top_commands': json.loads(row.top_commands) if row.top_commands else [],
        'ai_summary': row.ai_summary, 'openclaw_sessions': row.openclaw_sessions,
    }


@router.get("/digest", response_model=list)
def get_digests(db: Session = Depends(get_db)):
    rows = db.query(DailySummary).order_by(DailySummary.date.desc()).all()
    return [_row_to_dict(r) for r in rows]


@router.get("/digest/{date}")
def get_digest_by_date(date: str, db: Session = Depends(get_db)):
    row = db.query(DailySummary).filter(DailySummary.date == date).first()
    if not row:
        raise HTTPException(status_code=404, detail="Summary not found")
    return _row_to_dict(row)


from services.ai_summary import generate_daily_summary

@router.post("/digest/generate/{date}")
def generate_digest(date: str, db: Session = Depends(get_db)):
    result = generate_daily_summary(db, date)
    return result
