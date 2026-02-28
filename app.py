from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.mailgun.org')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)


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
                'images': [f'sets/jeff_brit/set2/img{i}.jpg' for i in range(1, 25)]
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
                'images': [f'sets/max_hailie/set1/img{i}.jpg' for i in range(1, 24)]
            },
            {
                'id': 3,
                'name': 'Engagement Shoot 3',
                'location': 'Utah',
                'cover_image': 'sets/max_hailie/set3/cover.jpg',
                'images': [f'sets/max_hailie/set3/img{i}.jpg' for i in range(1, 20)]
            }
        ]
    }
]



@app.route('/')
def home():
    featured_sets = GALLERY_SETS[:3]
    return render_template('home.html', featured_sets=featured_sets)


@app.route('/gallery')
def gallery():
    return render_template('gallery.html', gallery_sets=GALLERY_SETS)


@app.route('/gallery/<int:set_id>')
def gallery_set(set_id):
    gallery_set = next((s for s in GALLERY_SETS if s['id'] == set_id), None)
    if gallery_set is None:
        return "Gallery set not found", 404

    # Check if this gallery has subshoots
    if gallery_set.get('has_subshoots'):
        return render_template('gallery_subshoots.html', gallery_set=gallery_set)
    else:
        return render_template('gallery_set.html', gallery_set=gallery_set)


@app.route('/gallery/<int:set_id>/<int:subshoot_id>')
def gallery_subshoot(set_id, subshoot_id):
    gallery_set = next((s for s in GALLERY_SETS if s['id'] == set_id), None)
    if gallery_set is None:
        return "Gallery set not found", 404

    subshoot = next((s for s in gallery_set.get('subshoots', []) if s['id'] == subshoot_id), None)
    if subshoot is None:
        return "Subshoot not found", 404

    return render_template('gallery_set.html', gallery_set=subshoot, parent_name=gallery_set['name'])


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.get_json()

        # Create email message
        msg = Message(
            subject=f"New Wedding Inquiry from {data.get('name', 'Unknown')}",
            recipients=[os.environ.get('MAIL_RECIPIENT')],  # Where emails go
            sender=os.environ.get('MAIL_DEFAULT_SENDER')
        )

        # Format the email body - using .get() with defaults to avoid KeyErrors
        msg.body = f"""
NEW CONTACT FORM SUBMISSION - AMOR FRAMES

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CLIENT INFORMATION:
Name: {data.get('name', 'N/A')}
Email: {data.get('email', 'N/A')}
Phone: {data.get('phone', 'N/A')}
Location: {data.get('location', 'N/A')}

EVENT DETAILS:
Role: {data.get('role', 'N/A')}
Date Needed: {data.get('date', 'N/A')}
Event Type: {data.get('eventType', 'N/A')}

WEDDING VISION & REQUIREMENTS:
{data.get('weddingInfo', 'N/A')}

HOW THEY FOUND US:
{data.get('howFound', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Reply to: {data.get('email', 'N/A')}
Phone: {data.get('phone', 'N/A')}

This message was sent from the Amor Frames contact form.
        """

        mail.send(msg)
        return jsonify({'success': True, 'message': 'Email sent successfully!'})

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        import traceback
        traceback.print_exc()  # This will show full error details
        return jsonify({'success': False, 'message': f'Failed to send email: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')