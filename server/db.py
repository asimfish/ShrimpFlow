from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///shrimpflow.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


# 启用 WAL mode
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _sqlite_existing_columns(conn, table_name: str) -> set[str]:
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _sqlite_ensure_columns(conn, table_name: str, columns: dict[str, str]) -> None:
    existing = _sqlite_existing_columns(conn, table_name)
    for name, ddl in columns.items():
        if name not in existing:
            conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}")


def ensure_runtime_schema() -> None:
    """Apply lightweight SQLite migrations needed for the live demo database."""
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS claw_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schema VARCHAR NOT NULL DEFAULT 'clawprofile/v1',
                name VARCHAR NOT NULL,
                display VARCHAR NOT NULL,
                description VARCHAR,
                author VARCHAR,
                tags VARCHAR,
                license VARCHAR,
                forked_from VARCHAR,
                trust VARCHAR DEFAULT 'local',
                injection VARCHAR,
                is_active INTEGER DEFAULT 0,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS shared_claw_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                display VARCHAR,
                description VARCHAR,
                profile VARCHAR,
                patterns VARCHAR,
                workflows VARCHAR,
                downloads INTEGER DEFAULT 0,
                stars INTEGER DEFAULT 0,
                tags VARCHAR,
                created_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS openclaw_invocation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                profile_id INTEGER,
                provider VARCHAR,
                model VARCHAR,
                selector_type VARCHAR,
                selected_pattern_slugs VARCHAR,
                prompt_excerpt VARCHAR,
                response_summary VARCHAR,
                status VARCHAR,
                created_at INTEGER
            )
            """
        )
        _sqlite_ensure_columns(
            conn,
            "skills",
            {
                "cot_uses": "INTEGER DEFAULT 0",
                "manual_uses": "INTEGER DEFAULT 0",
                "auto_uses": "INTEGER DEFAULT 0",
                "combo_patterns": "VARCHAR",
                "workflow_roles": "VARCHAR",
            },
        )
        _sqlite_ensure_columns(
            conn,
            "behavior_patterns",
            {
                "profile_id": "INTEGER",
                "slug": "VARCHAR",
                "trigger": "VARCHAR",
                "body": "VARCHAR",
                "source": "VARCHAR DEFAULT 'auto'",
                "confidence_level": "VARCHAR",
                "learned_from_data": "VARCHAR",
                "skill_alignment_score": "INTEGER DEFAULT 0",
                "user_feedback": "VARCHAR",
                "reject_count": "INTEGER DEFAULT 0",
                "heat_score": "REAL DEFAULT 50.0",
                "last_accessed_at": "INTEGER DEFAULT 0",
                "access_count": "INTEGER DEFAULT 0",
                "lifecycle_state": "VARCHAR DEFAULT 'active'",
            },
        )
        _sqlite_ensure_columns(
            conn,
            "team_workflows",
            {
                "profile_id": "INTEGER",
                "steps": "VARCHAR",
            },
        )
        _sqlite_ensure_columns(
            conn,
            "openclaw_sessions",
            {
                "profile_id": "INTEGER",
                "injected_pattern_slugs": "VARCHAR",
                "analysis_summary": "VARCHAR",
                "analysis_status": "VARCHAR",
            },
        )
        _sqlite_ensure_columns(
            conn,
            "openclaw_documents",
            {
                "profile_id": "INTEGER",
            },
        )
        # Brain 层: EventAtom + Episode 表
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS event_atoms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                source VARCHAR NOT NULL,
                project VARCHAR,
                intent VARCHAR,
                tool VARCHAR,
                artifact VARCHAR,
                outcome VARCHAR,
                error_signature VARCHAR,
                command_family VARCHAR,
                task_hint VARCHAR,
                context_tags VARCHAR
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_event_atoms_event_id ON event_atoms(event_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_event_atoms_timestamp ON event_atoms(timestamp)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project VARCHAR,
                start_ts INTEGER NOT NULL,
                end_ts INTEGER NOT NULL,
                duration_seconds INTEGER,
                task_label VARCHAR,
                task_category VARCHAR,
                event_count INTEGER DEFAULT 0,
                atom_count INTEGER DEFAULT 0,
                tool_sequence VARCHAR,
                intent_sequence VARCHAR,
                outcome VARCHAR,
                features VARCHAR,
                session_ids VARCHAR,
                created_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_episodes_start_ts ON episodes(start_ts)"
        )
        # Feature Graph: EpisodeFeature + FeatureEdge
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS episode_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER NOT NULL,
                project VARCHAR,
                task_category VARCHAR,
                archetype VARCHAR,
                feature_vector VARCHAR,
                norm_vector VARCHAR,
                created_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_episode_features_episode_id ON episode_features(episode_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS feature_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                similarity REAL NOT NULL,
                edge_type VARCHAR,
                created_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_feature_edges_source_id ON feature_edges(source_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_feature_edges_target_id ON feature_edges(target_id)"
        )
        # Evidence Ledger: 模式置信度变化审计账本
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS evidence_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER NOT NULL,
                episode_id INTEGER,
                evidence_type VARCHAR NOT NULL,
                description VARCHAR,
                confidence_before INTEGER,
                confidence_after INTEGER,
                delta INTEGER,
                source VARCHAR,
                created_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_evidence_ledger_pattern_id ON evidence_ledger(pattern_id)"
        )
        # Phase 3: 模式语义关系图
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS pattern_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_pattern_id INTEGER NOT NULL,
                target_pattern_id INTEGER NOT NULL,
                relation_type VARCHAR NOT NULL,
                weight REAL DEFAULT 1.0,
                evidence_description VARCHAR,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_pattern_relations_source ON pattern_relations(source_pattern_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_pattern_relations_target ON pattern_relations(target_pattern_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS agent_taste_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER,
                updated_at INTEGER,
                preferred_categories VARCHAR,
                preferred_confidence_threshold INTEGER DEFAULT 70,
                preferred_sources VARCHAR,
                decision_history VARCHAR,
                taste_summary VARCHAR
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS background_tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                stage TEXT,
                result TEXT,
                error TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS discovered_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL,
                category VARCHAR,
                description TEXT,
                source VARCHAR,
                source_url VARCHAR,
                safety_score INTEGER DEFAULT 100,
                safety_flags VARCHAR,
                status VARCHAR DEFAULT 'pending',
                adopted_skill_id INTEGER,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS skill_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR NOT NULL,
                skill_sequence VARCHAR,
                frequency INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 0.0,
                source VARCHAR DEFAULT 'mined',
                matched_pattern_ids VARCHAR,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
