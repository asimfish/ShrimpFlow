import json
from collections import defaultdict

from sqlalchemy.orm import Session

from models.openclaw import OpenClawDocument
from models.skill import Skill
from services.ai_provider import chat


def _skills_snapshot(skills: list[Skill]) -> dict:
    ordered = sorted(skills, key=lambda item: (item.level, item.total_uses), reverse=True)
    strengths = ordered[:5]
    weaknesses = sorted(skills, key=lambda item: (item.level, item.total_uses))[:5]
    by_category = defaultdict(list)
    for skill in skills:
        by_category[skill.category].append(skill)
    category_levels = {
        category: round(sum(item.level for item in items) / max(1, len(items)))
        for category, items in by_category.items()
    }
    return {
        "strengths": [{"name": item.name, "level": item.level} for item in strengths],
        "weaknesses": [{"name": item.name, "level": item.level} for item in weaknesses],
        "category_levels": category_levels,
    }


def _docs_snapshot(db: Session) -> list[dict]:
    rows = db.query(OpenClawDocument).order_by(OpenClawDocument.created_at.desc()).limit(6).all()
    snapshot = []
    for row in rows:
        snapshot.append({
            "title": row.title,
            "type": row.type,
            "excerpt": (row.content or "")[:180],
        })
    return snapshot


def _heuristic_plan(goal: str, snapshot: dict, docs: list[dict]) -> dict:
    strengths = snapshot["strengths"]
    weaknesses = snapshot["weaknesses"]
    focus_areas = [item["name"] for item in weaknesses[:3]]
    doc_titles = [doc["title"] for doc in docs[:3]]
    phases = [
        {
            "title": "阶段 1 · 诊断与补基础",
            "objective": "先补齐最薄弱的 2-3 个能力点，形成稳定输入输出闭环。",
            "actions": [
                f"围绕目标“{goal}”梳理当前强项 {', '.join(item['name'] for item in strengths[:3]) or '暂无'} 与短板 {', '.join(focus_areas) or '暂无'}。",
                "用知识库里最近的资料提炼 3 个最值得复用的工作流或 checklist。",
                "选一个最小任务，要求能在 1-2 天内跑通并留下可复盘产物。",
            ],
        },
        {
            "title": "阶段 2 · 专项训练",
            "objective": "针对目标做有约束的专项训练，形成可量化改进。",
            "actions": [
                f"每周围绕 {', '.join(focus_areas) or '关键短板'} 做一次专题练习和一次复盘。",
                "把训练过程沉淀成固定模板：输入资料、预期结果、验证标准、失败复盘。",
                "在真实项目里刻意练习，而不是只做脱离上下文的学习。",
            ],
        },
        {
            "title": "阶段 3 · 系统化输出",
            "objective": "把学到的能力沉淀成知识库、行为准则和可复用模板。",
            "actions": [
                "将每次有效实践总结成行为模式，进入 ClawProfile。",
                f"优先整理这些资料：{', '.join(doc_titles) if doc_titles else '最近的实验日志与日报'}。",
                "每两周检查一次技能图谱，确认是否真的把短板拉高，而不是只增加资料数量。",
            ],
        },
    ]
    return {
        "goal": goal,
        "summary": f"当前建议围绕“{goal}”做目标驱动学习。优先利用已有强项带动短板，先跑最小闭环，再做专项训练，最后沉淀为知识库和行为准则。",
        "strengths": [item["name"] for item in strengths[:4]],
        "focus_areas": focus_areas,
        "phases": phases,
        "recommendations": [
            "学习计划必须绑定真实项目，不要只做泛泛阅读。",
            "每一轮学习至少产出一个可验证结果：脚本、笔记、实验或模式。",
            "短板优先，但要利用强项带动迁移，避免孤立刷题式学习。",
        ],
    }


def generate_learning_plan(db: Session, goal: str) -> dict:
    skills = db.query(Skill).order_by(Skill.level.desc(), Skill.total_uses.desc()).all()
    snapshot = _skills_snapshot(skills)
    docs = _docs_snapshot(db)

    prompt = (
        "你是资深技术成长教练。请基于用户当前技能画像和知识库内容，为其目标制定一个 3 阶段学习计划。"
        "返回严格 JSON，格式为 "
        '{"summary":"","strengths":[""],"focus_areas":[""],"phases":[{"title":"","objective":"","actions":[""]}],"recommendations":[""]}。\n\n'
        f"用户目标: {goal}\n"
        f"技能画像: {json.dumps(snapshot, ensure_ascii=False)}\n"
        f"最近知识库: {json.dumps(docs, ensure_ascii=False)}"
    )

    try:
        result = chat([{"role": "user", "content": prompt}], max_tokens=900)
        if result:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data = json.loads(cleaned)
            if isinstance(data, dict) and isinstance(data.get("phases"), list):
                return {
                    "goal": goal,
                    "summary": str(data.get("summary", "")).strip(),
                    "strengths": [str(item) for item in data.get("strengths", []) if isinstance(item, str)],
                    "focus_areas": [str(item) for item in data.get("focus_areas", []) if isinstance(item, str)],
                    "phases": [
                        {
                            "title": str(item.get("title", "")).strip(),
                            "objective": str(item.get("objective", "")).strip(),
                            "actions": [str(action) for action in item.get("actions", []) if isinstance(action, str)],
                        }
                        for item in data.get("phases", [])
                        if isinstance(item, dict)
                    ],
                    "recommendations": [str(item) for item in data.get("recommendations", []) if isinstance(item, str)],
                }
    except Exception:
        pass

    return _heuristic_plan(goal, snapshot, docs)
