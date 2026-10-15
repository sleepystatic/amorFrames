from flask import Flask, render_template, request, jsonify, url_for
from markupsafe import Markup
from PIL import Image
import functools
import hashlib
import os
import re
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

# Mail goes out over the Mailgun HTTP API (see send_email below), not SMTP,
# so no mail extension or SMTP credentials are needed here. In production the
# form is served by the Cloudflare Pages Function in functions/send_email.js;
# this route only runs when you're developing locally with `python app.py`.


# GALLERY_SETS paths point at the full-resolution originals in static/sets/.
# These filters swap in the web-sized derivatives so browsers never download
# a 20 MB original. Regenerate them with scripts/optimize_images.py.
@app.template_filter('web')
def web_image(path):
    """sets/foo/img1.jpg -> web/foo/img1.jpg (2400px, for full viewing)"""
    return path.replace('sets/', 'web/', 1)


@app.template_filter('mid')
def mid_image(path):
    """sets/foo/img1.jpg -> mid/foo/img1.jpg (1200px, phone masonry)"""
    return path.replace('sets/', 'mid/', 1)


@app.template_filter('thumb')
def thumb_image(path):
    """sets/foo/cover.jpg -> thumbs/foo/cover.jpg (800px, for grids)"""
    return path.replace('sets/', 'thumbs/', 1)


@functools.lru_cache(maxsize=None)
def _size_of(rel_path):
    """(width, height) of a file under static/, or None if it can't be read."""
    try:
        with Image.open(os.path.join(app.static_folder, rel_path)) as im:
            return im.size
    except Exception:
        return None


@app.template_global()
def dims(rel_path):
    """Emit width/height so the browser reserves the right box before the
    image arrives. Without these every image reflows the page as it loads,
    which is most of the layout-shift score."""
    size = _size_of(rel_path)
    return Markup(f'width="{size[0]}" height="{size[1]}"') if size else Markup('')


@functools.lru_cache(maxsize=None)
def _asset_version(filename):
    """Short content hash of a file under static/."""
    try:
        with open(os.path.join(app.static_folder, filename), 'rb') as fh:
            return hashlib.blake2b(fh.read(), digest_size=6).hexdigest()
    except OSError:
        return None


@app.url_defaults
def _version_static(endpoint, values):
    """Append ?v=<content hash> to every static URL.

    The assets are cached for a year at the edge, so without this a photo
    replaced under the same filename keeps serving the old bytes until that
    expires -- which is exactly what happened to logo.png and noise2.png.
    Changing the content changes the hash, so the URL changes and the cache
    is bypassed immediately. Frozen-Flask drops the query when it decides
    where to write, so the file still lands at its plain path.
    """
    if endpoint == 'static' and 'filename' in values and 'v' not in values:
        version = _asset_version(values['filename'])
        if version:
            values['v'] = version


@app.template_global()
@functools.lru_cache(maxsize=None)
def inline_css(filename='style.css'):
    """style.css, ready to drop into a <style> tag, with its url() targets
    rewritten to versioned absolute paths.

    Inlining it removes the only render-blocking request on the page, which
    Lighthouse measured at 271 ms of delayed first paint on mobile. The
    stylesheet is ~4 KB over the wire, so carrying it per-page costs less
    than the round trip it saves.
    """
    with open(os.path.join(app.static_folder, filename), encoding='utf-8') as fh:
        css = fh.read()

    def _version_ref(match):
        ref = match.group(1).strip('\'" ')
        if ref.startswith(('http:', 'https:', 'data:', '//', '/')):
            return match.group(0)
        return f"url('{url_for('static', filename=ref)}')"

    return Markup(re.sub(r'url\(([^)]+)\)', _version_ref, css))


GALLERY_SETS = [
    {
        'id': 1,
        'name': 'Riya & Simar',
        'location': 'Sacramento, CA',
        'cover_image': 'sets/riya_simar/cover.jpg',
        'images': [f'sets/riya_simar/img{i}.jpg' for i in range(1, 20)]

},
    {
        'id': 2,
        'name': 'Gurp & Anita',
        'location': 'Yosemite, CA',
        'cover_image': 'sets/gurp_anita/cover.jpg',
        'images': [f'sets/gurp_anita/img{i}.jpg' for i in range(1, 14)]
    },
    {
        'id': 3,
        'name': 'Jeff & Brit',
        'location': 'California',
        'cover_image': 'sets/jeff_brit/cover.jpg',
        'has_subshoots': True,
        'subshoots': [
            {
                'id': 1,
                'name': 'Engagement Shoot 1',
                'location': 'Los Angeles, CA',
                'cover_image': 'sets/jeff_brit/set1/cover.jpg',
                'images': [f'sets/jeff_brit/set1/img{i}.jpg' for i in range(1, 15)]
            },
            {
                'id': 2,
                'name': 'Engagement Shoot 2',
                'location': 'Half Moon Bay, CA',
                'cover_image': 'sets/jeff_brit/set2/cover.jpg',
                'images': [f'sets/jeff_brit/set2/img{i}.jpg' for i in range(1, 19)]
            }
        ]
    },
    {
        'id': 4,
        'name': 'Max & Hailie',
        'location': 'Utah',
        'cover_image': 'sets/max_hailie/cover.jpg',
        'has_subshoots': True,
        'subshoots': [
            {
                'id': 1,
                'name': 'Engagement Shoot 1',
                'location': 'Utah',
                'cover_image': 'sets/max_hailie/set2/cover.jpg',
                'images': [f'sets/max_hailie/set2/img{i}.jpg' for i in range(1, 22)]
            },
            {
                'id': 2,
                'name': 'Engagement Shoot 2',
                'location': 'Utah',
                'cover_image': 'sets/max_hailie/set1/cover.jpg',
                'images': [f'sets/max_hailie/set1/img{i}.jpg' for i in range(1, 22)]
            },
            {
                'id': 3,
                'name': 'Engagement Shoot 3',
                'location': 'Utah',
                'cover_image': 'sets/max_hailie/set3/cover.jpg',
                'images': [f'sets/max_hailie/set3/img{i}.jpg' for i in range(1, 20)]
            }
        ]
    },
    {
        'id': 5,
        'name': 'Felicia & Dillon',
        'location': 'California',
        'cover_image': 'sets/felicia_dillion/cover.jpg',
        'images': [f'sets/felicia_dillion/img{i}.jpg' for i in range(1, 25)]
    }
]



@app.route('/')
def home():
    featured_sets = GALLERY_SETS[:3]
    return render_template('home.html', featured_sets=featured_sets)


@app.route('/gallery/')
def gallery():
    return render_template('gallery.html', gallery_sets=GALLERY_SETS)


@app.route('/gallery/<int:set_id>/')
def gallery_set(set_id):
    gallery_set = next((s for s in GALLERY_SETS if s['id'] == set_id), None)
    if gallery_set is None:
        return "Gallery set not found", 404

    # Check if this gallery has subshoots
    if gallery_set.get('has_subshoots'):
        return render_template('gallery_subshoots.html', gallery_set=gallery_set)
    else:
        return render_template('gallery_set.html', gallery_set=gallery_set)


@app.route('/gallery/<int:set_id>/<int:subshoot_id>/')
def gallery_subshoot(set_id, subshoot_id):
    gallery_set = next((s for s in GALLERY_SETS if s['id'] == set_id), None)
    if gallery_set is None:
        return "Gallery set not found", 404

    subshoot = next((s for s in gallery_set.get('subshoots', []) if s['id'] == subshoot_id), None)
    if subshoot is None:
        return "Subshoot not found", 404

    return render_template('gallery_set.html', gallery_set=subshoot, parent_name=gallery_set['name'])


@app.route('/about/')
def about():
    return render_template('about.html')


@app.route('/contact/')
def contact():
    return render_template('contact.html')



@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.get_json()

        # Use Mailgun API instead of SMTP
        response = requests.post(
            f"https://api.mailgun.net/v3/{os.environ.get('MAILGUN_DOMAIN')}/messages",
            auth=("api", os.environ.get('MAILGUN_API_KEY')),
            data={
                "from": f"Amor Frames <{os.environ.get('MAIL_DEFAULT_SENDER')}>",
                "to": [os.environ.get('MAIL_RECIPIENT')],
                "subject": f"New Wedding Inquiry from {data.get('name', 'Unknown')}",
                "text": f"""
NEW CONTACT FORM SUBMISSION - AMOR FRAMES

CLIENT INFORMATION:
Name: {data.get('name', 'N/A')}
Email: {data.get('email', 'N/A')}
Phone: {data.get('phone', 'N/A')}
Location: {data.get('location', 'N/A')}

EVENT DETAILS:
Role: {data.get('role', 'N/A')}
Date Needed: {data.get('date', 'N/A')}
Event Type: {data.get('eventType', 'N/A')}

WEDDING VISION:
{data.get('weddingInfo', 'N/A')}

HOW THEY FOUND US:
{data.get('howFound', 'N/A')}

Reply to: {data.get('email', 'N/A')}
Phone: {data.get('phone', 'N/A')}
                """
            },
            timeout=30
        )

        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Email sent successfully!'})
        else:
            raise Exception(f"Mailgun API error: {response.text}")

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to send email'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')