import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models.episode import Episode, EventAtom

router = APIRouter(tags=["episodes"])


@router.get("/episodes")
def list_episodes(
    limit: int = 50,
    offset: int = 0,
    project: str = '',
    db: Session = Depends(get_db),
):
    query = db.query(Episode).order_by(Episode.start_ts.desc())
    if project:
        query = query.filter(Episode.project == project)
    rows = query.offset(offset).limit(limit).all()
    return [_episode_to_dict(r) for r in rows]


@router.get("/episodes/stats")
def episode_stats(db: Session = Depends(get_db)):
    total = db.query(Episode).count()
    atoms_total = db.query(EventAtom).count()
    # 按 task_category 分组
    from sqlalchemy import func
    category_counts = db.query(
        Episode.task_category, func.count(Episode.id)
    ).group_by(Episode.task_category).all()
    # 按 outcome 分组
    outcome_counts = db.query(
        Episode.outcome, func.count(Episode.id)
    ).group_by(Episode.outcome).all()
    return {
        'total_episodes': total,
        'total_atoms': atoms_total,
        'by_category': {c: n for c, n in category_counts if c},
        'by_outcome': {o: n for o, n in outcome_counts if o},
    }


@router.get("/episodes/{episode_id}")
def get_episode(episode_id: int, db: Session = Depends(get_db)):
    ep = db.query(Episode).filter(Episode.id == episode_id).first()
    if not ep:
        return {'error': 'Episode not found'}
    result = _episode_to_dict(ep)
    # 附带该 episode 的 atoms
    atoms = db.query(EventAtom).filter(
        EventAtom.timestamp >= ep.start_ts,
        EventAtom.timestamp <= ep.end_ts,
    ).order_by(EventAtom.timestamp.asc()).limit(50).all()
    result['atoms'] = [_atom_to_dict(a) for a in atoms]
    return result


@router.get("/atoms")
def list_atoms(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    rows = db.query(EventAtom).order_by(
        EventAtom.timestamp.desc()
    ).offset(offset).limit(limit).all()
    return [_atom_to_dict(r) for r in rows]


def _episode_to_dict(ep: Episode) -> dict:
    return {
        'id': ep.id,
        'project': ep.project,
        'start_ts': ep.start_ts,
        'end_ts': ep.end_ts,
        'duration_seconds': ep.duration_seconds,
        'task_label': ep.task_label,
        'task_category': ep.task_category,
        'event_count': ep.event_count,
        'atom_count': ep.atom_count,
        'tool_sequence': json.loads(ep.tool_sequence) if ep.tool_sequence else [],
        'intent_sequence': json.loads(ep.intent_sequence) if ep.intent_sequence else [],
        'outcome': ep.outcome,
        'features': json.loads(ep.features) if ep.features else {},
        'session_ids': json.loads(ep.session_ids) if ep.session_ids else [],
        'created_at': ep.created_at,
    }


def _atom_to_dict(a: EventAtom) -> dict:
    return {
        'id': a.id,
        'event_id': a.event_id,
        'timestamp': a.timestamp,
        'source': a.source,
        'project': a.project,
        'intent': a.intent,
        'tool': a.tool,
        'artifact': a.artifact,
        'outcome': a.outcome,
        'error_signature': a.error_signature,
        'command_family': a.command_family,
        'task_hint': a.task_hint,
    }


# Feature Graph API
@router.get("/feature-graph/archetypes")
def get_archetypes(db: Session = Depends(get_db)):
    from services.feature_graph import get_archetype_summary
    return get_archetype_summary(db)


@router.get("/feature-graph/stats")
def feature_graph_stats(db: Session = Depends(get_db)):
    from models.feature_graph import EpisodeFeature, FeatureEdge
    from sqlalchemy import func
    from collections import Counter
    total_nodes = db.query(EpisodeFeature).count()
    total_edges = db.query(FeatureEdge).count()
    archetype_counts = db.query(
        EpisodeFeature.archetype, func.count(EpisodeFeature.id)
    ).group_by(EpisodeFeature.archetype).all()
    edge_type_counts = db.query(
        FeatureEdge.edge_type, func.count(FeatureEdge.id)
    ).group_by(FeatureEdge.edge_type).all()
    return {
        'total_nodes': total_nodes,
        'total_edges': total_edges,
        'archetype_distribution': {a: n for a, n in archetype_counts if a},
        'edge_type_distribution': {e: n for e, n in edge_type_counts if e},
    }


# Evidence Ledger API
@router.get("/evidence-ledger/{pattern_id}")
def get_pattern_ledger(pattern_id: int, limit: int = 50, db: Session = Depends(get_db)):
    from services.evidence_ledger import get_ledger_for_pattern
    return get_ledger_for_pattern(db, pattern_id, limit)


@router.get("/evidence-ledger-stats")
def ledger_stats(db: Session = Depends(get_db)):
    from services.evidence_ledger import get_ledger_stats
    return get_ledger_stats(db)
