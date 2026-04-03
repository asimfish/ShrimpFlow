import json
import re
from collections import defaultdict
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern
from models.skill import Skill
from models.skill_workflow import SkillWorkflow
from services.ai_provider import chat

try:
    from services.taste_model import get_active_taste_profile
except ImportError:
    get_active_taste_profile = None

LEVEL_LABELS = ['入门', '基础', '进阶', '高级', '专家']
LEVEL_THRESHOLDS = [20, 40, 60, 80, 101]
PATTERN_TO_SKILL_CATEGORIES = {
    'coding': {'language', 'framework', 'tool'},
    'review': {'openclaw', 'language', 'framework'},
    'git': {'vcs'},
    'devops': {'devops', 'network', 'tool'},
    'collaboration': {'openclaw', 'tool'},
}
SKILL_CATEGORY_TO_PATTERN_CATEGORIES: dict[str, set[str]] = defaultdict(set)
for _p_cat, _s_set in PATTERN_TO_SKILL_CATEGORIES.items():
    for _s_cat in _s_set:
        SKILL_CATEGORY_TO_PATTERN_CATEGORIES[_s_cat].add(_p_cat)
TASTE_PREFERRED_BOOST_SCALE = 0.12 / 50.0
TASTE_LOW_WEIGHT_PENALTY_SCALE = 0.14 / 50.0
TASTE_REJECT_COUNT_PENALTY = 0.025
TASTE_REJECT_REASON_OVERLAP = 0.04
TASTE_FILTER_WEIGHT_MAX = 32
TASTE_FILTER_REJECT_MIN = 4
TASTE_ALIGNED_HIGH = 55
TASTE_ALIGNED_LOW = 42
SKILL_ADVANCED_FOCUS = {
    'language': '补强工程化、性能和可维护性约束',
    'framework': '向系统调优、复杂场景和最佳实践推进',
    'tool': '补齐自动化、诊断和组合使用能力',
    'devops': '把环境管理升级为稳定的交付与监控闭环',
    'vcs': '从命名和提交规范走向协作流程治理',
    'network': '把基础连接能力扩展到稳定排障与远程运维',
    'openclaw': '从高频使用升级为可复用工作流和审查习惯',
}


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?', '', cleaned).strip()
        cleaned = re.sub(r'```$', '', cleaned).strip()
    return cleaned


def _parse_json_value(raw: str | None):
    if not raw or not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _normalize_name(value: str) -> str:
    return re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '', (value or '').lower())


def _tokenize(value: str) -> set[str]:
    return {
        token for token in re.findall(r'[a-z0-9\u4e00-\u9fff]+', (value or '').lower())
        if len(token) >= 2
    }


def _level_band(level: int) -> int:
    for index, threshold in enumerate(LEVEL_THRESHOLDS):
        if level < threshold:
            return index
    return len(LEVEL_LABELS) - 1


def _format_trigger(trigger) -> str:
    if isinstance(trigger, dict):
        return json.dumps(trigger, ensure_ascii=False)
    if isinstance(trigger, str):
        return trigger
    return ''


def _parse_trigger(raw: str | None):
    parsed = _parse_json_value(raw) if isinstance(raw, str) else raw
    if isinstance(parsed, dict):
        return parsed
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _trim_text(value: str, limit: int = 180) -> str:
    compact = re.sub(r'\s+', ' ', (value or '')).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit - 1].rstrip() + '…'


def _pattern_to_skill_name(pattern: BehaviorPattern) -> str:
    raw = (pattern.name or '').strip()
    cleaned = re.sub(r'(规范|模式|习惯|流程|检查表|检查)$', '', raw).strip(' ：:-')
    if cleaned and len(cleaned) >= 2:
        return cleaned
    return raw or f'pattern-{pattern.id}'


def _advanced_candidates(skills: list[Skill]) -> list[dict]:
    by_category: dict[str, list[Skill]] = defaultdict(list)
    for skill in skills:
        by_category[skill.category].append(skill)

    results = []
    for category, items in by_category.items():
        top_skill = max(items, key=lambda item: (item.level, item.total_uses))
        current_band = _level_band(top_skill.level)
        if current_band >= len(LEVEL_LABELS) - 1:
            continue
        next_band = min(len(LEVEL_LABELS) - 1, current_band + 1)
        next_name = f'{top_skill.name} {LEVEL_LABELS[next_band]}'
        confidence = min(0.96, 0.58 + top_skill.level / 220 + min(top_skill.total_uses, 240) / 1000)
        focus = SKILL_ADVANCED_FOCUS.get(category, '继续提升在真实项目中的复杂度和稳定性')
        results.append({
            'name': next_name,
            'category': category,
            'reason': (
                f'当前 {category} 类最强项是 {top_skill.name}（level={top_skill.level}, uses={top_skill.total_uses}），'
                f'建议向下一档 {LEVEL_LABELS[next_band]} 能力推进，重点是 {focus}。'
            ),
            'type': 'advanced',
            'confidence': round(confidence, 2),
        })
    return sorted(results, key=lambda item: item['confidence'], reverse=True)


def _pattern_relevance(pattern: BehaviorPattern, skills: list[Skill]) -> tuple[float, Skill | None]:
    text = ' '.join(filter(None, [pattern.name, pattern.description, pattern.body]))
    text_norm = _normalize_name(text)
    text_tokens = _tokenize(text)
    bridge_categories = PATTERN_TO_SKILL_CATEGORIES.get(pattern.category, set())
    best_score = 0.0
    best_skill = None

    for skill in skills:
        score = 0.0
        if skill.category in bridge_categories:
            score += 0.34
        skill_norm = _normalize_name(skill.name)
        if skill_norm and skill_norm in text_norm:
            score += 0.45
        overlap = len(_tokenize(skill.name) & text_tokens)
        if overlap:
            score += min(0.2, overlap * 0.1)
        fuzzy = SequenceMatcher(None, skill.name.lower(), (pattern.name or '').lower()).ratio()
        score += fuzzy * 0.15
        if score > best_score:
            best_score = score
            best_skill = skill
    return best_score, best_skill


def _pattern_candidate_type(pattern: BehaviorPattern, skills: list[Skill], matched_skill: Skill | None) -> str:
    bridge_categories = PATTERN_TO_SKILL_CATEGORIES.get(pattern.category, set())
    category_skills = [skill for skill in skills if skill.category in bridge_categories]
    if not category_skills:
        return 'gap'
    avg_level = sum(skill.level for skill in category_skills) / max(1, len(category_skills))
    if matched_skill and matched_skill.level >= 55 and avg_level >= 50:
        return 'related'
    return 'gap'


def _pattern_reason(pattern: BehaviorPattern, matched_skill: Skill | None, candidate_type: str) -> str:
    base = (
        f'来自 community/imported pattern「{pattern.name}」，'
        f'当前置信度 {pattern.confidence}，证据数 {pattern.evidence_count}。'
    )
    if matched_skill:
        return (
            f'{base} 它与现有 skill「{matched_skill.name}」（level={matched_skill.level}）语义和场景相近，'
            f'适合作为{"相关扩展" if candidate_type == "related" else "当前能力缺口补齐"}方向。'
        )
    return f'{base} 当前 skill 图谱里缺少与该模式对应的稳定能力，适合作为新增补齐方向。'


def _related_pattern_candidates(db: Session, skills: list[Skill]) -> list[dict]:
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.source == 'imported',
        BehaviorPattern.status.in_(('confirmed', 'exportable')),
    ).order_by(BehaviorPattern.confidence.desc(), BehaviorPattern.evidence_count.desc()).all()

    if not patterns:
        patterns = db.query(BehaviorPattern).filter(
            BehaviorPattern.status.in_(('confirmed', 'exportable')),
        ).order_by(BehaviorPattern.confidence.desc(), BehaviorPattern.evidence_count.desc()).limit(20).all()

    results = []
    for pattern in patterns:
        relevance, matched_skill = _pattern_relevance(pattern, skills)
        candidate_type = _pattern_candidate_type(pattern, skills, matched_skill)
        if relevance < 0.32 and candidate_type == 'related':
            continue
        name = _pattern_to_skill_name(pattern)
        confidence = min(
            0.95,
            0.42 + pattern.confidence / 220 + pattern.evidence_count / 200 + relevance / 2,
        )
        results.append({
            'name': name,
            'category': pattern.category,
            'reason': _pattern_reason(pattern, matched_skill, candidate_type),
            'type': candidate_type,
            'confidence': round(confidence, 2),
        })
    return results


def _co_occurrence_candidates(db: Session, skills: list[Skill]) -> list[dict]:
    user_by_norm = {_normalize_name(s.name): s for s in skills}
    user_norms = set(user_by_norm)
    best: dict[str, dict] = {}
    for wf in db.query(SkillWorkflow).all():
        raw = wf.skill_sequence
        data = _parse_json_value(raw) if isinstance(raw, str) else raw
        if not isinstance(data, list):
            continue
        seq = [str(x).strip() for x in data if str(x).strip()]
        if len(seq) < 2:
            continue
        freq = int(getattr(wf, 'frequency', 1) or 1)
        sr = float(getattr(wf, 'success_rate', 0.0) or 0.0)
        wf_name = (wf.name or '').strip() or '未命名工作流'
        for i, name_b in enumerate(seq):
            norm_b = _normalize_name(name_b)
            if not norm_b or norm_b in user_norms:
                continue
            for j, name_a in enumerate(seq):
                if i == j:
                    continue
                norm_a = _normalize_name(name_a)
                if norm_a not in user_norms:
                    continue
                a_skill = user_by_norm[norm_a]
                conf = min(0.94, 0.38 + min(freq, 500) / 600.0 + sr * 0.35)
                row = {
                    'name': name_b,
                    'category': 'workflow',
                    'reason': f'你使用了 {a_skill.name}，在 {wf_name} 工作流中常与 {name_b} 搭配',
                    'type': 'workflow_co',
                    'confidence': round(conf, 2),
                }
                prev = best.get(norm_b)
                if prev is None or conf > prev['confidence']:
                    best[norm_b] = row
    return sorted(best.values(), key=lambda r: r['confidence'], reverse=True)


def _apply_taste_to_recommendations(items: list[dict], taste) -> list[dict]:
    if taste is None:
        return items
    preferred = _parse_json_value(getattr(taste, 'preferred_categories', None) or '') or {}
    if not isinstance(preferred, dict):
        preferred = {}
    summary = (getattr(taste, 'taste_summary', None) or '').strip()
    reject_tokens: set[str] = set()
    for marker in ('常见拒绝原因:', '用户填写的拒绝原因统计:'):
        if marker in summary:
            reject_tokens = _tokenize(summary.split(marker, 1)[-1])
            break
    adjusted = []
    for item in items:
        conf = float(item.get('confidence', 0))
        cat = item.get('category') or ''
        if preferred and cat in preferred:
            conf = min(1.0, conf + 0.10)
        if reject_tokens:
            blob = ' '.join(str(item.get(k) or '') for k in ('name', 'reason', 'category'))
            if _tokenize(blob) & reject_tokens:
                conf = max(0.0, conf - 0.08)
        adjusted.append({**item, 'confidence': round(conf, 2)})
    return sorted(adjusted, key=lambda row: row['confidence'], reverse=True)


def recommend_skills(db: Session, limit: int = 8) -> list[dict]:
    skills = db.query(Skill).order_by(Skill.level.desc(), Skill.total_uses.desc()).all()
    if not skills:
        return []

    existing_names = {_normalize_name(skill.name) for skill in skills}
    candidates = [
        *_advanced_candidates(skills),
        *_co_occurrence_candidates(db, skills),
        *_related_pattern_candidates(db, skills),
    ]

    deduped = []
    seen = set()
    for item in sorted(candidates, key=lambda row: row['confidence'], reverse=True):
        normalized = _normalize_name(item['name'])
        if not normalized or normalized in seen:
            continue
        if normalized in existing_names and item['type'] != 'advanced':
            continue
        seen.add(normalized)
        deduped.append(item)
        if len(deduped) >= max(1, limit):
            break
    taste_profile = None
    if get_active_taste_profile is not None:
        try:
            taste_profile = get_active_taste_profile(db)
        except Exception:
            taste_profile = None
    return _apply_taste_to_recommendations(deduped, taste_profile)


def _find_skill_pattern(db: Session, skill: Skill) -> BehaviorPattern | None:
    rows = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(('confirmed', 'exportable', 'learning')),
    ).all()
    target = _normalize_name(skill.name)
    for row in rows:
        if _normalize_name(row.name) == target:
            return row
    for row in rows:
        if target and target in _normalize_name(row.name):
            return row
    return None


def _has_anti_pattern(body: str) -> bool:
    return bool(re.search(r'anti[_ -]?pattern|反例|不要|避免|不适用', body or '', re.I))


def _heuristic_improvement_suggestions(skill: Skill, pattern: BehaviorPattern | None) -> list[dict]:
    if not pattern:
        return [
            {
                'type': 'mapping',
                'current': '未找到同名 BehaviorPattern',
                'suggested': f'为 skill「{skill.name}」补一个同名 pattern，并补齐 trigger、body、evidence。',
                'reason': '当前缺少可分析的 pattern 正文，无法给出基于内容的精修建议。',
            }
        ]

    body = (pattern.body or pattern.description or '').strip()
    trigger = _parse_trigger(pattern.trigger)
    suggestions = []

    if body:
        suggested = (
            f'## {pattern.name}\n\n'
            f'适用时机：{trigger.get("when") if isinstance(trigger, dict) and trigger.get("when") else "明确触发场景"}\n\n'
            '### 核心动作\n'
            '1. 用一句话说明目标。\n'
            '2. 列 3 条必须执行的检查点。\n'
            '3. 给 1 个最小示例。\n'
        )
        suggestions.append({
            'type': 'wording',
            'current': _trim_text(body, 160),
            'suggested': suggested,
            'reason': '建议把开头改成“适用时机 + 核心动作”结构，减少背景叙述，提升可扫描性。',
        })

    if not isinstance(trigger, dict) or not trigger.get('event') or not trigger.get('when'):
        suggestions.append({
            'type': 'trigger',
            'current': _format_trigger(trigger) or '未定义或非结构化 trigger',
            'suggested': json.dumps({
                'when': f'检测到与 {skill.name} 相关的关键操作时',
                'event': 'skill_usage',
                'context': [skill.category, skill.name],
            }, ensure_ascii=False),
            'reason': '当前 trigger 不够结构化，难以稳定命中。补齐 when/event/context 后更容易自动注入。',
        })

    if not _has_anti_pattern(body):
        suggestions.append({
            'type': 'anti_pattern',
            'current': '正文中未定义 anti_pattern 或不适用边界',
            'suggested': (
                '### Anti-pattern\n'
                f'- 不要在与 {skill.name} 无关的轻量改动中强行触发该 skill。\n'
                '- 不要在缺少必要上下文时给出过度具体的操作指令。\n'
            ),
            'reason': '补充反例和禁用条件可以减少误触发，也方便后续评估命中质量。',
        })

    if pattern.confidence < 80 or pattern.evidence_count < 20:
        suggestions.append({
            'type': 'confidence',
            'current': f'confidence={pattern.confidence}, evidence_count={pattern.evidence_count}, status={pattern.status}',
            'suggested': '补充 3-5 条 execution/evidence，并把规则改成可验证检查项，再分阶段提升到 confirmed/exportable。',
            'reason': '当前置信度仍偏依赖描述性文本，缺少可复验的触发和执行证据。',
        })

    return suggestions[:4]


def _merge_suggestions(primary: list[dict], fallback: list[dict]) -> list[dict]:
    merged = []
    seen = set()
    for item in [*primary, *fallback]:
        if not isinstance(item, dict):
            continue
        suggestion_type = str(item.get('type', '')).strip()
        if not suggestion_type or suggestion_type in seen:
            continue
        current = item.get('current')
        suggested = item.get('suggested')
        reason = item.get('reason')
        if not isinstance(current, str):
            current = json.dumps(current, ensure_ascii=False) if current is not None else ''
        if not isinstance(suggested, str):
            suggested = json.dumps(suggested, ensure_ascii=False) if suggested is not None else ''
        if not isinstance(reason, str):
            reason = str(reason or '')
        merged.append({
            'type': suggestion_type,
            'current': current,
            'suggested': suggested,
            'reason': reason.strip(),
        })
        seen.add(suggestion_type)
    return merged[:4]


def suggest_skill_improvements(db: Session, skill_id: int) -> dict:
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise ValueError('Skill not found')

    pattern = _find_skill_pattern(db, skill)
    heuristic = _heuristic_improvement_suggestions(skill, pattern)
    if not pattern:
        return {
            'skill_id': skill.id,
            'skill_name': skill.name,
            'suggestions': heuristic,
        }

    prompt = (
        '你是资深 skill 设计审查员。请阅读下面的 BehaviorPattern，输出严格 JSON：'
        '{"suggestions":[{"type":"wording|trigger|anti_pattern|confidence","current":"","suggested":"","reason":""}]}。\n'
        '要求：\n'
        '1. 给出 3-4 条具体、可执行的修改建议\n'
        '2. 优先覆盖措辞精简、trigger 补全、anti_pattern 补全、置信度提升路径\n'
        '3. suggested 必须能直接写回 skill/pattern 文案，避免空泛评价\n\n'
        f'Skill: {json.dumps({"id": skill.id, "name": skill.name, "category": skill.category, "level": skill.level, "total_uses": skill.total_uses}, ensure_ascii=False)}\n'
        f'Pattern: {json.dumps({"id": pattern.id, "name": pattern.name, "category": pattern.category, "status": pattern.status, "confidence": pattern.confidence, "evidence_count": pattern.evidence_count, "trigger": _parse_trigger(pattern.trigger), "body": pattern.body or pattern.description or ""}, ensure_ascii=False)}'
    )

    ai_suggestions: list[dict] = []
    try:
        result = chat([{'role': 'user', 'content': prompt}], max_tokens=900)
        if result:
            data = json.loads(_strip_json_fence(result))
            raw_suggestions = data.get('suggestions', [])
            if isinstance(raw_suggestions, list):
                ai_suggestions = [item for item in raw_suggestions if isinstance(item, dict)]
    except Exception:
        ai_suggestions = []

    return {
        'skill_id': skill.id,
        'skill_name': skill.name,
        'suggestions': _merge_suggestions(ai_suggestions, heuristic),
    }


def _heuristic_report_item(pattern: BehaviorPattern) -> dict:
    body = (pattern.body or pattern.description or '').strip()
    trigger = _parse_trigger(pattern.trigger)
    missing_trigger = not isinstance(trigger, dict) or not trigger.get('when') or not trigger.get('event')
    missing_anti = not _has_anti_pattern(body)
    low_signal = pattern.confidence < 60 or pattern.evidence_count < 12

    if missing_trigger:
        hint = '优先把 trigger 改成结构化字段，并缩小触发上下文；当前定义过宽，自动命中会不稳定。'
    elif low_signal:
        hint = '补充 execution/evidence 和可验证规则，把“经验描述”升级成“可复验流程”，再推动 confidence 上升。'
    elif missing_anti:
        hint = '建议补一段 anti-pattern，说明何时不要触发和何时只做轻提醒，减少误报。'
    else:
        hint = '可以压缩开头文案并保留 3-5 条关键检查点，再补一个失败示例，便于快速执行。'

    priority = 'low'
    if missing_trigger or low_signal:
        priority = 'high'
    elif missing_anti or len(body) < 80:
        priority = 'medium'

    return {
        'pattern_id': pattern.id,
        'name': pattern.name,
        'improvement_hint': hint,
        'priority': priority,
    }


def _bulk_ai_chunk(chunk: list[BehaviorPattern]) -> list[dict]:
    prompt_payload = [
        {
            'pattern_id': pattern.id,
            'name': pattern.name,
            'category': pattern.category,
            'confidence': pattern.confidence,
            'evidence_count': pattern.evidence_count,
            'trigger': _parse_trigger(pattern.trigger),
            'body_excerpt': _trim_text(pattern.body or pattern.description or '', 180),
        }
        for pattern in chunk
    ]
    prompt = (
        '你是 skill 质量审查员。请对每个 confirmed pattern 给出 1-2 句最重要的改进建议，'
        '并返回严格 JSON：{"items":[{"pattern_id":1,"name":"","improvement_hint":"","priority":"high|medium|low"}]}。\n'
        '判断优先级时重点看 trigger 是否具体、body 是否可执行、evidence/confidence 是否足够。\n\n'
        f'patterns={json.dumps(prompt_payload, ensure_ascii=False)}'
    )

    result = chat([{'role': 'user', 'content': prompt}], max_tokens=1200)
    if not result:
        return []
    data = json.loads(_strip_json_fence(result))
    items = data.get('items', [])
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            normalized.append({
                'pattern_id': int(item.get('pattern_id')),
                'name': str(item.get('name', '')).strip(),
                'improvement_hint': str(item.get('improvement_hint', '')).strip(),
                'priority': str(item.get('priority', 'medium')).strip() or 'medium',
            })
        except Exception:
            continue
    return normalized


def bulk_skill_improvement_report(db: Session) -> list[dict]:
    patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == 'confirmed',
    ).order_by(BehaviorPattern.confidence.asc(), BehaviorPattern.evidence_count.asc()).all()

    if not patterns:
        return []

    fallback_map = {pattern.id: _heuristic_report_item(pattern) for pattern in patterns}
    ai_map: dict[int, dict] = {}

    for index in range(0, len(patterns), 12):
        chunk = patterns[index:index + 12]
        try:
            for item in _bulk_ai_chunk(chunk):
                if item['pattern_id'] not in fallback_map:
                    continue
                if item['priority'] not in {'high', 'medium', 'low'}:
                    item['priority'] = fallback_map[item['pattern_id']]['priority']
                if not item['improvement_hint']:
                    item['improvement_hint'] = fallback_map[item['pattern_id']]['improvement_hint']
                if not item['name']:
                    item['name'] = fallback_map[item['pattern_id']]['name']
                ai_map[item['pattern_id']] = item
        except Exception:
            continue

    report = []
    for pattern in patterns:
        report.append(ai_map.get(pattern.id, fallback_map[pattern.id]))

    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    return sorted(
        report,
        key=lambda item: (priority_order.get(item['priority'], 3), item['pattern_id']),
    )
