import json
import logging
import re
import time
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from models.episode import Episode, EventAtom
from models.pattern import BehaviorPattern
from services.ai_provider import chat as ai_chat
from services.pattern_mining import bayesian_update, _confidence_to_level, _name_to_slug, _strip_json_fence

logger = logging.getLogger(__name__)

# 深层模式类型
DEEP_PATTERN_TYPES = [
    'workflow_habit',      # 工作流习惯: 固定的工具切换序列
    'error_recovery',      # 错误恢复: 遇到错误后的典型修复路径
    'quality_gate',        # 质量关卡: 提交前的检查习惯
    'tool_preference',     # 工具偏好: 特定场景下的工具选择
    'task_decomposition',  # 任务分解: 大任务的拆分模式
    'context_switch',      # 上下文切换: 项目/工具间的切换模式
]


def mine_workflow_habits(episodes: list[Episode]) -> list[dict]:
    # 从 Episode 的 tool_sequence 和 intent_sequence 中提取固定工作流
    sequence_counts = defaultdict(lambda: {'count': 0, 'episodes': [], 'outcomes': []})

    for ep in episodes:
        try:
            tool_seq = json.loads(ep.tool_sequence) if ep.tool_sequence else []
            intent_seq = json.loads(ep.intent_sequence) if ep.intent_sequence else []
        except (json.JSONDecodeError, TypeError):
            continue

        if len(tool_seq) < 3:
            continue

        # 提取长度3-5的子序列
        for window in (3, 4, 5):
            for i in range(len(tool_seq) - window + 1):
                sub_tools = tuple(tool_seq[i:i + window])
                sub_intents = tuple(intent_seq[i:i + window]) if len(intent_seq) > i + window - 1 else ()

                # 跳过全部相同的序列
                if len(set(sub_tools)) == 1:
                    continue

                key = ' -> '.join(f'{t}({intent_seq[i + j] if i + j < len(intent_seq) else "?"})' for j, t in enumerate(sub_tools))
                entry = sequence_counts[key]
                entry['count'] += 1
                if len(entry['episodes']) < 3:
                    entry['episodes'].append(ep.task_label or f'episode_{ep.id}')
                entry['outcomes'].append(ep.outcome)

    results = []
    for key, data in sorted(sequence_counts.items(), key=lambda x: x[1]['count'], reverse=True):
        if data['count'] < 3:
            continue
        if len(results) >= 6:
            break

        success_rate = data['outcomes'].count('success') / len(data['outcomes']) if data['outcomes'] else 0
        confidence = min(95, 40 + data['count'] * 5 + int(success_rate * 20))

        results.append({
            'type': 'workflow_habit',
            'name': f'工作流习惯: {key}',
            'description': f'在 {data["count"]} 个任务中观察到此工具切换序列，成功率 {success_rate:.0%}',
            'confidence': confidence,
            'occurrences': data['count'],
            'success_rate': round(success_rate, 2),
            'examples': data['episodes'][:3],
            'evidence': [
                {'context': 'episode_workflow_mining', 'insight': f'{data["count"]} 次观察, 成功率 {success_rate:.0%}', 'confidence': confidence},
            ],
        })
    return results


def mine_error_recovery_patterns(episodes: list[Episode], db: Session) -> list[dict]:
    # 找出包含错误的 Episode，分析错误后的恢复路径
    recovery_patterns = defaultdict(lambda: {'count': 0, 'recoveries': [], 'episodes': []})

    for ep in episodes:
        try:
            features = json.loads(ep.features) if ep.features else {}
        except (json.JSONDecodeError, TypeError):
            continue
        if not features.get('has_errors'):
            continue

        # 获取该 episode 的 atoms
        atoms = db.query(EventAtom).filter(
            EventAtom.timestamp >= ep.start_ts,
            EventAtom.timestamp <= ep.end_ts,
            EventAtom.project == ep.project,
        ).order_by(EventAtom.timestamp.asc()).all()

        # 找错误点和后续恢复动作
        for i, atom in enumerate(atoms):
            if not atom.error_signature:
                continue

            # 取错误后的3个动作作为恢复路径
            recovery = atoms[i + 1:i + 4]
            if not recovery:
                continue

            error_type = atom.error_signature
            recovery_path = ' -> '.join(f'{a.tool}({a.intent})' for a in recovery)
            key = f'{error_type} => {recovery_path}'

            entry = recovery_patterns[key]
            entry['count'] += 1
            entry['error_type'] = error_type
            entry['recovery_path'] = recovery_path
            if len(entry['episodes']) < 3:
                entry['episodes'].append(ep.task_label or f'episode_{ep.id}')
            # 检查恢复是否成功
            last_recovery = recovery[-1]
            entry['recoveries'].append(last_recovery.outcome)

    results = []
    for key, data in sorted(recovery_patterns.items(), key=lambda x: x[1]['count'], reverse=True):
        if data['count'] < 2:
            continue
        if len(results) >= 5:
            break

        success_rate = data['recoveries'].count('success') / len(data['recoveries']) if data['recoveries'] else 0
        confidence = min(90, 35 + data['count'] * 8 + int(success_rate * 25))

        results.append({
            'type': 'error_recovery',
            'name': f'错误恢复: {data["error_type"]} 后 {data["recovery_path"]}',
            'description': f'遇到 {data["error_type"]} 后，{data["count"]} 次采用此恢复路径，恢复成功率 {success_rate:.0%}',
            'confidence': confidence,
            'occurrences': data['count'],
            'success_rate': round(success_rate, 2),
            'examples': data['episodes'][:3],
            'evidence': [
                {'context': 'error_recovery_mining', 'insight': f'{data["error_type"]} => {data["recovery_path"]}', 'confidence': confidence},
            ],
        })
    return results


def mine_quality_gates(episodes: list[Episode]) -> list[dict]:
    # 分析提交前的检查习惯
    pre_commit_patterns = defaultdict(lambda: {'count': 0, 'episodes': []})

    for ep in episodes:
        try:
            intent_seq = json.loads(ep.intent_sequence) if ep.intent_sequence else []
            tool_seq = json.loads(ep.tool_sequence) if ep.tool_sequence else []
        except (json.JSONDecodeError, TypeError):
            continue

        # 找 committing 之前的动作序列
        for i, intent in enumerate(intent_seq):
            if intent != 'committing':
                continue
            # 取 commit 前的2-3个动作
            pre = list(zip(tool_seq[max(0, i - 3):i], intent_seq[max(0, i - 3):i]))
            if not pre:
                continue

            key = ' -> '.join(f'{t}({it})' for t, it in pre) + ' -> commit'
            entry = pre_commit_patterns[key]
            entry['count'] += 1
            if len(entry['episodes']) < 3:
                entry['episodes'].append(ep.task_label or f'episode_{ep.id}')

    results = []
    for key, data in sorted(pre_commit_patterns.items(), key=lambda x: x[1]['count'], reverse=True):
        if data['count'] < 2:
            continue
        if len(results) >= 4:
            break

        has_test = 'testing' in key
        confidence = min(90, 40 + data['count'] * 6 + (15 if has_test else 0))

        results.append({
            'type': 'quality_gate',
            'name': f'提交前检查: {key}',
            'description': f'在 {data["count"]} 次提交前观察到此检查序列' + ('，包含测试验证' if has_test else ''),
            'confidence': confidence,
            'occurrences': data['count'],
            'examples': data['episodes'][:3],
            'evidence': [
                {'context': 'quality_gate_mining', 'insight': f'提交前 {data["count"]} 次执行此检查', 'confidence': confidence},
            ],
        })
    return results


def mine_tool_preferences(episodes: list[Episode]) -> list[dict]:
    # 分析不同任务类型下的工具偏好
    category_tools = defaultdict(lambda: Counter())

    for ep in episodes:
        if not ep.task_category:
            continue
        try:
            features = json.loads(ep.features) if ep.features else {}
        except (json.JSONDecodeError, TypeError):
            continue
        tool_dist = features.get('tool_dist', {})
        for tool, ratio in tool_dist.items():
            category_tools[ep.task_category][tool] += 1

    results = []
    for category, tools in category_tools.items():
        if sum(tools.values()) < 3:
            continue
        top_tool, top_count = tools.most_common(1)[0]
        total = sum(tools.values())
        ratio = top_count / total

        if ratio < 0.4:
            continue

        confidence = min(85, 30 + int(ratio * 50) + top_count * 3)
        results.append({
            'type': 'tool_preference',
            'name': f'工具偏好: {category} 任务首选 {top_tool}',
            'description': f'在 {category} 类任务中，{ratio:.0%} 的 Episode 主要使用 {top_tool}',
            'confidence': confidence,
            'occurrences': top_count,
            'examples': [f'{category} 任务中 {top_tool} 使用率 {ratio:.0%}'],
            'evidence': [
                {'context': 'tool_preference_mining', 'insight': f'{category} => {top_tool} ({ratio:.0%})', 'confidence': confidence},
            ],
        })

    return results[:4]


def _ai_deep_refine(candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    prompt = (
        "你是资深开发行为分析师。输入是从开发者 Episode(任务片段)中挖掘出的候选行为模式。\n"
        "请执行以下操作:\n"
        "1. 过滤掉无实际指导价值的浅层模式\n"
        "2. 聚合重复或相似的模式\n"
        "3. 将每个模式改写为可执行的行为规范(不是描述性总结)\n"
        "4. 为每个规范生成: when(触发条件)、do(具体动作)、expect(预期结果)、anti_pattern(反模式)\n\n"
        "返回严格 JSON:\n"
        '{"norms":[{"name":"规范名","category":"coding|review|git|devops|collaboration",'
        '"when":"触发条件","do":"具体动作","expect":"预期结果","anti_pattern":"反模式",'
        '"confidence":80,"evidence_summary":"证据摘要","body":"markdown正文"}]}\n\n'
        f"候选模式:\n{json.dumps(candidates[:12], ensure_ascii=False)}"
    )

    try:
        text = ai_chat([{'role': 'user', 'content': prompt}], max_tokens=1500)
        if not text:
            return []
        data = json.loads(_strip_json_fence(text))
        norms = data.get('norms', [])
        refined = []
        for item in norms:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name', '')).strip()
            if not name:
                continue

            when = str(item.get('when', '')).strip()
            do = str(item.get('do', '')).strip()
            expect = str(item.get('expect', '')).strip()
            anti = str(item.get('anti_pattern', '')).strip()

            body_parts = [f'## {name}']
            if when:
                body_parts.append(f'\n### 触发条件\n{when}')
            if do:
                body_parts.append(f'\n### 执行动作\n{do}')
            if expect:
                body_parts.append(f'\n### 预期结果\n{expect}')
            if anti:
                body_parts.append(f'\n### 反模式\n{anti}')

            category = str(item.get('category', 'coding'))
            if category not in ('coding', 'review', 'git', 'devops', 'collaboration'):
                category = 'coding'

            refined.append({
                'name': name,
                'description': f'{when} => {do}' if when and do else name,
                'category': category,
                'confidence': max(1, min(99, int(item.get('confidence', 70)))),
                'trigger': {'when': when, 'event': '', 'context': [expect]} if when else name,
                'body': '\n'.join(body_parts),
                'evidence': [{'context': 'ai_deep_refine', 'insight': str(item.get('evidence_summary', '')), 'confidence': int(item.get('confidence', 70))}],
                'type': 'deep_norm',
            })
        return refined[:8]
    except Exception as e:
        logger.warning(f'AI deep refine failed: {e}')
        return []


def _heuristic_deep_refine(candidates: list[dict]) -> list[dict]:
    # 按 confidence 排序，取 top 6
    sorted_candidates = sorted(candidates, key=lambda c: (c.get('confidence', 0), c.get('occurrences', 0)), reverse=True)
    results = []
    for c in sorted_candidates[:6]:
        if c.get('confidence', 0) < 40:
            continue
        # 构建可执行规范格式
        body = f"## {c['name']}\n\n{c['description']}\n\n### 证据\n"
        for ex in c.get('examples', [])[:3]:
            body += f"- {ex}\n"

        results.append({
            'name': c['name'],
            'description': c['description'],
            'category': 'coding',
            'confidence': c['confidence'],
            'trigger': c['name'],
            'body': body,
            'evidence': c.get('evidence', []),
            'type': c.get('type', 'deep_norm'),
        })
    return results


def run_deep_mining(db: Session) -> list[dict]:
    # 获取最近的 Episodes
    episodes = db.query(Episode).order_by(
        Episode.created_at.desc()
    ).limit(200).all()

    if len(episodes) < 3:
        logger.info(f'Not enough episodes for deep mining: {len(episodes)}')
        return []

    # 并行挖掘多种模式
    candidates = []
    candidates.extend(mine_workflow_habits(episodes))
    candidates.extend(mine_error_recovery_patterns(episodes, db))
    candidates.extend(mine_quality_gates(episodes))
    candidates.extend(mine_tool_preferences(episodes))

    if not candidates:
        logger.info('No deep mining candidates found')
        return []

    logger.info(f'Deep mining found {len(candidates)} candidates, refining...')

    # AI 深度语义精炼
    refined = _ai_deep_refine(candidates) or _heuristic_deep_refine(candidates)

    # 持久化到 BehaviorPattern
    saved = []
    for norm in refined:
        existing = db.query(BehaviorPattern).filter(
            BehaviorPattern.name == norm['name']
        ).first()

        trigger_json = json.dumps(norm['trigger'], ensure_ascii=False) if isinstance(norm['trigger'], dict) else norm['trigger']
        evidence_json = json.dumps(norm.get('evidence', []), ensure_ascii=False)

        if existing:
            new_conf = int(bayesian_update(existing.confidence / 100, 0.15) * 100)
            existing.confidence = new_conf
            existing.confidence_level = _confidence_to_level(new_conf)
            existing.evidence_count += 1
            existing.body = norm['body']
            existing.description = norm['description']
            existing.trigger = trigger_json
            try:
                evolution = json.loads(existing.evolution) if existing.evolution else []
            except (json.JSONDecodeError, TypeError):
                evolution = []
            evolution.append({
                'date': time.strftime('%m-%d'),
                'confidence': new_conf,
                'event_description': f'深层挖掘更新: {norm.get("type", "deep")}',
            })
            existing.evolution = json.dumps(evolution, ensure_ascii=False)
            try:
                lfd = json.loads(existing.learned_from_data) if existing.learned_from_data else []
            except (json.JSONDecodeError, TypeError):
                lfd = []
            lfd.extend(norm.get('evidence', [])[:2])
            existing.learned_from_data = json.dumps(lfd[-10:], ensure_ascii=False)
            # Evidence Ledger: 记录 support 证据
            from services.evidence_ledger import record_mining_evidence
            record_mining_evidence(db, existing.id, None, 'support', f'深层挖掘再次确认: {norm.get("type", "deep")}')
        else:
            pattern = BehaviorPattern(
                name=norm['name'],
                category=norm['category'],
                description=norm['description'],
                confidence=norm['confidence'],
                evidence_count=1,
                learned_from='deep_episode_mining',
                rule='Episode 深层挖掘 + AI 语义精炼',
                created_at=int(time.time()),
                status='learning',
                evolution=json.dumps([{
                    'date': time.strftime('%m-%d'),
                    'confidence': norm['confidence'],
                    'event_description': f'深层挖掘首次发现: {norm.get("type", "deep")}',
                }], ensure_ascii=False),
                rules=json.dumps([]),
                executions=json.dumps([]),
                applicable_scenarios=json.dumps(norm.get('examples', [])[:3] if 'examples' in norm else []),
                slug=_name_to_slug(norm['name']),
                trigger=trigger_json,
                body=norm['body'],
                source='auto',
                confidence_level=_confidence_to_level(norm['confidence']),
                learned_from_data=evidence_json,
            )
            db.add(pattern)

        saved.append({
            'name': norm['name'],
            'category': norm['category'],
            'confidence': norm['confidence'],
            'type': norm.get('type', 'deep_norm'),
        })

    if saved:
        db.commit()
    logger.info(f'Deep mining saved {len(saved)} patterns')
    return saved
