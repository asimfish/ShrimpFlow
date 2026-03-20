import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session

from models.event import DevEvent
from models.skill import Skill
from models.openclaw import OpenClawDocument, OpenClawSession
from models.digest import DailySummary
from services.openclaw_runtime import analyze_recent_sessions_with_active_profile


HOME = str(Path.home())


# 采集结果
class CollectResult:
    def __init__(self, source):
        self.source = source
        self.inserted = 0
        self.skipped = 0
        self.errors = []

    def to_dict(self):
        return {'source': self.source, 'inserted': self.inserted,
                'skipped': self.skipped, 'errors': self.errors[:5]}


# 获取增量起点（排除种子数据）
def _get_max_timestamp(db, source):
    row = db.query(DevEvent.timestamp).filter(
        DevEvent.source == source,
        ~DevEvent.tags.contains('"seed"'),
    ).order_by(DevEvent.timestamp.desc()).first()
    return row[0] if row else 0


# 更新技能
def _update_skill(db, action, timestamp):
    skill_map = {
        'python': ('Python', 'language'),
        'pip': ('pip', 'package-manager'),
        'conda': ('conda', 'package-manager'),
        'git': ('Git', 'vcs'),
        'docker': ('Docker', 'devops'),
        'ssh': ('SSH', 'network'),
        'npm': ('npm', 'package-manager'),
        'pnpm': ('pnpm', 'package-manager'),
        'node': ('Node.js', 'language'),
        'cargo': ('Rust/Cargo', 'language'),
        'go ': ('Go', 'language'),
        'rustc': ('Rust', 'language'),
        'cmake': ('CMake', 'tool'),
        'make': ('Make', 'tool'),
        'vim': ('Vim', 'editor'),
        'nvim': ('Neovim', 'editor'),
        'code': ('VS Code', 'editor'),
        'pytest': ('pytest', 'tool'),
        'colcon': ('colcon/ROS2', 'framework'),
        'ros': ('ROS', 'framework'),
        'gazebo': ('Gazebo', 'tool'),
        'tensorboard': ('TensorBoard', 'tool'),
        'nvidia-smi': ('CUDA/GPU', 'devops'),
        'curl': ('curl', 'network'),
        'wget': ('wget', 'network'),
    }
    action_lower = action.lower()
    for keyword, (name, category) in skill_map.items():
        if keyword in action_lower:
            skill = db.query(Skill).filter(Skill.name == name).first()
            if skill:
                skill.total_uses += 1
                skill.last_used = timestamp
                if skill.total_uses > 50:
                    skill.level = min(5, skill.level + 1)
            else:
                # 检查是否已存在（避免 flush 后重复）
                try:
                    db.add(Skill(name=name, category=category, level=1,
                                 total_uses=1, last_used=timestamp, first_seen=timestamp))
                    db.flush()
                except Exception:
                    db.rollback()
            break


# 1. Shell 历史采集
def collect_shell_history(db):
    result = CollectResult('shell_history')
    history_path = os.path.join(HOME, '.zsh_history')
    if not os.path.exists(history_path):
        result.errors.append('~/.zsh_history not found')
        return result

    # 用已有命令去重（非标准格式没有可靠时间戳）
    existing_actions = set()
    for row in db.query(DevEvent.action).filter(
        DevEvent.source == 'terminal',
        DevEvent.tags.contains('"history"'),
    ).all():
        existing_actions.add(row[0])

    try:
        with open(history_path, 'rb') as f:
            raw = f.read()
        text = raw.decode('utf-8', errors='replace')
        lines = text.split('\n')

        batch = []
        file_mtime = int(os.path.getmtime(history_path))
        for line in lines:
            # 标准 zsh 扩展格式: : timestamp:0;command
            m = re.match(r'^: (\d+):\d+;(.+)', line)
            if m:
                ts = int(m.group(1))
                cmd = m.group(2).strip()
            else:
                # 非标准格式: 纯命令行
                cmd = line.strip().rstrip('\\')
                if not cmd or cmd.startswith('#') or cmd.startswith('\\'):
                    continue
                ts = file_mtime

            cmd_truncated = cmd[:500]
            if cmd_truncated in existing_actions:
                result.skipped += 1
                continue
            if not cmd or cmd in ('ls', 'cd', 'pwd', 'clear', 'exit', '\\'):
                result.skipped += 1
                continue

            existing_actions.add(cmd_truncated)
            batch.append(DevEvent(
                timestamp=ts, source='terminal', action=cmd_truncated,
                directory=HOME, project='local', branch='',
                exit_code=0, duration_ms=0,
                semantic='', tags=json.dumps(['shell', 'history']),
            ))
            _update_skill(db, cmd, ts)
            result.inserted += 1

            if len(batch) >= 100:
                db.add_all(batch)
                db.flush()
                batch = []

        if batch:
            db.add_all(batch)
        db.commit()
        if result.inserted > 0:
            analyze_recent_sessions_with_active_profile(db, limit=min(result.inserted + 5, 50))
    except Exception as e:
        result.errors.append(str(e)[:200])
        db.rollback()

    return result


# 提取 content 文本（支持 str 和 list 格式）
def _extract_text(raw_content):
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        parts = []
        for block in raw_content:
            if isinstance(block, dict):
                if block.get('type') == 'text':
                    parts.append(block.get('text', ''))
                elif 'text' in block:
                    parts.append(block['text'])
            elif isinstance(block, str):
                parts.append(block)
        return ' '.join(parts)
    return ''


def _discover_git_repos() -> list[str]:
    search_roots = [
        (os.path.join(HOME, 'Desktop'), 3),
        (os.path.join(HOME, 'Desktop', '比赛'), 4),
    ]
    explicit_repos = [
        os.path.join(HOME, 'Desktop', '比赛', 'omnistack', 'OmniStack'),
    ]

    repos: set[str] = set()
    for root_path, max_depth in search_roots:
        if not os.path.isdir(root_path):
            continue
        base_depth = root_path.rstrip(os.sep).count(os.sep)
        for current_root, dirs, _files in os.walk(root_path):
            depth = current_root.rstrip(os.sep).count(os.sep) - base_depth
            if depth > max_depth:
                dirs.clear()
                continue
            if '.git' in dirs:
                repos.add(current_root)
                dirs.remove('.git')

    for repo in explicit_repos:
        if os.path.isdir(os.path.join(repo, '.git')):
            repos.add(repo)

    return sorted(repos)


# 2. Claude Code 日志采集 — 生成 OpenClawSession + DevEvent
def collect_claude_code(db):
    result = CollectResult('claude_code')
    projects_dir = os.path.join(HOME, '.claude', 'projects')
    if not os.path.isdir(projects_dir):
        result.errors.append('~/.claude/projects/ not found')
        return result

    # 已导入的 session 文件名
    existing_files = set()
    for row in db.query(OpenClawDocument.title).filter(OpenClawDocument.type == 'claude_session_index').all():
        existing_files.add(row[0])

    try:
        for project_dir in Path(projects_dir).iterdir():
            if not project_dir.is_dir():
                continue
            project_name = project_dir.name.replace('-Users-liyufeng-', '').replace('-', '/')
            # 简化项目名
            parts = project_name.split('/')
            project_name = parts[-1] if parts else project_name

            for jsonl_file in project_dir.glob('*.jsonl'):
                file_key = f'{project_dir.name}/{jsonl_file.name}'
                if file_key in existing_files:
                    result.skipped += 1
                    continue

                # 解析整个 session 文件
                messages = []
                first_ts = None
                last_ts = None
                session_id = jsonl_file.stem

                with open(jsonl_file, 'r', errors='replace') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        entry_type = entry.get('type', '')
                        if entry_type not in ('user', 'assistant'):
                            continue

                        msg = entry.get('message', {})
                        content = _extract_text(msg.get('content', ''))
                        if not content:
                            continue

                        ts_str = entry.get('timestamp', '')
                        ts = 0
                        if ts_str:
                            try:
                                dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                ts = int(dt.timestamp())
                            except (ValueError, TypeError):
                                pass

                        if ts and not first_ts:
                            first_ts = ts
                        if ts:
                            last_ts = ts

                        role = 'user' if entry_type == 'user' else 'assistant'
                        messages.append({
                            'role': role,
                            'content': content[:500],
                            'timestamp': ts,
                        })

                if not messages or len(messages) < 2:
                    result.skipped += 1
                    continue

                # 生成 session title（取第一条 user 消息的前50字）
                first_user = next((m for m in messages if m['role'] == 'user'), None)
                title = first_user['content'][:50] if first_user else f'Claude Code Session {session_id[:8]}'
                title = title.replace('\n', ' ')

                created_at = first_ts if first_ts else int(os.path.getmtime(jsonl_file))

                # 推断 category
                content_lower = ' '.join(m['content'].lower() for m in messages[:5])
                if any(w in content_lower for w in ['bug', 'fix', 'error', 'debug', '报错']):
                    category = 'debug'
                elif any(w in content_lower for w in ['review', '审查', '检查']):
                    category = 'review'
                elif any(w in content_lower for w in ['设计', 'design', '架构', 'architecture']):
                    category = 'architecture'
                elif any(w in content_lower for w in ['论文', 'paper', '分析']):
                    category = 'paper'
                else:
                    category = 'learning'

                # 转换为 OpenClawMessage 格式
                openclaw_messages = []
                for m in messages[:50]:  # 限制50条消息
                    openclaw_messages.append({
                        'role': m['role'],
                        'content': m['content'],
                        'timestamp': m['timestamp'],
                    })

                summary = f'Claude Code 对话 ({len(messages)} 条消息, 项目: {project_name})'

                # 写入 OpenClawSession
                session = OpenClawSession(
                    title=title, category=category,
                    messages=json.dumps(openclaw_messages, ensure_ascii=False),
                    project=project_name,
                    tags=json.dumps(['claude_code', project_name]),
                    created_at=created_at, summary=summary,
                )
                db.add(session)
                db.flush()

                # 标记已处理
                db.add(OpenClawDocument(
                    title=file_key, type='claude_session_index',
                    content=f'Session {session.id}: {title}',
                    tags=json.dumps(['claude_code', 'index']),
                    created_at=created_at, source_session_id=session.id,
                ))

                # 写入 DevEvent
                db.add(DevEvent(
                    timestamp=created_at, source='claude_code',
                    action=f'claude session: {title}',
                    directory='', project=project_name, branch='',
                    exit_code=0, duration_ms=0,
                    semantic=summary,
                    tags=json.dumps(['claude', 'ai', 'session', category, project_name]),
                    openclaw_session_id=session.id,
                ))

                result.inserted += 1

        db.commit()
    except Exception as e:
        result.errors.append(str(e)[:200])
        db.rollback()

    return result


def collect_codex_sessions(db):
    result = CollectResult('codex')
    sessions_root = os.path.join(HOME, '.codex', 'sessions')
    if not os.path.isdir(sessions_root):
        result.errors.append('~/.codex/sessions/ not found')
        return result

    existing_files = {
        row[0]
        for row in db.query(OpenClawDocument.title).filter(OpenClawDocument.type == 'codex_session_index').all()
    }

    try:
        for jsonl_file in Path(sessions_root).rglob('*.jsonl'):
            file_key = str(jsonl_file).replace(f'{sessions_root}/', '')
            if file_key in existing_files:
                result.skipped += 1
                continue

            messages = []
            first_ts = None
            cwd = ''

            with open(jsonl_file, 'r', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if entry.get('type') == 'session_meta':
                        payload = entry.get('payload', {})
                        cwd = payload.get('cwd', '') or cwd
                        ts_str = entry.get('timestamp', '')
                        if ts_str:
                            try:
                                first_ts = int(datetime.fromisoformat(ts_str.replace('Z', '+00:00')).timestamp())
                            except (ValueError, TypeError):
                                pass
                        continue

                    if entry.get('type') != 'response_item':
                        continue

                    payload = entry.get('payload', {})
                    item_type = payload.get('type')
                    role = payload.get('role')
                    if item_type != 'message' or role not in ('assistant', 'user'):
                        continue

                    text_parts = []
                    for block in payload.get('content', []):
                        if isinstance(block, dict):
                            text = block.get('text') or block.get('content') or ''
                            if text:
                                text_parts.append(text)
                    content = '\n'.join(text_parts).strip()
                    if not content:
                        continue

                    ts_str = entry.get('timestamp', '')
                    ts = 0
                    if ts_str:
                        try:
                            ts = int(datetime.fromisoformat(ts_str.replace('Z', '+00:00')).timestamp())
                        except (ValueError, TypeError):
                            pass
                    if ts and not first_ts:
                        first_ts = ts

                    messages.append({
                        'role': role,
                        'content': content[:800],
                        'timestamp': ts,
                    })

            if len(messages) < 2:
                result.skipped += 1
                continue

            title = next((m['content'][:60].replace('\n', ' ') for m in messages if m['role'] == 'user'), f'Codex Session {jsonl_file.stem[:8]}')
            created_at = first_ts or int(os.path.getmtime(jsonl_file))
            project_name = os.path.basename(cwd) if cwd else 'codex'

            content_lower = ' '.join(m['content'].lower() for m in messages[:5])
            if any(w in content_lower for w in ['bug', 'fix', 'error', 'debug', '报错']):
                category = 'debug'
            elif any(w in content_lower for w in ['review', '审查', '检查']):
                category = 'review'
            elif any(w in content_lower for w in ['设计', 'design', '架构', 'architecture']):
                category = 'architecture'
            elif any(w in content_lower for w in ['论文', 'paper', '分析']):
                category = 'paper'
            else:
                category = 'learning'

            session = OpenClawSession(
                title=title,
                category=category,
                messages=json.dumps(messages[:60], ensure_ascii=False),
                project=project_name,
                tags=json.dumps(['codex', project_name], ensure_ascii=False),
                created_at=created_at,
                summary=f'Codex 对话 ({len(messages)} 条消息, 项目: {project_name})',
            )
            db.add(session)
            db.flush()

            db.add(OpenClawDocument(
                title=file_key,
                type='codex_session_index',
                content=f'Session {session.id}: {title}',
                tags=json.dumps(['codex', 'index'], ensure_ascii=False),
                created_at=created_at,
                source_session_id=session.id,
            ))

            db.add(DevEvent(
                timestamp=created_at,
                source='codex',
                action=f'codex session: {title}',
                directory=cwd,
                project=project_name,
                branch='',
                exit_code=0,
                duration_ms=0,
                semantic=f'Codex 对话 ({len(messages)} 条消息, 项目: {project_name})',
                tags=json.dumps(['codex', 'ai', 'session', category, project_name], ensure_ascii=False),
                openclaw_session_id=session.id,
            ))
            result.inserted += 1

        db.commit()
        if result.inserted > 0:
            analyze_recent_sessions_with_active_profile(db, limit=min(result.inserted + 5, 50))
    except Exception as e:
        result.errors.append(str(e)[:200])
        db.rollback()

    return result


# 3. OpenClaw/clawd 简报采集
def collect_clawd_docs(db):
    result = CollectResult('clawd')
    memory_dir = os.path.join(HOME, 'clawd', 'memory')
    if not os.path.isdir(memory_dir):
        result.errors.append('~/clawd/memory/ not found')
        return result

    # 已导入的文件
    existing = set()
    for row in db.query(OpenClawDocument.title).filter(OpenClawDocument.type.in_([
        'daily_summary', 'ai_tools_daily', 'ai_tools_weekly', 'ai_tools_index',
        'github_daily', 'media_daily', 'misc',
    ])).all():
        existing.add(row[0])

    # 文件名 → type 映射
    type_patterns = [
        (r'^daily-summary-(\d{4}-\d{2}-\d{2})\.md$', 'daily_summary'),
        (r'^ai-tools-weekly-(\d{4}-W\d{2})\.md$', 'ai_tools_weekly'),
        (r'^ai-tools-index\.md$', 'ai_tools_index'),
        (r'^ai-tools-(\d{4}-\d{2}-\d{2})\.md$', 'ai_tools_daily'),
        (r'^github-daily-(\d{4}-\d{2}-\d{2})\.md$', 'github_daily'),
        (r'^media-daily-(\d{4}-\d{2}-\d{2})\.md$', 'media_daily'),
    ]

    try:
        for filename in sorted(os.listdir(memory_dir)):
            if not filename.endswith('.md'):
                continue
            if filename in existing:
                result.skipped += 1
                continue

            filepath = os.path.join(memory_dir, filename)
            file_mtime = int(os.path.getmtime(filepath))

            # 确定 type
            doc_type = 'misc'
            date_str = ''
            for pattern, dtype in type_patterns:
                m = re.match(pattern, filename)
                if m:
                    doc_type = dtype
                    if m.groups():
                        date_str = m.group(1)
                    break

            with open(filepath, 'r', errors='replace') as f:
                content = f.read()

            # 写入 OpenClawDocument
            tags = [doc_type]
            if date_str:
                tags.append(date_str)
            db.add(OpenClawDocument(
                title=filename, type=doc_type, content=content,
                tags=json.dumps(tags), created_at=file_mtime,
                source_session_id=0,
            ))

            # 生成 DevEvent
            db.add(DevEvent(
                timestamp=file_mtime, source='openclaw',
                action=f'clawd: {filename}',
                directory=memory_dir, project='clawd', branch='',
                exit_code=0, duration_ms=0,
                semantic=f'OpenClaw {doc_type} 简报',
                tags=json.dumps(['openclaw', 'clawd', doc_type]),
            ))

            # 如果是 daily_summary，upsert DailySummary
            if doc_type == 'daily_summary' and date_str:
                existing_summary = db.query(DailySummary).filter(DailySummary.date == date_str).first()
                summary_text = content[:500]
                if existing_summary:
                    existing_summary.ai_summary = summary_text
                else:
                    db.add(DailySummary(
                        date=date_str, event_count=0,
                        top_projects=json.dumps([]),
                        top_commands=json.dumps([]),
                        ai_summary=summary_text,
                        openclaw_sessions=0,
                    ))

            result.inserted += 1

        db.commit()
    except Exception as e:
        result.errors.append(str(e)[:200])
        db.rollback()

    return result


# 4. Git 历史采集
def collect_git_history(db):
    result = CollectResult('git_history')
    repos = _discover_git_repos()
    existing_actions = {
        row[0] for row in db.query(DevEvent.action).filter(DevEvent.source == 'git').all()
    }

    try:
        batch = []
        for repo in repos:
            project = os.path.basename(repo)
            try:
                out = subprocess.run(
                    ['git', '-C', repo, 'log', '--format=%H|%at|%s|%an', '-n', '200'],
                    capture_output=True, text=True, timeout=10,
                )
                if out.returncode != 0:
                    continue
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

            for line in out.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|', 3)
                if len(parts) < 4:
                    continue
                commit_hash, ts_str, msg, author = parts
                ts = int(ts_str)
                action = f'commit: {msg} ({commit_hash[:7]})'
                if action in existing_actions:
                    result.skipped += 1
                    continue
                existing_actions.add(action)

                # 获取当前分支
                branch_out = subprocess.run(
                    ['git', '-C', repo, 'branch', '--show-current'],
                    capture_output=True, text=True, timeout=5,
                )
                branch = branch_out.stdout.strip() if branch_out.returncode == 0 else 'unknown'

                batch.append(DevEvent(
                    timestamp=ts, source='git',
                    action=action,
                    directory=repo, project=project, branch=branch,
                    exit_code=0, duration_ms=0,
                    semantic=f'Git commit by {author}',
                    tags=json.dumps(['git', 'commit', 'history', project, commit_hash[:7]]),
                ))
                result.inserted += 1

                if len(batch) >= 100:
                    db.add_all(batch)
                    db.flush()
                    batch = []

        if batch:
            db.add_all(batch)
        db.commit()
    except Exception as e:
        result.errors.append(str(e)[:200])
        db.rollback()

    return result


# 一键采集所有
def collect_all(db):
    results = []
    results.append(collect_shell_history(db))
    results.append(collect_claude_code(db))
    results.append(collect_codex_sessions(db))
    results.append(collect_clawd_docs(db))
    results.append(collect_git_history(db))
    return [r.to_dict() for r in results]
