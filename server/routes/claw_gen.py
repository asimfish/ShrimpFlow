"""Claw Generator routes"""
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db import get_db
from services.claw_generator import run_claw_generation, export_clawprofile_markdown, compute_alignment_score
from services.cot_miner import mine_cot_skills, aggregate_cot_profile, analyze_single_session
from services.workflow_inferrer import infer_workflows_from_episodes
from models.openclaw import OpenClawSession

router = APIRouter(tags=["claw"])


@router.post("/claw/generate")
def generate_claws(db: Session = Depends(get_db)):
    """完整 Claw 生成周期: CoT挖掘 + Workflow重建 → 保存为 BehaviorPattern"""
    return run_claw_generation(db)


@router.get("/claw/cot-profile")
def get_cot_profile(lookback_hours: int = Query(168), db: Session = Depends(get_db)):
    """获取用户 CoT 推理画像（不触发 AI，纯统计）"""
    from services.cot_miner import analyze_single_session, aggregate_cot_profile
    import time
    cutoff = int(time.time()) - lookback_hours * 3600
    sessions = db.query(OpenClawSession).filter(
        OpenClawSession.created_at > cutoff,
        OpenClawSession.messages.isnot(None),
    ).order_by(OpenClawSession.created_at.desc()).limit(80).all()

    analyses = [analyze_single_session(s) for s in sessions]
    analyses = [a for a in analyses if a and a.get('turn_count', 0) >= 2]
    if not analyses:
        return {'session_count': 0, 'message': '没有足够的对话数据'}
    return aggregate_cot_profile(analyses)


@router.get("/claw/alignment-score")
def get_alignment_score(db: Session = Depends(get_db)):
    """计算 ClawProfile 对齐得分 (0-100): 确认率 + 证据质量 + 类别匹配"""
    return compute_alignment_score(db)


@router.get("/claw/taste-dimensions")
def get_taste_dimensions(lookback_hours: int = Query(336), db: Session = Depends(get_db)):
    """V1: 5维度研究品味量化 (rigor/elegance/novelty/simplicity/reproducibility)"""
    from services.cot_miner import compute_taste_dimensions
    dims = compute_taste_dimensions(db, lookback_hours)
    return dims


@router.get("/claw/twin-snapshot")
def get_twin_snapshot(db: Session = Depends(get_db)):
    """V10: 完整 AI Twin 快照: CoT画像 + 5维度 + 对齐分数 合并"""
    import time
    from services.cot_miner import analyze_single_session, aggregate_cot_profile, compute_taste_dimensions
    cutoff = int(time.time()) - 168 * 3600
    sessions = db.query(OpenClawSession).filter(
        OpenClawSession.created_at > cutoff,
        OpenClawSession.messages.isnot(None),
    ).order_by(OpenClawSession.created_at.desc()).limit(80).all()
    analyses = [analyze_single_session(s) for s in sessions]
    analyses = [a for a in analyses if a and a.get('turn_count', 0) >= 2]
    cot = aggregate_cot_profile(analyses) if analyses else {'session_count': 0}
    dims = compute_taste_dimensions(db, 336)
    alignment = compute_alignment_score(db)
    return {**cot, **dims, 'alignment': alignment}


@router.get("/claw/export-markdown")
def export_markdown(
    ids: str = Query(None),
    db: Session = Depends(get_db),
):
    """导出已确认模式为 CLAUDE.md 格式的 Markdown"""
    id_list = [int(x) for x in ids.split(',') if x.strip()] if ids else None
    md = export_clawprofile_markdown(db, id_list)
    return {'markdown': md, 'char_count': len(md)}


@router.post("/claw/before-after")
def generate_before_after(db: Session = Depends(get_db)):
    """
    V9: 生成 Before/After 对比示例。
    对于每个高置信度已确认规范，展示：
    - 没有 ClawProfile 时 AI 会怎么回答（通用回答）
    - 有 ClawProfile 注入时 AI 会怎么回答（个性化回答）
    这是核心 Demo 素材。
    """
    import time as _time
    from services.ai_provider import chat as ai_chat
    from services.pattern_mining import _strip_json_fence
    from models.pattern import BehaviorPattern

    # 取置信度最高的 3 个已确认规范
    top_patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == 'confirmed',
        BehaviorPattern.body.isnot(None),
    ).order_by(BehaviorPattern.confidence.desc()).limit(3).all()

    if not top_patterns:
        return {'comparisons': [], 'message': '暂无已确认规范，请先确认一些模式'}

    comparisons = []
    for p in top_patterns[:2]:  # 最多2个，控制成本
        trigger = p.trigger or ''
        if isinstance(trigger, str) and trigger.startswith('{'):
            try:
                import json as _json
                trigger_obj = _json.loads(trigger)
                trigger = trigger_obj.get('when', trigger)
            except Exception:
                pass

        scenario = trigger[:200] if trigger else f'处理 {p.category} 相关任务'
        body = (p.body or '')[:500]

        prompt = (
            f"你是一个对比分析助手。请展示同一个问题在有/没有个人工作规范下的回答差异。\n\n"
            f"场景: {scenario}\n\n"
            f"个人工作规范 (仅在 WITH 版本使用):\n{body}\n\n"
            f"生成 JSON (不要 fence):\n"
            '{"question": "一个具体的示例问题(30字以内)", '
            '"without": "没有规范时AI的通用回答(100字，平庸且缺乏个性)", '
            '"with": "有规范注入时AI的个性化回答(100字，体现规范中的要求)"}'
        )

        try:
            text = ai_chat([{'role': 'user', 'content': prompt}], max_tokens=600)
            if text:
                data = _json.loads(_strip_json_fence(text))
                comparisons.append({
                    'pattern_id': p.id,
                    'pattern_name': p.name,
                    'category': p.category,
                    'confidence': p.confidence,
                    'question': data.get('question', scenario[:60]),
                    'without': data.get('without', ''),
                    'with': data.get('with', ''),
                })
        except Exception as e:
            pass

    return {'comparisons': comparisons, 'generated_at': int(_time.time())}


@router.get("/claw/twin-maturity")
def get_twin_maturity(db: Session = Depends(get_db)):
    """
    V10: 计算 AI Twin 成熟度 (0-100%) + 关键洞察。
    成熟度 = 数据量 × 质量 × 多样性。
    洞察 = 从品味维度中提炼出的关键发现（用于 Demo 叙事）。
    """
    import time as _time
    from models.pattern import BehaviorPattern
    from models.episode import Episode
    from services.cot_miner import compute_taste_dimensions

    # 数据量得分 (30分)
    cutoff_7d = int(_time.time()) - 7 * 86400
    cutoff_30d = int(_time.time()) - 30 * 86400
    sessions_7d = db.query(OpenClawSession).filter(OpenClawSession.created_at > cutoff_7d).count()
    episodes_30d = db.query(Episode).filter(Episode.start_ts > cutoff_30d).count()
    data_score = min(30, sessions_7d * 2 + episodes_30d // 2)

    # 质量得分 (40分)
    confirmed = db.query(BehaviorPattern).filter(BehaviorPattern.status == 'confirmed').count()
    total = db.query(BehaviorPattern).filter(BehaviorPattern.status.in_(['confirmed', 'learning'])).count()
    confirm_rate = confirmed / total if total > 0 else 0
    quality_score = int(confirm_rate * 40)

    # 多样性得分 (30分): 品味维度的均匀程度
    dims = compute_taste_dimensions(db, 336)
    dim_values = list(dims.values())
    if dim_values:
        mean = sum(dim_values) / len(dim_values)
        variance = sum((v - mean) ** 2 for v in dim_values) / len(dim_values)
        diversity = max(0, 30 - int(variance / 100))
    else:
        diversity = 0

    maturity = min(100, data_score + quality_score + diversity)

    # 状态标签
    if maturity >= 80:
        stage = '成熟期'
        stage_desc = 'AI Twin 已高度个性化，能准确反映你的思维风格'
    elif maturity >= 50:
        stage = '成长期'
        stage_desc = '核心偏好已建立，继续使用将进一步精炼'
    elif maturity >= 20:
        stage = '学习期'
        stage_desc = '已收集到初步数据，规范正在形成中'
    else:
        stage = '萌芽期'
        stage_desc = '刚开始，多使用 AI 工具以积累数据'

    # 关键洞察（从品味维度提炼的人话）
    insights = []
    top_dim = max(dims.items(), key=lambda x: x[1]) if dims else ('', 0)
    dim_labels = {
        'rigor': ('理论严谨性强', '你在 AI 对话中频繁要求形式化/证明/baseline，倾向于理论先行'),
        'elegance': ('追求解法优雅', '你在 AI 对话中经常纠正过于复杂的方案，偏好最简解法'),
        'novelty': ('高度创新导向', '你的对话中频繁讨论研究空白和新颖性，关注 SOTA'),
        'simplicity': ('极简主义倾向', '你倾向于去掉不必要的复杂度，"能简单绝不复杂"'),
        'reproducibility': ('极度重视可复现', '你的对话中频繁提及环境配置/随机种子，确保结果可复现'),
    }
    if top_dim[1] > 20:
        label, desc = dim_labels.get(top_dim[0], (top_dim[0], ''))
        insights.append({'type': 'dominant_trait', 'title': label, 'desc': desc, 'dim': top_dim[0], 'score': top_dim[1]})

    # 修正信号洞察
    rejected_patterns = db.query(BehaviorPattern).filter(
        BehaviorPattern.status == 'rejected',
        BehaviorPattern.reject_count >= 2,
    ).count()
    if rejected_patterns > 0:
        insights.append({
            'type': 'correction_signal',
            'title': f'发现 {rejected_patterns} 个负面偏好信号',
            'desc': '你多次拒绝的模式揭示了你不喜欢的工作方式，已被排除在规范之外',
            'dim': 'corrections',
            'score': rejected_patterns * 10,
        })

    # 潜力洞察
    if maturity < 50:
        insights.append({
            'type': 'potential',
            'title': '还有很大提升空间',
            'desc': f'当前成熟度 {maturity}%。每次使用 AI 工具并确认/拒绝模式，都在让 Twin 更了解你',
            'dim': 'growth',
            'score': 100 - maturity,
        })

    return {
        'maturity': maturity,
        'stage': stage,
        'stage_desc': stage_desc,
        'breakdown': {
            'data': data_score,
            'quality': quality_score,
            'diversity': diversity,
        },
        'stats': {
            'sessions_7d': sessions_7d,
            'episodes_30d': episodes_30d,
            'confirmed_patterns': confirmed,
            'total_patterns': total,
        },
        'insights': insights,
        'taste_dimensions': dims,
    }
