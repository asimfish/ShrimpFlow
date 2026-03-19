from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from db import get_db
from models.event import DevEvent
from models.skill import Skill
from models.openclaw import OpenClawSession
from models.digest import DailySummary
from schemas.stats import StatsOverview

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsOverview)
def get_stats(db: Session = Depends(get_db)):
    total_events = db.query(func.count(DevEvent.id)).scalar()
    total_skills = db.query(func.count(Skill.id)).scalar()
    total_projects = db.query(func.count(distinct(DevEvent.project))).scalar()
    total_openclaw_sessions = db.query(func.count(OpenClawSession.id)).scalar()
    total_days = db.query(func.count(DailySummary.id)).scalar()

    project_row = (
        db.query(DevEvent.project, func.count(DevEvent.id).label('cnt'))
        .group_by(DevEvent.project)
        .order_by(func.count(DevEvent.id).desc())
        .first()
    )
    most_active_project = project_row[0] if project_row else ''

    dates = [
        r[0] for r in
        db.query(DailySummary.date)
        .filter(DailySummary.event_count > 0)
        .order_by(DailySummary.date.desc())
        .all()
    ]
    streak = 0
    if dates:
        prev = datetime.strptime(dates[0], '%Y-%m-%d')
        streak = 1
        for d in dates[1:]:
            cur = datetime.strptime(d, '%Y-%m-%d')
            if (prev - cur).days == 1:
                streak += 1
                prev = cur
            else:
                break

    return {
        'total_events': total_events, 'total_days': total_days,
        'total_projects': total_projects, 'total_skills': total_skills,
        'total_openclaw_sessions': total_openclaw_sessions,
        'most_active_project': most_active_project, 'streak_days': streak,
    }
