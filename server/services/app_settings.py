import copy
import json
import os
import threading
from pathlib import Path
from typing import Optional

from services.provider_catalog import get_default_model_for_provider, get_default_provider_key, get_models_for_provider, list_provider_options

SETTINGS_PATH = Path(__file__).resolve().parents[1] / "runtime_settings.json"

AI_PROVIDER_STRATEGIES = ("auto", "heuristic_only")

_lock = threading.Lock()
_cache: Optional[dict] = None


def _default_settings() -> dict:
    selected_provider = get_default_provider_key() or "heuristic_only"
    default_model = get_default_model_for_provider(selected_provider) or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    selector_model = default_model
    return {
        "schedule": {
            "enabled": True,
            "interval_hours": 1.0,
        },
        "ai": {
            "selected_provider": selected_provider,
            "default_model": default_model,
            "selector_model": selector_model,
        },
    }


def _merge_settings(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_settings(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_settings_locked() -> dict:
    global _cache
    if _cache is not None:
        return copy.deepcopy(_cache)

    settings = _default_settings()
    if SETTINGS_PATH.exists():
        try:
            loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                settings = _merge_settings(settings, loaded)
        except (json.JSONDecodeError, OSError):
            pass

    _cache = settings
    return copy.deepcopy(settings)


def _write_settings_locked(settings: dict) -> None:
    global _cache
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _cache = copy.deepcopy(settings)


def get_all_settings() -> dict:
    with _lock:
        return _read_settings_locked()


def get_schedule_settings() -> dict:
    settings = get_all_settings().get("schedule", {})
    interval = float(settings.get("interval_hours", 3.0))
    return {
        "enabled": bool(settings.get("enabled", True)),
        "interval_hours": max(0.5, min(24.0, interval)),
    }


def update_schedule_settings(enabled: Optional[bool] = None, interval_hours: Optional[float] = None) -> dict:
    with _lock:
        settings = _read_settings_locked()
        schedule = settings.setdefault("schedule", {})
        if enabled is not None:
            schedule["enabled"] = bool(enabled)
        if interval_hours is not None:
            schedule["interval_hours"] = max(0.5, min(24.0, float(interval_hours)))
        _write_settings_locked(settings)
        return get_schedule_settings()


def _configured_providers() -> dict[str, bool]:
    return {
        "primary": bool(os.getenv("ANTHROPIC_API_KEY")),
        "fallback": bool(os.getenv("ANTHROPIC_FALLBACK_API_KEY")),
    }


def get_ai_settings() -> dict:
    defaults = _default_settings()["ai"]
    settings = get_all_settings().get("ai", {})
    provider_options = list_provider_options()
    valid_provider_keys = {provider["key"] for provider in provider_options}
    selected_provider = settings.get("selected_provider") or settings.get("provider_strategy") or defaults["selected_provider"]
    if selected_provider == "auto":
        selected_provider = defaults["selected_provider"]
    if selected_provider not in valid_provider_keys and selected_provider not in AI_PROVIDER_STRATEGIES:
        selected_provider = defaults["selected_provider"]

    available_models = get_models_for_provider(selected_provider)
    provider_default_model = get_default_model_for_provider(selected_provider) or defaults["default_model"]
    default_model = str(settings.get("default_model") or provider_default_model).strip() or provider_default_model
    if available_models and default_model not in {model["id"] for model in available_models}:
        default_model = provider_default_model or available_models[0]["id"]

    selector_model = str(settings.get("selector_model") or defaults["selector_model"]).strip() or default_model
    if available_models and selector_model not in {model["id"] for model in available_models}:
        selector_model = default_model

    providers = [
        {
            "key": "heuristic_only",
            "label": "仅本地启发式",
            "family": "local",
            "models": [],
            "default_model": None,
            "configured": True,
            "active": False,
            "preferred": False,
        },
        *[
            {
                **provider,
                "configured": True,
            }
            for provider in provider_options
        ],
    ]

    return {
        "selected_provider": selected_provider,
        "default_model": default_model,
        "selector_model": selector_model,
        "providers": providers,
        "models": available_models,
    }


def update_ai_settings(
    provider_strategy: Optional[str] = None,
    selected_provider: Optional[str] = None,
    default_model: Optional[str] = None,
    selector_model: Optional[str] = None,
) -> dict:
    with _lock:
        settings = _read_settings_locked()
        ai = settings.setdefault("ai", {})

        next_provider = selected_provider or provider_strategy
        valid_provider_keys = {provider["key"] for provider in list_provider_options()} | set(AI_PROVIDER_STRATEGIES)
        if next_provider is not None and next_provider in valid_provider_keys:
            ai["selected_provider"] = next_provider
        if default_model is not None:
            cleaned = default_model.strip()
            if cleaned:
                ai["default_model"] = cleaned
        if selector_model is not None:
            ai["selector_model"] = selector_model.strip() or ai.get("default_model") or _default_settings()["ai"]["default_model"]

        current_provider = ai.get("selected_provider") or _default_settings()["ai"]["selected_provider"]
        models = get_models_for_provider(current_provider)
        if models:
            model_ids = {model["id"] for model in models}
            if ai.get("default_model") not in model_ids:
                ai["default_model"] = models[0]["id"]
            if ai.get("selector_model") not in model_ids:
                ai["selector_model"] = ai["default_model"]

        _write_settings_locked(settings)
        return get_ai_settings()
