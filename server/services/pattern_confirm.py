import json
from datetime import datetime

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern
from routes.events import notify_new_event

# 有意义的模式类别（AI交互/科研/工程/git）
MEANINGFUL_CATEGORIES = ('coding', 'review', 'git', 'devops', 'collaboration')


def push_pending_patterns(db: Session) -> int:
    # 找出 confidence>=70 且 status='learning' 的模式，通过 SSE 推送
    rows = db.query(BehaviorPattern).filter(
        BehaviorPattern.confidence >= 70,
        BehaviorPattern.status == 'learning',
    ).all()
    pushed = 0
    for p in rows:
        if p.category not in MEANINGFUL_CATEGORIES:
            continue
        notify_new_event({
            'type': 'pattern_pending',
            'pattern': {
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'confidence': p.confidence,
                'description': p.description,
                'evidence_count': p.evidence_count,
            },
        })
        pushed += 1
    return pushed


def confirm_pattern(db: Session, pattern_id: int) -> dict:
    # 用户确认 -> status='confirmed'，正式成为 ClawProfile
    p = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not p:
        raise ValueError('Pattern not found')
    p.status = 'confirmed'
    evo = json.loads(p.evolution) if p.evolution else []
    evo.append({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'score': p.confidence,
        'note': '用户确认',
    })
    p.evolution = json.dumps(evo, ensure_ascii=False)
    db.commit()
    return {'id': p.id, 'status': 'confirmed'}


def reject_pattern(db: Session, pattern_id: int) -> dict:
    # 用户拒绝 -> confidence 降到 10，status 保持 'learning'，证据保留
    p = db.query(BehaviorPattern).filter(BehaviorPattern.id == pattern_id).first()
    if not p:
        raise ValueError('Pattern not found')
    p.confidence = 10
    p.status = 'learning'
    evo = json.loads(p.evolution) if p.evolution else []
    evo.append({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'score': 10,
        'note': '用户拒绝，证据保留继续学习',
    })
    p.evolution = json.dumps(evo, ensure_ascii=False)
    db.commit()
    return {'id': p.id, 'status': 'learning', 'confidence': 10}
