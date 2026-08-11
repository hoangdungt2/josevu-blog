"""Google OAuth (authlib) + session + email allowlist."""
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from .config import settings

router = APIRouter()

oauth = OAuth()
oauth.register(
    "google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def _callback_url() -> str:
    return f"{settings.oauth_redirect_base}/auth/callback"


@router.get("/auth/login")
async def login(request: Request):
    return await oauth.google.authorize_redirect(request, _callback_url())


@router.get("/auth/callback")
async def callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo") or {}
    email = (user.get("email") or "").lower()
    if not email or email not in settings.allowed_emails:
        request.session.clear()
        return HTMLResponse(
            "<h1>Access denied</h1>"
            "<p>This account is not authorized.</p>"
            '<p><a href="/auth/login">Try another account</a></p>',
            status_code=403,
        )
    request.session["user"] = {
        "email": email,
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
    }
    return RedirectResponse(url="/", status_code=303)


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
