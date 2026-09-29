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

Add the four secrets. Each prompts for the value:

```bash
npx wrangler pages secret put MAILGUN_API_KEY --project-name amorframes
npx wrangler pages secret put MAILGUN_DOMAIN --project-name amorframes
npx wrangler pages secret put MAIL_DEFAULT_SENDER --project-name amorframes
npx wrangler pages secret put MAIL_RECIPIENT --project-name amorframes
```

Values:

- `MAILGUN_API_KEY` — the **Private API key** from Mailgun → API Keys. Not the SMTP password.
- `MAILGUN_DOMAIN` — `amorframesbyluv.com`
- `MAIL_DEFAULT_SENDER` — `amorframes@amorframesbyluv.com`
- `MAIL_RECIPIENT` — `amorframesbyluv@gmail.com`

Secrets only apply to deployments made *after* they exist, so set them before deploying.

If the Mailgun account is in the EU region, change `api.mailgun.net` to
`api.eu.mailgun.net` in `functions/send_email.js`.

## Deploy

From the project root, so Wrangler picks up `functions/`:

```bash
python freeze.py
npx wrangler pages deploy build --project-name amorframes --branch main
```

Wrangler only uploads changed files, so deploys after the first are quick.

## Updating the site

**Text or layout** — edit the template, then rebuild and deploy.

**Adding photos** — drop the originals into `originals/sets/<set>/`, add them to
`GALLERY_SETS` in `app.py`, then:

```bash
python scripts/optimize_images.py
python freeze.py
npx wrangler pages deploy build --project-name amorframes --branch main
```

`freeze.py` fails loudly if a page references an asset that isn't in the build,
so a mismatch between `GALLERY_SETS` and the files on disk gets caught before
it ships.

**Previewing locally** — `python app.py` runs the normal Flask dev server at
`http://localhost:5000`, including the `/send_email` route.

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

## After cutover

`Procfile`, `Dockerfile`, and `.dockerignore` are leftovers from server-based
hosting and do nothing on Pages. Once the domain is live and stable they can be
deleted, along with `gunicorn` from `requirements.txt`.
