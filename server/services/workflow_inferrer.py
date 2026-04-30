"""
Workflow 重建 (M2)
连接: Episode（做了什么任务）+ CoT（怎么思考的）+ 结果（git提交/输出）
→ 推断完整可重用的 Workflow 模板

CatchMe 只能回答"昨天做了什么"
ShrimpFlow 能输出"下次做类似任务的最优步骤清单"
"""
import json
import logging
import re
import time
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from models.episode import Episode
from models.openclaw import OpenClawSession
from models.event import DevEvent
from models.skill import Skill
from services.ai_provider import chat as ai_chat
from services.pattern_mining import _confidence_to_level, _name_to_slug, _strip_json_fence

logger = logging.getLogger(__name__)

# 成功结局信号
_SUCCESS_SIGNALS = re.compile(
    r'(done|complete|finished|成功|完成|合并|deployed|shipped|released|passed|通过)',
    re.I,
)
# Workflow 相关的意图序列
_WORKFLOW_INTENTS = {
    'feature': ['coding', 'testing', 'committing'],
    'bugfix': ['debugging', 'coding', 'testing', 'committing'],
    'review': ['reviewing', 'committing'],
    'deploy': ['building', 'deploying'],
    'refactor': ['reviewing', 'coding', 'testing', 'committing'],
    'research': ['learning', 'coding'],
}


def _episode_to_workflow_context(episode: Episode) -> dict:
    """将 Episode 转为 Workflow 分析上下文"""
    features = json.loads(episode.features) if episode.features else {}
    tool_dist = features.get('tool_dist', {})
    intent_dist = features.get('intent_dist', {})

    # 提取主要工具链
    top_tools = [k for k, v in sorted(tool_dist.items(), key=lambda x: x[1], reverse=True) if v > 0.05]
    top_intents = [k for k, v in sorted(intent_dist.items(), key=lambda x: x[1], reverse=True) if v > 0.05]

    tool_seq = json.loads(episode.tool_sequence) if episode.tool_sequence else []
    intent_seq = json.loads(episode.intent_sequence) if episode.intent_sequence else []

    return {
        'episode_id': episode.id,
        'project': episode.project or '',
        'task_category': episode.task_category or 'unknown',
        'task_label': episode.task_label or '',
        'duration_min': round((episode.duration_seconds or 0) / 60),
        'outcome': episode.outcome or 'unknown',
        'top_tools': top_tools[:5],
        'top_intents': top_intents[:5],
        'tool_sequence_sample': tool_seq[:8],
        'intent_sequence_sample': intent_seq[:8],
        'has_tests': features.get('has_tests', False),
        'has_commits': features.get('has_commits', False),
        'error_rate': features.get('error_rate', 0),
        'event_count': episode.event_count or 0,
    }


def _find_linked_sessions(db: Session, episode: Episode) -> list[OpenClawSession]:
    """找与该 Episode 时间窗口重叠的 AI 对话"""
    session_ids = json.loads(episode.session_ids) if episode.session_ids else []
    if session_ids:
        sessions = db.query(OpenClawSession).filter(
            OpenClawSession.id.in_(session_ids),
        ).all()
        if sessions:
            return sessions

    # 按时间窗口查找
    start = episode.start_ts - 300
    end = (episode.end_ts or episode.start_ts) + 300
    return db.query(OpenClawSession).filter(
        OpenClawSession.created_at >= start,
        OpenClawSession.created_at <= end,
    ).all()


def _extract_session_summary(session: OpenClawSession) -> str:
    """提取 session 摘要"""
    if session.analysis_summary:
        return session.analysis_summary[:500]
    if session.summary:
        return session.summary[:500]
    # 从 messages 提取摘要
    try:
        msgs = json.loads(session.messages) if session.messages else []
    except (json.JSONDecodeError, TypeError):
        msgs = []
    parts = []
    for m in msgs[:6]:
        if m.get('role') == 'user':
            content = str(m.get('content', ''))
            if len(content) > 20:
                parts.append(f'用户: {content[:150]}')
    return ' | '.join(parts)[:400]


def infer_workflows_from_episodes(db: Session, lookback_hours: int = 336) -> list[dict]:
    """
    主入口: 从近期成功 Episode 中重建 Workflow 模板。
    只处理有明确结果的 episode（success/has_commits）。
    """
    cutoff = int(time.time()) - lookback_hours * 3600
    episodes = db.query(Episode).filter(
        Episode.start_ts > cutoff,
        Episode.event_count >= 5,
    ).order_by(Episode.start_ts.desc()).limit(100).all()

    if len(episodes) < 3:
        logger.info(f'Workflow inference: not enough episodes ({len(episodes)})')
        return []

    # 只取成功的 episode
    successful = []
    for ep in episodes:
        features = json.loads(ep.features) if ep.features else {}
        if ep.outcome == 'success' or features.get('has_commits'):
            successful.append(ep)

    if len(successful) < 2:
        logger.info('Workflow inference: not enough successful episodes')
        return []

    # 按任务类别分组
    by_category: dict[str, list[Episode]] = defaultdict(list)
    for ep in successful:
        cat = ep.task_category or 'unknown'
        by_category[cat].append(ep)

    workflow_candidates = []

    for category, eps in by_category.items():
        if len(eps) < 2:
            continue
        if category in ('unknown', ''):
            continue

        # 提取该类别的工具序列模式
        all_intent_seqs = []
        all_tool_seqs = []
        durations = []
        error_rates = []

        for ep in eps:
            ctx = _episode_to_workflow_context(ep)
            if ctx['intent_sequence_sample']:
                all_intent_seqs.append(tuple(ctx['intent_sequence_sample'][:6]))
            if ctx['tool_sequence_sample']:
                all_tool_seqs.append(tuple(ctx['tool_sequence_sample'][:6]))
            durations.append(ctx['duration_min'])
            error_rates.append(ctx['error_rate'])

        # 找最常见的序列模式
        intent_counter = Counter(all_intent_seqs)
        most_common_intent = intent_counter.most_common(1)
        dominant_seq = list(most_common_intent[0][0]) if most_common_intent else []

        avg_duration = round(sum(durations) / len(durations)) if durations else 0
        avg_error_rate = round(sum(error_rates) / len(error_rates), 3) if error_rates else 0

        # 找关联的 AI 对话
        session_summaries = []
        for ep in eps[:3]:
            linked = _find_linked_sessions(db, ep)
            for s in linked[:2]:
                summary = _extract_session_summary(s)
                if summary:
                    session_summaries.append(summary)

        workflow_candidates.append({
            'category': category,
            'episode_count': len(eps),
            'dominant_intent_sequence': dominant_seq,
            'avg_duration_min': avg_duration,
            'avg_error_rate': avg_error_rate,
            'has_ai_context': len(session_summaries) > 0,
            'ai_context_summaries': session_summaries[:3],
            'projects': list(set(ep.project for ep in eps if ep.project))[:3],
        })

    if not workflow_candidates:
        return []

    # AI 将候选转为 Workflow 模板
    workflows = _ai_build_workflow_templates(workflow_candidates)
    _enrich_workflows_with_skill_matches(db, workflows)
    return workflows


def _step_matches_skill(step_text_lc: str, skill_lc: str) -> bool:
    """Lowercase substring containment (either direction)."""
    if not skill_lc or not step_text_lc:
        return False
    return skill_lc in step_text_lc or step_text_lc in skill_lc


def _enrich_workflows_with_skill_matches(db: Session, workflows: list[dict]) -> None:
    """Cross-reference inferred workflows with Skill rows; mutates workflows in place."""
    if not workflows:
        return

    skills = db.query(Skill).all()
    skill_pairs = [(s.name.strip(), (s.name or '').lower().strip()) for s in skills if s.name]

    for wf in workflows:
        steps = wf.get('steps') or []
        matched_names: set[str] = set()
        steps_with_match = 0

        for step in steps:
            if not isinstance(step, dict):
                continue
            action = str(step.get('action', '') or '').lower()
            tool = str(step.get('tool', '') or '').lower()
            step_text_lc = f'{action} {tool}'.strip()

            step_hit = False
            for orig_name, skill_lc in skill_pairs:
                if _step_matches_skill(step_text_lc, skill_lc):
                    matched_names.add(orig_name)
                    step_hit = True

            if step_hit:
                steps_with_match += 1

        n = len([s for s in steps if isinstance(s, dict)])
        wf['matched_skills'] = sorted(matched_names)
        wf['skill_coverage'] = round(100 * steps_with_match / n) if n else 0


def _ai_build_workflow_templates(candidates: list[dict]) -> list[dict]:
    """AI 将 Episode 聚合数据 → 完整 Workflow 模板"""
    candidates_text = json.dumps(candidates[:6], ensure_ascii=False, indent=2)

    prompt = (
        "你是开发流程专家，专门从开发行为数据中提炼可重用的工作流模板。\n\n"
        "以下是从真实开发记录中聚合的任务模式统计:\n\n"
        f"{candidates_text}\n\n"
        "请为每种有意义的任务类型生成一个标准 Workflow 模板。\n"
        "Workflow 是一组步骤的有序清单，下次做同类任务时可直接参考。\n\n"
        "返回严格 JSON (不要 markdown fence):\n"
        '{"workflows": [{'
        '"name": "Workflow名称（如: 功能开发工作流）",'
        '"category": "coding|review|git|devops|collaboration",'
        '"task_type": "任务类型",'
        '"steps": ['
        '{"order": 1, "action": "动作描述", "tool": "工具名", "duration_hint": "5min", "checkpoint": "检查点"}'
        '],'
        '"trigger": "触发条件（什么情况下使用这个 Workflow）",'
        '"expected_outcome": "预期结果",'
        '"avg_duration_min": 30,'
        '"confidence": 70,'
        '"evidence": "基于什么数据推断的"'
        '}]}'
    )

    try:
        text = ai_chat([{'role': 'user', 'content': prompt}], max_tokens=2000)
        if not text:
            return []
        data = json.loads(_strip_json_fence(text))
        workflows = data.get('workflows', [])
        result = []
        for wf in workflows:
            if not isinstance(wf, dict) or not wf.get('name') or not wf.get('steps'):
                continue
            steps = wf.get('steps', [])
            if not steps:
                continue

            # 生成可注入 AI 的 body
            body_lines = [f'## {wf["name"]}\n']
            body_lines.append(f'**触发**: {wf.get("trigger", "")}\n')
            body_lines.append('**步骤**:\n')
            for step in steps:
                tool = step.get('tool', '')
                checkpoint = step.get('checkpoint', '')
                line = f'{step.get("order", "?")}. **{step.get("action", "")}**'
                if tool:
                    line += f' ({tool})'
                if checkpoint:
                    line += f' → 检查: {checkpoint}'
                body_lines.append(line)
            body_lines.append(f'\n**预期结果**: {wf.get("expected_outcome", "")}')
            body_lines.append(f'\n**典型耗时**: {wf.get("avg_duration_min", "?")} 分钟')

            category = wf.get('category', 'coding')
            if category not in ('coding', 'review', 'git', 'devops', 'collaboration'):
                category = 'coding'

            result.append({
                'type': 'inferred_workflow',
                'name': str(wf['name']).strip(),
                'category': category,
                'description': f"基于 {next((c['episode_count'] for c in candidates if c['category'] == wf.get('task_type', '')), '多')} 次实际任务推断",
                'confidence': max(40, min(88, int(wf.get('confidence', 65)))),
                'trigger': str(wf.get('trigger', '')).strip(),
                'body': '\n'.join(body_lines),
                'steps': steps,
                'avg_duration_min': wf.get('avg_duration_min', 0),
                'source': 'workflow_inference',
                'evidence': [{'context': 'episode_workflow', 'insight': str(wf.get('evidence', '')), 'confidence': int(wf.get('confidence', 65))}],
            })
        return result[:4]
    except Exception as e:
        logger.warning(f'Workflow template build failed: {e}')
        return []
