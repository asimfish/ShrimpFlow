from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from services.app_settings import get_ai_settings, update_ai_settings
from services.scheduler import get_schedule_config, update_schedule_config

router = APIRouter(tags=["settings"])


class ScheduleConfigRequest(BaseModel):
    enabled: Optional[bool] = None
    interval_hours: Optional[float] = None


class AIConfigRequest(BaseModel):
    selected_provider: Optional[str] = None
    provider_strategy: Optional[str] = None
    default_model: Optional[str] = None
    selector_model: Optional[str] = None


@router.get("/settings/schedule")
def get_schedule():
    return get_schedule_config()


@router.post("/settings/schedule")
def update_schedule(req: ScheduleConfigRequest):
    update_schedule_config(req.enabled, req.interval_hours)
    return get_schedule_config()


@router.get("/settings/ai")
def get_ai_config():
    return get_ai_settings()


@router.post("/settings/ai")
def update_ai_config(req: AIConfigRequest):
    return update_ai_settings(
        selected_provider=req.selected_provider,
        provider_strategy=req.provider_strategy,
        default_model=req.default_model,
        selector_model=req.selector_model,
    )
