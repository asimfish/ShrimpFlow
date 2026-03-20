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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
