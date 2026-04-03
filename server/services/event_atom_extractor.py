import json
import re
import time

from sqlalchemy.orm import Session

from models.episode import EventAtom
from models.event import DevEvent

# intent 推断规则
_INTENT_RULES = [
    (re.compile(r'commit|push|merge|rebase', re.I), 'committing'),
    (re.compile(r'test|pytest|jest|vitest|spec', re.I), 'testing'),
    (re.compile(r'debug|fix|error|bug|traceback', re.I), 'debugging'),
    (re.compile(r'deploy|docker|k8s|nginx|pm2', re.I), 'deploying'),
    (re.compile(r'review|pr |pull.?request|diff', re.I), 'reviewing'),
    (re.compile(r'install|pip|npm|pnpm|conda|brew', re.I), 'configuring'),
    (re.compile(r'build|compile|colcon|webpack|vite', re.I), 'building'),
    (re.compile(r'ssh|remote|scp|rsync', re.I), 'connecting'),
    (re.compile(r'learn|doc|read|study|tutorial', re.I), 'learning'),
]

# tool 推断
_TOOL_MAP = {
    'git': 'git',
    'claude_code': 'claude',
    'codex': 'codex',
    'vscode_cursor': 'editor',
    'openclaw': 'openclaw',
    'terminal': 'terminal',
    'shell': 'terminal',
    'env': 'system',
}

# command family 推断
_CMD_FAMILIES = [
    (re.compile(r'^git\s+(commit|add|push|pull|merge|rebase|checkout|branch|stash|log|diff|reset)', re.I), lambda m: f'git_{m.group(1)}'),
    (re.compile(r'^(npm|pnpm|yarn)\s+(run|install|build|test|dev)', re.I), lambda m: f'npm_{m.group(2)}'),
    (re.compile(r'^python\s', re.I), lambda _: 'python_run'),
    (re.compile(r'^(pytest|vitest|jest)', re.I), lambda m: f'test_{m.group(1)}'),
    (re.compile(r'^pip\s+(install|uninstall)', re.I), lambda m: f'pip_{m.group(1)}'),
    (re.compile(r'^docker\s+(build|run|compose|push)', re.I), lambda m: f'docker_{m.group(1)}'),
    (re.compile(r'^ssh\s', re.I), lambda _: 'ssh_connect'),
    (re.compile(r'^cd\s', re.I), lambda _: 'navigate'),
    (re.compile(r'^(cat|less|head|tail|grep|find|ls)\s', re.I), lambda m: f'read_{m.group(1)}'),
    (re.compile(r'^(vim|nano|code|cursor)\s', re.I), lambda _: 'editor_open'),
]

# error signature 提取
_ERROR_PATTERNS = [
    (re.compile(r'(ModuleNotFoundError|ImportError)'), 'import_error'),
    (re.compile(r'(SyntaxError|IndentationError)'), 'syntax_error'),
    (re.compile(r'(TypeError|AttributeError|KeyError|ValueError)'), 'type_error'),
    (re.compile(r'(ConnectionError|TimeoutError|ConnectionRefused)'), 'network_error'),
    (re.compile(r'(PermissionError|EACCES)'), 'permission_error'),
    (re.compile(r'(FileNotFoundError|ENOENT|No such file)'), 'file_not_found'),
    (re.compile(r'(FAILED|FAIL|Error|error|failed)', re.I), 'generic_error'),
]


def _infer_intent(source: str, action: str, semantic: str) -> str:
    text = f'{action} {semantic}'
    for pattern, intent in _INTENT_RULES:
        if pattern.search(text):
            return intent
    # source-based fallback
    if source in ('claude_code', 'codex'):
        return 'coding'
    if source == 'git':
        return 'committing'
    if source == 'openclaw':
        return 'learning'
    return 'coding'


def _infer_tool(source: str) -> str:
    return _TOOL_MAP.get(source, 'terminal')


def _infer_command_family(action: str) -> str:
    for pattern, extractor in _CMD_FAMILIES:
        m = pattern.search(action)
        if m:
            return extractor(m)
    return 'other'


def _infer_outcome(action: str, semantic: str, exit_code: int) -> str:
    if exit_code != 0:
        return 'failure'
    text = f'{action} {semantic}'
    if re.search(r'(success|passed|ok|done|完成)', text, re.I):
        return 'success'
    if re.search(r'(fail|error|crash|abort|拒绝)', text, re.I):
        return 'failure'
    return 'unknown'


def _extract_error_signature(action: str, semantic: str) -> str:
    text = f'{action} {semantic}'
    for pattern, sig in _ERROR_PATTERNS:
        if pattern.search(text):
            return sig
    return ''


def _extract_artifact(action: str, source: str) -> str:
    # 从 action 中提取文件路径、commit hash 等
    # commit hash
    m = re.search(r'\b([0-9a-f]{7,40})\b', action)
    if m and source == 'git':
        return f'commit:{m.group(1)[:7]}'
    # file path
    m = re.search(r'(/[\w./\-]+\.\w+)', action)
    if m:
        return f'file:{m.group(1)}'
    # session
    if 'session' in action.lower():
        m = re.search(r'session[:\s]+(\S+)', action, re.I)
        if m:
            return f'session:{m.group(1)[:20]}'
    return ''


def _extract_task_hint(action: str, semantic: str, source: str) -> str:
    # 从 semantic 字段提取任务提示
    if semantic and len(semantic) > 10:
        return semantic[:100]
    if source in ('claude_code', 'codex') and ':' in action:
        return action.split(':', 1)[1].strip()[:100]
    return ''


def extract_atoms_from_events(db: Session, limit: int = 2000) -> int:
    # 找出还没有 atom 的事件
    existing_event_ids = {
        row[0] for row in db.query(EventAtom.event_id).all()
    }

    events = db.query(DevEvent).order_by(
        DevEvent.timestamp.desc()
    ).limit(limit).all()

    count = 0
    batch = []
    for event in events:
        if event.id in existing_event_ids:
            continue

        atom = EventAtom(
            event_id=event.id,
            timestamp=event.timestamp,
            source=event.source,
            project=event.project,
            intent=_infer_intent(event.source, event.action, event.semantic or ''),
            tool=_infer_tool(event.source),
            artifact=_extract_artifact(event.action, event.source),
            outcome=_infer_outcome(event.action, event.semantic or '', event.exit_code),
            error_signature=_extract_error_signature(event.action, event.semantic or ''),
            command_family=_infer_command_family(event.action),
            task_hint=_extract_task_hint(event.action, event.semantic or '', event.source),
            context_tags=json.dumps(
                json.loads(event.tags) if event.tags else [],
                ensure_ascii=False,
            ),
        )
        batch.append(atom)
        count += 1

        if len(batch) >= 200:
            db.add_all(batch)
            db.flush()
            batch = []

    if batch:
        db.add_all(batch)
    db.commit()
    return count
