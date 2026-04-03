"""Scan local skill libraries (Cursor / Claude / Codex / project) and match against DB skills."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy.orm import Session

from models.pattern import BehaviorPattern
from models.skill import Skill
from services.pattern_mining import _confidence_to_level, _name_to_slug
from services.skill_recommender import _normalize_name, _tokenize

# Paths relative to user home or project root
_SKILL_LIBRARY_REL_PATHS = (
    ".cursor/skills-cursor",
    ".claude/skills",
    ".codex/skills",
)

_ARROW_RE = re.compile(r"[→->]\s*(.+)$")
_SKILL_TOKEN_RE = re.compile(r"^[\w./-]+")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")


@dataclass
class ExternalSkill:
    name: str
    description: str
    category: str
    path: str
    source_library: str
    paths: list[str] = field(default_factory=list)

    def merge_from(self, other: ExternalSkill) -> None:
        if other.path and other.path not in self.paths:
            self.paths.append(other.path)
        if (not self.description or len(other.description) > len(self.description)) and other.description:
            self.description = other.description
        if self.category == "uncategorized" and other.category != "uncategorized":
            self.category = other.category


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _expand_skill_roots() -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    home = Path.home()

    for rel in _SKILL_LIBRARY_REL_PATHS:
        base = home / rel
        try:
            if base.is_dir():
                roots.append((str(base), base.resolve()))
        except OSError:
            continue

    proj_skills = _project_root() / "skills"
    try:
        if proj_skills.is_dir():
            roots.append((str(proj_skills.resolve()), proj_skills.resolve()))
    except OSError:
        pass

    return roots


def _strip_inline_note(segment: str) -> str:
    s = segment.strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    s = re.sub(r"\s*（[^）]*）\s*$", "", s).strip()
    m = _SKILL_TOKEN_RE.match(s)
    return m.group(0).strip() if m else s


def _parse_index_bullets(text: str, default_category: str) -> list[tuple[str, str, str]]:
    """Return list of (skill_name, category, one_line_description)."""
    found: list[tuple[str, str, str]] = []
    category = default_category
    for raw_line in text.splitlines():
        line = raw_line.strip()
        sec = _SECTION_RE.match(line)
        if sec:
            cat = sec.group(1).strip().rstrip("/").strip()
            category = cat if cat else default_category
            continue
        if not line.startswith("-"):
            continue
        body = line.lstrip("-").strip()
        desc = body
        m = _ARROW_RE.search(body)
        if not m:
            continue
        rhs = m.group(1).strip()
        desc = body[: m.start()].strip()
        for part in rhs.split(","):
            name = _strip_inline_note(part)
            if not name or len(name) < 2:
                continue
            if not re.match(r"^[\w./-]+$", name):
                continue
            found.append((name, category, desc))
    return found


def _safe_read_text(path: Path, limit: int = 400_000) -> str | None:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
        if len(data) > limit:
            return data[:limit]
        return data
    except OSError:
        return None


def _extract_skill_md_body(path: Path) -> str | None:
    """Return Markdown body after YAML frontmatter (or full file if no frontmatter)."""
    raw = _safe_read_text(path, limit=400_000)
    if not raw:
        return None
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            return raw[end + 4 :].lstrip("\n")
    return raw


def _parse_skill_md_frontmatter(path: Path) -> tuple[str | None, str | None]:
    raw = _safe_read_text(path, limit=120_000)
    if not raw:
        return None, None
    name: str | None = None
    description: str | None = None
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            fm = raw[3:end]
            for line in fm.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    k = key.strip().lower()
                    v = val.strip().strip('"').strip("'")
                    if k == "name" and v:
                        name = v
                    elif k == "description" and v:
                        description = v
    if not name:
        for line in raw.splitlines():
            if line.startswith("# "):
                name = line[2:].strip()
                break
    return name, description


def _relative_skill_category(skill_path: Path, library_root: Path) -> str:
    try:
        rel = skill_path.relative_to(library_root)
        parts = rel.parts
        if len(parts) > 1:
            return parts[0].rstrip("/")
    except ValueError:
        pass
    return "uncategorized"


def scan_local_skill_libraries() -> list[ExternalSkill]:
    """Scan known skill directories; parse INDEX.md and SKILL.md files."""
    by_key: dict[str, ExternalSkill] = {}

    for library_label, root in _expand_skill_roots():
        index_path = root / "INDEX.md"
        if index_path.is_file():
            content = _safe_read_text(index_path)
            if content:
                for name, category, desc in _parse_index_bullets(content, "index"):
                    key = _normalize_name(name)
                    if not key:
                        continue
                    path_str = str(index_path)
                    ex = ExternalSkill(
                        name=name,
                        description=desc or "",
                        category=category,
                        path=path_str,
                        source_library=library_label,
                        paths=[path_str],
                    )
                    if key in by_key:
                        by_key[key].merge_from(ex)
                    else:
                        by_key[key] = ex

        try:
            for skill_file in root.rglob("SKILL.md"):
                try:
                    if not skill_file.is_file():
                        continue
                except OSError:
                    continue
                name, description = _parse_skill_md_frontmatter(skill_file)
                if not name:
                    continue
                key = _normalize_name(name)
                if not key:
                    continue
                category = _relative_skill_category(skill_file, root)
                path_str = str(skill_file.resolve())
                ex = ExternalSkill(
                    name=name,
                    description=description or "",
                    category=category,
                    path=path_str,
                    source_library=library_label,
                    paths=[path_str],
                )
                if key in by_key:
                    by_key[key].merge_from(ex)
                else:
                    by_key[key] = ex
        except OSError:
            continue

    return sorted(by_key.values(), key=lambda x: (x.source_library, x.name.lower()))


def _skill_md_path_from_external(ext: ExternalSkill) -> Path | None:
    for p in ext.paths:
        if p.endswith("SKILL.md"):
            cand = Path(p)
            try:
                if cand.is_file():
                    return cand.resolve()
            except OSError:
                continue
    return None


def _category_for_pattern(category: str) -> str:
    c = (category or "").strip().lower()
    allowed = frozenset({"coding", "review", "git", "devops", "collaboration"})
    if c in allowed:
        return c
    return "coding"


def import_skills_as_patterns(db: Session) -> int:
    """Import local SKILL.md entries as confirmed BehaviorPatterns for pattern mining."""
    external = scan_local_skill_libraries()
    now = int(time.time())
    imported = 0

    for ext in external:
        skill_path = _skill_md_path_from_external(ext)
        if not skill_path:
            continue

        body = _extract_skill_md_body(skill_path)
        if not body:
            continue

        name = (ext.name or "").strip()
        if not name:
            continue

        slug = _name_to_slug(name)
        if not slug:
            slug = "skill-" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]

        existing = db.query(BehaviorPattern).filter(BehaviorPattern.slug == slug).first()
        if existing:
            continue

        desc = (ext.description or "").strip()
        if not desc:
            first_line = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
            desc = first_line[:500] if first_line else name

        trigger = json.dumps(
            {
                "when": "本地技能库 SKILL.md",
                "event": "skill_library",
                "context": [ext.source_library, str(skill_path)],
            },
            ensure_ascii=False,
        )

        learned_from_data = json.dumps(
            [
                {
                    "context": str(skill_path),
                    "insight": desc[:240],
                    "confidence": 80,
                }
            ],
            ensure_ascii=False,
        )

        pattern = BehaviorPattern(
            name=name,
            category=_category_for_pattern(ext.category),
            description=desc[:500],
            confidence=80,
            evidence_count=1,
            learned_from="skill_library",
            rule="从本地技能库导入的 SKILL.md（人工策展）",
            created_at=now,
            status="confirmed",
            evolution=json.dumps(
                [
                    {
                        "date": time.strftime("%m-%d"),
                        "confidence": 80,
                        "event_description": "从本地技能库导入",
                    }
                ],
                ensure_ascii=False,
            ),
            rules=json.dumps([]),
            executions=json.dumps([]),
            applicable_scenarios=json.dumps([str(skill_path)]),
            slug=slug,
            trigger=trigger,
            body=body,
            source="imported",
            confidence_level=_confidence_to_level(80),
            learned_from_data=learned_from_data,
            skill_alignment_score=0,
        )
        db.add(pattern)
        imported += 1

    db.commit()
    return imported


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _upgrade_hint(external_name: str, local_name: str) -> bool:
    en = (external_name or "").lower()
    ln = (local_name or "").lower()
    if not ln or ln not in en:
        return False
    markers = (
        "v2",
        "v3",
        "pro",
        "plus",
        "advanced",
        "进阶",
        "高级",
        "专家",
        "expert",
        "deep",
        "深度",
    )
    return any(m in en for m in markers) and en != ln


def match_external_with_local(
    db: Session,
    external_skills: list[ExternalSkill],
) -> dict:
    """Classify external skills vs DB: new, related, upgrade."""
    try:
        local_rows = db.query(Skill).all()
    except Exception:
        local_rows = []

    local_by_norm = {_normalize_name(s.name): s for s in local_rows if s.name}
    local_names_norm = set(local_by_norm.keys())

    new_skills: list[dict] = []
    related_skills: list[dict] = []
    upgrade_skills: list[dict] = []

    for ext in external_skills:
        n = _normalize_name(ext.name)
        if not n:
            continue
        if n not in local_names_norm:
            new_skills.append(
                {
                    "name": ext.name,
                    "description": ext.description,
                    "category": ext.category,
                    "path": ext.path,
                    "paths": ext.paths,
                    "source_library": ext.source_library,
                }
            )

        best_local: Skill | None = None
        best_score = 0.0
        for skill in local_rows:
            sn = _normalize_name(skill.name)
            if not sn:
                continue
            score = _similarity(ext.name, skill.name)
            if ext.category and skill.category and ext.category.lower() == skill.category.lower():
                score += 0.12
            overlap = len(_tokenize(ext.name) & _tokenize(skill.name))
            if overlap:
                score += min(0.15, overlap * 0.05)
            if sn == n:
                score = max(score, 0.99)
            if score > best_score:
                best_score = score
                best_local = skill

        if best_local and 0.35 <= best_score < 0.95 and n not in local_names_norm:
            related_skills.append(
                {
                    "external": {
                        "name": ext.name,
                        "category": ext.category,
                        "description": ext.description,
                        "source_library": ext.source_library,
                    },
                    "local_skill": {
                        "id": best_local.id,
                        "name": best_local.name,
                        "category": best_local.category,
                        "level": best_local.level,
                    },
                    "score": round(min(best_score, 0.94), 3),
                }
            )

        for skill in local_rows:
            if _upgrade_hint(ext.name, skill.name):
                upgrade_skills.append(
                    {
                        "external": {
                            "name": ext.name,
                            "description": ext.description,
                            "category": ext.category,
                            "source_library": ext.source_library,
                        },
                        "base_skill": {
                            "id": skill.id,
                            "name": skill.name,
                            "category": skill.category,
                            "level": skill.level,
                        },
                    }
                )

    return {
        "new_skills": new_skills,
        "related_skills": related_skills,
        "upgrade_skills": upgrade_skills,
    }


def get_discovery_report(db: Session) -> dict:
    """Scan libraries, match against DB, return structured report + stats."""
    roots = _expand_skill_roots()
    external = scan_local_skill_libraries()
    matched = match_external_with_local(db, external)

    return {
        "libraries_scanned": [label for label, _ in roots],
        "stats": {
            "total_scanned": len(external),
            "new_found": len(matched["new_skills"]),
            "related_found": len(matched["related_skills"]),
            "upgrade_found": len(matched["upgrade_skills"]),
            "library_count": len(roots),
        },
        "external_skills": [
            {
                "name": e.name,
                "description": e.description,
                "category": e.category,
                "path": e.path,
                "paths": e.paths,
                "source_library": e.source_library,
            }
            for e in external
        ],
        **matched,
    }
