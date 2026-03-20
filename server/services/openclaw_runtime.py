import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models.openclaw import OpenClawSession
from models.pattern import BehaviorPattern
from models.profile import ClawProfile

load_dotenv()


def _active_profile(db: Session) -> ClawProfile | None:
    return db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()


def _session_text(session: OpenClawSession) -> str:
    messages = json.loads(session.messages) if session.messages else []
    parts = [session.title or "", session.summary or ""]
    for message in messages:
        parts.append(str(message.get("content", "")))
    return "\n".join(part for part in parts if part).lower()


def _extract_keywords(text: str) -> set[str]:
    return {
        token for token in re.split(r"[^a-zA-Z0-9\u4e00-\u9fff]+", text.lower())
        if len(token) >= 2
    }


def _pattern_score(pattern: BehaviorPattern, session_text: str, session_keywords: set[str]) -> tuple[int, list[str]]:
    matched_terms: list[str] = []
    score = 0

    combined_text = " ".join(filter(None, [
        pattern.name,
        pattern.description,
        pattern.rule,
        pattern.body,
    ]))
    pattern_keywords = _extract_keywords(combined_text)
    shared = sorted(pattern_keywords & session_keywords)
    if shared:
        matched_terms.extend(shared[:6])
        score += min(len(shared) * 3, 18)

    trigger: Any = None
    if pattern.trigger:
        try:
            trigger = json.loads(pattern.trigger) if isinstance(pattern.trigger, str) and pattern.trigger.startswith("{") else pattern.trigger
        except json.JSONDecodeError:
            trigger = pattern.trigger

    if isinstance(trigger, dict):
        trigger_text = " ".join(
            [str(trigger.get("when", "")), str(trigger.get("event", ""))]
            + [str(item) for item in trigger.get("context", [])]
        ).lower()
        trigger_terms = _extract_keywords(trigger_text)
        trigger_shared = sorted(trigger_terms & session_keywords)
        if trigger_shared:
            matched_terms.extend(trigger_shared[:4])
            score += min(len(trigger_shared) * 4, 16)
    elif isinstance(trigger, str) and trigger:
        trigger_terms = _extract_keywords(trigger)
        trigger_shared = sorted(trigger_terms & session_keywords)
        if trigger_shared:
            matched_terms.extend(trigger_shared[:4])
            score += min(len(trigger_shared) * 4, 16)

    score += min(pattern.confidence // 10, 10)
    return score, list(dict.fromkeys(matched_terms))


def _heuristic_analysis(profile: ClawProfile, session: OpenClawSession, patterns: list[BehaviorPattern]) -> dict:
    session_text = _session_text(session)
    session_keywords = _extract_keywords(session_text)

    ranked = []
    for pattern in patterns:
        score, matched_terms = _pattern_score(pattern, session_text, session_keywords)
        if score > 0:
            ranked.append((score, pattern, matched_terms))

    ranked.sort(key=lambda item: (item[0], item[1].confidence), reverse=True)
    top = ranked[:5]
    injected_slugs = [pattern.slug or pattern.name for _, pattern, _ in top]

    if top:
        details = [
            f"{pattern.name}: 匹配词 {', '.join(terms[:4]) if terms else '高置信规则'}"
            for _, pattern, terms in top
        ]
        summary = (
            f"Active ClawProfile: {profile.display}。"
            f" 基于当前会话内容匹配到 {len(top)} 个模式，优先注入: "
            + "；".join(details)
        )
    else:
        summary = f"Active ClawProfile: {profile.display}。当前会话未命中显著模式，使用 profile 默认上下文。"

    return {
        "profile_id": profile.id,
        "profile_name": profile.display,
        "matched_patterns": [
            {
                "id": pattern.id,
                "slug": pattern.slug,
                "name": pattern.name,
                "confidence": pattern.confidence,
                "matched_terms": terms,
                "body_preview": (pattern.body or pattern.description or "")[:160],
            }
            for _, pattern, terms in top
        ],
        "summary": summary,
        "status": "heuristic",
        "injected_pattern_slugs": injected_slugs,
    }


def analyze_session_with_active_profile(db: Session, session_id: int) -> dict:
    session = db.query(OpenClawSession).filter(OpenClawSession.id == session_id).first()
    if not session:
        raise ValueError("Session not found")

    profile = _active_profile(db)
    if not profile:
        raise ValueError("Active profile not found")

    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.profile_id == profile.id,
    ).order_by(BehaviorPattern.confidence.desc()).all()

    result = _heuristic_analysis(profile, session, patterns)
    session.profile_id = profile.id
    session.injected_pattern_slugs = json.dumps(result["injected_pattern_slugs"], ensure_ascii=False)
    session.analysis_summary = result["summary"]
    session.analysis_status = result["status"]
    db.commit()
    db.refresh(session)
    return result


def analyze_recent_sessions_with_active_profile(db: Session, limit: int = 20) -> int:
    profile = _active_profile(db)
    if not profile:
        return 0

    rows = db.query(OpenClawSession).filter(
        (OpenClawSession.profile_id.is_(None)) | (OpenClawSession.profile_id == profile.id),
    ).order_by(OpenClawSession.created_at.desc()).limit(limit).all()
    updated = 0
    for session in rows:
        analyze_session_with_active_profile(db, session.id)
        updated += 1
    return updated
