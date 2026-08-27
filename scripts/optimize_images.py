"""Generate web-sized image derivatives from the full-resolution originals.

The originals (static/sets/, static/images/) are NOT served to browsers and are
not tracked in git -- keep your own backup of them. This script builds the
derivatives that Flask actually serves:

    static/sets/<set>/img.jpg    ->  static/web/<set>/img.jpg      2400px  display
                                 ->  static/thumbs/<set>/img.jpg    800px  grids
    static/images/<name>         ->  static/web/images/<name>       per CSS box

Run from the project root after adding or replacing any photo:

    python scripts/optimize_images.py

Rerunning is safe -- existing derivatives are overwritten in place.
"""
import os
import shutil
import sys

from PIL import Image, ImageOps

SETS_SRC = os.path.join('static', 'sets')
WEB_DST = os.path.join('static', 'web')
THUMB_DST = os.path.join('static', 'thumbs')
IMAGES_SRC = os.path.join('static', 'images')
IMAGES_DST = os.path.join('static', 'web', 'images')

WEB_EDGE, WEB_Q = 2400, 82
THUMB_EDGE, THUMB_Q = 800, 80

# Site chrome. Long edge in px, sized ~3x the CSS box for retina headroom.
CHROME_TARGETS = {
    'hero-background.jpg': 2560,     # full-viewport hero background
    'hero-background-pf.jpg': 2560,  # full-viewport hero background
    'footer1.jpg': 600,              # .footer-floating-image.large   180x150
    'footer2.jpg': 600,              # .footer-floating-image.medium  150x120
    'scattered1.jpg': 900,           # .scattered-image.medium        200x250
    'scattered2.jpg': 900,           # .scattered-image.large         250x300
    'logo.png': 1200,                # .logo-image           max 300x80
    'footer-logo.png': 800,          # .footer-logo          max 200x80
}
# Already small, or CSS textures used at native size.
CHROME_PASSTHROUGH = {'noise.png', 'noise2.png'}
# Referenced nowhere, or only from inside an HTML comment.
CHROME_SKIP = {'hero-background-large.jpg', 'about-portfolio.jpg'}


def _derive(im, edge, quality, dest):
    """Resize a decoded image onto its long edge and write a JPEG/PNG."""
    img = ImageOps.exif_transpose(im)          # bake in camera orientation
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


def build_gallery():
    srcs = sorted(
        os.path.join(dp, f)
        for dp, _, fns in os.walk(SETS_SRC)
        for f in fns
        if f.lower().endswith(('.jpg', '.jpeg')) and not f.startswith('._')
    )
    tot_in = tot_web = tot_thumb = 0
    for i, src in enumerate(srcs, 1):
        rel = os.path.relpath(src, SETS_SRC).replace(os.sep, '/')
        tot_in += os.path.getsize(src)
        with _open_scaled(src, WEB_EDGE) as im:
            _, wsz = _derive(im, WEB_EDGE, WEB_Q, os.path.join(WEB_DST, rel))
        with _open_scaled(src, THUMB_EDGE) as im:
            _, tsz = _derive(im, THUMB_EDGE, THUMB_Q, os.path.join(THUMB_DST, rel))
        tot_web += wsz
        tot_thumb += tsz
        print(f"  [{i:3d}/{len(srcs)}] {rel}", flush=True)
    return tot_in, tot_web + tot_thumb


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
        dst = os.path.join(IMAGES_DST, name)
        if name in CHROME_PASSTHROUGH:
            shutil.copyfile(src, dst)
        else:
            edge = CHROME_TARGETS[name]
            with _open_scaled(src, edge) as im:
                _derive(im, edge, WEB_Q, dst)
        tot_out += os.path.getsize(dst)
        print(f"  {name}", flush=True)
    return tot_in, tot_out


def main():
    if not os.path.isdir(SETS_SRC) or not os.path.isdir(IMAGES_SRC):
        sys.exit("Originals not found. Restore static/sets/ and static/images/ "
                 "from your backup before running this.")
    print("Gallery sets ->")
    g_in, g_out = build_gallery()
    print("Site chrome ->")
    c_in, c_out = build_chrome()
    tin, tout = g_in + c_in, g_out + c_out
    print(f"\noriginals  : {tin/1048576:9.1f} MB")
    print(f"served     : {tout/1048576:9.1f} MB  ({tin/max(tout,1):.0f}x smaller)")


if __name__ == '__main__':
    main()
