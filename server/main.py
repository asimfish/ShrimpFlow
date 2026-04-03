import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import engine, Base, ensure_runtime_schema
from routes import agent_taste, events, skills, patterns, openclaw, digest, community, stats, collector, search, profiles, settings, episodes, tasks, claw_gen, meta_agent

app = FastAPI(title="ShrimpFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(patterns.router, prefix="/api")
app.include_router(openclaw.router, prefix="/api")
app.include_router(digest.router, prefix="/api")
app.include_router(community.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(collector.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(episodes.router, prefix="/api")
app.include_router(agent_taste.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(claw_gen.router, prefix="/api")
app.include_router(meta_agent.router, prefix="/api")


@app.on_event("startup")
async def on_startup():
    # 确保新模型被导入，create_all 才能建表
    import models.agent_taste  # noqa: F401
    import models.episode  # noqa: F401
    import models.feature_graph  # noqa: F401
    import models.invocation  # noqa: F401
    import models.skill  # noqa: F401
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    from seed import seed_database, ensure_runtime_records
    seed_database()
    ensure_runtime_records(run_session_analysis=False)
    # 启动定时采集调度器
    from services.scheduler import start_scheduler
    start_scheduler()
    from services.iteration_scheduler import start_iteration_scheduler
    start_iteration_scheduler()


if __name__ == "__main__":
    enable_reload = os.getenv("SHRIMPFLOW_RELOAD", "1") == "1"
    uvicorn.run("main:app", host="127.0.0.1", port=7891, reload=enable_reload)
