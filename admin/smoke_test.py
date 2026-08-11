"""Smoke test the admin app with a faked session (no OAuth needed)."""
from itsdangerous.url_safe import URLSafeTimedSerializer
from starlette.testclient import TestClient

from admin.app import app
from admin.config import settings


def mint_session_cookie(session_data: dict) -> str:
    """Replicate Starlette SessionMiddleware's cookie format:
    base64(json(session)) signed with TimestampSigner."""
    import base64
    import json
    import itsdangerous

    secret = settings.session_secret or "dev-insecure-change-me"
    signer = itsdangerous.TimestampSigner(str(secret))
    data = base64.b64encode(json.dumps(session_data).encode("utf-8"))
    return signer.sign(data).decode("utf-8")


def main():
    client = TestClient(app)
    cookie = mint_session_cookie({"user": {"email": "hoangdung@gmail.com", "name": "Jose", "picture": ""}})
    client.cookies.set("session", cookie)

    r = client.get("/api/me")
    print("me:", r.status_code, r.json())

    r = client.get("/api/posts")
    posts = r.json()
    print("posts:", r.status_code, "count=", len(posts))
    print("  first:", posts[0]["slug"], "-", posts[0]["title"][:40])

    r = client.get("/api/posts/hello-world")
    print("get hello-world:", r.status_code, "md_len=", len(r.json()["markdown"]))

    r = client.get("/")
    print("index.html:", r.status_code, "len=", len(r.text),
          "has editor div:", '<div class="editor" id="editor">' in r.text)

    r = client.get("/editor.js")
    print("editor.js:", r.status_code, "len=", len(r.text),
          "has Editor import:", "import { Editor }" in r.text)

    crud_test(client)


def crud_test(client):
    """Exercise create/update/upload/delete with git mocked (no real push)."""
    import os
    from admin import app as _app, git_ops, posts

    calls = []
    _app.git_ops.commit_and_push = lambda paths, message: calls.append(("push", paths)) or (True, "")
    _app.git_ops.rm_and_push = lambda path, message: calls.append(("rm", path)) or (True, "")

    slug = "smoke-test-post"  # derived from title "Smoke Test Post"
    # ensure clean state
    f = posts.settings.posts_dir / (slug + ".md")
    if f.exists():
        f.unlink()

    r = client.post("/api/posts", json={
        "title": "Smoke Test Post",
        "draft": True,
        "markdown": "# Hello\n\nThis is a **test** post.\n\n- one\n- two\n",
    })
    print("create:", r.status_code, r.json())
    assert r.status_code == 200, r.text
    created_slug = r.json()["slug"]
    assert created_slug == slug, created_slug

    written = f.read_text(encoding="utf-8")
    assert "+++" in written and "title = \"Smoke Test Post\"" in written and "draft = true" in written, written
    assert "This is a **test** post" in written

    r = client.get("/api/posts/" + slug)
    print("read created:", r.status_code, "title=", r.json()["title"], "draft=", r.json()["draft"])

    r = client.put("/api/posts/" + slug, json={
        "title": "Smoke Test Post (renamed)",
        "draft": False,
        "markdown": "# Updated\n\nContent changed.\n",
    })
    print("update:", r.status_code, r.json())
    assert r.status_code == 200
    # file still exists under same slug (title didn't change slug source; slug passed = existing)
    written = f.read_text(encoding="utf-8")
    assert "title = \"Smoke Test Post (renamed)\"" in written and "draft = false" in written, written

    # upload a tiny svg (text-based, avoids binary hex issues)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>'
    r = client.post("/api/upload", files={"file": ("tiny.svg", svg, "image/svg+xml")})
    print("upload:", r.status_code, r.json())
    assert r.status_code == 200
    url = r.json()["url"]
    assert url.startswith("/images/"), url
    uploaded = posts.settings.images_dir / url.split("/")[-1]
    assert uploaded.exists()
    uploaded.unlink()  # cleanup

    r = client.delete("/api/posts/" + slug)
    print("delete:", r.status_code, r.json())
    assert r.status_code == 200
    assert not f.exists()

    print("git calls recorded:", calls)
    print("CRUD test OK")


if __name__ == "__main__":
    main()
