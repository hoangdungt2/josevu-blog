# josevu-blog admin

A small local web app to write/edit/delete Hugo blog posts in a rich-text
editor (with paste-to-upload images). Under the hood it writes Markdown files
to the repo and commits + pushes, which triggers the Cloudflare Pages rebuild.

The admin is exposed at `https://posts.josevu.com` via a Cloudflare Tunnel and
protected by Google OAuth (email allowlist).

## One-time setup

### 1. Python deps + config

```bash
./admin/run.sh   # creates the venv + installs deps on first run; refuses to do
                 # anything useful until .env exists (see step 3)
```

Copy the config template and fill it in:

```bash
cp admin/.env.example admin/.env
```

Generate a session secret:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Put that value in `admin/.env` as `SESSION_SECRET`.

### 2. Google OAuth client

1. Go to https://console.cloud.google.com/ → APIs & Services → Credentials.
2. Create an OAuth 2.0 Client ID (Application type: **Web application**).
3. Under **Authorized redirect URIs**, add:
   `https://posts.josevu.com/auth/callback`
4. Copy the Client ID and Client Secret into `admin/.env` as
   `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

### 3. Fill in `admin/.env`

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SESSION_SECRET=<random 64 hex chars>
ALLOWED_EMAILS=hoangdung@gmail.com
OAUTH_REDIRECT_BASE=https://posts.josevu.com
```

### 4. Cloudflare Tunnel

Install `cloudflared` (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
and log in:

```bash
cloudflared tunnel login
```

Create a named tunnel:

```bash
cloudflared tunnel create josevu-admin
```

This prints a tunnel UUID and creates a credentials file. Add a DNS route so
`posts.josevu.com` points at the tunnel (Cloudflare creates the CNAME):

```bash
cloudflared tunnel route dns josevu-admin posts.josevu.com
```

Create the tunnel config at `~/.cloudflared/config.yml`:

```yaml
tunnel: <tunnel-uuid>
credentials-file: /home/<you>/.cloudflared/<tunnel-uuid>.json

ingress:
  - hostname: posts.josevu.com
    service: http://localhost:7331
  - service: http_status:404
```

Run the tunnel (in a separate terminal, or as a service):

```bash
cloudflared tunnel run josevu-admin
```

(To run it as a systemd service: `sudo cloudflared service install`.)

## Running

Two processes, in two terminals (or run the tunnel as a service):

```bash
./admin/run.sh                 # terminal 1: the admin server (localhost:7331)
cloudflared tunnel run josevu-admin   # terminal 2: the tunnel
```

Then open https://posts.josevu.com → Google login → editor.

## How it works

- The editor (Tiptap) works in HTML. On save, Turndown converts to Markdown.
- On edit, Marked converts the stored Markdown back to HTML.
- Saving writes `content/posts/<slug>.md` (TOML frontmatter) and runs
  `git add && git commit && git push`. Cloudflare Pages rebuilds → live in ~1–2 min.
- Pasted images are uploaded to `static/images/` and referenced as
  `/images/<file>` (committed + pushed with the post).
- Only `hoangdung@gmail.com` (or any email in `ALLOWED_EMAILS`) may log in.

## Notes

- The admin code lives in `admin/` and is **ignored by Hugo** — it never
  appears in the public build. Only uploaded images in `static/images/` are
  served on the live site (intended).
- `admin/.env` is gitignored. Never commit secrets.
- To run the smoke test (no OAuth needed): `admin/.venv/bin/python -m admin.smoke_test`
