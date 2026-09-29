"""Render the Flask app to a static site in build/ for Cloudflare Pages.

    python freeze.py

Photos are NOT compressed here. scripts/optimize_images.py already produced
correctly sized derivatives (static/web at 2400px, static/thumbs at 800px)
from the originals; re-encoding them during the freeze would be a second
lossy pass over images that are already the right size. Add or replace a
photo by running scripts/optimize_images.py first, then this.

The full-resolution originals live in originals/, deliberately outside
static/, because Frozen-Flask copies everything under static/ into build/.
"""
import re
import shutil
import sys
from pathlib import Path

from flask_frozen import Freezer

from app import app, GALLERY_SETS

BUILD = Path('build')
# Files that belong at the site root but aren't Flask routes.
ROOT_EXTRAS = Path('cloudflare')

app.config['FREEZER_DESTINATION'] = str(BUILD)
# Warn instead of dying if a single asset is missing; verify_build() below
# turns that back into a hard failure so nothing ships broken silently.
app.config['FREEZER_IGNORE_404_NOT_FOUND'] = True
# Don't let the freezer delete the root extras we copy in afterwards.
app.config['FREEZER_DESTINATION_IGNORE'] = ['_headers', '_redirects']

freezer = Freezer(app)


@freezer.register_generator
def gallery_set():
    for s in GALLERY_SETS:
        yield {'set_id': s['id']}


@freezer.register_generator
def gallery_subshoot():
    for s in GALLERY_SETS:
        for sub in s.get('subshoots', []):
            yield {'set_id': s['id'], 'subshoot_id': sub['id']}


def copy_root_extras():
    """Drop _headers (and any future _redirects) at the build root."""
    if not ROOT_EXTRAS.is_dir():
        return
    for src in ROOT_EXTRAS.iterdir():
        if src.is_file():
            shutil.copyfile(src, BUILD / src.name)
            print(f"  + {src.name}")


def verify_build():
    """Every asset referenced by a built page must exist in build/."""
    pages = sorted(BUILD.rglob('*.html'))
    refs, missing = set(), []
    for page in pages:
        html = re.sub(r'<!--.*?-->', '', page.read_text(encoding='utf-8'),
                      flags=re.S)  # browsers never fetch commented-out srcs
        refs |= set(re.findall(r'(?:src|href|url\()[="\']*\s*(/static/[^"\')\s]+)',
                               html))
    for ref in sorted(refs):
        if not (BUILD / ref.lstrip('/')).exists():
            missing.append(ref)

    strays = [p for p in BUILD.rglob('*')
              if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg')
              and p.stat().st_size > 5 * 1024 * 1024]

    total = sum(p.stat().st_size for p in BUILD.rglob('*') if p.is_file())
    count = sum(1 for p in BUILD.rglob('*') if p.is_file())
    print(f"\n  {len(pages)} pages, {count} files, {total/1048576:.1f} MB")
    print(f"  {len(refs)} distinct asset references, {len(missing)} missing")

    if missing:
        print("\n  MISSING:")
        for m in missing:
            print(f"    {m}")
    if strays:
        print("\n  UNEXPECTEDLY LARGE (an original may have leaked in):")
        for s in strays:
            print(f"    {s.stat().st_size/1048576:6.1f} MB  {s}")
    return not missing and not strays


if __name__ == '__main__':
    freezer.freeze()
    copy_root_extras()
    if not verify_build():
        sys.exit("\nBuild is not deployable -- fix the above before deploying.")
    print("\nSite generated in build/ -- ready to deploy.")
