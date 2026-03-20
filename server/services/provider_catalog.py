import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - compatibility for Python < 3.11
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        tomllib = None  # type: ignore

HOME = Path.home()
CLAUDE_CONFIG_PATH = HOME / ".claude" / "config.json"
CLAUDE_SETTINGS_PATH = HOME / ".claude" / "settings.json"
OPENCLAW_CONFIG_PATH = HOME / ".openclaw" / "openclaw.json"
CODEX_CONFIG_PATH = HOME / ".codex" / "config.toml"
CODEX_AUTH_PATH = HOME / ".codex" / "auth.json"

DEFAULT_CLAUDE_MODELS = [
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "claude-opus-4-6", "name": "Claude Opus 4.6"},
]

SAFE_DEFAULT_CLAUDE_MODELS = [
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
]

STABLE_PROVIDER_PRIORITY = (
    "claude:office3",
    "claude:aipor",
    "codex:crs",
)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _read_toml(path: Path) -> dict:
    if tomllib is None:
        return {}
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return {}


def _models_from_openclaw() -> dict[str, list[dict]]:
    config = _read_json(OPENCLAW_CONFIG_PATH)
    providers = config.get("models", {}).get("providers", {})
    mapping: dict[str, list[dict]] = {}
    for provider in providers.values():
        if not isinstance(provider, dict):
            continue
        base_url = provider.get("baseUrl")
        models = provider.get("models", [])
        if isinstance(base_url, str) and isinstance(models, list) and models:
            cleaned = []
            for item in models:
                if not isinstance(item, dict):
                    continue
                model_id = str(item.get("id", "")).strip()
                if not model_id:
                    continue
                cleaned.append({
                    "id": model_id,
                    "name": str(item.get("name", model_id)).strip() or model_id,
                })
            if cleaned:
                mapping[base_url.rstrip("/")] = cleaned
    return mapping


def _infer_claude_models(base_url: str) -> list[dict]:
    base = base_url.rstrip("/")
    if base in _models_from_openclaw():
        return _models_from_openclaw()[base]
    if "code.aipor.cc" in base:
        return DEFAULT_CLAUDE_MODELS
    if "/api/claude_code/" in base:
        return SAFE_DEFAULT_CLAUDE_MODELS
    return SAFE_DEFAULT_CLAUDE_MODELS


def _preferred_model_id(models: list[dict]) -> str:
    for preferred in ("claude-sonnet-4-6", "claude-sonnet-4-5", "gpt-5.4", "claude-opus-4-6"):
        for model in models:
            if model.get("id") == preferred:
                return preferred
    return models[0]["id"] if models else ""


def _resolve_active_claude_profile(config: dict, settings: dict) -> Optional[str]:
    env = settings.get("env", {})
    current_base_url = env.get("ANTHROPIC_BASE_URL")
    current_auth_token = env.get("ANTHROPIC_AUTH_TOKEN")
    profiles = config.get("providerProfiles", {})
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        if profile.get("baseUrl") == current_base_url and profile.get("authToken") == current_auth_token:
            return name
    return None


@lru_cache(maxsize=1)
def get_provider_catalog() -> dict:
    claude_config = _read_json(CLAUDE_CONFIG_PATH)
    claude_settings = _read_json(CLAUDE_SETTINGS_PATH)
    codex_config = _read_toml(CODEX_CONFIG_PATH)
    codex_auth = _read_json(CODEX_AUTH_PATH)

    active_claude_profile = _resolve_active_claude_profile(claude_config, claude_settings)
    default_claude_profile = claude_config.get("primaryApiKey") if isinstance(claude_config.get("primaryApiKey"), str) else None

    providers: list[dict] = []

    for name, profile in (claude_config.get("providerProfiles", {}) or {}).items():
        if not isinstance(profile, dict):
            continue
        base_url = str(profile.get("baseUrl", "")).strip()
        if not base_url:
            continue
        models = _infer_claude_models(base_url)
        providers.append({
            "key": f"claude:{name}",
            "label": f"Claude Code / {name}",
            "family": "claude_code",
            "provider_name": name,
            "base_url": base_url,
            "models": models,
            "default_model": _preferred_model_id(models),
            "active": name == active_claude_profile,
            "preferred": name == default_claude_profile,
        })

    codex_provider_key = str(codex_config.get("model_provider", "")).strip()
    codex_model = str(codex_config.get("model", "")).strip()
    codex_providers = codex_config.get("model_providers", {}) or {}
    codex_provider = codex_providers.get(codex_provider_key, {}) if isinstance(codex_providers, dict) else {}
    if codex_provider_key and isinstance(codex_provider, dict):
        base_url = str(codex_provider.get("base_url", "")).strip()
        env_key = str(codex_provider.get("env_key", "")).strip()
        api_key = os.getenv(env_key) or codex_auth.get("OPENAI_API_KEY") or ""
        providers.append({
            "key": f"codex:{codex_provider_key}",
            "label": f"Codex / {codex_provider_key}",
            "family": "codex",
            "provider_name": codex_provider_key,
            "base_url": base_url,
            "models": [{"id": codex_model, "name": codex_model}] if codex_model else [],
            "default_model": _preferred_model_id([{"id": codex_model, "name": codex_model}] if codex_model else []),
            "active": True,
            "preferred": True,
            "wire_api": str(codex_provider.get("wire_api", "responses")),
            "env_key": env_key,
            "api_key_present": bool(api_key),
        })

    default_provider_key = None
    for provider in providers:
        if provider.get("active"):
            default_provider_key = provider["key"]
            break
    if default_provider_key is None and providers:
        default_provider_key = providers[0]["key"]

    return {
        "providers": providers,
        "default_provider_key": default_provider_key,
    }


def list_provider_options() -> list[dict]:
    return [
        {
            "key": provider["key"],
            "label": provider["label"],
            "family": provider["family"],
            "models": provider.get("models", []),
            "default_model": provider.get("default_model"),
            "active": provider.get("active", False),
            "preferred": provider.get("preferred", False),
        }
        for provider in get_provider_catalog()["providers"]
    ]


def get_default_provider_key() -> Optional[str]:
    catalog = get_provider_catalog()
    available = {provider["key"] for provider in catalog["providers"]}
    for key in STABLE_PROVIDER_PRIORITY:
        if key in available:
            return key
    return catalog.get("default_provider_key")


def resolve_provider_runtime(provider_key: Optional[str]) -> Optional[dict]:
    if not provider_key:
        return None
    for provider in get_provider_catalog()["providers"]:
        if provider["key"] != provider_key:
            continue
        if provider["family"] == "claude_code":
            claude_config = _read_json(CLAUDE_CONFIG_PATH)
            profile_name = provider["provider_name"]
            profile = (claude_config.get("providerProfiles", {}) or {}).get(profile_name, {})
            api_key = str(profile.get("authToken", "")).strip()
            if not api_key:
                return None
            return {
                "family": "claude_code",
                "provider_key": provider_key,
                "provider_name": profile_name,
                "base_url": provider["base_url"],
                "api_key": api_key,
                "models": provider.get("models", []),
                "default_model": provider.get("default_model"),
            }
        if provider["family"] == "codex":
            codex_config = _read_toml(CODEX_CONFIG_PATH)
            codex_auth = _read_json(CODEX_AUTH_PATH)
            provider_name = provider["provider_name"]
            provider_config = (codex_config.get("model_providers", {}) or {}).get(provider_name, {})
            env_key = str(provider_config.get("env_key", "")).strip()
            api_key = os.getenv(env_key) or codex_auth.get("OPENAI_API_KEY")
            if not api_key:
                return None
            return {
                "family": "codex",
                "provider_key": provider_key,
                "provider_name": provider_name,
                "base_url": str(provider_config.get("base_url", "")).rstrip("/"),
                "api_key": api_key,
                "wire_api": str(provider_config.get("wire_api", "responses")),
                "models": provider.get("models", []),
                "default_model": provider.get("default_model"),
            }
    return None


def get_models_for_provider(provider_key: Optional[str]) -> list[dict]:
    if not provider_key:
        return []
    runtime = resolve_provider_runtime(provider_key)
    if not runtime:
        for provider in list_provider_options():
            if provider["key"] == provider_key:
                return provider.get("models", [])
        return []
    return runtime.get("models", [])


def get_default_model_for_provider(provider_key: Optional[str]) -> str:
    if not provider_key:
        return ""
    for provider in get_provider_catalog()["providers"]:
        if provider["key"] == provider_key:
            return str(provider.get("default_model", "")).strip()
    models = get_models_for_provider(provider_key)
    return _preferred_model_id(models)
