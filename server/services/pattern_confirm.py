import json
import threading
import time
from datetime import datetime

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern
from models.skill import Skill
from routes.events import notify_new_event
from services.evidence_ledger import is_meaningful_rule, record_evidence
from services.memory_lifecycle import record_access
from services.taste_model import get_pending_pattern_recommendations, record_pattern_decision

# 有意义的模式类别（AI交互/科研/工程/git）
MEANINGFUL_CATEGORIES = ('coding', 'review', 'git', 'devops', 'collaboration')


def _load_json_list(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _append_user_feedback(pattern: BehaviorPattern, action: str, reason: str = '') -> None:
    feedback = _load_json_list(pattern.user_feedback)
    feedback.append({
        'action': action,
        'ts': int(time.time()),
        'reason': reason or '',
    })
    pattern.user_feedback = json.dumps(feedback[-20:], ensure_ascii=False)


def _compute_skill_alignment_score(pattern: BehaviorPattern, skills: list[Skill]) -> int:
    haystack = f'{pattern.name or ""}\n{pattern.description or ""}'.lower()
    matched = 0
    category_bonus = 0
    seen_names: set[str] = set()

    for skill in skills:
        skill_name = (skill.name or '').strip().lower()
        if skill_name and skill_name not in seen_names and skill_name in haystack:
            matched += 1
            seen_names.add(skill_name)
        if not category_bonus and skill.category == pattern.category:
            category_bonus = 10

    return min(100, matched * 20 + category_bonus)


def push_pending_patterns(db: Session) -> int:
    # 使用 taste model 决定哪些候选值得进入待确认队列，并按优先级排序。
    rows = get_pending_pattern_recommendations(db)
    skills = db.query(Skill).all()
    pushed = 0
    dirty = False
    pending_payloads: list[tuple[int, int, int, dict]] = []
    for item in rows:
        p = item['pattern']
        if (p.reject_count or 0) >= 2:
            continue
        if p.category not in MEANINGFUL_CATEGORIES:
            continue
        if not is_meaningful_rule(p):
            continue
        if item['action'] != 'confirm':
            continue
        alignment_score = _compute_skill_alignment_score(p, skills)
        if (p.skill_alignment_score or 0) != alignment_score:
            p.skill_alignment_score = alignment_score
            dirty = True
        pending_payloads.append((
            item['priority_score'],
            alignment_score,
            p.confidence,
            {
                'type': 'pattern_pending',
                'pattern': {
                    'id': p.id,
                    'name': p.name,
                    'category': p.category,
                    'confidence': p.confidence,
                    'description': p.description,
                    'evidence_count': p.evidence_count,
                    'source': p.source,
                    'skill_alignment_score': alignment_score,
                    'taste_action': item['action'],
                    'priority_score': item['priority_score'],
                    'taste_reasons': item['reasons'],
                },
            },
        ))
    if dirty:
        db.commit()
    for _, _, _, payload in sorted(pending_payloads, key=lambda item: (item[0], item[1], item[2]), reverse=True):
        notify_new_event(payload)
        pushed += 1
    return pushed


def confirm_pattern(db: Session, pattern_id: int) -> dict:
    # 用户确认 -> status='confirmed'，正式成为 ClawProfile
    p = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not p:
        raise ValueError('Pattern not found')
    p.status = 'confirmed'
    _append_user_feedback(p, 'confirm')
    evo = json.loads(p.evolution) if p.evolution else []
    evo.append({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'score': p.confidence,
        'note': '用户确认',
    })
    p.evolution = json.dumps(evo, ensure_ascii=False)
    db.commit()
    # 强化: 确认是最强的访问信号
    record_access(db, pattern_id)
    # 记录 utility 证据
    record_evidence(db, pattern_id, 'utility', '用户确认该模式有效', source='user_confirm')
    taste = record_pattern_decision(db, p, 'confirmed', '用户确认该模式值得保留')
    return {
        'id': p.id,
        'status': 'confirmed',
        'user_feedback': _load_json_list(p.user_feedback),
        'taste_summary': taste.taste_summary,
    }


def reject_pattern(db: Session, pattern_id: int, reason: str = '') -> dict:
    # 用户拒绝 -> 标记 rejected，累计 reject_count，并记录负反馈证据
    p = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not p:
        raise ValueError('Pattern not found')
    p.status = 'rejected'
    p.reject_count = (p.reject_count or 0) + 1
    _append_user_feedback(p, 'reject', reason)
    evo = json.loads(p.evolution) if p.evolution else []
    evo.append({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'score': p.confidence,
        'note': f'用户拒绝: {reason}' if reason else '用户拒绝',
    })
    p.evolution = json.dumps(evo, ensure_ascii=False)
    db.commit()
    # 记录 conflict 证据
    evidence_desc = f'用户拒绝该模式: {reason}' if reason else '用户拒绝该模式'
    record_evidence(db, pattern_id, 'conflict', evidence_desc, source='user_reject')
    # V4: 将拒绝原因提取为负向偏好信号，写入 negative 证据
    if reason:
        negative_desc = f'用户拒绝: {reason} — 这揭示了一个隐性偏好'
    else:
        negative_desc = '用户拒绝该模式 — 这揭示了一个隐性偏好'
    record_evidence(db, pattern_id, 'negative', negative_desc, source='user_reject_signal')
    # 后台触发 CoT 重分析（非阻塞）
    def _bg_mine():
        try:
            from db import SessionLocal
            bg_db = SessionLocal()
            try:
                from services.cot_miner import mine_cot_skills
                mine_cot_skills(bg_db)
            finally:
                bg_db.close()
        except Exception:
            pass
    threading.Thread(target=_bg_mine, daemon=True).start()
    taste = record_pattern_decision(db, p, 'rejected', reason or '用户认为该模式不值得确认')
    return {
        'id': p.id,
        'status': 'rejected',
        'confidence': p.confidence,
        'reject_count': p.reject_count,
        'user_feedback': _load_json_list(p.user_feedback),
        'taste_summary': taste.taste_summary,
    }
