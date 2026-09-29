"""Copy the Cloudflare Pages secrets from .env into .dev.vars.

    python scripts/sync_secrets.py

Wrangler's masked prompts refuse pasted input in most terminals, so upload the
whole file at once instead:

    npx wrangler pages secret bulk .dev.vars --project-name amorframes

.dev.vars is gitignored and doubles as the local secret store for
`npx wrangler pages dev build`. Values are never printed -- only key names and
a masked preview, so this is safe to run with someone watching.
"""
import sys
from pathlib import Path

# The four keys functions/send_email.js reads off `env`.
NEEDED = [
    'MAILGUN_API_KEY',
    'MAILGUN_DOMAIN',
    'MAIL_DEFAULT_SENDER',
    'MAIL_RECIPIENT',
]

ENV = Path('.env')
DEV_VARS = Path('.dev.vars')


def load_env(path):
    """Minimal dotenv read. Tolerates spaces around '=' and quoted values."""
    values = {}
    with path.open(encoding='utf-8-sig') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def mask(value):
    if len(value) <= 6:
        return '*' * len(value)
    return value[:2] + '*' * (len(value) - 4) + value[-2:]


def main():
    if not ENV.is_file():
        sys.exit(".env not found -- run this from the project root.")

    env = load_env(ENV)
    missing = [k for k in NEEDED if not env.get(k)]
    if missing:
        sys.exit(f"Missing from .env: {', '.join(missing)}")

    # Explicit LF and no BOM: wrangler's dotenv reader would otherwise fold
    # a stray CR into the value and the Mailgun auth header would fail.
    with DEV_VARS.open('w', encoding='utf-8', newline='\n') as fh:
        for key in NEEDED:
            fh.write(f"{key}={env[key]}\n")

    print(f"wrote {DEV_VARS}")
    for key in NEEDED:
        print(f"  {key:<22} {len(env[key]):3d} chars  {mask(env[key])}")
    print(f"\nupload with:\n  npx wrangler pages secret bulk {DEV_VARS} "
          f"--project-name amorframes")


if __name__ == '__main__':
    main()
