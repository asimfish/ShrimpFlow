import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session

from models.event import DevEvent
from models.skill import Skill
from models.openclaw import OpenClawDocument
from models.digest import DailySummary


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
    except Exception as e:
        result.errors.append(str(e)[:200])
        db.rollback()

    return result


# 2. Claude Code 日志采集
def collect_claude_code(db):
    result = CollectResult('claude_code')
    projects_dir = os.path.join(HOME, '.claude', 'projects')
    if not os.path.isdir(projects_dir):
        result.errors.append('~/.claude/projects/ not found')
        return result

    cutoff = _get_max_timestamp(db, 'claude_code')
    # 已处理的 session 标记
    processed = set()
    existing = db.query(OpenClawDocument.title).filter(OpenClawDocument.type == 'claude_session_index').all()
    for row in existing:
        processed.add(row[0])

    try:
        batch = []
        for project_dir in Path(projects_dir).iterdir():
            if not project_dir.is_dir():
                continue
            project_name = project_dir.name.split('-')[-1] if '-' in project_dir.name else project_dir.name

            for jsonl_file in project_dir.glob('*.jsonl'):
                with open(jsonl_file, 'r', errors='replace') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        if entry.get('type') != 'assistant':
                            continue
                        msg = entry.get('message', {})
                        raw_content = msg.get('content', '')
                        # content 可能是 str 或 list (Claude API 格式)
                        if isinstance(raw_content, list):
                            text_parts = []
                            for block in raw_content:
                                if isinstance(block, dict):
                                    if block.get('type') == 'text':
                                        text_parts.append(block.get('text', ''))
                                    elif 'text' in block:
                                        text_parts.append(block['text'])
                                elif isinstance(block, str):
                                    text_parts.append(block)
                            content = ' '.join(text_parts)
                        elif isinstance(raw_content, str):
                            content = raw_content
                        else:
                            continue
                        if not content:
                            continue

                        ts_str = entry.get('timestamp', '')
                        if not ts_str:
                            continue
                        try:
                            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            ts = int(dt.timestamp())
                        except (ValueError, TypeError):
                            continue

                        if ts <= cutoff:
                            result.skipped += 1
                            continue

                        session_id = entry.get('sessionId', '')
                        # 每个 session 只记录一次
                        session_key = f'{session_id}_{ts}'
                        if session_key in processed:
                            result.skipped += 1
                            continue
                        processed.add(session_key)

                        # 截取前 200 字作为 action
                        action_text = content[:200].replace('\n', ' ')
                        cwd = entry.get('cwd', '')

                        batch.append(DevEvent(
                            timestamp=ts, source='claude_code',
                            action=f'claude: {action_text}',
                            directory=cwd, project=project_name, branch='',
                            exit_code=0, duration_ms=0,
                            semantic=f'Claude Code 对话 ({entry.get("model", "unknown")})',
                            tags=json.dumps(['claude', 'ai']),
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
    cutoff = _get_max_timestamp(db, 'git')
    desktop = os.path.join(HOME, 'Desktop')

    # 找 git 仓库（深度 ≤ 2）
    repos = []
    for root, dirs, files in os.walk(desktop):
        depth = root.replace(desktop, '').count(os.sep)
        if depth > 2:
            dirs.clear()
            continue
        if '.git' in dirs:
            repos.append(root)
            dirs.remove('.git')

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
                if ts <= cutoff:
                    result.skipped += 1
                    continue

                # 获取当前分支
                branch_out = subprocess.run(
                    ['git', '-C', repo, 'branch', '--show-current'],
                    capture_output=True, text=True, timeout=5,
                )
                branch = branch_out.stdout.strip() if branch_out.returncode == 0 else 'unknown'

                batch.append(DevEvent(
                    timestamp=ts, source='git',
                    action=f'commit: {msg} ({commit_hash[:7]})',
                    directory=repo, project=project, branch=branch,
                    exit_code=0, duration_ms=0,
                    semantic=f'Git commit by {author}',
                    tags=json.dumps(['git', 'commit']),
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
    results.append(collect_clawd_docs(db))
    results.append(collect_git_history(db))
    return [r.to_dict() for r in results]
