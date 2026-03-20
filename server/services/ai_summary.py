import json
from datetime import datetime, timezone
from collections import defaultdict

from models.event import DevEvent
from models.digest import DailySummary
from services.ai_provider import chat


def _events_to_summary_text(events):
    # 将事件列表转为文本描述
    source_counts = defaultdict(int)
    project_counts = defaultdict(int)
    actions = []

    for e in events:
        source_counts[e.source] += 1
        project_counts[e.project] += 1
        actions.append(f'[{e.source}] {e.action[:80]}')

    lines = [
        f'总事件数: {len(events)}',
        f'来源分布: {dict(source_counts)}',
        f'项目分布: {dict(project_counts)}',
        '代表性事件:',
    ]
    # 取前 20 个代表性事件
    step = max(1, len(actions) // 20)
    for i in range(0, len(actions), step):
        if len(lines) > 25:
            break
        lines.append(f'  - {actions[i]}')

    return '\n'.join(lines)


def _heuristic_summary(events, top_projects, top_commands, ai_session_count):
    # 无 API / API 失败时使用增强模板
    source_desc = []
    source_labels = {'terminal': '终端', 'git': 'Git', 'openclaw': 'OpenClaw', 'claude_code': 'Claude Code', 'codex': 'Codex', 'env': '环境'}
    source_map = defaultdict(int)
    for e in events:
        source_map[e.source] += 1
    for src, cnt in sorted(source_map.items(), key=lambda x: x[1], reverse=True)[:3]:
        source_desc.append(f'{source_labels.get(src, src)} {cnt} 次')
    source_str = '、'.join(source_desc) if source_desc else '无明确来源'
    proj_str = '、'.join(n for n, _ in top_projects[:3]) if top_projects else '未知'
    cmd_str = ''
    if top_commands:
        cmd_str = f'常用命令: {", ".join(c for c, _ in top_commands[:3])}。'
    return f'今日 {len(events)} 个事件 ({source_str})，AI 协作 {ai_session_count} 次。活跃项目: {proj_str}。{cmd_str}'


def generate_daily_summary(db, date_str):
    # 解析日期范围
    dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    day_start = int(dt.timestamp())
    day_end = day_start + 86400

    events = db.query(DevEvent).filter(
        DevEvent.timestamp >= day_start,
        DevEvent.timestamp < day_end,
        ~DevEvent.tags.contains('"seed"'),
    ).order_by(DevEvent.timestamp).all()

    if not events:
        return {'date': date_str, 'ai_summary': '今天没有研究活动。', 'event_count': 0}

    # 统计数据
    project_counts = defaultdict(int)
    cmd_counts = defaultdict(int)
    ai_session_ids = set()
    ai_activity_count = 0

    for e in events:
        project_counts[e.project] += 1
        if e.source == 'terminal':
            cmd = e.action.split(' ')[0]
            cmd_counts[cmd] += 1
        if e.source in ('openclaw', 'claude_code', 'codex'):
            ai_activity_count += 1
            if e.openclaw_session_id:
                ai_session_ids.add(e.openclaw_session_id)

    top_projects = sorted(project_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_commands = sorted(cmd_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ai_session_count = len(ai_session_ids) if ai_session_ids else ai_activity_count

    # 尝试用 AI 生成摘要
    event_text = _events_to_summary_text(events)
    prompt = f"""请用中文为以下开发者的一天活动生成简洁摘要（2-3句话）。重点描述主要工作内容和成果。

日期: {date_str}
{event_text}"""

    ai_summary = chat([{'role': 'user', 'content': prompt}], max_tokens=200)
    if not ai_summary:
        ai_summary = _heuristic_summary(events, top_projects, top_commands, ai_session_count)

    # 更新或创建 DailySummary
    existing = db.query(DailySummary).filter(DailySummary.date == date_str).first()
    if existing:
        existing.event_count = len(events)
        existing.top_projects = json.dumps([{'name': n, 'count': c} for n, c in top_projects])
        existing.top_commands = json.dumps([{'cmd': c, 'count': n} for c, n in top_commands])
        existing.ai_summary = ai_summary
        existing.openclaw_sessions = ai_session_count
    else:
        db.add(DailySummary(
            date=date_str,
            event_count=len(events),
            top_projects=json.dumps([{'name': n, 'count': c} for n, c in top_projects]),
            top_commands=json.dumps([{'cmd': c, 'count': n} for c, n in top_commands]),
            ai_summary=ai_summary,
            openclaw_sessions=ai_session_count,
        ))
    db.commit()

    return {
        'date': date_str, 'event_count': len(events),
        'top_projects': [{'name': n, 'count': c} for n, c in top_projects],
        'top_commands': [{'cmd': c, 'count': n} for c, n in top_commands],
        'ai_summary': ai_summary, 'openclaw_sessions': ai_session_count,
    }


def generate_pattern_description(pattern_name, evidence_events):
    events_text = '\n'.join(f'- {e}' for e in evidence_events[:10])
    prompt = f"""请用中文为以下开发行为模式生成简洁描述（1-2句话）。

模式名称: {pattern_name}
相关事件:
{events_text}"""

    result = chat([{'role': 'user', 'content': prompt}], max_tokens=100)
    return result if result else f'行为模式: {pattern_name}'
