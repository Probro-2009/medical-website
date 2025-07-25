import os
from flask import render_template
import smtplib
from flask import Blueprint, request, redirect, flash
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import qrcode
from io import BytesIO
from dotenv import load_dotenv
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, DateField, FileField
from wtforms.validators import DataRequired, Optional
import json
from datetime import datetime
from flask import send_from_directory
from flask import send_file, abort
from dotenv import dotenv_values, set_key
from flask import jsonify

load_dotenv()

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
PATIENT_DIR = 'patients'

@admin_bp.route('/', methods=['GET'])
def admin_dashboard():
    return render_template('admin_dashboard.html')

@admin_bp.route('/search-patient/patients/<patient_id>', methods=['GET'])
def download_patient_pdf(patient_id):
    pdf_path = os.path.join(PATIENT_DIR, patient_id, f"{patient_id}.pdf")
    if os.path.exists(pdf_path):
        return send_file(pdf_path, mimetype='application/pdf')
    else:
        flash(f"❌ PDF not found for Patient ID {patient_id}")
        return abort(404, description=f"PDF not found for Patient ID {patient_id}")

@admin_bp.route('/search-patient', methods=['GET', 'POST'])
def search_patient():
    query = request.args.get('query', '').strip().lower()
    patients = []

    if os.path.exists(PATIENT_DIR):
        for entry in os.scandir(PATIENT_DIR):
            if entry.is_dir() and entry.name.isdigit():
                patient_id = entry.name
                pdf_path = os.path.join(entry.path, f"{patient_id}.pdf")
                if os.path.exists(pdf_path):
                    # Optional: Parse some data from PDF or fallback to folder metadata
                    # Using folder created time as registration date
                    reg_time = datetime.fromtimestamp(entry.stat().st_ctime).strftime('%Y-%m-%d')
                    
                    # Load full_name from embedded info (stored optionally as meta), or fallback
                    full_name = "Unknown"
                    txt_path = os.path.join(entry.path, "meta.json")
                    if os.path.exists(txt_path):
                        try:
                            with open(txt_path, "r") as f:
                                data = json.load(f)
                                full_name = data.get("full_name", "Unknown")
                        except:
                            pass

                    if (not query or query in patient_id.lower() or query in full_name.lower()):
                        patients.append({
                            "patient_id": patient_id,
                            "full_name": full_name,
                            "reg_date": reg_time
                        })

    return render_template('search-patient.html', patients=patients, query=query)


class ConsultationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    age = IntegerField('Age', validators=[Optional()])
    dob = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    marital_status = StringField('Marital Status', validators=[Optional()])
    sex = StringField('Sex', validators=[Optional()])
    mobile = StringField('Mobile No.', validators=[Optional()])
    occupation = StringField('Occupation', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    email = StringField('Email', validators=[Optional()])
    referred_by = StringField('Referred By', validators=[Optional()])
    chief_complaints = TextAreaField('Chief Complaints', validators=[Optional()])
    past_history = TextAreaField('Past History', validators=[Optional()])
    personal_history = TextAreaField('Personal History', validators=[Optional()])
    family_history = TextAreaField('Family History', validators=[Optional()])
    examination_general = TextAreaField('General', validators=[Optional()])
    examination_local = TextAreaField('Local', validators=[Optional()])
    investigation = TextAreaField('Investigation', validators=[Optional()])
    diagnosis = TextAreaField('Diagnosis', validators=[Optional()])
    treatment = TextAreaField('Treatment', validators=[Optional()])
    relation = StringField('Relation with Patient', validators=[Optional()])
    witness = StringField('Witness', validators=[Optional()])
    signature_file = FileField('Signature', validators=[Optional()])

@admin_bp.route('/add-patient', methods=['GET'])
def add_patient_form():
    form = ConsultationForm()
    return render_template('add-patient.html', form=form)

def get_next_patient_id():
    if not os.path.exists(PATIENT_DIR):
        os.makedirs(PATIENT_DIR)
    existing = [int(f.name) for f in os.scandir(PATIENT_DIR) if f.is_dir() and f.name.isdigit()]
    next_id = max(existing, default=0) + 1
    return f"{next_id:04d}"

from PIL import Image

def generate_qr_code(data: str):
    qr = qrcode.make(data)
    return qr  # return as PIL Image


def create_pdf(form_data: dict, patient_id: str, qr_img=None, sig_path=None):
    from reportlab.lib import colors

    pdf_path = os.path.join(PATIENT_DIR, patient_id, f"{patient_id}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Header
    c.setFillColor(colors.HexColor("#2c3e50"))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 40, "Dr. Dhanashree Chitre's Homeopathic and Cosmetic Clinic")
    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 65, "Consultation Form")

    # QR Code (top-right)
    if qr_img:
        c.drawInlineImage(qr_img, width - 55*mm, height - 60*mm, 45*mm, 45*mm)

    y = height - 100
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)

    for key, value in form_data.items():
        if key in ['signature_file', 'csrf_token']:  # Ignore unwanted fields
            continue
        if y < 100:
            c.showPage()
            y = height - 50
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30, y, f"{key.replace('_', ' ').title()}:")
        c.setFont("Helvetica", 10)
        c.drawString(130, y, str(value))
        y -= 16

    # Signature image
    if sig_path and os.path.exists(sig_path):
        y -= 40
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30, y, "Patient Signature:")
        c.drawInlineImage(sig_path, 130, y - 50, width=120, height=70)
        y -= 60

    c.showPage()
    c.save()
    return pdf_path


def send_email(pdf_path):
    user = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    fixed_recipient = "dhanashree.shirodkar@gmail.com"

    try:
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = fixed_recipient
        msg["Subject"] = "Your Consultation Form - Dr. Dhanashree Chitre"

        body = "Please find attached your consultation form PDF.\n\nRegards,\nDr. Dhanashree Chitre's Clinic"
        msg.attach(MIMEText(body, "plain"))

        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(pdf_path)}"'
            msg.attach(part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        print(f"❌ Failed to send email to {fixed_recipient}: {e}")
        return False

@admin_bp.route('/add-patient/<patient_id>', methods=['GET'])
def view_or_edit_patient(patient_id):
    form = ConsultationForm()
    patient_folder = os.path.join(PATIENT_DIR, patient_id)
    meta_path = os.path.join(patient_folder, "meta.json")

    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            saved_data = json.load(f)

        for field_name, field_value in saved_data.items():
            if hasattr(form, field_name):
                field = getattr(form, field_name)

                # 🛠 Convert 'dob' to date object
                if field_name == "dob" and isinstance(field_value, str):
                    try:
                        field.data = datetime.strptime(field_value, "%Y-%m-%d").date()
                    except ValueError:
                        field.data = None
                else:
                    field.data = field_value

    return render_template('add-patient.html', form=form, patient_id=patient_id)

@admin_bp.route('/delete-patient/<patient_id>', methods=['GET'])
def delete_patient(patient_id):
    patient_folder = os.path.join(PATIENT_DIR, patient_id)
    if os.path.exists(patient_folder):
        import shutil
        shutil.rmtree(patient_folder)
        flash(f"🗑️ Patient {patient_id} deleted successfully.")
    else:
        flash(f"⚠️ Patient {patient_id} not found.")
    return redirect('/admin/search-patient')



@admin_bp.route('/submit_form', methods=['POST'])
def submit_form():
    form_data = request.form.to_dict()
    patient_id = get_next_patient_id()
    patient_folder = os.path.join(PATIENT_DIR, patient_id)
    os.makedirs(patient_folder, exist_ok=True)

    sig_path = None
    sig = request.files.get("signature_file")
    if sig and sig.filename:
        sig_path = os.path.join(patient_folder, secure_filename(sig.filename))
        sig.save(sig_path)

    # Save full_name metadata
    
    # Save all form data (not just full_name)
    with open(os.path.join(patient_folder, "meta.json"), "w") as f:
       json.dump(form_data, f)


    qr_data = f"Patient ID: {patient_id}\nName: {form_data.get('full_name', '')}"
    qr_img = generate_qr_code(qr_data)
    pdf_path = create_pdf(form_data, patient_id, qr_img, sig_path)

    try:
        email_sent = send_email(pdf_path)
        if email_sent:
            flash(f"✅ Form submitted and emailed to dhanashree.shirodkar@gmail.com. Patient ID: {patient_id}")
        else:
            flash(f"⚠️ Form saved, but email failed to send to dhanashree.shirodkar@gmail.com.")
    except Exception as e:
        print(f"❌ Exception during email sending: {e}")
        flash("⚠️ Form saved, but email failed due to internal error.")

    return redirect('/admin/add-patient')  # ✅ This must be inside the function


SMTP_ENV_PATH = '.env'

@admin_bp.route('/emails-sms', methods=['GET', 'POST'])
def emails_sms():
    # Load current sender options
    env = dotenv_values(SMTP_ENV_PATH)
    sender_options = [
        {"email": "arunakchitre@gmail.com", "password": env.get("SMTP_PASSWORD")}
    ]

    # Add dynamically saved SMTP_EMAIL-N / SMTP_PASSWORD-N
    i = 1
    while True:
        email_key = f"SMTP_EMAIL-{i}"
        pass_key = f"SMTP_PASSWORD-{i}"
        if email_key in env and pass_key in env:
            sender_options.append({
                "email": env[email_key],
                "password": env[pass_key]
            })
            i += 1
        else:
            break

    if request.method == 'POST':
        from_email = request.form.get('from_email')
        to_emails = request.form.get('to_emails', '')
        subject = request.form.get('subject', '')
        body = request.form.get('body', '')
        attachment = request.files.get('attachment')

        # Get sender credentials
        password = None
        for sender in sender_options:
            if sender["email"] == from_email:
                password = sender["password"]
                break

        if not password:
            flash("❌ Invalid sender credentials.")
            return redirect('/admin/emails-sms')

        # Prepare email
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_emails
        msg['Subject'] = subject
        msg.attach(MIMEText(body, "plain"))

        # Add attachment
        if attachment and attachment.filename != '':
            if attachment.content_length > 5 * 1024 * 1024:
                flash("❌ Attachment too large (max 5MB).")
                return redirect('/admin/emails-sms')

            part = MIMEApplication(attachment.read(), Name=attachment.filename)
            part['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
            msg.attach(part)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(from_email, password)
                server.send_message(msg)
            flash("✅ Email sent successfully!")
        except Exception as e:
            flash(f"❌ Failed to send email: {e}")

        return redirect('/admin/emails-sms')

    return render_template('emails-sms.html', sender_options=sender_options)

@admin_bp.route('/emails-sms/save-sender', methods=['POST'])
def save_sender():
    new_email = request.form.get("email")
    new_password = request.form.get("password")

    if not new_email or not new_password:
        return jsonify({"success": False, "message": "Missing email or password"}), 400

    env = dotenv_values(SMTP_ENV_PATH)

    # Find next available index
    i = 1
    while True:
        email_key = f"SMTP_EMAIL-{i}"
        if email_key not in env:
            break
        i += 1

    set_key(SMTP_ENV_PATH, f"SMTP_EMAIL-{i}", new_email)
    set_key(SMTP_ENV_PATH, f"SMTP_PASSWORD-{i}", new_password)

    return jsonify({"success": True, "email": new_email})



