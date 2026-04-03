from sqlalchemy import Column, Integer, String

from db import Base


class EventAtom(Base):
    __tablename__ = "event_atoms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    source = Column(String, nullable=False)
    project = Column(String, index=True)
    # 结构化行为原子字段
    intent = Column(String)  # 意图: coding/debugging/testing/deploying/reviewing/learning/configuring
    tool = Column(String)  # 工具: git/terminal/claude/cursor/codex/browser
    artifact = Column(String)  # 产物: file_path/branch/commit_hash/test_result
    outcome = Column(String)  # 结果: success/failure/partial/unknown
    error_signature = Column(String)  # 错误签名: 归一化的错误类型
    command_family = Column(String)  # 命令族: git_commit/npm_test/python_run 等
    task_hint = Column(String)  # 任务提示: 从上下文推断的任务目标
    context_tags = Column(String)  # JSON: 上下文标签


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project = Column(String, index=True)
    start_ts = Column(Integer, nullable=False, index=True)
    end_ts = Column(Integer, nullable=False)
    duration_seconds = Column(Integer)
    # 任务描述
    task_label = Column(String)  # AI 或启发式推断的任务标签
    task_category = Column(String)  # feature/bugfix/refactor/test/deploy/review/learn
    # 统计
    event_count = Column(Integer, default=0)
    atom_count = Column(Integer, default=0)
    tool_sequence = Column(String)  # JSON: 工具使用序列
    intent_sequence = Column(String)  # JSON: 意图序列
    outcome = Column(String)  # overall: success/failure/abandoned/unknown
    # 特征
    features = Column(String)  # JSON: 特征向量 {tool_dist, intent_dist, duration, ...}
    # 关联
    session_ids = Column(String)  # JSON: 关联的 openclaw_session_id 列表
    created_at = Column(Integer)
