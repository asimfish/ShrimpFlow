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
    real_events = db.query(DevEvent).filter(~DevEvent.tags.contains('"seed"'))
    total_events = real_events.with_entities(func.count(DevEvent.id)).scalar() or 0
    total_skills = db.query(func.count(Skill.id)).scalar() or 0
    total_projects = real_events.with_entities(func.count(distinct(DevEvent.project))).scalar() or 0
    total_openclaw_sessions = db.query(func.count(OpenClawSession.id)).scalar() or 0
    total_claude_sessions = db.query(func.count(OpenClawSession.id)).filter(
        OpenClawSession.tags.contains('"claude_code"')
    ).scalar() or 0
    total_codex_sessions = db.query(func.count(OpenClawSession.id)).filter(
        OpenClawSession.tags.contains('"codex"')
    ).scalar() or 0
    total_git_commits = db.query(func.count(DevEvent.id)).filter(
        DevEvent.source == 'git',
        ~DevEvent.tags.contains('"seed"'),
    ).scalar() or 0
    total_days = db.query(func.count(DailySummary.id)).scalar() or 0

    project_row = (
        db.query(DevEvent.project, func.count(DevEvent.id).label('cnt'))
        .filter(~DevEvent.tags.contains('"seed"'))
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
        'total_claude_sessions': total_claude_sessions,
        'total_codex_sessions': total_codex_sessions,
        'total_git_commits': total_git_commits,
        'most_active_project': most_active_project, 'streak_days': streak,
    }
