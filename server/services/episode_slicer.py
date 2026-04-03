import json
import time
from collections import Counter

from sqlalchemy.orm import Session

from models.episode import Episode, EventAtom

# Episode 切分参数
GAP_THRESHOLD = 1800  # 30分钟无活动视为任务边界
MIN_EPISODE_EVENTS = 3  # 最少3个事件才构成 Episode
MAX_EPISODE_DURATION = 14400  # 单个 Episode 最长4小时

# task_category 推断权重
_CATEGORY_INTENT_MAP = {
    'coding': 'feature',
    'debugging': 'bugfix',
    'testing': 'test',
    'deploying': 'deploy',
    'reviewing': 'review',
    'building': 'build',
    'committing': 'feature',
    'configuring': 'config',
    'learning': 'learn',
    'connecting': 'deploy',
}


def _compute_features(atoms: list[EventAtom]) -> dict:
    # 工具分布
    tool_counts = Counter(a.tool for a in atoms)
    total = len(atoms)
    tool_dist = {k: round(v / total, 3) for k, v in tool_counts.most_common(8)}

    # 意图分布
    intent_counts = Counter(a.intent for a in atoms)
    intent_dist = {k: round(v / total, 3) for k, v in intent_counts.most_common(8)}

    # 命令族分布
    cmd_counts = Counter(a.command_family for a in atoms if a.command_family != 'other')
    cmd_dist = {k: v for k, v in cmd_counts.most_common(6)}

    # 结果分布
    outcome_counts = Counter(a.outcome for a in atoms)

    # 错误率
    error_count = sum(1 for a in atoms if a.error_signature)
    error_rate = round(error_count / total, 3) if total else 0

    # 持续时间
    duration = atoms[-1].timestamp - atoms[0].timestamp if len(atoms) > 1 else 0

    # 项目集中度
    project_counts = Counter(a.project for a in atoms if a.project)
    primary_project = project_counts.most_common(1)[0][0] if project_counts else ''

    return {
        'tool_dist': tool_dist,
        'intent_dist': intent_dist,
        'cmd_dist': cmd_dist,
        'outcome_dist': dict(outcome_counts),
        'error_rate': error_rate,
        'duration': duration,
        'event_count': total,
        'primary_project': primary_project,
        'unique_tools': len(tool_counts),
        'unique_intents': len(intent_counts),
        'has_errors': error_count > 0,
        'has_tests': 'testing' in intent_counts,
        'has_commits': 'committing' in intent_counts,
    }


def _infer_task_category(atoms: list[EventAtom]) -> str:
    intent_counts = Counter(a.intent for a in atoms)
    if not intent_counts:
        return 'unknown'
    dominant_intent = intent_counts.most_common(1)[0][0]
    return _CATEGORY_INTENT_MAP.get(dominant_intent, 'feature')


def _infer_task_label(atoms: list[EventAtom], category: str) -> str:
    # 从 task_hint 中找最有信息量的
    hints = [a.task_hint for a in atoms if a.task_hint and len(a.task_hint) > 10]
    if hints:
        # 取最长的 hint 作为标签
        return max(hints, key=len)[:120]

    # 从 artifact 推断
    artifacts = [a.artifact for a in atoms if a.artifact]
    if artifacts:
        return f'{category}: {artifacts[0]}'

    # fallback
    tools = Counter(a.tool for a in atoms).most_common(2)
    tool_str = '+'.join(t[0] for t in tools)
    return f'{category} ({tool_str}, {len(atoms)} events)'


def _infer_overall_outcome(atoms: list[EventAtom]) -> str:
    outcomes = [a.outcome for a in atoms]
    if not outcomes:
        return 'unknown'
    # 看最后几个事件的结果
    tail = outcomes[-3:] if len(outcomes) >= 3 else outcomes
    if all(o == 'success' for o in tail):
        return 'success'
    if any(o == 'failure' for o in tail):
        return 'failure'
    # 如果有 commit 说明大概率成功
    if any(a.intent == 'committing' for a in atoms[-5:]):
        return 'success'
    return 'unknown'


def slice_episodes(db: Session, lookback_hours: int = 72) -> int:
    cutoff = int(time.time()) - lookback_hours * 3600

    # 获取已有 episode 的最大 end_ts，避免重复切分
    last_episode = db.query(Episode).order_by(Episode.end_ts.desc()).first()
    if last_episode and last_episode.end_ts > cutoff:
        cutoff = last_episode.end_ts

    atoms = db.query(EventAtom).filter(
        EventAtom.timestamp > cutoff,
    ).order_by(EventAtom.timestamp.asc()).all()

    if len(atoms) < MIN_EPISODE_EVENTS:
        return 0

    # 按时间间隔切分
    episodes_raw = []
    current_group = [atoms[0]]

    for i in range(1, len(atoms)):
        gap = atoms[i].timestamp - atoms[i - 1].timestamp
        duration = atoms[i].timestamp - current_group[0].timestamp

        if gap > GAP_THRESHOLD or duration > MAX_EPISODE_DURATION:
            if len(current_group) >= MIN_EPISODE_EVENTS:
                episodes_raw.append(current_group)
            current_group = [atoms[i]]
        else:
            current_group.append(atoms[i])

    if len(current_group) >= MIN_EPISODE_EVENTS:
        episodes_raw.append(current_group)

    # 按项目二次切分: 同一时间段内不同项目的事件分开
    final_episodes = []
    for group in episodes_raw:
        project_groups = {}
        for atom in group:
            proj = atom.project or '_unknown'
            project_groups.setdefault(proj, []).append(atom)

        for proj, proj_atoms in project_groups.items():
            if len(proj_atoms) >= MIN_EPISODE_EVENTS:
                final_episodes.append(proj_atoms)
            elif len(project_groups) == 1:
                # 只有一个项目，保留
                final_episodes.append(proj_atoms)

    # 写入数据库
    count = 0
    now = int(time.time())
    for group in final_episodes:
        if len(group) < MIN_EPISODE_EVENTS:
            continue

        features = _compute_features(group)
        category = _infer_task_category(group)
        label = _infer_task_label(group, category)
        outcome = _infer_overall_outcome(group)

        # 收集关联的 session_ids
        session_ids = list({
            int(tag) for a in group
            if a.context_tags
            for tag in _extract_session_ids(a.context_tags)
        })

        episode = Episode(
            project=features['primary_project'],
            start_ts=group[0].timestamp,
            end_ts=group[-1].timestamp,
            duration_seconds=group[-1].timestamp - group[0].timestamp,
            task_label=label,
            task_category=category,
            event_count=len(group),
            atom_count=len(group),
            tool_sequence=json.dumps(
                [a.tool for a in group[:30]],
                ensure_ascii=False,
            ),
            intent_sequence=json.dumps(
                [a.intent for a in group[:30]],
                ensure_ascii=False,
            ),
            outcome=outcome,
            features=json.dumps(features, ensure_ascii=False),
            session_ids=json.dumps(session_ids),
            created_at=now,
        )
        db.add(episode)
        count += 1

    if count:
        db.commit()
    return count


def _extract_session_ids(context_tags_json: str) -> list[str]:
    # 从 context_tags 中提取数字型 session id
    try:
        tags = json.loads(context_tags_json)
        return [str(t) for t in tags if isinstance(t, int)]
    except (json.JSONDecodeError, TypeError):
        return []
