import json
import re
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from models.event import DevEvent
from models.pattern import BehaviorPattern
from models.skill import Skill
from services.ai_provider import chat as ai_chat
from services.taste_model import get_active_taste_profile


def _confidence_to_level(score: int) -> str:
    if score >= 90:
        return 'very_high'
    if score >= 70:
        return 'high'
    if score >= 40:
        return 'medium'
    return 'low'


def _name_to_slug(name: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '-', name).strip('-').lower()
    return slug[:50]


# 挖掘结果类型
class MinedPattern:
    def __init__(self, id, name, description, type, confidence, occurrences, examples):
        self.id = id
        self.name = name
        self.description = description
        self.type = type
        self.confidence = confidence
        self.occurrences = occurrences
        self.examples = examples

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'description': self.description,
            'type': self.type, 'confidence': self.confidence,
            'occurrences': self.occurrences, 'examples': self.examples,
        }


ACTION_LABELS = {
    'openclaw-chat': 'OpenClaw 协作',
    'env-check': '环境检查',
    'git-commit': '提交代码',
    'git-merge': '合并分支',
    'git-op': 'Git 操作',
    'claude-edit': 'Claude Code 协作',
    'codex-edit': 'Codex 协作',
    'python-run': '运行脚本',
    'test-run': '执行测试',
    'build': '执行构建',
    'ssh-connect': '连接远程环境',
    'monitor': '监控训练或服务',
    'pkg-install': '安装依赖',
    'terminal-cmd': '终端操作',
}

CATEGORY_MAP = {'sequence': 'coding', 'time': 'devops', 'correlation': 'collaboration'}


def _humanize_action(action_key: str) -> str:
    return ACTION_LABELS.get(action_key, action_key)


def _candidate_trigger(candidate: dict):
    if candidate['type'] == 'sequence':
        steps = [part.strip() for part in candidate['raw_name'].split('->')]
        first = steps[0] if steps else candidate['raw_name']
        next_steps = [_humanize_action(part) for part in steps[1:]]
        return {
            'when': f'检测到{_humanize_action(first)}',
            'event': first,
            'context': [f'后续常见动作: {" -> ".join(next_steps)}'] if next_steps else [],
        }
    if candidate['type'] == 'correlation':
        steps = [part.strip() for part in candidate['raw_name'].split('->')]
        first = steps[0] if steps else candidate['raw_name']
        next_step = _humanize_action(steps[1]) if len(steps) > 1 else candidate['name']
        return {
            'when': f'{_humanize_action(first)}后',
            'event': first,
            'context': [f'高频联动: {next_step}'],
        }
    return f'时间模式: {candidate["name"]}'


def _candidate_body(candidate: dict) -> str:
    lines = [
        f"## {candidate['name']}",
        "",
        candidate['description'],
        "",
        "### 应用建议",
    ]
    if candidate['type'] == 'sequence':
        lines.append("- 在该流程起点提前准备测试、构建或提交流程，减少上下文切换。")
    elif candidate['type'] == 'correlation':
        lines.append("- 将这组高频联动动作收敛为固定 checklist 或自动化步骤。")
    else:
        lines.append("- 将该时间规律用于安排批量任务、定时采集或集中验证窗口。")
    if candidate['examples']:
        lines.extend(["", "### 证据样例"])
        lines.extend(f"- {example}" for example in candidate['examples'][:3])
    return "\n".join(lines)


def _build_candidate_record(pattern: MinedPattern) -> dict:
    raw_name = pattern.name.replace(' -> ', '->')
    humanized = ' -> '.join(_humanize_action(part.strip()) for part in raw_name.split('->'))
    if pattern.type == 'sequence':
        name = f'工程序列: {humanized}'
    elif pattern.type == 'correlation':
        name = f'联动习惯: {humanized}'
    elif pattern.id == 'time-weekday':
        name = '工作日集中推进'
    else:
        name = pattern.name

    description = pattern.description
    if pattern.type == 'time' and pattern.id != 'time-weekday':
        description = f'调度规律: {pattern.description}'

    candidate = {
        'raw_name': raw_name,
        'name': name,
        'description': description,
        'type': pattern.type,
        'category': CATEGORY_MAP.get(pattern.type, 'coding'),
        'confidence': pattern.confidence,
        'occurrences': pattern.occurrences,
        'examples': pattern.examples,
        'learned_from_data': [
            {
                'context': f'auto_mining_{pattern.type}',
                'insight': description,
                'confidence': pattern.confidence,
            },
            *[
                {
                    'context': example[:80],
                    'insight': '来自统计挖掘的行为证据',
                    'confidence': pattern.confidence,
                }
                for example in pattern.examples[:2]
            ],
        ],
    }
    candidate['trigger'] = _candidate_trigger(candidate)
    candidate['body'] = _candidate_body(candidate)
    return candidate


def _is_shallow_candidate(candidate: dict) -> bool:
    if candidate['type'] != 'time':
        return False
    return candidate['raw_name'].startswith('高峰时段') or '偏好' in candidate['raw_name']


def _normalize_candidate_key(candidate: dict) -> str:
    return f"{candidate['type']}::{candidate['name'].lower()}"


def _compute_skill_alignment_score(candidate: dict, skills: list[Skill]) -> int:
    haystack = f'{candidate.get("name", "")}\n{candidate.get("description", "")}'.lower()
    matched = 0
    category_bonus = 0
    seen_names: set[str] = set()

    for skill in skills:
        skill_name = (skill.name or '').strip().lower()
        if skill_name and skill_name not in seen_names and skill_name in haystack:
            matched += 1
            seen_names.add(skill_name)
        if not category_bonus and skill.category == candidate.get('category'):
            category_bonus = 10

    return min(100, matched * 20 + category_bonus)


def _apply_skill_alignment_boost(candidates: list[dict], skills: list[Skill]) -> list[dict]:
    boosted = []
    for candidate in candidates:
        alignment_score = _compute_skill_alignment_score(candidate, skills)
        boost = min(15, alignment_score // 10)
        updated = dict(candidate)
        updated['skill_alignment_score'] = alignment_score
        updated['confidence'] = min(99, updated['confidence'] + boost)
        boosted.append(updated)

    return sorted(
        boosted,
        key=lambda item: (item.get('skill_alignment_score', 0), item['confidence'], item['occurrences']),
        reverse=True,
    )


def _merge_candidates(left: dict, right: dict) -> dict:
    merged = dict(left)
    merged['confidence'] = max(left['confidence'], right['confidence'])
    merged['occurrences'] = left['occurrences'] + right['occurrences']
    merged['examples'] = list(dict.fromkeys([*left['examples'], *right['examples']]))[:4]
    merged['learned_from_data'] = [*left['learned_from_data'], *right['learned_from_data']][:5]
    merged['body'] = _candidate_body(merged)
    return merged


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith('```'):
        stripped = re.sub(r'^```(?:json)?', '', stripped).strip()
        stripped = re.sub(r'```$', '', stripped).strip()
    return stripped


def _heuristic_semantic_refine(candidates: list[dict]) -> list[dict]:
    refined: dict[str, dict] = {}
    for candidate in candidates:
        if candidate['confidence'] < 45:
            continue
        if _is_shallow_candidate(candidate):
            continue
        key = _normalize_candidate_key(candidate)
        if key in refined:
            refined[key] = _merge_candidates(refined[key], candidate)
        else:
            refined[key] = candidate
    results = sorted(
        refined.values(),
        key=lambda item: (item['confidence'], item['occurrences']),
        reverse=True,
    )
    return results[:8]


def _taste_reject_constraint_for_prompt(db: Session) -> str:
    try:
        tp = get_active_taste_profile(db)
        summary = (tp.taste_summary or "").strip() if tp else ""
        marker = "常见拒绝原因:"
        idx = summary.find(marker)
        return summary[idx:].strip() if idx >= 0 else ""
    except Exception:
        return ""


def _ai_semantic_refine(candidates: list[dict], reject_constraint: str = "") -> list[dict] | None:
    if not candidates:
        return []

    reject_block = ""
    if reject_constraint.strip():
        reject_block = (
            f"用户已明确拒绝以下类型的建议，请避免生成类似内容: {reject_constraint.strip()}\n\n"
        )
    prompt = (
        "你是资深工程行为模式提炼器。以下是从开发者行为数据中统计挖掘出的候选模式。"
        "任务:\n"
        "1. 过滤掉浅层时间规律（如'每天X点提交'）和噪声候选\n"
        "2. 将语义相似的候选合并为一条有价值的模式\n"
        "3. 只保留对 AI 自动开发有操作价值的模式（具备明确的 when/do/expect 结构）\n"
        "4. description 用中文，50字以内，聚焦行为价值而非统计事实\n"
        "5. trigger 描述触发条件（字符串即可），body 用 Markdown 给出可执行规范\n\n"
        "返回严格 JSON，格式为:\n"
        '{"patterns":[{"name":"规范名(10字内)","description":"价值描述",'
        '"category":"coding|review|git|devops|collaboration","confidence":80,'
        '"occurrences":6,"examples":["具体例子"],"trigger":"触发条件描述",'
        '"body":"## 规范\\n### 触发\\n...\\n### 执行\\n...\\n### 预期\\n...",'
        '"learned_from_data":[{"context":"数据来源","insight":"关键洞察","confidence":75}]}]}\n\n'
        f"{reject_block}"
        f"候选模式({len(candidates)}条):\n{json.dumps(candidates[:15], ensure_ascii=False)}"
    )

    try:
        text = ai_chat([{'role': 'user', 'content': prompt}], max_tokens=2000)
        if not text:
            return None
        data = json.loads(_strip_json_fence(text))
        raw_patterns = data.get('patterns', [])
        refined = []
        for index, item in enumerate(raw_patterns):
            if not isinstance(item, dict):
                continue
            name = str(item.get('name', '')).strip()
            description = str(item.get('description', '')).strip()
            category = str(item.get('category', 'coding')).strip() or 'coding'
            if not name or not description:
                continue
            refined.append({
                'raw_name': name,
                'name': name,
                'description': description,
                'type': 'semantic',
                'category': category if category in ('coding', 'review', 'git', 'devops', 'collaboration') else 'coding',
                'confidence': max(1, min(99, int(item.get('confidence', 70)))),
                'occurrences': max(1, int(item.get('occurrences', 1))),
                'examples': [str(example) for example in item.get('examples', []) if isinstance(example, str)][:4],
                'trigger': item.get('trigger'),
                'body': str(item.get('body', '')).strip() or f'## {name}\n\n{description}',
                'learned_from_data': [
                    evidence for evidence in item.get('learned_from_data', [])
                    if isinstance(evidence, dict)
                ][:5] or [{
                    'context': f'ai_semantic_refine_{index}',
                    'insight': description,
                    'confidence': max(1, min(99, int(item.get('confidence', 70)))),
                }],
            })
        return refined[:8]
    except Exception:
        return None


def semantic_refine_patterns(patterns: list[MinedPattern], reject_constraint: str = "") -> list[dict]:
    candidates = [_build_candidate_record(pattern) for pattern in patterns]
    return _ai_semantic_refine(candidates, reject_constraint) or _heuristic_semantic_refine(candidates)


# 简化 action 为类别标签
def _simplify_action(source, action):
    if source == 'openclaw':
        return 'openclaw-chat'
    if source == 'env':
        return 'env-check'
    if source == 'git':
        if 'commit' in action:
            return 'git-commit'
        if 'merge' in action:
            return 'git-merge'
        return 'git-op'
    if source == 'claude_code':
        return 'claude-edit'
    if source == 'codex':
        return 'codex-edit'
    # terminal
    if 'python' in action:
        return 'python-run'
    if 'pytest' in action or 'test' in action:
        return 'test-run'
    if 'colcon' in action or 'build' in action:
        return 'build'
    if 'ssh' in action:
        return 'ssh-connect'
    if 'nvidia-smi' in action or 'tensorboard' in action:
        return 'monitor'
    if 'pip' in action or 'conda' in action:
        return 'pkg-install'
    return 'terminal-cmd'


# 频繁序列挖掘
def mine_frequent_sequences(events, window_size=3, min_support=3):
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    seq_counts = defaultdict(lambda: {'count': 0, 'examples': []})

    for i in range(len(sorted_events) - window_size + 1):
        window = sorted_events[i:i + window_size]
        # 4 小时内的事件才算序列
        day_span = (window[-1].timestamp - window[0].timestamp) / 3600
        if day_span > 4:
            continue

        key = ' -> '.join(_simplify_action(e.source, e.action) for e in window)
        entry = seq_counts[key]
        entry['count'] += 1
        if len(entry['examples']) < 2:
            entry['examples'].append(' | '.join(e.action[:50] for e in window))

    results = []
    for key, v in sorted(seq_counts.items(), key=lambda x: x[1]['count'], reverse=True):
        if v['count'] < min_support:
            continue
        if len(results) >= 8:
            break
        results.append(MinedPattern(
            id=f'seq-{len(results)}',
            name=key,
            description=f'该序列在 {v["count"]} 个时间窗口中出现',
            type='sequence',
            confidence=min(95, 50 + v['count'] * 3),
            occurrences=v['count'],
            examples=v['examples'],
        ))
    return results


# 时间模式检测
def mine_time_patterns(events):
    patterns = []
    hour_counts = [0] * 24
    day_of_week_counts = [0] * 7
    source_by_hour = defaultdict(lambda: [0] * 24)

    for e in events:
        d = datetime.fromtimestamp(e.timestamp)
        hour_counts[d.hour] += 1
        day_of_week_counts[d.weekday()] += 1
        source_by_hour[e.source][d.hour] += 1

    total_events = len(events)
    if total_events == 0:
        return patterns

    # 高峰时段
    max_hour = hour_counts.index(max(hour_counts))
    peak_ratio = hour_counts[max_hour] / total_events
    patterns.append(MinedPattern(
        id='time-peak',
        name=f'高峰时段: {max_hour}:00-{max_hour + 1}:00',
        description=f'{peak_ratio * 100:.1f}% 的事件集中在此时段',
        type='time',
        confidence=min(95, round(peak_ratio * 500)),
        occurrences=hour_counts[max_hour],
        examples=[f'{max_hour}:00 时段产生 {hour_counts[max_hour]} 个事件'],
    ))

    # 工作日 vs 周末 (Python weekday: 0=Mon, 6=Sun)
    weekday_avg = sum(day_of_week_counts[:5]) / 5
    weekend_avg = sum(day_of_week_counts[5:]) / 2
    if weekday_avg > weekend_avg * 1.5:
        patterns.append(MinedPattern(
            id='time-weekday',
            name='工作日集中型',
            description=f'工作日平均 {round(weekday_avg)} 事件，周末 {round(weekend_avg)} 事件',
            type='time',
            confidence=min(90, round(weekday_avg / (weekend_avg + 1) * 30)),
            occurrences=round(weekday_avg * 5),
            examples=['工作日活跃度显著高于周末'],
        ))

    # 来源时间偏好
    for source, hours in source_by_hour.items():
        peak_h = hours.index(max(hours))
        source_total = sum(hours)
        if source_total < 10:
            continue
        ratio = hours[peak_h] / source_total
        if ratio > 0.15:
            patterns.append(MinedPattern(
                id=f'time-source-{source}',
                name=f'{source} 偏好 {peak_h}:00',
                description=f'{source} 事件 {ratio * 100:.0f}% 集中在 {peak_h}:00',
                type='time',
                confidence=min(85, round(ratio * 300)),
                occurrences=hours[peak_h],
                examples=[f'{peak_h}:00 产生 {hours[peak_h]} 个 {source} 事件'],
            ))

    return patterns


# 关联模式检测
def mine_correlations(events):
    patterns = []
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    pair_counts = defaultdict(int)
    source_counts = defaultdict(int)

    for i in range(len(sorted_events) - 1):
        curr = _simplify_action(sorted_events[i].source, sorted_events[i].action)
        nxt = _simplify_action(sorted_events[i + 1].source, sorted_events[i + 1].action)
        # 10 分钟内
        if sorted_events[i + 1].timestamp - sorted_events[i].timestamp > 600:
            continue
        pair = f'{curr} -> {nxt}'
        pair_counts[pair] += 1
        source_counts[curr] += 1

    for pair, count in pair_counts.items():
        if count < 4:
            continue
        first = pair.split(' -> ')[0]
        total = source_counts.get(first, 1)
        confidence = round(count / total * 100)
        if confidence < 30:
            continue
        patterns.append(MinedPattern(
            id=f'corr-{len(patterns)}',
            name=pair,
            description=f'{count} 次观察到此关联，置信度 {confidence}%',
            type='correlation',
            confidence=min(95, confidence),
            occurrences=count,
            examples=[f'{first} 之后 {confidence}% 概率出现后续动作'],
        ))

    return sorted(patterns, key=lambda p: p.confidence, reverse=True)[:6]


# 贝叶斯置信度更新
def bayesian_update(prior, evidence_strength=0.1):
    # evidence_strength: 0-1, 新证据的强度
    likelihood = 0.8 + evidence_strength * 0.2
    marginal = prior * likelihood + (1 - prior) * (1 - likelihood)
    posterior = (prior * likelihood) / marginal if marginal > 0 else prior
    return min(0.99, max(0.01, posterior))


# 运行所有挖掘算法
def mine_all_patterns(events):
    return [
        *mine_frequent_sequences(events),
        *mine_time_patterns(events),
        *mine_correlations(events),
    ]


# 触发挖掘并存储结果
def run_mining(db: Session):
    events = db.query(DevEvent).filter(
        ~DevEvent.tags.contains('"seed"'),
    ).order_by(DevEvent.timestamp.desc()).limit(5000).all()
    if not events:
        return []

    reject_hint = _taste_reject_constraint_for_prompt(db)
    mined = semantic_refine_patterns(mine_all_patterns(events), reject_hint)
    skills = db.query(Skill).all()
    if skills:
        mined = _apply_skill_alignment_boost(mined, skills)

    # 将挖掘结果写入数据库
    import time
    saved = []
    for p in mined:
        # 检查是否已存在同名模式
        existing = db.query(BehaviorPattern).filter(BehaviorPattern.name == p['name']).first()
        if existing:
            # 更新置信度
            new_conf = int(bayesian_update(existing.confidence / 100, 0.1) * 100)
            existing.confidence = new_conf
            existing.confidence_level = _confidence_to_level(new_conf)
            existing.evidence_count += p['occurrences']
            existing.category = p['category']
            existing.skill_alignment_score = p.get('skill_alignment_score', existing.skill_alignment_score or 0)
            existing.trigger = json.dumps(p['trigger'], ensure_ascii=False) if isinstance(p['trigger'], dict) else p['trigger']
            existing.body = p['body']
            existing.description = p['description']
            # 追加演化记录
            evolution = json.loads(existing.evolution) if existing.evolution else []
            evolution.append({
                'date': datetime.now().strftime('%m-%d'),
                'confidence': new_conf,
                'event_description': f'语义聚合更新: {p["occurrences"]} 次观察',
            })
            existing.evolution = json.dumps(evolution)
            lfd = json.loads(existing.learned_from_data) if existing.learned_from_data else []
            lfd.extend(p['learned_from_data'][:2])
            existing.learned_from_data = json.dumps(lfd)
            saved.append({
                'name': p['name'],
                'description': p['description'],
                'confidence': new_conf,
                'occurrences': p['occurrences'],
                'category': p['category'],
                'skill_alignment_score': p.get('skill_alignment_score', existing.skill_alignment_score or 0),
            })
        else:
            pattern = BehaviorPattern(
                name=p['name'], category=p['category'],
                description=p['description'], confidence=p['confidence'],
                evidence_count=p['occurrences'], learned_from='semantic_auto_mining',
                rule='自动挖掘 + 语义聚合', created_at=int(time.time()),
                status='learning',
                evolution=json.dumps([{
                    'date': datetime.now().strftime('%m-%d'),
                    'confidence': p['confidence'],
                    'event_description': f'首次发现: {p["occurrences"]} 次观察',
                }]),
                rules=json.dumps([]),
                executions=json.dumps([]),
                applicable_scenarios=json.dumps(p['examples']),
                slug=_name_to_slug(p['name']),
                trigger=json.dumps(p['trigger'], ensure_ascii=False) if isinstance(p['trigger'], dict) else p['trigger'],
                body=p['body'],
                source='auto',
                confidence_level=_confidence_to_level(p['confidence']),
                learned_from_data=json.dumps(p['learned_from_data'], ensure_ascii=False),
                skill_alignment_score=p.get('skill_alignment_score', 0),
            )
            db.add(pattern)
            saved.append({
                'name': p['name'],
                'description': p['description'],
                'confidence': p['confidence'],
                'occurrences': p['occurrences'],
                'category': p['category'],
                'skill_alignment_score': p.get('skill_alignment_score', 0),
            })

    db.commit()
    return saved
