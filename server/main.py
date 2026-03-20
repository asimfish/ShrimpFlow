import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import engine, Base, ensure_runtime_schema
from routes import events, skills, patterns, openclaw, digest, community, stats, collector, search, profiles, settings

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


@app.on_event("startup")
async def on_startup():
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
    uvicorn.run("main:app", host="0.0.0.0", port=7891, reload=enable_reload)
