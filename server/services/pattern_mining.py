import json
import re
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from models.event import DevEvent
from models.pattern import BehaviorPattern


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

    mined = mine_all_patterns(events)

    # 将挖掘结果写入数据库
    import time
    saved = []
    for p in mined:
        # 检查是否已存在同名模式
        existing = db.query(BehaviorPattern).filter(BehaviorPattern.name == p.name).first()
        if existing:
            # 更新置信度
            new_conf = int(bayesian_update(existing.confidence / 100, 0.1) * 100)
            existing.confidence = new_conf
            existing.confidence_level = _confidence_to_level(new_conf)
            existing.evidence_count += p.occurrences
            # 追加演化记录
            evolution = json.loads(existing.evolution) if existing.evolution else []
            evolution.append({
                'date': datetime.now().strftime('%m-%d'),
                'confidence': new_conf,
                'event_description': f'挖掘更新: {p.occurrences} 次观察',
            })
            existing.evolution = json.dumps(evolution)
            # 追加 learned_from_data
            lfd = json.loads(existing.learned_from_data) if existing.learned_from_data else []
            lfd.append({
                'context': f'auto_mining_{datetime.now().strftime("%m%d")}',
                'insight': f'{p.type} 模式再次确认，{p.occurrences} 次新观察',
                'confidence': new_conf,
            })
            existing.learned_from_data = json.dumps(lfd)
            saved.append(p.to_dict())
        else:
            # 新建模式 — ClawProfile v1 compliant
            category_map = {'sequence': 'coding', 'time': 'devops', 'correlation': 'collaboration'}
            slug = _name_to_slug(p.name)
            conf_level = _confidence_to_level(p.confidence)

            # 根据类型生成 trigger
            trigger = None
            if p.type == 'sequence':
                steps = p.name.split(' -> ')
                trigger = json.dumps({
                    'when': f'检测到 {steps[0]} 动作',
                    'event': steps[0],
                    'context': [f'后续预期: {" → ".join(steps[1:])}'],
                })
            elif p.type == 'time':
                trigger = f'时间模式: {p.name}'
            elif p.type == 'correlation':
                parts = p.name.split(' -> ')
                trigger = json.dumps({
                    'when': f'{parts[0]} 完成后',
                    'event': parts[0] if len(parts) > 0 else p.name,
                    'context': [f'关联动作: {parts[-1]}'] if len(parts) > 1 else [],
                })

            # 生成 body (prompt 正文)
            body = f'## {p.name}\n\n{p.description}\n\n'
            if p.examples:
                body += '### 观察到的实例\n\n'
                for ex in p.examples:
                    body += f'- {ex}\n'

            # 生成 learned_from_data
            learned_from_data = [{
                'context': f'auto_mining_{p.type}',
                'insight': p.description,
                'confidence': p.confidence,
            }]
            for ex in p.examples[:2]:
                learned_from_data.append({
                    'context': ex[:80],
                    'insight': f'来自 {p.type} 挖掘的实例证据',
                    'confidence': p.confidence,
                })

            pattern = BehaviorPattern(
                name=p.name, category=category_map.get(p.type, 'coding'),
                description=p.description, confidence=p.confidence,
                evidence_count=p.occurrences, learned_from='auto_mining',
                rule=f'自动挖掘: {p.type}', created_at=int(time.time()),
                status='learning',
                evolution=json.dumps([{
                    'date': datetime.now().strftime('%m-%d'),
                    'confidence': p.confidence,
                    'event_description': f'首次发现: {p.occurrences} 次观察',
                }]),
                rules=json.dumps([]),
                executions=json.dumps([]),
                applicable_scenarios=json.dumps(p.examples),
                slug=slug,
                trigger=trigger,
                body=body,
                source='auto',
                confidence_level=conf_level,
                learned_from_data=json.dumps(learned_from_data),
            )
            db.add(pattern)
            saved.append(p.to_dict())

    db.commit()
    return saved
