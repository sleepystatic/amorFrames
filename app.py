from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
import os

app = Flask(__name__)

# Email configuration (you'll add your credentials later)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')  # Set this in your environment
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')  # Set this in your environment
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER')

mail = Mail(app)

# Gallery sets data (will move to database later for CMS)
GALLERY_SETS = [
    {
        'id': 1,
        'name': 'Max & Hailie',
        'location': 'Napa Valley, CA',
        'cover_image': 'sets/couple1/cover.jpg',
        'images': [f'sets/couple1/img{i}.jpg' for i in range(1, 7)]
    },
    {
        'id': 2,
        'name': 'Gurp & Anita',
        'location': 'Santa Monica, CA',
        'cover_image': 'sets/couple2/cover.jpg',
        'images': [f'{i}.jpg' for i in range(1, 14)]
    },
    {
        'id': 3,
        'name': 'Jeff & Brit',
        'location': 'San Francisco, CA',
        'cover_image': 'sets/couple3/cover.jpg',
        'images': [f'sets/couple3/img{i}.jpg' for i in range(1, 18)]
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
    return render_template('gallery_set.html', gallery_set=gallery_set)


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
            recipients=[os.environ.get('EMAIL_USER')]  # Or hardcode your email here
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