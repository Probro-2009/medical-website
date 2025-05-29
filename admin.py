import os
import json
from flask import jsonify
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

admin_blueprint = Blueprint('admin', __name__, template_folder='templates')

PATIENTS_FOLDER = r"C:\Users\aruna\Downloads\medical-website\patients"
@admin_blueprint.route('/register-patient', methods=['POST'])
def register_patient():
    if not session.get('admin_logged_in'):
        return jsonify(success=False, message="Unauthorized")

    data = request.get_json()
    name = data.get("name", "").strip().replace(" ", "_")
    if not name:
        return jsonify(success=False, message="Invalid name.")

    filepath = os.path.join(PATIENTS_FOLDER, f"{name}.json")

    # Overwrite if file exists (update), else create new
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))


@admin_blueprint.route('/get-patient/<name>')
def get_patient(name):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    safe_name = name.strip().replace(" ", "_")
    filepath = os.path.join(PATIENTS_FOLDER, f"{safe_name}.json")
    if not os.path.exists(filepath):
        return jsonify({'error': 'Patient not found'}), 404

    with open(filepath, 'r') as f:
        data = json.load(f)
    return jsonify(data)


@admin_blueprint.route('/patients/list')
def list_patients():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        files = [f.replace('.json', '') for f in os.listdir(PATIENTS_FOLDER) if f.endswith('.json')]
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_blueprint.route('/patients/delete/<name>', methods=['POST'])
def delete_patient(name):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    safe_name = name.strip().replace(" ", "_")
    filepath = os.path.join(PATIENTS_FOLDER, f"{safe_name}.json")

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Patient not found'}), 404


# Serve add_patient.html and load patient data if editing
@admin_blueprint.route('/add-patient')
def add_patient_page():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))  # Adjust login route as needed

    edit_name = request.args.get('edit', '').strip()
    patient_data = None
    if edit_name:
        filepath = os.path.join(PATIENTS_FOLDER, f"{edit_name.replace(' ', '_')}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                patient_data = json.load(f)

    return render_template('add_patient.html', patient=patient_data)


@admin_blueprint.route('/patients/search')
def search_patients():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    query = request.args.get('query', '').strip().lower()
    if not query:
        return jsonify([])

    try:
        files = [f.replace('.json', '') for f in os.listdir(PATIENTS_FOLDER) if f.endswith('.json')]
        matches = [name for name in files if query in name.lower()]
        return jsonify(matches)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Dummy credentials
ADMIN_EMAIL = 'admin@example.com'
ADMIN_PASSWORD = 'admin123'

# SMTP credentials for sending email
SENDER_EMAIL = "arunakchitre@gmail.com"
SENDER_PASSWORD = "kmhv ghkx cpcq kshr"
RECEIVER_EMAIL = "dr.dhanashreechitre09@gmail.com"


def send_forgot_password_email():
    try:
        body = f"""User clicked 'Forgot password'.

✅ Admin Credentials:
Email: {ADMIN_EMAIL}
Password: {ADMIN_PASSWORD}
"""

        msg = MIMEMultipart("alternative")
        msg['Subject'] = "Forgot Password Access Request"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)


@admin_blueprint.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Incorrect email or password", "error")
            return render_template('admin_login.html')
    return render_template('admin_login.html')


@admin_blueprint.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
    return render_template('admin_dashboard.html')

@admin_blueprint.route('/add-patient')
def add_patient():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
    return render_template('add_patient.html')

@admin_blueprint.route('/view-patient')
def view_patient():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.login'))
    return render_template('view_patient.html')


@admin_blueprint.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))


@admin_blueprint.route('/forgot-password', methods=['POST'])
def forgot_password():
    success, message = send_forgot_password_email()
    if success:
        flash("✅ Admin credentials sent to doctor.", "success")
    else:
        flash(f"❌ Failed to send email: {message}", "error")
    return redirect(url_for('admin.login'))
