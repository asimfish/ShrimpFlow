import os
import json
from datetime import datetime, timezone
from collections import defaultdict

from dotenv import load_dotenv

from models.event import DevEvent
from models.digest import DailySummary

load_dotenv()


def _get_client():
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


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

    # 尝试用 Claude 生成摘要
    client = _get_client()
    if client:
        event_text = _events_to_summary_text(events)
        prompt = f"""请用中文为以下开发者的一天活动生成简洁摘要（2-3句话）。重点描述主要工作内容和成果。

日期: {date_str}
{event_text}"""

        try:
            response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=200,
                messages=[{'role': 'user', 'content': prompt}],
            )
            ai_summary = response.content[0].text
        except Exception:
            ai_summary = f'今天共产生 {len(events)} 个事件，AI 协作 {ai_session_count} 次。主要集中在 {top_projects[0][0] if top_projects else "未知"} 项目。'
    else:
        # 无 API key 时使用增强模板
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
        ai_summary = f'今日 {len(events)} 个事件 ({source_str})，AI 协作 {ai_session_count} 次。活跃项目: {proj_str}。{cmd_str}'

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
    client = _get_client()
    if not client:
        return f'行为模式: {pattern_name}'

    events_text = '\n'.join(f'- {e}' for e in evidence_events[:10])
    prompt = f"""请用中文为以下开发行为模式生成简洁描述（1-2句话）。

模式名称: {pattern_name}
相关事件:
{events_text}"""

    try:
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=100,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return response.content[0].text
    except Exception:
        return f'行为模式: {pattern_name}'
