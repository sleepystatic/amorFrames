"""Generate web-sized image derivatives from the full-resolution originals.

The originals live in originals/ -- outside static/, so the static build never
sweeps 2.5 GB of camera files into build/ -- and are not tracked in git. Keep
your own backup of them. This script builds the derivatives Flask serves:

    originals/sets/<set>/img.jpg ->  static/web/<set>/img.jpg      2400px  lightbox
                                 ->  static/mid/<set>/img.jpg      1200px  phone masonry
                                 ->  static/thumbs/<set>/img.jpg    800px  grids
    originals/images/<name>      ->  static/web/images/<name>       per CSS box

The 1200px tier exists because the masonry collapses to a single column below
480px and the container has 2rem of padding either side, so a photo renders
about 311 CSS px wide. On a DPR-2.6 phone that is ~816 device px -- just past
the 800px thumb, so without a middle candidate the browser rounds up and pulls
the 2400px file.

The two hero backgrounds additionally get -800/-1400/-2560 variants, because a
phone was downloading the full 2560px file (422 KB) as its LCP image.

Run from the project root after adding or replacing any photo:

    python scripts/optimize_images.py

Rerunning is safe -- existing derivatives are overwritten in place.
"""
import os
import shutil
import sys

from PIL import Image, ImageOps

SETS_SRC = os.path.join('originals', 'sets')
WEB_DST = os.path.join('static', 'web')
MID_DST = os.path.join('static', 'mid')
THUMB_DST = os.path.join('static', 'thumbs')
IMAGES_SRC = os.path.join('originals', 'images')
IMAGES_DST = os.path.join('static', 'web', 'images')

WEB_EDGE, WEB_Q = 2400, 82
MID_EDGE, MID_Q = 1200, 80
THUMB_EDGE, THUMB_Q = 800, 80

# Full-bleed hero backgrounds. Each width becomes <name>-<width>.jpg and the
# template offers them through srcset, so a phone fetches 800w (~60 KB) rather
# than 2560w (~422 KB).
HERO_WIDTHS = [800, 1400, 2560]
RESPONSIVE = {'hero-background.jpg', 'hero-background-pf.jpg'}

# Single-size chrome. Long edge in px, ~2-3x the CSS box for retina headroom.
CHROME_TARGETS = {
    'footer1.jpg': 600,       # .footer-floating-image.large   180x150
    'footer2.jpg': 600,       # .footer-floating-image.medium  150x120
    'scattered1.jpg': 900,    # .scattered-image.medium        200x250
    'scattered2.jpg': 900,    # .scattered-image.large         250x300
    'logo.png': 600,          # .logo-image        max 300x80, eager, above fold
    'footer-logo.png': 500,   # .footer-logo       max 200x80
}

# The body's noise overlay. Its colour is a constant dark grey; the texture is
# entirely in the alpha channel, which is why it will not compress. Palette
# mode crushes 83 alpha levels down to 6 and visibly bands it, so keep LA and
# shrink the tile instead -- style.css sets background-size to match.
NOISE_TILE = 150
NOISE_FILES = {'noise2.png', 'noise.png'}

# Referenced nowhere, or only from inside an HTML comment.
CHROME_SKIP = {'hero-background-large.jpg', 'about-portfolio.jpg'}


def _derive(im, edge, quality, dest):
    """Resize a decoded image onto its long edge and write a JPEG/PNG."""
    img = ImageOps.exif_transpose(im)           # bake in camera orientation
    img.thumbnail((edge, edge), Image.LANCZOS)  # preserves aspect ratio
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if dest.lower().endswith('.png'):
        img.save(dest, 'PNG', optimize=True)    # keep alpha on the logos
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=quality,
                                optimize=True, progressive=True)
    return img.size, os.path.getsize(dest)


def _open_scaled(path, edge):
    """Open a JPEG, hinting the decoder to downscale while reading."""
    im = Image.open(path)
    if not path.lower().endswith('.png'):
        im.draft('RGB', (edge * 2, edge * 2))
    return im


def _write_noise(src, dst):
    """Shrink the noise tile without touching its alpha gradient."""
    with Image.open(src) as im:
        tile = im.convert('RGBA').resize((NOISE_TILE, NOISE_TILE), Image.LANCZOS)
        tile.convert('LA').save(dst, 'PNG', optimize=True)
    return os.path.getsize(dst)


def build_gallery():
    srcs = sorted(
        os.path.join(dp, f)
        for dp, _, fns in os.walk(SETS_SRC)
        for f in fns
        if f.lower().endswith(('.jpg', '.jpeg')) and not f.startswith('._')
    )
    tot_in = tot_out = 0
    tiers = ((WEB_EDGE, WEB_Q, WEB_DST),
             (MID_EDGE, MID_Q, MID_DST),
             (THUMB_EDGE, THUMB_Q, THUMB_DST))
    for i, src in enumerate(srcs, 1):
        rel = os.path.relpath(src, SETS_SRC).replace(os.sep, '/')
        tot_in += os.path.getsize(src)
        for edge, quality, dest_root in tiers:
            with _open_scaled(src, edge) as im:
                _, size = _derive(im, edge, quality, os.path.join(dest_root, rel))
            tot_out += size
        print(f"  [{i:3d}/{len(srcs)}] {rel}", flush=True)
    return tot_in, tot_out


def build_chrome():
    os.makedirs(IMAGES_DST, exist_ok=True)
    favicons_src = os.path.join(IMAGES_SRC, 'favicons')
    if os.path.isdir(favicons_src):
        shutil.copytree(favicons_src, os.path.join(IMAGES_DST, 'favicons'),
                        dirs_exist_ok=True)

    tot_in = tot_out = 0
    for name in sorted(os.listdir(IMAGES_SRC)):
        src = os.path.join(IMAGES_SRC, name)
        if os.path.isdir(src) or name.startswith('._') or name in CHROME_SKIP:
            continue
        tot_in += os.path.getsize(src)

        if name in NOISE_FILES:
            size = _write_noise(src, os.path.join(IMAGES_DST, name))
            tot_out += size
            print(f"  {name} -> {NOISE_TILE}px LA  {size/1024:.1f} KB", flush=True)
            continue

        if name in RESPONSIVE:
            stem, ext = os.path.splitext(name)
            for width in HERO_WIDTHS:
                dst = os.path.join(IMAGES_DST, f"{stem}-{width}{ext}")
                with _open_scaled(src, width) as im:
                    _, size = _derive(im, width, WEB_Q, dst)
                tot_out += size
                print(f"  {stem}-{width}{ext}  {size/1024:.1f} KB", flush=True)
            continue

        dst = os.path.join(IMAGES_DST, name)
        with _open_scaled(src, CHROME_TARGETS[name]) as im:
            _derive(im, CHROME_TARGETS[name], WEB_Q, dst)
        tot_out += os.path.getsize(dst)
        print(f"  {name}", flush=True)
    return tot_in, tot_out


def prune_stale():
    """Remove derivatives from earlier runs that nothing references now."""
    stale = [os.path.join(IMAGES_DST, n) for n in RESPONSIVE]
    for path in stale:
        if os.path.isfile(path):
            os.remove(path)
            print(f"  removed superseded {os.path.basename(path)}", flush=True)


def main():
    if not os.path.isdir(SETS_SRC) or not os.path.isdir(IMAGES_SRC):
        sys.exit("Originals not found. Restore originals/sets/ and "
                 "originals/images/ from your backup before running this.")
    print("Gallery sets ->")
    g_in, g_out = build_gallery()
    print("Site chrome ->")
    c_in, c_out = build_chrome()
    prune_stale()
    tin, tout = g_in + c_in, g_out + c_out
    print(f"\noriginals  : {tin/1048576:9.1f} MB")
    print(f"served     : {tout/1048576:9.1f} MB  ({tin/max(tout,1):.0f}x smaller)")


if __name__ == '__main__':
    main()
