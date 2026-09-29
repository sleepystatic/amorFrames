"""Build the static site and publish it to Cloudflare Pages.

    python scripts/deploy.py              build + deploy
    python scripts/deploy.py --photos     re-optimize photos first, then both
    python scripts/deploy.py --dry-run    build and verify, publish nothing

Pushing to GitHub does not deploy anything -- the Pages project is in
direct-upload mode. This script is what makes a change live.

freeze.py verifies the build before this uploads: if a page references an
asset that isn't there, the deploy is aborted rather than shipped broken.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = 'amorframes'
BRANCH = 'main'
ROOT = Path(__file__).resolve().parent.parent


def run(cmd, label):
    """Run a command from the project root, streaming its output."""
    print(f"\n=== {label} ===", flush=True)
    result = subprocess.run(cmd, cwd=ROOT, shell=False)
    if result.returncode != 0:
        sys.exit(f"\n{label} failed (exit {result.returncode}) -- nothing deployed.")


def npx():
    """Wrangler runs through npx, which is npx.cmd on Windows."""
    found = shutil.which('npx') or shutil.which('npx.cmd')
    if not found:
        sys.exit("npx not found on PATH -- install Node.js to deploy.")
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--photos', action='store_true',
                        help='regenerate image derivatives from originals/ first')
    parser.add_argument('--dry-run', action='store_true',
                        help='build and verify only, do not publish')
    args = parser.parse_args()

    if args.photos:
        if not (ROOT / 'originals').is_dir():
            sys.exit("originals/ not found -- restore it from your backup "
                     "before using --photos.")
        run([sys.executable, 'scripts/optimize_images.py'], 'Optimizing photos')

    run([sys.executable, 'freeze.py'], 'Building static site')

    if args.dry_run:
        print("\n--dry-run: build verified, nothing published.")
        return

    run([npx(), 'wrangler', 'pages', 'deploy', 'build',
         '--project-name', PROJECT, '--branch', BRANCH], 'Deploying to Cloudflare')

    print("\nLive at https://amorframesbyluv.com "
          "(and https://amorframes.pages.dev)")


if __name__ == '__main__':
    main()
