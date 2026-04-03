import json
import logging
import re
import time
from collections import Counter

from sqlalchemy.orm import Session

from models.openclaw import OpenClawSession
from models.episode import Episode
from services.ai_provider import chat as ai_chat
from services.pattern_mining import _strip_json_fence

logger = logging.getLogger(__name__)

# 从 AI 对话内容中提取行为信号的关键词
_SIGNAL_PATTERNS = {
    'debugging': re.compile(r'(error|bug|fix|debug|traceback|exception|crash|报错|修复|调试)', re.I),
    'architecture': re.compile(r'(design|architect|refactor|pattern|structure|架构|重构|设计模式)', re.I),
    'testing': re.compile(r'(test|spec|assert|coverage|mock|测试|断言|覆盖率)', re.I),
    'deployment': re.compile(r'(deploy|docker|ci/cd|pipeline|nginx|部署|容器|流水线)', re.I),
    'learning': re.compile(r'(learn|tutorial|explain|how.?to|understand|学习|教程|理解)', re.I),
    'review': re.compile(r'(review|pr|pull.?request|code.?review|审查|评审)', re.I),
    'optimization': re.compile(r'(optim|perf|speed|cache|memory|性能|优化|缓存)', re.I),
}

# 从对话中提取工具/技术偏好
_TECH_PATTERNS = {
    'python': re.compile(r'\b(python|pip|pytest|django|flask|fastapi)\b', re.I),
    'javascript': re.compile(r'\b(javascript|typescript|node|npm|pnpm|react|vue|next)\b', re.I),
    'git': re.compile(r'\b(git|commit|branch|merge|rebase|cherry.?pick)\b', re.I),
    'docker': re.compile(r'\b(docker|container|k8s|kubernetes|compose)\b', re.I),
    'database': re.compile(r'\b(sql|postgres|mysql|sqlite|redis|mongo|数据库)\b', re.I),
    'ai_tools': re.compile(r'\b(claude|gpt|copilot|cursor|codex|ai.?assist)\b', re.I),
}


def _extract_session_text(session: OpenClawSession) -> str:
    # 提取对话的纯文本内容
    messages = json.loads(session.messages) if session.messages else []
    parts = []
    for msg in messages:
        content = msg.get('content', '')
        if isinstance(content, str) and len(content) > 5:
            parts.append(content[:2000])
    return '\n'.join(parts)


def _extract_signals(text: str) -> dict:
    # 从文本中提取行为信号
    signals = {}
    for signal_type, pattern in _SIGNAL_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            signals[signal_type] = len(matches)
    return signals


def _extract_tech_stack(text: str) -> dict:
    # 从文本中提取技术栈偏好
    techs = {}
    for tech, pattern in _TECH_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            techs[tech] = len(matches)
    return techs


def _extract_problem_solving_patterns(messages: list[dict]) -> list[dict]:
    # 从对话轮次中提取问题解决模式
    # 模式: user提问 -> assistant回答 -> user确认/追问
    patterns = []
    for i in range(len(messages) - 1):
        if messages[i].get('role') != 'user':
            continue
        user_msg = messages[i].get('content', '')
        if len(user_msg) < 10:
            continue

        # 检查是否是问题/求助
        is_question = bool(re.search(r'[?？]|怎么|如何|为什么|how|why|what|can you', user_msg, re.I))
        is_error_report = bool(re.search(r'error|bug|报错|出错|失败', user_msg, re.I))

        if not is_question and not is_error_report:
            continue

        # 看 assistant 回答后用户是否满意
        next_msgs = messages[i + 1:i + 3]
        resolved = False
        for nm in next_msgs:
            if nm.get('role') == 'user':
                content = nm.get('content', '')
                if re.search(r'(thank|ok|好的|可以|成功|解决|works|perfect)', content, re.I):
                    resolved = True
                    break

        pattern_type = 'error_resolution' if is_error_report else 'question_answer'
        patterns.append({
            'type': pattern_type,
            'question_excerpt': user_msg[:150],
            'resolved': resolved,
        })

    return patterns


def mine_from_sessions(db: Session, lookback_hours: int = 168) -> list[dict]:
    # 从 OpenClawSession 对话内容中挖掘行为模式
    cutoff = int(time.time()) - lookback_hours * 3600
    sessions = db.query(OpenClawSession).filter(
        OpenClawSession.created_at > cutoff,
    ).order_by(OpenClawSession.created_at.desc()).limit(100).all()

    if len(sessions) < 2:
        logger.info(f'Not enough sessions for mining: {len(sessions)}')
        return []

    # 聚合所有对话的信号
    all_signals = Counter()
    all_techs = Counter()
    all_problem_patterns = []
    session_categories = Counter()

    for session in sessions:
        text = _extract_session_text(session)
        if len(text) < 50:
            continue

        signals = _extract_signals(text)
        techs = _extract_tech_stack(text)
        for k, v in signals.items():
            all_signals[k] += v
        for k, v in techs.items():
            all_techs[k] += v

        messages = json.loads(session.messages) if session.messages else []
        problem_patterns = _extract_problem_solving_patterns(messages)
        all_problem_patterns.extend(problem_patterns)

        if session.category:
            session_categories[session.category] += 1

    candidates = []

    # 1. AI 协作偏好模式
    if all_signals:
        top_signal = all_signals.most_common(1)[0]
        if top_signal[1] >= 3:
            candidates.append({
                'type': 'ai_collaboration_focus',
                'name': f'AI协作偏好: 主要用于{top_signal[0]}',
                'description': f'在 {len(sessions)} 次AI对话中，{top_signal[0]} 相关讨论出现 {top_signal[1]} 次，是最频繁的协作场景',
                'confidence': min(85, 40 + top_signal[1] * 3),
                'occurrences': top_signal[1],
                'examples': [f'{k}: {v}次' for k, v in all_signals.most_common(3)],
                'evidence': [{'context': 'session_signal_mining', 'insight': f'AI对话信号分布: {dict(all_signals.most_common(5))}', 'confidence': min(85, 40 + top_signal[1] * 3)}],
            })

    # 2. 技术栈偏好
    if all_techs:
        top_tech = all_techs.most_common(1)[0]
        if top_tech[1] >= 5:
            candidates.append({
                'type': 'tech_stack_preference',
                'name': f'技术栈偏好: {top_tech[0]} 为主',
                'description': f'AI对话中 {top_tech[0]} 相关讨论最多({top_tech[1]}次)，表明这是主要技术栈',
                'confidence': min(80, 35 + top_tech[1] * 2),
                'occurrences': top_tech[1],
                'examples': [f'{k}: {v}次' for k, v in all_techs.most_common(4)],
                'evidence': [{'context': 'session_tech_mining', 'insight': f'技术栈分布: {dict(all_techs.most_common(5))}', 'confidence': min(80, 35 + top_tech[1] * 2)}],
            })

    # 3. 问题解决模式
    if all_problem_patterns:
        error_resolutions = [p for p in all_problem_patterns if p['type'] == 'error_resolution']
        if len(error_resolutions) >= 2:
            resolved_count = sum(1 for p in error_resolutions if p['resolved'])
            total = len(error_resolutions)
            resolve_rate = resolved_count / total if total else 0
            candidates.append({
                'type': 'problem_solving_style',
                'name': f'问题解决风格: AI辅助调试 (解决率{resolve_rate:.0%})',
                'description': f'在 {total} 次错误报告中，{resolved_count} 次通过AI对话解决，解决率 {resolve_rate:.0%}',
                'confidence': min(80, 35 + total * 4),
                'occurrences': total,
                'examples': [p['question_excerpt'][:80] for p in error_resolutions[:3]],
                'evidence': [{'context': 'session_problem_mining', 'insight': f'{total}次错误报告, 解决率{resolve_rate:.0%}', 'confidence': min(80, 35 + total * 4)}],
            })

    # 4. AI 使用频率模式
    if session_categories:
        top_cat = session_categories.most_common(1)[0]
        if top_cat[1] >= 3:
            candidates.append({
                'type': 'ai_usage_pattern',
                'name': f'AI使用模式: {top_cat[0]}类对话最多',
                'description': f'{top_cat[0]} 类AI对话占比最高({top_cat[1]}/{len(sessions)}), 表明这是主要AI使用场景',
                'confidence': min(75, 30 + top_cat[1] * 5),
                'occurrences': top_cat[1],
                'examples': [f'{k}: {v}次' for k, v in session_categories.most_common(3)],
                'evidence': [{'context': 'session_category_mining', 'insight': f'对话类别分布: {dict(session_categories)}', 'confidence': min(75, 30 + top_cat[1] * 5)}],
            })

    # 5. AI 深度语义精炼 (如果候选足够多)
    if len(candidates) >= 2:
        refined = _ai_refine_session_patterns(candidates)
        if refined:
            return refined

    return candidates


def _ai_refine_session_patterns(candidates: list[dict]) -> list[dict]:
    prompt = (
        "你是开发行为分析师。以下是从开发者AI对话中挖掘出的行为模式候选。\n"
        "请:\n"
        "1. 过滤掉无实际指导价值的模式\n"
        "2. 将有价值的模式改写为可执行行为规范\n"
        "3. 为每个规范生成: when/do/expect/anti_pattern\n\n"
        "返回严格JSON:\n"
        '{"norms":[{"name":"规范名","category":"coding|review|git|devops|collaboration",'
        '"when":"触发条件","do":"具体动作","expect":"预期结果","anti_pattern":"反模式",'
        '"confidence":70,"evidence_summary":"证据摘要"}]}\n\n'
        f"候选:\n{json.dumps(candidates[:8], ensure_ascii=False)}"
    )
    try:
        text = ai_chat([{'role': 'user', 'content': prompt}], max_tokens=1200)
        if not text:
            return []
        data = json.loads(_strip_json_fence(text))
        norms = data.get('norms', [])
        results = []
        for item in norms:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name', '')).strip()
            if not name:
                continue
            when = str(item.get('when', '')).strip()
            do = str(item.get('do', '')).strip()
            body_parts = [f'## {name}']
            if when:
                body_parts.append(f'\n### 触发条件\n{when}')
            if do:
                body_parts.append(f'\n### 执行动作\n{do}')
            expect = str(item.get('expect', '')).strip()
            if expect:
                body_parts.append(f'\n### 预期结果\n{expect}')
            anti = str(item.get('anti_pattern', '')).strip()
            if anti:
                body_parts.append(f'\n### 反模式\n{anti}')

            category = str(item.get('category', 'coding'))
            if category not in ('coding', 'review', 'git', 'devops', 'collaboration'):
                category = 'coding'

            results.append({
                'type': 'session_norm',
                'name': name,
                'description': f'{when} => {do}' if when and do else name,
                'category': category,
                'confidence': max(1, min(99, int(item.get('confidence', 65)))),
                'occurrences': 1,
                'examples': [str(item.get('evidence_summary', ''))],
                'trigger': {'when': when, 'event': '', 'context': [expect]} if when else name,
                'body': '\n'.join(body_parts),
                'evidence': [{'context': 'session_ai_refine', 'insight': str(item.get('evidence_summary', '')), 'confidence': int(item.get('confidence', 65))}],
            })
        return results[:6]
    except Exception as e:
        logger.warning(f'AI session pattern refine failed: {e}')
        return []
