"""
Claw Generator (M3)
将 CoT 挖掘 + Workflow 重建的结果，统一转换为 ClawProfile 格式的 BehaviorPattern。
核心差异点: ShrimpFlow 输出可执行的 AI 指令规范，而不只是统计摘要。

输出物: BehaviorPattern.body 可以直接注入 AI 上下文（CLAUDE.md / OpenClaw Profile）
"""
import json
import logging
import time

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern
from models.profile import ClawProfile
from models.skill_workflow import SkillWorkflow
from services.cot_miner import mine_cot_skills
from services.workflow_inferrer import infer_workflows_from_episodes
from services.pattern_mining import bayesian_update, _confidence_to_level, _name_to_slug
from services.evidence_ledger import record_evidence
from services.pattern_quota import can_create_pattern

logger = logging.getLogger(__name__)


def _save_candidate_as_pattern(
    db: Session,
    candidate: dict,
    profile_id: int | None = None,
) -> BehaviorPattern | None:
    """将候选保存为 BehaviorPattern，去重已有同名条目"""
    name = candidate.get('name', '').strip()
    if not name or len(name) < 4:
        return None

    slug = _name_to_slug(name)
    existing = db.query(BehaviorPattern).filter(BehaviorPattern.slug == slug).first()

    confidence = max(1, min(99, int(candidate.get('confidence', 60))))
    category = candidate.get('category', 'coding')
    body = candidate.get('body', '') or candidate.get('description', '')
    trigger_raw = candidate.get('trigger', '')
    trigger = json.dumps({'when': trigger_raw}, ensure_ascii=False) if isinstance(trigger_raw, str) and trigger_raw else trigger_raw

    evidence_data = candidate.get('evidence', [])
    learned_from_data = json.dumps(evidence_data, ensure_ascii=False)

    now = int(time.time())

    if existing:
        # 贝叶斯更新置信度
        prior = existing.confidence / 100.0
        new_conf = int(bayesian_update(prior, 0.1) * 100)
        existing.confidence = max(existing.confidence, new_conf)
        existing.confidence_level = _confidence_to_level(existing.confidence)
        existing.evidence_count = (existing.evidence_count or 0) + 1
        # 如果 body 更丰富则更新
        if body and len(body) > len(existing.body or ''):
            existing.body = body
        db.commit()

        record_evidence(db, existing.id, 'support',
                        f'重挖掘: {candidate.get("type", "unknown")}', source='claw_generator')
        return existing

    # Admission gate: daily cap + global quota before we create a new row.
    admission = can_create_pattern(db, source='auto')
    if not admission.allowed:
        logger.info(
            'claw_generator: skipping new pattern %r (reason=%s, total=%s, auto_today=%s)',
            name,
            admission.reason,
            admission.total_active,
            admission.auto_created_last_day,
        )
        return None

    pattern = BehaviorPattern(
        name=name,
        category=category,
        description=candidate.get('description', '')[:240],
        confidence=confidence,
        confidence_level=_confidence_to_level(confidence),
        evidence_count=1,
        slug=slug,
        trigger=trigger,
        body=body,
        source='auto',
        status='learning',
        learned_from='cot_and_workflow_mining',
        learned_from_data=learned_from_data,
        profile_id=profile_id,
        created_at=now,
        evolution=json.dumps([{
            'date': time.strftime('%m-%d'),
            'confidence': confidence,
            'event_description': f'由 {candidate.get("type", "claw_generator")} 生成',
        }], ensure_ascii=False),
    )
    db.add(pattern)
    db.flush()

    record_evidence(db, pattern.id, 'support',
                    f'初始生成: {candidate.get("type", "unknown")}', source='claw_generator')
    return pattern


def run_claw_generation(db: Session) -> dict:
    """
    完整 Claw 生成周期:
    1. CoT 挖掘 → Skill 候选
    2. Workflow 重建 → Workflow 候选
    3. 全部保存为 BehaviorPattern（learning 状态，等待用户确认）
    """
    logger.info('Starting Claw generation cycle...')

    # 找活跃 Profile
    active_profile = db.query(ClawProfile).filter(ClawProfile.is_active == 1).first()
    profile_id = active_profile.id if active_profile else None

    # 1. CoT 挖掘
    cot_skills = mine_cot_skills(db)
    logger.info(f'CoT mining: {len(cot_skills)} skill candidates')

    # 2. Workflow 重建
    workflows = infer_workflows_from_episodes(db)
    logger.info(f'Workflow inference: {len(workflows)} workflow candidates')

    # 3. 保存
    cot_saved = []
    for c in cot_skills:
        p = _save_candidate_as_pattern(db, c, profile_id)
        if p:
            cot_saved.append({'id': p.id, 'name': p.name, 'confidence': p.confidence})

    wf_saved = []
    for w in workflows:
        p = _save_candidate_as_pattern(db, w, profile_id)
        if p:
            wf_saved.append({'id': p.id, 'name': p.name, 'confidence': p.confidence})

    db.commit()

    total = len(cot_saved) + len(wf_saved)
    logger.info(f'Claw generation complete: {len(cot_saved)} skills + {len(wf_saved)} workflows = {total} total')

    return {
        'cot_skills': cot_saved,
        'workflow_patterns': wf_saved,
        'total_generated': total,
        'timestamp': int(time.time()),
    }


def compute_alignment_score(db: Session) -> dict:
    """
    计算 ClawProfile 与用户真实行为的对齐得分 (0-100)。
    三个维度: 确认率、证据质量、类别覆盖。
    """
    from services.cot_miner import aggregate_cot_profile, analyze_single_session
    from models.openclaw import OpenClawSession

    all_patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status.in_(['confirmed', 'learning', 'rejected'])
    ).all()

    total = len(all_patterns)
    if total == 0:
        return {
            'score': 0,
            'confirmed': 0,
            'total': 0,
            'well_supported': 0,
            'top_categories': [],
            'grade': 'F',
        }

    confirmed_patterns = [p for p in all_patterns if p.status == 'confirmed']
    confirmed = len(confirmed_patterns)
    confirmed_ratio = confirmed / total if total > 0 else 0

    well_supported = sum(1 for p in confirmed_patterns if (p.evidence_count or 0) >= 3)
    evidence_quality = well_supported / confirmed if confirmed > 0 else 0

    # 获取 CoT 画像的 top categories
    cutoff = int(time.time()) - 7 * 24 * 3600
    sessions = db.query(OpenClawSession).filter(
        OpenClawSession.created_at > cutoff,
        OpenClawSession.messages.isnot(None),
    ).order_by(OpenClawSession.created_at.desc()).limit(80).all()

    top_categories: list[str] = []
    if sessions:
        analyses = [analyze_single_session(s) for s in sessions]
        analyses = [a for a in analyses if a and a.get('turn_count', 0) >= 2]
        if analyses:
            profile = aggregate_cot_profile(analyses)
            top_categories = profile.get('top_categories', [])

    # 类别匹配: confirmed 模式中有多少类别命中 top_categories
    if top_categories and confirmed_patterns:
        matched_cats = sum(
            1 for p in confirmed_patterns if (p.category or '') in top_categories
        )
        category_match = matched_cats / confirmed if confirmed > 0 else 0
    else:
        category_match = confirmed_ratio  # 回退到确认率

    score = int(
        (confirmed_ratio * 40) +
        (evidence_quality * 30) +
        (category_match * 30)
    )
    score = max(0, min(100, score))

    if score >= 90:
        grade = 'A'
    elif score >= 75:
        grade = 'B'
    elif score >= 60:
        grade = 'C'
    elif score >= 45:
        grade = 'D'
    elif score >= 30:
        grade = 'E'
    else:
        grade = 'F'

    return {
        'score': score,
        'confirmed': confirmed,
        'total': total,
        'well_supported': well_supported,
        'top_categories': top_categories,
        'grade': grade,
    }


def _build_confidence_bar(confidence: int) -> str:
    filled = round(confidence / 10)
    empty = 10 - filled
    return f'[{"█" * filled}{"░" * empty}] {confidence}%'


def _parse_skill_sequence_json(raw: str | None) -> list[str]:
    """Parse skill_sequence JSON (string[]) safely; return empty list on failure."""
    if not raw or not str(raw).strip():
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for item in data:
        if item is None:
            continue
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _source_badge(source: str | None) -> str:
    label_map = {
        'cot_mining': 'CoT挖掘',
        'workflow_inference': 'Workflow推断',
        'auto': '自动生成',
        'user': '用户提交',
        'claw_generator': 'Claw生成器',
    }
    src = source or 'auto'
    label = label_map.get(src, src)
    return f'`[{label}]`'


def export_clawprofile_markdown(db: Session, pattern_ids: list[int] | None = None) -> str:
    """
    将 confirmed 模式导出为可直接粘贴到 CLAUDE.md 的 Markdown 格式。
    这是 ShrimpFlow 的终极产出: 个人化 AI 工作规范文档。
    """
    from models.episode import Episode
    from models.openclaw import OpenClawSession

    q = db.query(BehaviorPattern).filter(BehaviorPattern.status == 'confirmed')
    if pattern_ids:
        q = q.filter(BehaviorPattern.id.in_(pattern_ids))
    patterns = q.order_by(BehaviorPattern.confidence.desc()).all()

    if not patterns:
        return '# 暂无已确认的行为规范\n'

    # 数据质量统计
    session_count = db.query(OpenClawSession).count()
    episode_count = db.query(Episode).count()

    sections: dict[str, list[BehaviorPattern]] = {}
    for p in patterns:
        cat = p.category or 'coding'
        if cat not in sections:
            sections[cat] = []
        sections[cat].append(p)

    category_names = {
        'coding': '编码规范',
        'review': '代码审查',
        'git': 'Git 规范',
        'devops': '运维部署',
        'collaboration': 'AI 协作',
    }

    gen_date = time.strftime('%Y-%m-%d %H:%M')

    lines = [
        '# 个人开发规范',
        '',
        '> 由 **ShrimpFlow** 从真实开发行为数据中自动提炼，可直接作为 CLAUDE.md 使用。',
        '',
        '## 文档信息',
        '',
        f'| 项目 | 值 |',
        f'|------|-----|',
        f'| 生成时间 | {gen_date} |',
        f'| 已确认规范数 | {len(patterns)} 条 |',
        f'| 分析的对话会话 | {session_count} 个 |',
        f'| 分析的工作片段 | {episode_count} 个 |',
        '',
        '---',
        '',
    ]

    for cat, ps in sections.items():
        lines.append(f'## {category_names.get(cat, cat)}')
        lines.append('')
        for p in ps:
            evidence = p.evidence_count or 0
            evidence_badge = f'`[{evidence}条证据]`'
            src_badge = _source_badge(p.source)
            conf_bar = _build_confidence_bar(p.confidence)

            lines.append(f'### {p.name}')
            lines.append('')
            lines.append(f'{evidence_badge} {src_badge} {conf_bar}')
            lines.append('')

            if p.description:
                lines.append(f'**说明**: {p.description}')
                lines.append('')

            if p.trigger:
                try:
                    t = json.loads(p.trigger) if p.trigger.startswith('{') else {'when': p.trigger}
                    when = t.get('when', p.trigger)
                except Exception:
                    when = p.trigger
                lines.append(f'**触发条件**: {when}')
                lines.append('')

            if p.body:
                lines.append('**规范内容**:')
                lines.append('')
                lines.append(p.body)
                lines.append('')

            # 证据溯源脚注
            learned = []
            try:
                learned = json.loads(p.learned_from_data) if p.learned_from_data else []
            except (json.JSONDecodeError, TypeError):
                pass
            if learned:
                lines.append('<details><summary>证据来源</summary>')
                lines.append('')
                for entry in learned[:5]:
                    ctx = entry.get('context', '')
                    insight = entry.get('insight', '')
                    if ctx or insight:
                        footnote = f'> **{ctx}**' if ctx else ''
                        if insight:
                            footnote += f'  \n> _{insight}_' if footnote else f'> _{insight}_'
                        lines.append(footnote)
                        lines.append('')
                lines.append('</details>')
                lines.append('')

            lines.append('---')
            lines.append('')

    workflows = (
        db.query(SkillWorkflow)
        .order_by(SkillWorkflow.frequency.desc())
        .limit(10)
        .all()
    )
    if workflows:
        lines.append('## Skill Workflow 模板')
        lines.append('')
        lines.append('以下是从你的使用习惯中挖掘的 Skill 组合流程，可作为工作流参考。')
        lines.append('')
        for wf in workflows:
            seq = _parse_skill_sequence_json(wf.skill_sequence)
            chain = ' → '.join(seq) if seq else '（无技能链）'
            freq = int(wf.frequency or 0)
            sr = float(wf.success_rate or 0.0)
            pct = int(round(sr * 100))
            lines.append(f'### {wf.name}')
            lines.append('')
            lines.append(f'**频率**: {freq} 次观察 | **成功率**: {pct}%')
            lines.append(f'**技能链**: {chain}')
            lines.append('')

    lines += [
        '## 使用说明',
        '',
        '本文件由 ShrimpFlow 自动生成，基于你的真实开发会话提炼。',
        '',
        '**使用方式**:',
        '',
        '1. 将本文件内容追加到项目根目录的 `CLAUDE.md` 中',
        '2. 或将其保存为 `~/.claude/PERSONAL_RULES.md` 并在 CLAUDE.md 中引用',
        '3. Claude ​Code 会在每次会话开始时自动读取，将你的个人规范注入 AI 工作流',
        '',
        '**更新规范**:',
        '',
        '- 前往 ShrimpFlow 的 Brain 页面，确认/拒绝新的候选模式',
        '- 拒绝时填写原因，系统会学习你的隐性偏好',
        '- 每隔一段时间重新导出以获得最新版本',
        '',
        f'> 此文件由 ShrimpFlow 在 {gen_date} 自动生成，请勿手动编辑。',
    ]

    return '\n'.join(lines)
