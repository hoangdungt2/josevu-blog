"""Post CRUD: read/write Markdown files with TOML or YAML frontmatter."""
import re
import tomllib
from datetime import datetime
from pathlib import Path

import yaml

from .config import settings


def _parse(text: str) -> tuple[dict, str]:
    """Parse TOML (+++) or YAML (---) frontmatter. Returns (frontmatter, body)."""
    if text.startswith("+++"):
        end = text.find("+++", 3)
        if end == -1:
            return {}, text
        return tomllib.loads(text[3:end]), text[end + 3:].lstrip("\n")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end == -1:
            return {}, text
        body_start = end + 4
        if text[body_start:body_start + 1] == "\n":
            body_start += 1
        try:
            fm = yaml.safe_load(text[3:end]) or {}
        except yaml.YAMLError:
            fm = {}
        return fm, text[body_start:].lstrip("\n")
    return {}, text


def _slugify(value: str) -> str:
    s = value.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "post"


def _toml_str(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def list_posts() -> list[dict]:
    out = []
    for f in sorted(settings.posts_dir.glob("*.md")):
        fm, _ = _parse(f.read_text(encoding="utf-8"))
        out.append(
            {
                "slug": f.stem,
                "title": fm.get("title", f.stem),
                "date": str(fm.get("date", "")),
                "draft": bool(fm.get("draft", False)),
            }
        )
    out.sort(key=lambda p: p["date"], reverse=True)
    return out


def get_post(slug: str) -> dict | None:
    f = settings.posts_dir / f"{slug}.md"
    if not f.exists():
        return None
    fm, body = _parse(f.read_text(encoding="utf-8"))
    return {
        "slug": slug,
        "title": fm.get("title", slug),
        "date": str(fm.get("date", "")),
        "draft": bool(fm.get("draft", False)),
        "markdown": body,
    }


def write_post(
    slug: str,
    title: str,
    date: str,
    draft: bool,
    markdown: str,
    old_slug: str | None = None,
) -> tuple[str, Path]:
    settings.posts_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(slug) if not slug else _slugify(slug)
    target = settings.posts_dir / f"{slug}.md"
    if not date:
        date = datetime.now().astimezone().isoformat(timespec="seconds")
    fm = (
        "+++\n"
        f"date = {_toml_str(date)}\n"
        f"draft = {'true' if draft else 'false'}\n"
        f"title = {_toml_str(title)}\n"
        "+++\n\n"
    )
    target.write_text(fm + markdown.rstrip() + "\n", encoding="utf-8")
    if old_slug and old_slug != slug:
        old = settings.posts_dir / f"{old_slug}.md"
        if old.exists() and old.resolve() != target.resolve():
            old.unlink()
    return slug, target


def delete_post(slug: str) -> bool:
    f = settings.posts_dir / f"{slug}.md"
    if f.exists():
        f.unlink()
        return True
    return False
