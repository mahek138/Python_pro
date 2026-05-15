from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from email.message import EmailMessage
import smtplib
import os
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import quote
from dotenv import load_dotenv

# Load environment variables from .env file, overriding stale process values.
load_dotenv(override=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
db = SQLAlchemy(app)

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

DEFAULT_COUNTRY_CODE = os.getenv('DEFAULT_COUNTRY_CODE', '+91')
POLICE_DEPARTMENT_EMAIL = os.getenv('POLICE_DEPARTMENT_EMAIL', '').strip()
YOUTUBE_CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID', '').strip()

SAFETY_CHANNELS = [
    {'id': 'UCIU6nZbHFUj9wNCTlOdRLbQ', 'title': 'Self-Defense Channel 1', 'language': 'english'},
    {'id': 'UC8zU8NqCid-1V0BOn6P9eWA', 'title': 'Self-Defense Channel 2', 'language': 'hindi'},
    {'id': 'UCNMZWa1QP42jHrmmzayFEeg', 'title': 'Self-Defense Channel 3', 'language': 'marathi'},
    {'id': 'UCMD_k2IDOQpGU4D8OMyHXVQ', 'title': 'Self-Defense Channel 4', 'language': 'english'},
    {'id': 'UC_p97VpY717fLp2uAn0M_mQ', 'title': 'Self-Defense Channel 5', 'language': 'hindi'},
    {'id': 'UCp_hX-tGjB-1H376N3SId7g', 'title': 'Self-Defense Channel 6', 'language': 'marathi'},
]

SUPPORTED_VIDEO_LANGUAGES = ['english', 'hindi', 'marathi']

# Database Models
class SavedNumber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class UserLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    accuracy = db.Column(db.Float)

# Initialize database
with app.app_context():
    db.create_all()
    # Remove legacy hardcoded contacts so only user-added numbers are used.
    legacy_numbers = ['+917796298219', '7796298219']
    removed = SavedNumber.query.filter(SavedNumber.number.in_(legacy_numbers)).delete(synchronize_session=False)
    if removed:
        db.session.commit()

alerts_active = False

# Sample police stations database (India)
POLICE_STATIONS = [
    {'name': 'Central Police Station', 'lat': 28.6139, 'lon': 77.2090, 'phone': '+919876543210', 'email': 'central-police@example.com'},
    {'name': 'East Police Station', 'lat': 28.5921, 'lon': 77.2500, 'phone': '+919876543211', 'email': 'east-police@example.com'},
    {'name': 'North Police Station', 'lat': 28.7041, 'lon': 77.1025, 'phone': '+919876543212', 'email': 'north-police@example.com'},
    {'name': 'West Police Station', 'lat': 28.6692, 'lon': 77.0580, 'phone': '+919876543213', 'email': 'west-police@example.com'},
    {'name': 'South Police Station', 'lat': 28.5244, 'lon': 77.1855, 'phone': '+919876543214', 'email': 'south-police@example.com'},
]

def get_nearest_police_station(lat, lon):
    """Find the nearest police station to given coordinates."""
    if not lat or not lon:
        return None
    min_distance = float('inf')
    nearest = None
    for station in POLICE_STATIONS:
        # Simple distance calculation (not exact, but good for demo)
        distance = ((station['lat'] - lat) ** 2 + (station['lon'] - lon) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            nearest = station
    return nearest


def build_sos_message(latest_location=None, police=None):
    lines = [
        'EMERGENCY ALERT: I need help immediately.',
        'Please contact me right away.',
    ]

    if latest_location:
        lines.append(
            f"Live location: https://maps.google.com/?q={latest_location.latitude},{latest_location.longitude}"
        )
        lines.append(
            f"Coordinates: {latest_location.latitude:.6f}, {latest_location.longitude:.6f}"
        )
    else:
        lines.append('Live location is not available yet.')

    if police:
        lines.append(f"Nearest Police Station: {police['name']} ({police.get('phone', 'N/A')})")

    return '\n'.join(lines)


def normalize_phone_number(raw_number):
    """Normalize phone input to E.164-like format with strong India support."""
    if not raw_number:
        return None

    cleaned = (
        raw_number.strip()
        .replace(' ', '')
        .replace('-', '')
        .replace('(', '')
        .replace(')', '')
    )

    # Convert 00-prefix to + for international format.
    if cleaned.startswith('00') and cleaned[2:].isdigit():
        cleaned = f'+{cleaned[2:]}'

    # If number already has +, validate and keep.
    if cleaned.startswith('+'):
        digits = cleaned[1:]
        if digits.isdigit() and 7 <= len(digits) <= 15:
            return f'+{digits}'
        return None

    if not cleaned.isdigit():
        return None

    # India-specific acceptance:
    # 10-digit mobile (starts 6-9), 11-digit with leading 0, or 12-digit with 91.
    if len(cleaned) == 10 and cleaned[0] in '6789':
        return f'+91{cleaned}'
    if len(cleaned) == 11 and cleaned.startswith('0') and cleaned[1] in '6789':
        return f'+91{cleaned[1:]}'
    if len(cleaned) == 12 and cleaned.startswith('91') and cleaned[2] in '6789':
        return f'+{cleaned}'

    # Fallback for other international formats entered without +.
    if 7 <= len(cleaned) <= 15:
        return f'+{cleaned}'

    return None


def send_reset_email(to_email, reset_link):
    mail_server = os.getenv('MAIL_SERVER')
    mail_port = int(os.getenv('MAIL_PORT', '587'))
    mail_username = os.getenv('MAIL_USERNAME')
    mail_password = os.getenv('MAIL_PASSWORD')
    mail_from = os.getenv('MAIL_FROM', mail_username)
    mail_use_tls = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'

    if not mail_server or not mail_username or not mail_password or not mail_from:
        return False

    msg = EmailMessage()
    msg['Subject'] = 'Spark Women - Password Reset'
    msg['From'] = mail_from
    msg['To'] = to_email
    msg.set_content(
        "You requested a password reset for Spark Women.\n\n"
        f"Use this link to reset your password: {reset_link}\n\n"
        "This link expires in 1 hour."
    )

    try:
        with smtplib.SMTP(mail_server, mail_port, timeout=15) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.send_message(msg)
        return True
    except Exception as exc:
        print(f"Failed to send reset email: {exc}")
        return False


def send_incident_report_email(subject, body, to_email=None):
    mail_server = os.getenv('MAIL_SERVER')
    mail_port = int(os.getenv('MAIL_PORT', '587'))
    mail_username = os.getenv('MAIL_USERNAME')
    mail_password = os.getenv('MAIL_PASSWORD')
    mail_from = os.getenv('MAIL_FROM', mail_username)
    mail_use_tls = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'

    target_email = (to_email or POLICE_DEPARTMENT_EMAIL or '').strip()
    if not target_email:
        return False, 'POLICE_DEPARTMENT_EMAIL is not configured in .env.'

    if not mail_server or not mail_username or not mail_password or not mail_from:
        return False, 'Email service is not configured. Set MAIL_SERVER, MAIL_USERNAME, and MAIL_PASSWORD.'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mail_from
    msg['To'] = target_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(mail_server, mail_port, timeout=15) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.send_message(msg)
        return True, 'incident report sent'
    except Exception as exc:
        return False, f'Failed to send incident report email: {exc}'


def fetch_latest_channel_video(channel_id):
    if not channel_id:
        return None

    feed_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
    with urllib.request.urlopen(feed_url, timeout=12) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'yt': 'http://www.youtube.com/xml/schemas/2015',
    }

    latest_entry = root.find('atom:entry', ns)
    if latest_entry is None:
        return None

    video_id = latest_entry.findtext('yt:videoId', default='', namespaces=ns)
    title = latest_entry.findtext('atom:title', default='Latest YouTube video', namespaces=ns)
    published = latest_entry.findtext('atom:published', default='', namespaces=ns)

    if not video_id:
        return None

    return {
        'video_id': video_id,
        'title': title,
        'published': published,
        'watch_url': f'https://www.youtube.com/watch?v={video_id}',
    }


def get_static_asset_version(filename):
    asset_path = os.path.join(app.static_folder, filename)
    try:
        return int(os.path.getmtime(asset_path))
    except OSError:
        return 1


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/manifest.webmanifest')
def pwa_manifest():
    return send_from_directory('static', 'manifest.webmanifest', mimetype='application/manifest+json')


@app.route('/sw.js')
def service_worker():
    response = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    print(f"Login attempt: {email}")

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        return redirect(url_for('dashboard'))

    # Keep existing hardcoded admin login for compatibility.
    if email == "hr@gmail.com" and password == "1234":
        return redirect(url_for('dashboard'))
    return render_template('login.html', error_message='Invalid login credentials!'), 401

@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    if request.method == 'GET':
        return render_template('signup.html')

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    if not name or not email or not password:
        return render_template('signup.html', error_message='Please fill all fields.'), 400

    if len(password) < 6:
        return render_template('signup.html', error_message='Password must be at least 6 characters.'), 400

    if User.query.filter_by(email=email).first():
        return render_template('signup.html', error_message='Email already registered. Please log in.'), 409

    user = User(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return render_template('signup.html', success_message='Account created successfully. You can log in now.')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password_page():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = request.form.get('email', '').strip().lower()
    if not email:
        return render_template('forgot_password.html', error_message='Please enter your email address.'), 400

    user = User.query.filter_by(email=email).first()
    if user:
        token = serializer.dumps(email, salt='password-reset')
        reset_link = url_for('reset_password_page', token=token, _external=True)
        email_sent = send_reset_email(email, reset_link)
        if email_sent:
            return render_template('forgot_password.html', success_message='Reset link sent to your email.')
        return render_template(
            'forgot_password.html',
            success_message='Email service is not configured. Use the development reset link below.',
            reset_link=reset_link
        )
    return render_template('forgot_password.html', error_message='No account found with this email.'), 404


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_page(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        return render_template('forgot_password.html', error_message='Reset link expired. Please request a new one.'), 400
    except BadSignature:
        return render_template('forgot_password.html', error_message='Invalid reset link.'), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template('forgot_password.html', error_message='Account not found for this reset link.'), 404

    if request.method == 'GET':
        return render_template('reset_password.html', token=token)

    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if len(password) < 6:
        return render_template('reset_password.html', token=token, error_message='Password must be at least 6 characters.')
    if password != confirm_password:
        return render_template('reset_password.html', token=token, error_message='Passwords do not match.')

    user.password_hash = generate_password_hash(password)
    db.session.commit()
    return render_template('login.html', error_message='Password reset successful. Please log in.')

@app.route('/dashboard')
def dashboard():
    return render_template('homeinterface.html')

@app.route('/get-started')
def get_started():
    return render_template('getstarted.html')

@app.route('/home-interface')
def home_interface():
    return render_template('homeinterface.html')

@app.route('/contact-interface')
def contact_interface():
    saved_numbers = [num.number for num in SavedNumber.query.all()]
    return render_template('contactinterface.html', saved_numbers=saved_numbers)


@app.route('/incident-report', methods=['GET', 'POST'])
def incident_report():
    latest_location = UserLocation.query.order_by(UserLocation.timestamp.desc()).first()
    police = get_nearest_police_station(
        latest_location.latitude if latest_location else None,
        latest_location.longitude if latest_location else None
    )
    target_police_email = police.get('email') if police and police.get('email') else POLICE_DEPARTMENT_EMAIL

    if request.method == 'GET':
        return render_template(
            'incident_report.html',
            latest_location=latest_location,
            police=police,
            police_department_email=target_police_email,
        )

    victim_name = request.form.get('victim_name', '').strip()
    contact_number = request.form.get('contact_number', '').strip()
    incident_type = request.form.get('incident_type', '').strip()
    incident_location = request.form.get('incident_location', '').strip()
    incident_description = request.form.get('incident_description', '').strip()
    additional_notes = request.form.get('additional_notes', '').strip()

    if not victim_name or not contact_number or not incident_type or not incident_description:
        flash('Please fill all required fields before submitting the report.', 'error')
        return render_template(
            'incident_report.html',
            latest_location=latest_location,
            police=police,
            police_department_email=target_police_email,
            form_data=request.form,
        ), 400

    report_location = incident_location
    if not report_location and latest_location:
        report_location = f"{latest_location.latitude}, {latest_location.longitude}"

    google_maps_link = ''
    if latest_location:
        google_maps_link = f"https://maps.google.com/?q={latest_location.latitude},{latest_location.longitude}"

    subject = f"Incident Report from {victim_name} - {incident_type}"
    body_lines = [
        'A voluntary incident report has been submitted through the Spark Women app.',
        '',
        f'Victim Name: {victim_name}',
        f'Contact Number: {contact_number}',
        f'Incident Type: {incident_type}',
        f'Incident Location: {report_location or "Not provided"}',
        f'Description: {incident_description}',
    ]

    if additional_notes:
        body_lines.extend(['', f'Additional Notes: {additional_notes}'])

    if latest_location:
        body_lines.extend([
            '',
            f'Live Location: {latest_location.latitude}, {latest_location.longitude}',
            f'Google Maps Link: {google_maps_link}',
        ])

    if police:
        body_lines.extend([
            '',
            f'Nearest Police Station: {police["name"]}',
            f'Police Station Phone: {police.get("phone", "N/A")} ',
        ])

    success, result_message = send_incident_report_email(subject, '\n'.join(body_lines), target_police_email)

    alert_message = f'Incident report submitted for {victim_name} ({incident_type}).'
    db.session.add(Alert(message=alert_message[:200]))
    db.session.commit()

    if success:
        flash(f'Report sent to police department email: {target_police_email}', 'success')
        return render_template(
            'incident_report_success.html',
            victim_name=victim_name,
            incident_type=incident_type,
            police_department_email=target_police_email,
            google_maps_link=google_maps_link,
            police=police,
        )

    flash(result_message, 'error')
    return render_template(
        'incident_report.html',
        latest_location=latest_location,
        police=police,
        police_department_email=target_police_email,
        form_data=request.form,
    ), 500

@app.route('/sos-interface')
def sos_interface():
    return render_template('sosinterface.html', alerts_active=alerts_active)

@app.route('/self-defense')
def self_defense():
    selected_language = request.args.get('lang', 'english').strip().lower()
    if selected_language not in SUPPORTED_VIDEO_LANGUAGES:
        selected_language = 'english'

    filtered_channels = [
        channel for channel in SAFETY_CHANNELS
        if channel.get('language', '').lower() == selected_language
    ]
    if not filtered_channels:
        selected_language = 'english'
        filtered_channels = [
            channel for channel in SAFETY_CHANNELS
            if channel.get('language', '').lower() == selected_language
        ]

    default_channel_id = filtered_channels[0]['id'] if filtered_channels else ''
    selected_channel_id = request.args.get('q', default_channel_id).strip()
    valid_channel_ids = {channel['id'] for channel in filtered_channels}
    if selected_channel_id not in valid_channel_ids:
        selected_channel_id = default_channel_id

    # YouTube uploads playlist can be derived from a channel ID by replacing the UC prefix with UU.
    uploads_playlist_id = f"UU{selected_channel_id[2:]}" if selected_channel_id.startswith('UC') else ''
    safety_video_url = (
        f'https://www.youtube.com/embed?listType=playlist&list={uploads_playlist_id}&autoplay=1&mute=1&playsinline=1'
        if uploads_playlist_id else
        'https://www.youtube.com/embed?listType=search&list=women%20self%20defense%20basics&autoplay=1&mute=1&playsinline=1'
    )
    safety_watch_url = f'https://www.youtube.com/channel/{selected_channel_id}/videos' if selected_channel_id else 'https://www.youtube.com/'

    return render_template(
        'selfdefence.html',
        safety_video_url=safety_video_url,
        safety_watch_url=safety_watch_url,
        safety_channels=filtered_channels,
        selected_channel_id=selected_channel_id,
        selected_language=selected_language,
        supported_video_languages=SUPPORTED_VIDEO_LANGUAGES,
        youtube_channel_configured=bool(YOUTUBE_CHANNEL_ID),
        asset_version=get_static_asset_version('pwa.js'),
    )


@app.route('/api/youtube-latest', methods=['GET'])
def youtube_latest_video():
    if not YOUTUBE_CHANNEL_ID:
        return jsonify({
            'status': 'unavailable',
            'message': 'Set YOUTUBE_CHANNEL_ID in .env to enable upload alerts.'
        }), 200

    try:
        latest_video = fetch_latest_channel_video(YOUTUBE_CHANNEL_ID)
    except Exception as exc:
        return jsonify({'status': 'error', 'message': f'Failed to fetch latest video: {exc}'}), 500

    if not latest_video:
        return jsonify({'status': 'empty', 'message': 'No video found in channel feed yet.'}), 200

    return jsonify({'status': 'success', 'latest_video': latest_video}), 200

@app.route('/add-number', methods=['POST'])
def add_number():
    new_number = request.form.get('number', '')
    normalized_number = normalize_phone_number(new_number)

    if normalized_number:
        if not SavedNumber.query.filter_by(number=normalized_number).first():
            db.session.add(SavedNumber(number=normalized_number))
            db.session.commit()
            print(f"New SOS Number Added: {normalized_number}")
        else:
            print(f"Number {normalized_number} already exists")
    else:
        print(f"Invalid number format: {new_number}")

    return redirect(url_for('contact_interface'))


@app.route('/remove-number', methods=['POST'])
def remove_number():
    number_to_remove = request.form.get('number', '')
    normalized_number = normalize_phone_number(number_to_remove)

    if normalized_number:
        existing = SavedNumber.query.filter_by(number=normalized_number).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            print(f"SOS Number Removed: {normalized_number}")
        else:
            print(f"Number not found for removal: {normalized_number}")
    else:
        print(f"Invalid number for removal: {number_to_remove}")

    return redirect(url_for('contact_interface'))

@app.route('/update-location', methods=['POST'])
def update_location():
    """Store user's current location."""
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    accuracy = data.get('accuracy')

    if lat is not None and lon is not None:
        location = UserLocation(latitude=lat, longitude=lon, accuracy=accuracy)
        db.session.add(location)
        db.session.commit()
        return jsonify({"status": "success", "message": "Location updated"}), 200
    return jsonify({"status": "error", "message": "Invalid location data"}), 400


@app.route('/nearest-police', methods=['GET'])
def nearest_police():
    """Get nearest police station."""
    latest_location = UserLocation.query.order_by(UserLocation.timestamp.desc()).first()
    if not latest_location:
        return jsonify({"status": "error", "message": "Location not available"}), 400
    
    police = get_nearest_police_station(latest_location.latitude, latest_location.longitude)
    if police:
        return jsonify({"status": "success", "police": police}), 200
    return jsonify({"status": "error", "message": "No nearby police station found"}), 404


@app.route('/panic', methods=['POST'])
def panic_alert():
    wants_json = (
        request.is_json
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.accept_mimetypes.best == 'application/json'
    )

    saved_numbers = SavedNumber.query.all()

    if not saved_numbers:
        message = "No contacts available. Add at least one SOS contact first."
        if wants_json:
            return jsonify({"status": "error", "message": message}), 400
        flash(message, 'error')
        return redirect(url_for('dashboard'))

    # Get latest location and nearest police station for the SOS preview.
    latest_location = UserLocation.query.order_by(UserLocation.timestamp.desc()).first()
    police = get_nearest_police_station(
        latest_location.latitude if latest_location else None,
        latest_location.longitude if latest_location else None
    )
    sos_message = build_sos_message(latest_location, police)
    encoded_sos_message = quote(sos_message, safe='')
    sms_contacts = []
    normalized_numbers = []
    for num in saved_numbers:
        normalized_number = normalize_phone_number(num.number)
        if normalized_number:
            normalized_numbers.append(normalized_number)
            sms_contacts.append({
                'raw': num.number,
                'normalized': normalized_number,
                'sms_link': f"sms:{normalized_number}?body={encoded_sos_message}",
            })
        else:
            sms_contacts.append({
                'raw': num.number,
                'normalized': '',
                'sms_link': '',
            })

    unique_numbers = list(dict.fromkeys(normalized_numbers))
    sms_all_link = ''
    if unique_numbers:
        recipients = ','.join(unique_numbers)
        sms_all_link = f"sms:{recipients}?body={encoded_sos_message}"

    # Log the alert request for audit/history.
    db.session.add(Alert(message=sos_message[:200]))
    db.session.commit()

    if not wants_json:
        flash('Opening your phone message app with SOS text and live location.', 'success')
        return render_template(
            'sos_alert.html',
            sos_message=sos_message,
            encoded_sos_message=encoded_sos_message,
            sms_contacts=sms_contacts,
            sms_all_link=sms_all_link,
            saved_numbers=saved_numbers,
            latest_location=latest_location,
            police=police,
        )

    return jsonify({
        "status": "success",
        "message": "SOS message ready for phone share",
        "sos_message": sos_message,
        "contacts": sms_contacts,
        "sms_all_link": sms_all_link,
    })

@app.route('/laws')
def laws_page():
    return render_template('lawsinterface.html')

@app.route('/start', methods=['POST'])
def start_alerts():
    global alerts_active
    alerts_active = True
    print("Action: SOS Alerts have been ACTIVATED")
    return redirect(url_for('sos_interface'))

@app.route('/stop', methods=['POST'])
def stop_alerts():
    global alerts_active
    alerts_active = False
    print("Action: SOS Alerts have been DEACTIVATED")
    return redirect(url_for('sos_interface'))

if __name__ == '__main__':
    app.run(debug=True)