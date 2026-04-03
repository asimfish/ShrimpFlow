"""
CoT 推理链挖掘 (M1)
比 CatchMe 更深：不只记录"做了什么"，而是从 AI 对话中推断"怎么思考的"

三类信号:
1. 推理结构 - assistant 消息里的思考链（先分析→再拆解→最后实现）
2. 用户修正信号 - 用户对 AI 回答的修正揭示真实偏好
3. 决策链 - 面对选择时的决策模式（总是选 X 而不是 Y）
"""
import json
import logging
import re
import time
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from models.invocation import OpenClawInvocationLog
from models.openclaw import OpenClawSession
from services.ai_provider import chat as ai_chat
from services.pattern_mining import (
    bayesian_update, _confidence_to_level, _name_to_slug, _strip_json_fence,
)
from services.skill_tracker import mine_skill_workflows

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 推理结构识别正则
# ─────────────────────────────────────────────

# 步骤化思考（"首先...然后...最后..."）
_STEP_PATTERNS = re.compile(
    r'(首先|第一步|step\s*1|first[,，]?\s+i.ll|to\s+start|let.s\s+begin)'
    r'|([①②③④⑤]|\d+[.、．])\s*\S',
    re.I,
)
# 分析前置（"让我先分析/理解/检查"）
_ANALYZE_FIRST = re.compile(
    r'(let me (first |)analyze|let me (first |)check|let me (understand|look at|examine))'
    r'|(先(分析|理解|检查|看看|了解))'
    r'|(我(来|先)(分析|拆解|梳理|理解))',
    re.I,
)
# 权衡决策（"X vs Y"，"我选择X因为"）
_TRADEOFF = re.compile(
    r'(vs\.?|versus|compared to|alternatively|instead of|rather than|一方面.*另一方面|相比|选择.*因为|比较.*更好)',
    re.I,
)
# 验证习惯（"让我测试/验证/确认"）
_VERIFY_HABIT = re.compile(
    r'(let.?s (test|verify|check|confirm|validate))'
    r'|(测试(一下|下|看看)|验证(一下|下)|确认(一下|下))',
    re.I,
)
# 用户修正信号（"不是这样/改成/应该是"）
_USER_CORRECTION = re.compile(
    r'(不(对|是|行|要|需要)|错了|不应该|应该(是|用)|改(成|为|一下)|不(用|要用)|换(成|为))',
    re.I,
)
# 用户偏好肯定（"好的/可以/完美/正是"）
_USER_CONFIRM = re.compile(
    r'(^(好的?|可以|对|是的?|没错|完美|正是|just right|perfect|exactly|great|thanks)'
    r'|(这(样|个)就(行|好|可以)了))',
    re.I,
)


def _extract_messages(session: OpenClawSession) -> list[dict]:
    try:
        msgs = json.loads(session.messages) if session.messages else []
        return [m for m in msgs if isinstance(m, dict) and m.get('role') and m.get('content')]
    except Exception:
        return []


def _is_meaningful(text: str, min_len: int = 30) -> bool:
    return bool(text) and len(text.strip()) >= min_len


def analyze_single_session(session: OpenClawSession) -> dict:
    """
    分析单个 session，提取 CoT 特征向量。
    返回: {reasoning_depth, step_thinking, analyze_first, tradeoff_thinking,
           verify_habit, correction_count, confirm_count, turn_count,
           avg_assistant_len, correction_excerpts, decision_excerpts}
    """
    messages = _extract_messages(session)
    if len(messages) < 2:
        return {}

    step_count = 0
    analyze_count = 0
    tradeoff_count = 0
    verify_count = 0
    correction_count = 0
    confirm_count = 0
    assistant_lens = []
    correction_excerpts = []
    decision_excerpts = []

    for i, msg in enumerate(messages):
        role = msg.get('role', '')
        content = str(msg.get('content', ''))
        if not content:
            continue

        if role == 'assistant':
            assistant_lens.append(len(content))
            if _STEP_PATTERNS.search(content):
                step_count += 1
            if _ANALYZE_FIRST.search(content):
                analyze_count += 1
            m = _TRADEOFF.search(content)
            if m:
                tradeoff_count += 1
                # 提取决策句子
                start = max(0, m.start() - 60)
                end = min(len(content), m.end() + 120)
                decision_excerpts.append(content[start:end].strip())

            if _VERIFY_HABIT.search(content):
                verify_count += 1

        elif role == 'user':
            m_corr = _USER_CORRECTION.search(content)
            if m_corr and _is_meaningful(content):
                correction_count += 1
                correction_excerpts.append(content[:200])
            elif _USER_CONFIRM.match(content.strip()):
                confirm_count += 1

    turn_count = len(messages)
    avg_len = sum(assistant_lens) / len(assistant_lens) if assistant_lens else 0

    # 综合推理深度得分 0-100
    reasoning_depth = min(100, int(
        step_count * 15
        + analyze_count * 20
        + tradeoff_count * 15
        + verify_count * 10
        + (1 if avg_len > 800 else 0) * 15
        + min(20, turn_count * 2)
    ))

    return {
        'session_id': session.id,
        'reasoning_depth': reasoning_depth,
        'step_thinking': step_count,
        'analyze_first': analyze_count,
        'tradeoff_thinking': tradeoff_count,
        'verify_habit': verify_count,
        'correction_count': correction_count,
        'confirm_count': confirm_count,
        'turn_count': turn_count,
        'avg_assistant_len': round(avg_len),
        'correction_excerpts': correction_excerpts[:3],
        'decision_excerpts': decision_excerpts[:3],
        'category': session.category or '',
        'project': session.project or '',
    }


def aggregate_cot_profile(analyses: list[dict]) -> dict:
    """将多个 session 分析聚合为用户 CoT 画像"""
    if not analyses:
        return {}

    total = len(analyses)
    return {
        'session_count': total,
        'avg_reasoning_depth': round(sum(a['reasoning_depth'] for a in analyses) / total),
        'step_thinking_rate': round(sum(1 for a in analyses if a['step_thinking'] > 0) / total, 2),
        'analyze_first_rate': round(sum(1 for a in analyses if a['analyze_first'] > 0) / total, 2),
        'tradeoff_rate': round(sum(1 for a in analyses if a['tradeoff_thinking'] > 0) / total, 2),
        'verify_rate': round(sum(1 for a in analyses if a['verify_habit'] > 0) / total, 2),
        'total_corrections': sum(a['correction_count'] for a in analyses),
        'total_confirms': sum(a['confirm_count'] for a in analyses),
        'correction_excerpts': [
            e for a in analyses for e in a.get('correction_excerpts', [])
        ][:10],
        'decision_excerpts': [
            e for a in analyses for e in a.get('decision_excerpts', [])
        ][:10],
        'top_categories': [
            k for k, _ in Counter(a['category'] for a in analyses if a['category']).most_common(3)
        ],
    }


def _ai_extract_cot_skills(cot_profile: dict, correction_excerpts: list[str]) -> list[dict]:
    """
    调用 AI 将 CoT 特征 + 修正语料 → 可执行 Skill 候选。
    这是 CatchMe 没有的核心能力。
    """
    excerpts_text = '\n'.join(f'- {e[:200]}' for e in correction_excerpts[:8]) or '(无修正样本)'
    prompt = (
        "你是开发者行为分析专家，专门从 AI 对话记录中提炼可执行的个人工作规范。\n\n"
        "以下是一位开发者在过去数周内与 AI 助手对话的行为统计:\n\n"
        f"- 平均推理深度: {cot_profile.get('avg_reasoning_depth', 0)}/100\n"
        f"- 步骤化思考率: {cot_profile.get('step_thinking_rate', 0):.0%}\n"
        f"- 先分析后实现率: {cot_profile.get('analyze_first_rate', 0):.0%}\n"
        f"- 权衡决策率: {cot_profile.get('tradeoff_rate', 0):.0%}\n"
        f"- 验证确认率: {cot_profile.get('verify_rate', 0):.0%}\n"
        f"- 对 AI 的修正次数: {cot_profile.get('total_corrections', 0)}\n"
        f"- 对话轮次总计: {cot_profile.get('session_count', 0)}\n\n"
        "用户修正 AI 回答的原话样本（揭示真实偏好）:\n"
        f"{excerpts_text}\n\n"
        "请基于以上数据，推断出 2-4 个该开发者的**高价值个人工作规范**。\n"
        "每个规范必须是**可注入 AI 提示词**的可执行指令，格式如 CLAUDE.md 规则。\n\n"
        "返回严格 JSON (不要 markdown fence):\n"
        '{"skills": [{'
        '"name": "规范名称",'
        '"category": "coding|review|git|devops|collaboration",'
        '"trigger": "触发场景描述",'
        '"body": "完整的 Markdown 格式指令，这段文字将被直接注入到 AI 上下文中",'
        '"confidence": 60,'
        '"evidence": "从哪些信号推断出来的",'
        '"cot_source": "step_thinking|analyze_first|tradeoff|verify|correction"'
        '}]}'
    )
    try:
        text = ai_chat([{'role': 'user', 'content': prompt}], max_tokens=1500)
        if not text:
            return []
        data = json.loads(_strip_json_fence(text))
        skills = data.get('skills', [])
        result = []
        for s in skills:
            if not isinstance(s, dict) or not s.get('name') or not s.get('body'):
                continue
            category = s.get('category', 'coding')
            if category not in ('coding', 'review', 'git', 'devops', 'collaboration'):
                category = 'coding'
            result.append({
                'type': 'cot_derived_skill',
                'name': str(s['name']).strip(),
                'category': category,
                'description': str(s.get('evidence', '')).strip(),
                'confidence': max(40, min(90, int(s.get('confidence', 65)))),
                'trigger': str(s.get('trigger', '')).strip(),
                'body': str(s['body']).strip(),
                'cot_source': str(s.get('cot_source', 'mixed')),
                'source': 'cot_mining',
                'evidence': [{'context': 'cot_analysis', 'insight': str(s.get('evidence', '')), 'confidence': int(s.get('confidence', 65))}],
            })
        return result[:4]
    except Exception as e:
        logger.warning(f'CoT skill extraction failed: {e}')
        return []


def mine_cot_skills(db: Session, lookback_hours: int = 168) -> list[dict]:
    """
    主入口: 从近期 AI 对话中挖掘 CoT 推理模式 → Skill 候选。
    相比 session_mining.py 的关键词统计，这里做结构化推理分析。
    """
    cutoff = int(time.time()) - lookback_hours * 3600
    sessions = db.query(OpenClawSession).filter(
        OpenClawSession.created_at > cutoff,
        OpenClawSession.messages.isnot(None),
    ).order_by(OpenClawSession.created_at.desc()).limit(80).all()

    if len(sessions) < 3:
        logger.info(f'CoT mining: not enough sessions ({len(sessions)})')
        return []

    # 逐会话分析
    analyses = []
    for session in sessions:
        result = analyze_single_session(session)
        if result and result.get('turn_count', 0) >= 2:
            analyses.append(result)

    if not analyses:
        return []

    profile = aggregate_cot_profile(analyses)
    logger.info(
        f'CoT profile: depth={profile["avg_reasoning_depth"]}, '
        f'step={profile["step_thinking_rate"]:.0%}, '
        f'verify={profile["verify_rate"]:.0%}, '
        f'sessions={profile["session_count"]}'
    )

    # 仅当推理深度足够时才值得提炼
    if profile['avg_reasoning_depth'] < 10 and profile['session_count'] < 5:
        return []

    # AI 提炼可执行 Skill
    skills = _ai_extract_cot_skills(profile, profile.get('correction_excerpts', []))

    # 也返回基于统计的基础模式（不依赖 AI，快速回退）
    stat_patterns = _build_stat_patterns(profile)
    combined = skills + stat_patterns

    # 写入 InvocationLog，供 skill_tracker.mine_skill_workflows() 从 selected_pattern_slugs 挖掘序列
    now_ts = int(time.time())
    anchor_session_id = sessions[0].id
    wrote_log = False
    for cand in combined:
        name = (cand.get('name') or '').strip()
        if not name:
            continue
        # mine_skill_workflows 忽略长度 <2 的序列；第二项 'cot' 标记来源且满足长度
        slug_seq = [_name_to_slug(name), 'cot']
        db.add(OpenClawInvocationLog(
            session_id=anchor_session_id,
            profile_id=None,
            provider='cot_miner',
            model=None,
            selector_type='cot',
            selected_pattern_slugs=json.dumps(slug_seq, ensure_ascii=False),
            prompt_excerpt=(cand.get('trigger') or '')[:500] or None,
            response_summary=(cand.get('description') or '')[:500] or None,
            status='ok',
            created_at=now_ts,
        ))
        wrote_log = True
    if wrote_log:
        db.commit()
        mine_skill_workflows(db)

    return combined


def _build_stat_patterns(profile: dict) -> list[dict]:
    """纯统计的推理模式，不依赖 AI，作为 AI 提炼的补充。"""
    patterns = []
    if profile.get('step_thinking_rate', 0) >= 0.5:
        patterns.append({
            'type': 'cot_stat',
            'name': '步骤化思考习惯',
            'category': 'coding',
            'description': f'{profile["step_thinking_rate"]:.0%} 的对话中 AI 使用了步骤化推理，说明用户偏好结构化解决问题',
            'confidence': min(80, 40 + int(profile['step_thinking_rate'] * 40)),
            'trigger': '面对复杂问题时',
            'body': '## 步骤化推理规范\n\n分析问题时，请始终:\n1. 先理解现状和目标\n2. 分解为可操作的子步骤\n3. 逐步实现，每步给出预期结果\n4. 最后验证整体结果',
            'cot_source': 'step_thinking',
            'source': 'cot_stat',
            'evidence': [{'context': 'cot_stat', 'insight': f'步骤化思考出现率 {profile["step_thinking_rate"]:.0%}', 'confidence': min(80, 40 + int(profile['step_thinking_rate'] * 40))}],
        })
    if profile.get('verify_rate', 0) >= 0.4:
        patterns.append({
            'type': 'cot_stat',
            'name': '验证驱动开发习惯',
            'category': 'coding',
            'description': f'{profile["verify_rate"]:.0%} 的对话包含验证步骤，用户习惯在实现后立即验证',
            'confidence': min(75, 35 + int(profile['verify_rate'] * 40)),
            'trigger': '完成代码实现后',
            'body': '## 验证驱动规范\n\n每次代码修改后，必须:\n- 说明如何验证该修改的正确性\n- 提供可直接运行的验证命令\n- 预期输出是什么',
            'cot_source': 'verify',
            'source': 'cot_stat',
            'evidence': [{'context': 'cot_stat', 'insight': f'验证习惯出现率 {profile["verify_rate"]:.0%}', 'confidence': min(75, 35 + int(profile['verify_rate'] * 40))}],
        })
    return patterns


# ─────────────────────────────────────────────
# V1: 研究品味 5 维度量化
# ─────────────────────────────────────────────

_RIGOR_SIGNALS = re.compile(
    r'(formal(ly|ize)|theorem|proof|lemma|assumption|定理|证明|严格|形式化'
    r'|ground truth|ablat|statistical|significance|p-value|baseline|control)',
    re.I,
)
_ELEGANCE_SIGNALS = re.compile(
    r'(elegant|simple|minimal|clean|beautiful|简洁|优雅|最简|avoid.*complex'
    r'|unnecessary|over.?engineer|convoluted)',
    re.I,
)
_NOVELTY_SIGNALS = re.compile(
    r'(novel|new|first|state.of.the.art|sota|prior work|existing|gap|limitation'
    r'|创新|新颖|首次|现有方法|研究空白)',
    re.I,
)
_SIMPLICITY_SIGNALS = re.compile(
    r'(simpl(e|ify|icity)|minimal|straightforward|direct|one.line|单一|简单|直接'
    r'|不需要|去掉|reduce|strip)',
    re.I,
)
_REPRODUCIBILITY_SIGNALS = re.compile(
    r'(reproduc|replicat|seed|deterministic|version|environment|docker|config'
    r'|可复现|确定性|随机种子|版本|环境)',
    re.I,
)

_TASTE_DIMS = {
    'rigor': _RIGOR_SIGNALS,
    'elegance': _ELEGANCE_SIGNALS,
    'novelty': _NOVELTY_SIGNALS,
    'simplicity': _SIMPLICITY_SIGNALS,
    'reproducibility': _REPRODUCIBILITY_SIGNALS,
}


def compute_taste_dimensions(db: Session, lookback_hours: int = 336) -> dict:
    """
    V1: 计算研究品味5维度得分 (0-100)。
    信号来源:
    - assistant 消息的关键词（用户引导 AI 关注的维度）
    - user 消息的修正语（暴露真实偏好）
    """
    cutoff = int(time.time()) - lookback_hours * 3600
    sessions = db.query(OpenClawSession).filter(
        OpenClawSession.created_at > cutoff,
        OpenClawSession.messages.isnot(None),
    ).order_by(OpenClawSession.created_at.desc()).limit(100).all()

    if not sessions:
        return {d: 0 for d in _TASTE_DIMS}

    dim_counts = {d: 0 for d in _TASTE_DIMS}
    total_msgs = 0

    for session in sessions:
        try:
            msgs = json.loads(session.messages) if session.messages else []
        except (json.JSONDecodeError, TypeError):
            continue
        for msg in msgs:
            content = str(msg.get('content', ''))
            if len(content) < 20:
                continue
            total_msgs += 1
            for dim, pattern in _TASTE_DIMS.items():
                if pattern.search(content):
                    dim_counts[dim] += 1

    if total_msgs == 0:
        return {d: 0 for d in _TASTE_DIMS}

    # 归一化到 0-100（基于出现频率 + 非线性缩放）
    scores = {}
    for dim, count in dim_counts.items():
        rate = count / total_msgs
        # sigmoid-like 缩放: rate=0.1 → ~50, rate=0.3 → ~80
        score = int(100 * (1 - 1 / (1 + rate * 10)))
        scores[dim] = min(100, score)

    # 也纳入已确认 pattern 的类别权重作为补充信号
    from models.pattern import BehaviorPattern
    confirmed = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == 'confirmed',
    ).all()

    cat_map = {
        'rigor': ('review', 'devops'),
        'novelty': ('coding',),
        'simplicity': ('coding',),
        'elegance': ('review',),
        'reproducibility': ('devops',),
    }
    for dim, cats in cat_map.items():
        bonus = sum(1 for p in confirmed if p.category in cats)
        scores[dim] = min(100, scores[dim] + bonus * 3)

    return scores
