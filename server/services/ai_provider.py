import os
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv

from services.app_settings import get_ai_settings
from services.provider_catalog import get_default_provider_key, list_provider_options, resolve_provider_runtime

load_dotenv()

logger = logging.getLogger(__name__)

_active_provider: Optional[str] = None
_last_invocation = {
    'provider': None,
    'model': None,
    'strategy': None,
}

RESCUE_PROVIDER_ORDER = (
    'claude:office3',
    'claude:aipor',
    'codex:crs',
)


def _get_http_client():
    # 检测系统代理（Clash/V2Ray 等），确保 SDK 能正常连接
    proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy') or os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    if not proxy:
        # macOS 常见本地代理端口
        for port in (7890, 7897, 1087, 8118):
            try:
                httpx.get(f'http://127.0.0.1:{port}', timeout=0.3)
                proxy = f'http://127.0.0.1:{port}'
                break
            except Exception:
                continue
    if proxy:
        logger.info(f'Using HTTP proxy: {proxy}')
        return httpx.Client(proxy=proxy, timeout=httpx.Timeout(60.0))
    return httpx.Client(timeout=httpx.Timeout(60.0))


def _create_anthropic_client(api_key: str, base_url: str):
    import anthropic
    return anthropic.Anthropic(api_key=api_key, base_url=base_url, http_client=_get_http_client())


def get_model() -> str:
    return get_ai_settings()['default_model']


def get_selector_model() -> str:
    return get_ai_settings()['selector_model']


def get_last_invocation_meta() -> dict:
    return dict(_last_invocation)


def _provider_fallback_order(selected_provider: Optional[str]) -> list[str]:
    options = list_provider_options()
    ordered = []
    if selected_provider and selected_provider not in {'auto', 'heuristic_only'}:
        ordered.append(selected_provider)
    active = next((item['key'] for item in options if item.get('active')), None)
    preferred = next((item['key'] for item in options if item.get('preferred')), None)
    default_key = get_default_provider_key()
    for key in [active, preferred, default_key, *RESCUE_PROVIDER_ORDER]:
        if key and key not in ordered:
            ordered.append(key)
    for item in options:
        if item['key'] not in ordered:
            ordered.append(item['key'])
    return ordered


def has_available_client(selected_provider: Optional[str] = None) -> bool:
    provider_key = selected_provider or get_ai_settings().get('selected_provider')
    if provider_key == 'heuristic_only':
        return False
    for key in _provider_fallback_order(provider_key):
        if resolve_provider_runtime(key):
            return True
    return False


def _call_anthropic(runtime: dict, messages: list[dict], model: str, max_tokens: int) -> Optional[str]:
    client = _create_anthropic_client(runtime['api_key'], runtime['base_url'])
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
    )
    text = ''.join(
        block.text for block in response.content
        if getattr(block, 'type', None) == 'text'
    ).strip()
    return text or None


def _responses_input(messages: list[dict]) -> list[dict]:
    items = []
    for message in messages:
        content = message.get('content', '')
        if isinstance(content, str):
            items.append({
                'role': message.get('role', 'user'),
                'content': [{'type': 'input_text', 'text': content}],
            })
        else:
            items.append({
                'role': message.get('role', 'user'),
                'content': [{'type': 'input_text', 'text': str(content)}],
            })
    return items


def _call_responses(runtime: dict, messages: list[dict], model: str, max_tokens: int) -> Optional[str]:
    base_url = runtime['base_url'].rstrip('/')
    url = f'{base_url}/responses'
    payload = {
        'model': model,
        'input': _responses_input(messages),
        'max_output_tokens': max_tokens,
    }
    client = _get_http_client()
    response = client.post(
        url,
        headers={
            'Authorization': f'Bearer {runtime["api_key"]}',
            'Content-Type': 'application/json',
        },
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    text = data.get('output_text')
    if isinstance(text, str) and text.strip():
        return text.strip()

    pieces = []
    for item in data.get('output', []) if isinstance(data.get('output'), list) else []:
        if not isinstance(item, dict):
            continue
        for content in item.get('content', []) if isinstance(item.get('content'), list) else []:
            if not isinstance(content, dict):
                continue
            if content.get('type') in {'output_text', 'text'} and isinstance(content.get('text'), str):
                pieces.append(content['text'])
    joined = ''.join(pieces).strip()
    return joined or None


def _error_text(error: Exception) -> str:
    return str(error).lower()


def _is_unsupported_model_error(error: Exception) -> bool:
    text = _error_text(error)
    return (
        '没有可用的渠道支持该模型' in text
        or 'unsupported model' in text
        or 'model_not_found' in text
    )


def _model_candidates(runtime: dict, target_model: Optional[str]) -> list[str]:
    ordered: list[str] = []
    for model_name in [
        target_model,
        runtime.get('default_model'),
        *[model.get('id') for model in runtime.get('models', []) if isinstance(model, dict)],
    ]:
        if isinstance(model_name, str) and model_name and model_name not in ordered:
            ordered.append(model_name)
    return ordered


def chat(messages: list[dict], max_tokens: int = 300, model: Optional[str] = None) -> Optional[str]:
    global _active_provider
    settings = get_ai_settings()
    selected_provider = settings.get('selected_provider')
    if selected_provider == 'heuristic_only':
        return None

    target_model = model if model else get_model()

    ordered_keys = _provider_fallback_order(selected_provider)
    if _active_provider and _active_provider in ordered_keys:
        ordered_keys = [_active_provider, *[key for key in ordered_keys if key != _active_provider]]

    for provider_key in ordered_keys:
        runtime = resolve_provider_runtime(provider_key)
        if not runtime:
            continue
        model_candidates = _model_candidates(runtime, target_model)
        last_error: Optional[Exception] = None
        for index, use_model in enumerate(model_candidates):
            try:
                if runtime['family'] == 'claude_code':
                    text = _call_anthropic(runtime, messages, use_model, max_tokens)
                else:
                    text = _call_responses(runtime, messages, use_model, max_tokens)
                if text:
                    _active_provider = provider_key
                    _last_invocation.update({
                        'provider': provider_key,
                        'model': use_model,
                        'strategy': selected_provider,
                    })
                    logger.info(f'AI provider [{provider_key}] success, model={use_model}')
                    return text
            except Exception as e:
                last_error = e
                if _is_unsupported_model_error(e) and index < len(model_candidates) - 1:
                    logger.warning(f'AI provider [{provider_key}] model {use_model} unsupported, retrying with safer model')
                    continue
                break
        if last_error is not None:
            logger.warning(f'AI provider [{provider_key}] failed: {last_error}')
        continue

    return None
