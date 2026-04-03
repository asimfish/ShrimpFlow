import json
import time
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from services.task_runner import create_task, update_task, get_fresh_session
from models.event import DevEvent
from routes.events import notify_new_event

router = APIRouter(tags=["collector"])


class CollectEventRequest(BaseModel):
    source: str
    action: str
    directory: str = ''
    project: str = ''
    branch: str = ''
    exit_code: int = 0
    duration_ms: int = 0
    semantic: str = ''
    tags: list[str] = []
    openclaw_session_id: int | None = None


@router.post("/collect/event")
def collect_event(req: CollectEventRequest, db: Session = Depends(get_db)):
    event = DevEvent(
        timestamp=int(time.time()),
        source=req.source,
        action=req.action,
        directory=req.directory,
        project=req.project,
        branch=req.branch,
        exit_code=req.exit_code,
        duration_ms=req.duration_ms,
        semantic=req.semantic,
        tags=json.dumps(req.tags),
        openclaw_session_id=req.openclaw_session_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    notify_new_event({
        'id': event.id,
        'timestamp': event.timestamp,
        'source': event.source,
        'action': event.action,
        'project': event.project,
        'branch': event.branch,
        'directory': event.directory,
        'exit_code': event.exit_code,
        'duration_ms': event.duration_ms,
        'semantic': event.semantic,
        'tags': req.tags,
        'openclaw_session_id': event.openclaw_session_id,
    })
    return {'id': event.id, 'status': 'ok'}


@router.post("/collect/terminal")
def collect_terminal(req: CollectEventRequest, db: Session = Depends(get_db)):
    req.source = 'terminal'
    return collect_event(req, db)


@router.post("/collect/git")
def collect_git(req: CollectEventRequest, db: Session = Depends(get_db)):
    req.source = 'git'
    return collect_event(req, db)


@router.post("/collect/openclaw")
def collect_openclaw(req: CollectEventRequest, db: Session = Depends(get_db)):
    req.source = 'openclaw'
    return collect_event(req, db)


from services.real_data_collector import (
    collect_shell_history, collect_claude_code, collect_codex_sessions,
    collect_clawd_docs, collect_git_history, collect_vscode_cursor, collect_all,
)


@router.post("/collect/shell-history")
def api_collect_shell(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_shell_history
    result = collect_shell_history(db)
    return result.to_dict()


@router.post("/collect/claude-code")
def api_collect_claude(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_claude_code
    result = collect_claude_code(db)
    return result.to_dict()


@router.post("/collect/codex")
def api_collect_codex(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_codex_sessions
    result = collect_codex_sessions(db)
    return result.to_dict()


@router.post("/collect/clawd")
def api_collect_clawd(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_clawd_docs
    result = collect_clawd_docs(db)
    return result.to_dict()


@router.post("/collect/git-history")
def api_collect_git(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_git_history
    result = collect_git_history(db)
    return result.to_dict()


@router.post("/collect/vscode-cursor")
def api_collect_vscode_cursor(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_vscode_cursor
    result = collect_vscode_cursor(db)
    return result.to_dict()


@router.post("/collect/all")
def api_collect_all(db: Session = Depends(get_db)):
    from services.real_data_collector import collect_all
    results = collect_all(db)
    return {'results': results}


def run_collect_and_analyze(db: Session) -> dict:
    # 公共逻辑: 采集 + 挖掘 + AI增强 + 生成摘要
    from services.real_data_collector import collect_all
    from services.pattern_mining import run_mining
    from services.ai_summary import generate_pattern_description, generate_daily_summary
    from services.pattern_confirm import push_pending_patterns
    from models.pattern import BehaviorPattern
    from models.event import DevEvent
    from datetime import datetime
    from sqlalchemy import func
    import json as _json

    results = collect_all(db)
    mined = run_mining(db)

    # 对新挖掘的模式尝试 AI 增强描述
    for p_dict in mined:
        row = db.query(BehaviorPattern).filter(BehaviorPattern.name == p_dict['name']).first()
        if row and row.learned_from == 'auto_mining':
            examples = _json.loads(row.applicable_scenarios) if row.applicable_scenarios else []
            desc = generate_pattern_description(row.name, examples)
            if desc and desc != row.description:
                row.description = desc
    db.commit()

    # 为所有有真实事件的日期重新生成摘要
    event_dates = db.query(
        func.strftime('%Y-%m-%d', DevEvent.timestamp, 'unixepoch').label('d')
    ).filter(
        ~DevEvent.tags.contains('"seed"'),
    ).distinct().all()
    generated_count = 0
    for (date_str,) in event_dates:
        if not date_str:
            continue
        generate_daily_summary(db, date_str)
        generated_count += 1

    today_str = datetime.now().strftime('%Y-%m-%d')
    generate_daily_summary(db, today_str)

    # Brain 深层流水线: EventAtom → Episode → DeepMining → SessionMining → FeatureGraph → EvidenceLedger
    from services.event_atom_extractor import extract_atoms_from_events
    from services.episode_slicer import slice_episodes
    from services.deep_mining import run_deep_mining
    from services.session_mining import mine_from_sessions
    from services.feature_graph import build_feature_graph
    from services.evidence_ledger import filter_meaningful_patterns, record_mining_evidence

    atoms_count = extract_atoms_from_events(db, limit=3000)
    episodes_count = slice_episodes(db, lookback_hours=720)
    deep_mined = run_deep_mining(db)

    # OpenClawSession 对话内容挖掘
    session_mined = mine_from_sessions(db, lookback_hours=720)
    # 持久化 session 挖掘结果
    session_saved = _persist_session_patterns(db, session_mined)

    # 构建 Feature Graph (处理所有历史 episodes)
    graph_result = build_feature_graph(db, lookback_hours=8760)

    # Evidence Ledger: 为深层挖掘的模式记录 support 证据
    for item in deep_mined:
        pattern = db.query(BehaviorPattern).filter(BehaviorPattern.name == item.get('name')).first()
        if pattern:
            record_mining_evidence(db, pattern.id, None, 'support', f'深层挖掘确认: {item.get("type", "deep")}')

    # 有意义性过滤
    meaningful_ids = filter_meaningful_patterns(db)

    # 推送高置信度待确认模式
    pushed = push_pending_patterns(db)

    return {
        'results': results,
        'mining_count': len(mined),
        'deep_mining_count': len(deep_mined),
        'session_mining_count': len(session_mined),
        'atoms_extracted': atoms_count,
        'episodes_sliced': episodes_count,
        'feature_graph': graph_result,
        'meaningful_patterns': len(meaningful_ids),
        'digest_updated': True,
        'digests_generated': generated_count,
        'patterns_pushed': pushed,
    }


def _persist_session_patterns(db: Session, patterns: list[dict]) -> int:
    # 持久化 session 挖掘出的模式
    from services.pattern_mining import bayesian_update, _confidence_to_level, _name_to_slug
    from services.evidence_ledger import record_mining_evidence

    saved = 0
    for norm in patterns:
        name = norm.get('name', '')
        if not name:
            continue

        existing = db.query(BehaviorPattern).filter(BehaviorPattern.name == name).first()
        trigger = norm.get('trigger', name)
        trigger_json = json.dumps(trigger, ensure_ascii=False) if isinstance(trigger, dict) else trigger
        evidence_json = json.dumps(norm.get('evidence', []), ensure_ascii=False)

        if existing:
            new_conf = int(bayesian_update(existing.confidence / 100, 0.12) * 100)
            existing.confidence = new_conf
            existing.confidence_level = _confidence_to_level(new_conf)
            existing.evidence_count += 1
            if norm.get('body'):
                existing.body = norm['body']
            if norm.get('description'):
                existing.description = norm['description']
            existing.trigger = trigger_json
            evo = json.loads(existing.evolution) if existing.evolution else []
            evo.append({
                'date': time.strftime('%m-%d'),
                'confidence': new_conf,
                'event_description': f'对话挖掘更新: {norm.get("type", "session")}',
            })
            existing.evolution = json.dumps(evo, ensure_ascii=False)
            record_mining_evidence(db, existing.id, None, 'support', f'对话挖掘确认: {norm.get("type", "session")}')
        else:
            category = norm.get('category', 'coding')
            if category not in ('coding', 'review', 'git', 'devops', 'collaboration'):
                category = 'coding'
            pattern = BehaviorPattern(
                name=name,
                category=category,
                description=norm.get('description', name),
                confidence=norm.get('confidence', 50),
                evidence_count=1,
                learned_from='session_mining',
                rule='OpenClaw 对话挖掘 + AI 语义精炼',
                created_at=int(time.time()),
                status='learning',
                evolution=json.dumps([{
                    'date': time.strftime('%m-%d'),
                    'confidence': norm.get('confidence', 50),
                    'event_description': f'对话挖掘首次发现: {norm.get("type", "session")}',
                }], ensure_ascii=False),
                rules=json.dumps([]),
                executions=json.dumps([]),
                applicable_scenarios=json.dumps(norm.get('examples', [])[:3]),
                slug=_name_to_slug(name),
                trigger=trigger_json,
                body=norm.get('body', ''),
                source='auto',
                confidence_level=_confidence_to_level(norm.get('confidence', 50)),
                learned_from_data=evidence_json,
            )
            db.add(pattern)

        saved += 1

    if saved:
        db.commit()
    return saved


@router.post("/collect/all-and-analyze")
def api_collect_all_and_analyze(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task_id = create_task(db, "collect")
    background_tasks.add_task(_run_collect_background, task_id)
    return {"task_id": task_id}


def _run_collect_background(task_id: str):
    db = get_fresh_session()
    try:
        update_task(db, task_id, "running", 5, "开始采集…")
        from services.real_data_collector import collect_all
        results = collect_all(db)
        update_task(db, task_id, "running", 25, "采集完成，挖掘模式…")
        from services.pattern_mining import run_mining
        mined = run_mining(db)
        update_task(db, task_id, "running", 45, "AI 增强描述…")
        import json as _json
        from services.ai_summary import generate_pattern_description, generate_daily_summary
        from models.pattern import BehaviorPattern
        from models.event import DevEvent
        from datetime import datetime
        from sqlalchemy import func
        for p_dict in mined:
            row = db.query(BehaviorPattern).filter(BehaviorPattern.name == p_dict['name']).first()
            if row and row.learned_from == 'auto_mining':
                examples = _json.loads(row.applicable_scenarios) if row.applicable_scenarios else []
                desc = generate_pattern_description(row.name, examples)
                if desc and desc != row.description:
                    row.description = desc
        db.commit()
        update_task(db, task_id, "running", 55, "生成日报摘要…")
        event_dates = db.query(
            func.strftime('%Y-%m-%d', DevEvent.timestamp, 'unixepoch').label('d')
        ).filter(~DevEvent.tags.contains('"seed"')).distinct().all()
        generated_count = 0
        for (date_str,) in event_dates:
            if not date_str:
                continue
            generate_daily_summary(db, date_str)
            generated_count += 1
        generate_daily_summary(db, datetime.now().strftime('%Y-%m-%d'))
        update_task(db, task_id, "running", 65, "Brain 深层流水线…")
        from services.event_atom_extractor import extract_atoms_from_events
        from services.episode_slicer import slice_episodes
        from services.deep_mining import run_deep_mining
        from services.session_mining import mine_from_sessions
        from services.feature_graph import build_feature_graph
        from services.evidence_ledger import filter_meaningful_patterns, record_mining_evidence
        atoms_count = extract_atoms_from_events(db, limit=3000)
        episodes_count = slice_episodes(db, lookback_hours=720)
        deep_mined = run_deep_mining(db)
        update_task(db, task_id, "running", 80, "对话挖掘 + 特征图…")
        session_mined = mine_from_sessions(db, lookback_hours=720)
        session_saved = _persist_session_patterns(db, session_mined)
        graph_result = build_feature_graph(db, lookback_hours=8760)
        for item in deep_mined:
            pattern = db.query(BehaviorPattern).filter(BehaviorPattern.name == item.get('name')).first()
            if pattern:
                record_mining_evidence(db, pattern.id, None, 'support', f'深层挖掘确认: {item.get("type", "deep")}')
        meaningful_ids = filter_meaningful_patterns(db)
        update_task(db, task_id, "running", 90, "推送待确认模式…")
        from services.pattern_confirm import push_pending_patterns
        pushed = push_pending_patterns(db)
        result = {
            'results': results,
            'mining_count': len(mined),
            'deep_mining_count': len(deep_mined),
            'session_mining_count': len(session_mined),
            'atoms_extracted': atoms_count,
            'episodes_sliced': episodes_count,
            'feature_graph': graph_result,
            'meaningful_patterns': len(meaningful_ids),
            'digest_updated': True,
            'digests_generated': generated_count,
            'patterns_pushed': pushed,
        }
        update_task(db, task_id, "done", 100, "完成", result=result)
    except Exception as e:
        update_task(db, task_id, "error", 0, "出错", error=str(e))
    finally:
        db.close()
