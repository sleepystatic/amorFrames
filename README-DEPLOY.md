# Deploying Amor Frames

The site is a Flask app rendered to static HTML and hosted on **Cloudflare Pages**
(free, unlimited bandwidth, global CDN, no cold starts). The contact form runs as
a Cloudflare Pages Function that posts to the Mailgun API.

Nothing about the site requires a running Python server in production.

## Layout

| Path | What it is |
|---|---|
| `app.py` | The Flask app. Source of truth for pages and `GALLERY_SETS`. |
| `templates/`, `static/` | Pages and the web-sized assets that actually get served. |
| `originals/` | Full-resolution camera files. **Not tracked, not deployed.** Kept outside `static/` so the build can't sweep 2.5 GB into `build/`. |
| `scripts/optimize_images.py` | `originals/` → `static/web/` (2400px) + `static/thumbs/` (800px). |
| `freeze.py` | Renders the app to `build/`, then verifies every referenced asset exists. |
| `functions/send_email.js` | Pages Function answering `POST /send_email`. |
| `cloudflare/_headers` | Security + cache headers, copied to the build root. |
| `build/` | Generated output. Not tracked. |

## One-time setup

```bash
npm install -g wrangler
```

Log in (opens a browser):

```bash
npx wrangler login
```

Create the project:

```bash
npx wrangler pages project create amorframes --production-branch main
```

Add the four secrets. `.dev.vars` (gitignored) holds them as `KEY=VALUE`, and
Wrangler uploads the whole file in one go — no typing into masked prompts:

```bash
npx wrangler pages secret bulk .dev.vars --project-name amorframes
```

The keys are `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `MAIL_DEFAULT_SENDER` and
`MAIL_RECIPIENT`, mirroring `.env`. `MAILGUN_API_KEY` is Mailgun's **Private API
key**, not the SMTP password — it's the value the Flask app passes as
`auth=("api", ...)`.

If `.dev.vars` is ever lost, regenerate it from `.env`:

```bash
python scripts/sync_secrets.py
```

To set a single secret interactively instead, pipe it in rather than fighting
the masked prompt:

```bash
echo "the-value" | npx wrangler pages secret put MAILGUN_API_KEY --project-name amorframes
```

Secrets only apply to deployments made *after* they exist, so set them before
deploying. Confirm with `npx wrangler pages secret list --project-name amorframes`.

If the Mailgun account is in the EU region, change `api.mailgun.net` to
`api.eu.mailgun.net` in `functions/send_email.js`.

## Deploy

**Pushing to GitHub does not deploy.** The Pages project is in direct-upload
mode, so Cloudflare never reads the repo — GitHub is backup and history only.
This is what makes a change live:

```bash
python scripts/deploy.py
```

That builds, verifies, and publishes. Wrangler only uploads changed files, so
deploys after the first are quick.

| Command | Use it for |
|---|---|
| `python scripts/deploy.py` | Text, layout, CSS, template or function changes |
| `python scripts/deploy.py --photos` | After adding or replacing photos |
| `python scripts/deploy.py --dry-run` | Build and verify without publishing |

The underlying two steps, if you'd rather run them yourself — from the project
root, so Wrangler picks up `functions/`:

```bash
python freeze.py
npx wrangler pages deploy build --project-name amorframes --branch main
```

## Updating the site

**Text or layout** — edit the template, then `python scripts/deploy.py`.

**Adding photos** — drop the originals into `originals/sets/<set>/`, add them to
`GALLERY_SETS` in `app.py`, then `python scripts/deploy.py --photos`.

`freeze.py` fails loudly if a page references an asset that isn't in the build,
so a mismatch between `GALLERY_SETS` and the files on disk is caught before it
ships rather than after.

**Previewing locally** — `python app.py` runs the normal Flask dev server at
`http://localhost:5000`, including the `/send_email` route.

**Committing** — commit and push as normal for history and backup. It has no
effect on what's live; only a deploy does that.

## Connecting the domain

1. Cloudflare dashboard → **Add a site** → `amorframesbyluv.com` → Free plan.
2. Cloudflare imports the existing DNS. **Before continuing, confirm the Mailgun
   records came across** — the SPF and DKIM `TXT` records, the `MX` records, and
   any Mailgun `CNAME`. If they're missing, copy them from Mailgun's domain
   settings. Without them the contact form stops delivering. Delete the old
   Render records.
3. Point the GoDaddy nameservers at the two Cloudflare gives you.
4. Once Cloudflare shows the domain active (usually under an hour, up to 24),
   go to the Pages project → **Custom domains** → add both `amorframesbyluv.com`
   and `www.amorframesbyluv.com`. SSL is automatic.
5. Verify the live site, then delete the Render service.

## Local development

`python app.py` runs the Flask dev server at `http://localhost:5000` with live
template reloading. Its `/send_email` route is a local stand-in for the Pages
Function, so the contact form works while you're developing.

To exercise the real Pages Function instead, build first and let Wrangler serve
it:

```bash
python freeze.py
npx wrangler pages dev build
```

Secrets for local function runs go in `.dev.vars` (gitignored), same keys as
the deployed secrets.
