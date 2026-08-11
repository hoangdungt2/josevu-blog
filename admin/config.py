"""Configuration loaded from admin/.env (gitignored) and environment."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ADMIN_DIR = Path(__file__).resolve().parent
REPO_ROOT = ADMIN_DIR.parent

load_dotenv(ADMIN_DIR / ".env")


def _emails() -> tuple[str, ...]:
    raw = os.getenv("ALLOWED_EMAILS", "")
    return tuple(e.strip().lower() for e in raw.split(",") if e.strip())


@dataclass
class Settings:
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    allowed_emails: tuple = _emails()
    oauth_redirect_base: str = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:7331").rstrip("/")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "7331"))
    repo_root: Path = REPO_ROOT
    posts_dir: Path = REPO_ROOT / "content" / "posts"
    images_dir: Path = REPO_ROOT / "static" / "images"
    blog_base_url: str = os.getenv("BLOG_BASE_URL", "https://josevu.com").rstrip("/")


settings = Settings()
