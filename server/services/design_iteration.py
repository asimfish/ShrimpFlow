import asyncio
import json
import time
from pathlib import Path

from db import SessionLocal
from models.community import SharedClawProfile
from models.digest import DailySummary
from models.event import DevEvent
from models.openclaw import OpenClawSession
from models.pattern import BehaviorPattern
from models.workflow import TeamWorkflow

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "CLAWPROFILE_ITERATIONS.md"
STATE_PATH = Path(__file__).resolve().parents[1] / "server" / "iteration_state.json"

ITERATION_ROUNDS = {
    2: {
        "title": "Shadow 结构化事件抽取",
        "focus": "把原始事件升级成包含 intent/tool/artifact/outcome/error_signature 的行为原子。",
        "deliverables": [
            "新增 EventAtom 层而不是继续只看 action 文本",
            "把 command family / error signature / artifact ref 作为统一字段采集",
            "为后续 Episode 切分准备 task_hint 和 outcome 标签",
        ],
    },
    3: {
        "title": "Shadow 到 Episode 切片",
        "focus": "从事件流切出有目标的任务片段，而不是直接统计共现。",
        "deliverables": [
            "定义 Episode 边界和 task-level success label",
            "把 session / project / artifact 关联进同一任务片段",
            "为 Brain 提供任务推进片段而不是孤立日志",
        ],
    },
    4: {
        "title": "Brain 原型层",
        "focus": "先形成 Pattern Prototype，再决定是否编译成 ClawProfile。",
        "deliverables": [
            "把 preconditions / anti-patterns / expected outcomes 纳入原型",
            "区分‘描述性总结’与‘可执行规范’",
            "让 prototype 成为行为学习的中间层",
        ],
    },
    5: {
        "title": "Evidence Ledger 账本",
        "focus": "把每次模式置信度变化变成可审计账本。",
        "deliverables": [
            "记录 support / conflict / novelty / utility 四类证据",
            "让 confidence 更新不再只是 occurrence 累加",
            "支持解释“为什么这条规范变强/变弱”",
        ],
    },
    6: {
        "title": "特征图库 V1",
        "focus": "建立统一的 episode 特征库，支撑相似度判断。",
        "deliverables": [
            "先做词法、结构、工件、任务、结果五类特征",
            "支持快速过滤候选 episode",
            "为后续向量相似度预留接口",
        ],
    },
    7: {
        "title": "相似度与去重",
        "focus": "把新增证据和旧原型进行稳健比对，减少杂乱规则。",
        "deliverables": [
            "先做硬过滤，再做结构相似，最后做语义相似",
            "让重复证据合并到旧原型而不是继续长新规则",
            "显式处理冲突证据和反例",
        ],
    },
    8: {
        "title": "ClawProfile 编译器",
        "focus": "把 prototype 编译成可注入、可执行、可维护的 ClawProfile 单元。",
        "deliverables": [
            "输出 when/scope/evidence/strategy/expected outcome/failure mode",
            "为 Autopilot 工作流提供可编排步骤",
            "保留原型与编译产物之间的映射",
        ],
    },
    9: {
        "title": "Mirror 反馈增强",
        "focus": "让 Mirror 不只是展示数据，而是展示规则形成过程。",
        "deliverables": [
            "可视化 prototype 到 ClawProfile 的演化链路",
            "显示证据账本和冲突记录",
            "让用户能审查为什么某条规范存在",
        ],
    },
    10: {
        "title": "Autopilot 执行回写",
        "focus": "让下游 workflow 的执行结果回灌到 Brain。",
        "deliverables": [
            "记录 workflow step success/failure/override",
            "把 usefulness 写回 PatternEvidenceLedger",
            "建立从相关性到有效性的升级路径",
        ],
    },
    11: {
        "title": "ClawProfile 分层",
        "focus": "把规则分成核心层、领域层、项目层、个人层。",
        "deliverables": [
            "支持 profile overlays",
            "避免规则仓库越长越乱",
            "让下游 workflow 可以按层选用规则",
        ],
    },
    12: {
        "title": "可维护置信度机制",
        "focus": "把 support/diversity/utility/conflict/staleness 纳入统一分数。",
        "deliverables": [
            "实现多因子 confidence 更新",
            "支持 stale rule 自动衰减",
            "支持 utility 高但证据少的人工保留规则",
        ],
    },
    13: {
        "title": "领域扩展包",
        "focus": "让 ClawProfile 能承载 robotics、research、release 等扩展包。",
        "deliverables": [
            "用 pack/namespace 组织规则",
            "支持社区导入时保留来源与 trust",
            "减少不同领域规范互相污染",
        ],
    },
    14: {
        "title": "审查与验证闸门",
        "focus": "把夜间自动迭代和 build/test/review 闸门整合。",
        "deliverables": [
            "每轮改进都写 iteration report",
            "自动验证失败时只记录建议，不盲目改动代码",
            "为真正无人值守迭代建立安全边界",
        ],
    },
    15: {
        "title": "ClawProfile 操作系统化",
        "focus": "把规则学习、执行反馈和社区分发合成完整闭环。",
        "deliverables": [
            "Shadow/Mirror/Brain/Autopilot 统一围绕 ClawProfile 演化",
            "让 ClawProfile 成为可增长、可审计、可复用的核心产物",
            "为后续真正生成性 workflow 奠定数据和规则基础",
        ],
    },
}


def _read_state() -> dict:
    if not STATE_PATH.exists():
        return {"next_generation": 2, "last_run_at": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"next_generation": 2, "last_run_at": None}


def _write_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _snapshot() -> dict:
    db = SessionLocal()
    try:
        return {
            "events": db.query(DevEvent).count(),
            "sessions": db.query(OpenClawSession).count(),
            "patterns": db.query(BehaviorPattern).count(),
            "workflows": db.query(TeamWorkflow).count(),
            "shared_profiles": db.query(SharedClawProfile).count(),
            "digests": db.query(DailySummary).count(),
        }
    finally:
        db.close()


def append_iteration_note(force: bool = False) -> bool:
    state = _read_state()
    generation = int(state.get("next_generation", 2))
    payload = ITERATION_ROUNDS.get(generation)
    if payload is None:
        return False

    if not force and state.get("last_run_at"):
        last_run_at = int(state["last_run_at"])
        if time.time() - last_run_at < 3500:
            return False

    stats = _snapshot()
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DOC_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n\n")
        handle.write(f"## 第 {generation} 代：{payload['title']}\n\n")
        handle.write(f"- 时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
        handle.write(f"- 核心焦点: {payload['focus']}\n")
        handle.write(f"- 当前快照: events={stats['events']}, sessions={stats['sessions']}, patterns={stats['patterns']}, workflows={stats['workflows']}, shared_profiles={stats['shared_profiles']}\n")
        handle.write("- 本轮目标:\n")
        for item in payload["deliverables"]:
            handle.write(f"  - {item}\n")
        handle.write("- 备注: 这是自动化的高层迭代审视记录，不会在夜间无提示修改代码。\n")

    _write_state({
        "next_generation": generation + 1,
        "last_run_at": int(time.time()),
        "last_title": payload["title"],
        "last_focus": payload["focus"],
    })
    return True


async def run_iteration_loop(interval_seconds: int = 3600):
    await asyncio.sleep(10)
    while True:
        try:
            append_iteration_note()
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)
