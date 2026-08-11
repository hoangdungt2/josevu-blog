"""FastAPI app: routes, session, auth middleware, git wiring."""
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import router as auth_router
from .config import settings
from . import posts, git_ops, upload

TEMPLATES = Path(__file__).resolve().parent / "templates"
INDEX = TEMPLATES / "index.html"


class AuthMiddleware(BaseHTTPMiddleware):
    """Protect all routes except /auth/* and /health; redirect to Google login."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/auth") or path == "/health":
            return await call_next(request)
        if not request.session.get("user"):
            if path.startswith("/api/"):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            return RedirectResponse("/auth/login", status_code=303)
        return await call_next(request)


app = FastAPI(title="josevu-blog admin")
app.include_router(auth_router)

# Order matters: AuthMiddleware is added first (inner), SessionMiddleware last
# (outer) so request.session is available inside AuthMiddleware.
app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret or "dev-insecure-change-me",
    same_site="lax",
    https_only=settings.oauth_redirect_base.startswith("https"),
    max_age=60 * 60 * 24 * 30,
)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/api/me")
async def me(request: Request):
    return request.session["user"]


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(INDEX)


@app.get("/editor.js", include_in_schema=False)
async def editor_js():
    return FileResponse(TEMPLATES / "editor.js", media_type="text/javascript")


@app.get("/api/posts")
async def api_list():
    return posts.list_posts()


@app.get("/api/posts/{slug}")
async def api_get(slug: str):
    p = posts.get_post(slug)
    if p is None:
        raise HTTPException(404, "post not found")
    return p


def _commit_paths(message: str, repo_paths: list[str]) -> None:
    ok, err = git_ops.commit_and_push(repo_paths, message)
    if not ok:
        raise HTTPException(500, f"git push failed: {err}")


@app.post("/api/posts")
async def api_create(payload: dict):
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "title is required")
    slug = posts._slugify(title)
    date = payload.get("date") or ""
    draft = bool(payload.get("draft", False))
    markdown = payload.get("markdown") or ""
    slug, target = posts.write_post(slug, title, date, draft, markdown)
    _commit_paths(
        f"Add post {title!r} via admin",
        [str(target.relative_to(settings.repo_root))],
    )
    return {"slug": slug, "ok": True}


@app.put("/api/posts/{slug}")
async def api_update(slug: str, payload: dict):
    existing = posts.get_post(slug)
    if existing is None:
        raise HTTPException(404, "post not found")
    title = (payload.get("title") or existing["title"]).strip()
    date = payload.get("date") or existing["date"]
    draft = bool(payload.get("draft", existing["draft"]))
    markdown = payload.get("markdown")
    if markdown is None:
        markdown = existing["markdown"]
    new_slug, target = posts.write_post(
        payload.get("slug") or slug, title, date, draft, markdown, old_slug=slug
    )
    repo_paths = [str(target.relative_to(settings.repo_root))]
    if new_slug != slug:
        repo_paths.append(str((settings.posts_dir / f"{slug}.md").relative_to(settings.repo_root)))
    _commit_paths(f"Update post {title!r} via admin", repo_paths)
    return {"slug": new_slug, "ok": True}


@app.delete("/api/posts/{slug}")
async def api_delete(slug: str):
    if not posts.delete_post(slug):
        raise HTTPException(404, "post not found")
    ok, err = git_ops.rm_and_push(
        str((settings.posts_dir / f"{slug}.md").relative_to(settings.repo_root)),
        f"Delete post {slug!r} via admin",
    )
    if not ok:
        # File already removed locally; commit the deletion manually as fallback.
        git_ops._run(["git", "add", "-A"])
        git_ops._run(["git", "commit", "-m", f"Delete post {slug!r} via admin"])
        git_ops._run(["git", "push"])
    return {"ok": True}


@app.post("/api/upload")
async def api_upload(file: UploadFile):
    try:
        url, dest = await upload.save_image(file)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _commit_paths(
        f"Add image {dest.name!r} via admin",
        [str(dest.relative_to(settings.repo_root))],
    )
    return {"url": url}
