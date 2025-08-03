from flask_wtf.csrf import CSRFProtect
import logging
from redis import Redis
from flask_talisman import Talisman
from flask import Flask, request, send_from_directory, redirect, url_for, render_template, session, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid
import requests
import os
from admin import admin_bp
from login import login_bp
from fallback import fallback_bp
from datetime import timedelta
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, request, Response
from developer import developer_bp
from sysmon import sysmon_bp
from market.market import market_bp
from werkzeug.utils import secure_filename
from logging.handlers import RotatingFileHandler
import re
from collections import defaultdict
from datetime import datetime, timedelta
import json
from email.mime.application import MIMEApplication
from datetime import datetime, timezone
from copilot_bp import copilot_bp
from models import db, User, Patient, Appointment


login_attempts = defaultdict(list)  # { ip_address: [timestamps...] }
MAX_ATTEMPTS = 5
BLOCK_WINDOW = timedelta(minutes=10)


load_dotenv()



app = Flask(__name__, static_folder="frontend/public")
app.secret_key = os.getenv("SECRET_KEY")

# Fix: allow thread-safe access for SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db?check_same_thread=False'


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app)

db.init_app(app)
#app.config.update({
   # 'SESSION_COOKIE_SECURE': True,         # Only over HTTPS
    #'SESSION_COOKIE_HTTPONLY': True,       # JS can't access session
   # 'SESSION_COOKIE_SAMESITE': 'Lax',      # Prevent CSRF
   # 'PERMANENT_SESSION_LIFETIME': timedelta(hours=1)  # Auto-logout after 1 hour
#})
#csrf = CSRFProtect(app)
#limiter = Limiter(
    #get_remote_address,
   # storage_uri="redis://localhost:6379",  # Change if hosted
    #app=app
#)
# ✅ Flask-Talisman for security headers and HTTPS enforcement
#Talisman(app,
   # content_security_policy={
        #'default-src': "'self'",
        #'img-src': "'self' data:",
        #'script-src': "'self'",
        #'style-src': "'self' 'unsafe-inline'"
   # },
    #force_https=False
#)
socketio = SocketIO(app)

# ✅ Audit log setup
audit_logger = logging.getLogger("audit")
audit_handler = RotatingFileHandler('logs/audit.log', maxBytes=10240, backupCount=5)
audit_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
audit_logger.setLevel(logging.INFO)
audit_logger.addHandler(audit_handler)

# Simple Audit Logger
def log_audit(action, user="System"):
    log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {user}: {action}\n"
    with open("logs/audit.log", "a") as f:
        f.write(log_entry)

# Test Audit Entry Route
@app.route("/test-audit")
def test_audit():
    log_audit("Test audit entry added!", user="Developer")
    return "Audit logged."


SECURITY_DIR = "security"
SECURITY_STATUS_FILE = os.path.join(SECURITY_DIR, "security_status.json")

if not os.path.exists(SECURITY_DIR):
    os.makedirs(SECURITY_DIR)

def load_security_status():
    if not os.path.exists(SECURITY_STATUS_FILE):
        default_data = {
            "last_security_rating_update": "1970-01-01T00:00:00",
            "security_rating": 8.5,
            "last_scan_time": "1970-01-01T00:00:00"
        }
        with open(SECURITY_STATUS_FILE, "w") as f:
            json.dump(default_data, f)
    with open(SECURITY_STATUS_FILE, "r") as f:
        return json.load(f)

def save_security_status(data):
    with open(SECURITY_STATUS_FILE, "w") as f:
        json.dump(data, f)

@app.route("/api/real-security-status")
def real_security_status():
    target_url = "https://drdhanashreechitre.com"  # Change this to your target site

    headers_score = 0
    vulnerabilities_found = 0
    headers_analysis = {}

    try:
        response = requests.get(target_url)
        resp_headers = response.headers

        # Check important security headers
        expected_headers = {
            "Content-Security-Policy": 3,
            "Strict-Transport-Security": 2,
            "X-Content-Type-Options": 1,
            "X-Frame-Options": 1,
            "Referrer-Policy": 1,
            "Permissions-Policy": 1
        }

        for header, weight in expected_headers.items():
            if header in resp_headers:
                headers_score += weight
                headers_analysis[header] = "✅ Present"
            else:
                headers_analysis[header] = "❌ Missing"

        # Simulate Vulnerability Scan (Extend with ZAP/Nmap later)
        if "X-XSS-Protection" not in resp_headers:
            vulnerabilities_found += 1  # Example XSS Check

        if "X-Content-Type-Options" not in resp_headers:
            vulnerabilities_found += 1  # MIME Sniffing Check

        if response.status_code != 200:
            vulnerabilities_found += 2  # Site returned non-200

    except Exception as e:
        print(f"Scan Failed: {e}")
        headers_analysis = {"Error": str(e)}

    # Rating out of 10
    security_rating = min(10, headers_score + (2 if vulnerabilities_found == 0 else 0))

    return jsonify({
        "security_rating": security_rating,
        "vulnerabilities_found": vulnerabilities_found,
        "headers_analysis": headers_analysis
    })

@app.route("/api/files-structure")
def api_files_structure():
    root_dir = "."  # Adjust if needed

    file_tree = []

    for root, dirs, files in os.walk(root_dir):
        # Skip hidden/system folders
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue

        depth = root.count(os.sep)
        indent = "│   " * depth + "├── "

        if root != ".":
            file_tree.append(f"{indent}{os.path.basename(root)}/")

        subindent = "│   " * (depth + 1) + "├── "
        for f in files:
            f_path = os.path.join(root, f)
            size = os.path.getsize(f_path) // 1024  # KB
            mtime = time.strftime('%d-%m-%Y %H:%M', time.localtime(os.path.getmtime(f_path)))
            file_tree.append(f"{subindent}{f} ({size} KB) [{mtime}]")

    return jsonify({"files": file_tree})


@app.route("/api/active-apis")
def api_active_apis():
    api_routes = []
    for rule in app.url_map.iter_rules():
        if "static" in rule.endpoint:
            continue
        api_routes.append({
            "endpoint": rule.rule,
            "methods": list(rule.methods - {'HEAD', 'OPTIONS'})
        })

    return jsonify({"routes": api_routes})
    
    return jsonify({"files": file_tree})
@app.route("/api/env-files")
def api_env_files():
    try:
        with open(".env", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = ["No .env file found."]

    env_changes = []
    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if line and not line.startswith("#"):
            if "=" in line:
                key = line.split("=")[0].strip()
                env_changes.append(f"{idx}. {key}")

    return jsonify({"env_changes": env_changes})

@app.route("/api/error-reports")
def api_error_reports():
    try:
        with open("logs/error.log", "r") as f:
            lines = f.readlines()[-10:]  # Last 10 lines
    except FileNotFoundError:
        lines = ["No error logs found."]

    errors = []
    for line in lines[::-1]:  # Start from latest
        if "ERROR" in line or "Traceback" in line:
            timestamp = line.split(' ')[0]  # Assuming log starts with timestamp
            errors.append(f"{timestamp} - {line.strip()}")

    return jsonify({"errors": errors if errors else ["No tracebacks found."]})



# ✅ Middleware to inject viewport meta for mobile responsiveness
@app.after_request
def add_mobile_meta(response):
    try:
        if response.content_type == "text/html; charset=utf-8":
            response_data = response.get_data(as_text=True)

            # Check if viewport meta already exists to avoid duplication
            if '<meta name="viewport"' not in response_data:
                # Inject viewport meta inside <head>
                response_data = response_data.replace(
                    "<head>",
                    """<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
      img { max-width: 100%; height: auto; }
      body { overflow-x: hidden; }
      table { width: 100%; display: block; overflow-x: auto; }
    </style>
                    """,
                    1  # Only replace the first <head>
                )
                response.set_data(response_data)
    except Exception as e:
        print(f"Error injecting meta tag: {e}")

    return response

# ✅ Now import blueprint and pass model
from login import login_bp
app.register_blueprint(login_bp(User))

# ✅ Register the blueprint
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(fallback_bp)
app.register_blueprint(developer_bp)
app.register_blueprint(market_bp)
app.register_blueprint(sysmon_bp)
app.register_blueprint(copilot_bp)


with app.app_context():
    db.create_all()


def send_sms(mobile, message):
    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        'authorization': os.getenv('FAST2SMS_API_KEY'),
        'Content-Type': "application/json"
    }
    payload = {
        "route": "q",
        "message": message,
        "language": "english",
        "flash": 0,
        "numbers": mobile
    }
    response = requests.post(url, json=payload, headers=headers)
    print("SMS Status:", response.status_code, response.text)

SMTP_SENDER = "arunakchitre@gmail.com"
SMTP_RECEIVER = "rushikesh.chitre@gmail.com"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
LAST_SENT_FILE = "last_log_sent.json"

def send_security_alert(ip, email_attempted):
    subject = "🚨 Security Alert: Repeated Failed Login Attempts"
    body = f"""<html>
    <body>
        <h3>Security Warning</h3>
        <p>Multiple failed login attempts detected:</p>
        <ul>
            <li><strong>IP Address:</strong> {ip}</li>
            <li><strong>Email Attempted:</strong> {email_attempted}</li>
            <li><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</li>
        </ul>
    </body>
    </html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_SENDER
    msg["To"] = SMTP_RECEIVER
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_SENDER, SMTP_PASSWORD)
            server.send_message(msg)
        print("✅ Security alert email sent.")
    except Exception as e:
        print(f"❌ Failed to send security alert: {e}")

def send_log_file(file_path, log_type):
    subject = f"📄 {log_type} Log File Report"
    body = f"Attached is the latest {log_type.lower()} log."

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = SMTP_SENDER
    msg["To"] = SMTP_RECEIVER
    msg.attach(MIMEText(body, "plain"))

    try:
        with open(file_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
            msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_SENDER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"✅ Sent {log_type} log file.")
    except Exception as e:
        print(f"❌ Failed to send {log_type} log: {e}")

def send_logs_if_due():
    now = datetime.now(timezone.utc)

    due_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

    if os.path.exists(LAST_SENT_FILE) and os.path.getsize(LAST_SENT_FILE) > 0:
        with open(LAST_SENT_FILE, "r") as f:
            try:
                data = json.load(f)
                last_sent_str = data.get("last_sent", "1970-01-01T00:00:00")
                last_sent = datetime.strptime(last_sent_str, "%Y-%m-%dT%H:%M:%S")
            except json.JSONDecodeError:
                print("❌ JSON decode error in last_log_sent.json. Using default time.")
                last_sent = datetime.min
    else:
        last_sent = datetime.min

    # Check if due
    if last_sent.date() < now.date() and now > due_time:
        send_log_file("logs/error.log", "Error")
        send_log_file("logs/audit.log", "Audit")

        with open(LAST_SENT_FILE, "w") as f:
            json.dump({"last_sent": now.strftime("%Y-%m-%dT%H:%M:%S")}, f)



@app.route('/assets/<path:filename>')
def serve_combined_assets(filename):
    frontend_path = os.path.join('frontend', 'public', 'assets')
    templates_path = os.path.join('templates', 'assets')

    # Priority: frontend/public/assets first
    file_path_frontend = os.path.join(frontend_path, filename)
    file_path_templates = os.path.join(templates_path, filename)

    if os.path.isfile(file_path_frontend):
        return send_from_directory(frontend_path, filename)
    elif os.path.isfile(file_path_templates):
        return send_from_directory(templates_path, filename)
    else:
        abort(404)

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/book")
def serve_book():
    if "patient_user" not in session:
        return redirect(url_for("login"))
    return send_from_directory(app.static_folder, "book.html")


@app.route("/<path:filename>")
def serve_static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route("/submit", methods=["POST"])
#@limiter.limit("3 per minute")
def submit_form():
    try:
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        age = request.form.get('age')
        gender = request.form.get('gender')
        mobile = request.form.get('mobile')
        appointment = request.form.get('appointment')
        problem = request.form.get('problem')

        new_appointment = Appointment(
            first_name=first_name, last_name=last_name, age=age, gender=gender, mobile=mobile,
            appointment=appointment, problem=problem
        )
        db.session.add(new_appointment)
        db.session.commit()

        session['mobile'] = mobile

        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; background-color: #f9f9f9; color: #333; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
        <h2 style="color: #4CAF50; font-size: 24px; text-align: center;">New Appointment Booking</h2>
        <p><strong>Name:</strong> {first_name} {last_name}</p>
        <p><strong>Age:</strong> {age}</p>
        <p><strong>Gender:</strong> {gender}</p>
        <p><strong>Mobile:</strong> {mobile}</p>
        <p><strong>Suggested Appointment:</strong> {appointment}</p>
        <p><strong>Problem:</strong> {problem}</p>
        <hr style="border: 1px solid #f1f1f1;">
        
        <form action="http://localhost:5000/respond" method="post" style="text-align: center;">
            <input type="hidden" name="mobile" value="{mobile}" />
            
            <textarea name="doctor_note" placeholder="Doctor's note..." rows="4" cols="50" style="width: 100%; padding: 10px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 15px;" required></textarea><br>
            
            <div style="margin-bottom: 15px;">
                <input type="radio" id="accept" name="status" value="accept" required>
                <label for="accept" style="font-size: 16px; margin-right: 20px;">Accept</label>
                <input type="radio" id="reject" name="status" value="reject">
                <label for="reject" style="font-size: 16px;">Reject</label>
            </div>
            
            <button type="submit" style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
                Submit Response
            </button>
        </form>
    </div>
</body>
</html>
"""


        sender_email = "arunakchitre@gmail.com"
        smtp_password = os.getenv("SMTP_PASSWORD")
        receiver_email = "dr.dhanashreechitre09@gmail.com"

        msg = MIMEMultipart("alternative")
        msg['Subject'] = 'New Patient Appointment'
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, smtp_password)
            server.send_message(msg)

        print("✅ Email sent.")
        return redirect(url_for('serve_thankyou', mobile=mobile))
        audit_logger.info(f"APPOINTMENT SUBMITTED by {mobile}")


    except Exception as e:
        app.logger.error("Email sending failed", exc_info=True)
        return "Internal Server Error", 500
        return f"Failed to send email: {str(e)}", 500

@app.route("/respond", methods=["POST"])
#@limiter.limit("3 per minute")
def respond():
    mobile = request.form.get('mobile')
    status = request.form.get('status')
    doctor_note = request.form.get('doctor_note')

    appointment = Appointment.query.filter_by(mobile=mobile).first()

    if appointment:
        appointment.status = 'Accepted' if status == 'accept' else 'Rejected'
        appointment.doctor_note = doctor_note
        db.session.commit()
        audit_logger.info(f"APPOINTMENT {status.upper()} by Doctor for mobile: {mobile}")


        message = f"Your appointment is {appointment.status}. Doctor's note: {doctor_note}"
        send_sms(mobile, message)

        return f"Appointment {appointment.status} and SMS sent."
    else:
        return "Invalid mobile number.", 404


@app.route("/thankyou")
def serve_thankyou():
    mobile = request.args.get('mobile')
    return render_template('thankyou.html', mobile=mobile)


from flask import flash

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        ip = request.remote_addr
        now = datetime.now(timezone.utc)

        # Clean old attempts
        login_attempts[ip] = [t for t in login_attempts[ip] if now - t < BLOCK_WINDOW]

       # if len(login_attempts[ip]) >= MAX_ATTEMPTS:
           # audit_logger.warning(f"BLOCKED LOGIN - Too many attempts from {ip}")
           # send_security_alert(ip, email)  # email alert
           # return "❌ Too many failed attempts. Try again later.", 400

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session.permanent = True
            session["user_email"] = user.email
            audit_logger.info(f"LOGIN SUCCESS - {user.email} from {ip}")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid email or password.")
            login_attempts[ip].append(now)
            audit_logger.warning(f"LOGIN FAILED - {email} from {ip}")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        password = request.form["password"]

        # ✅ Enforce strong password policy
       # import re
        #if not re.fullmatch(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).{8,}', password):
           # return "❌ Password must be at least 8 characters long and include uppercase, lowercase, and a number.", 400

        if User.query.filter_by(username=username).first():
            return "❌ Username already taken", 409
        if User.query.filter_by(email=email).first():
            return "❌ Email already registered", 409

        user = User(username=username, email=email, mobile=mobile)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


import sqlite3
from flask import session, render_template, redirect, url_for

def get_user_from_db(user_id):
    conn = sqlite3.connect("instance/appointments.db")  # ✅ adjust if needed
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

@app.route("/dashboard")
def dashboard():
    if "patient_user" not in session:
        return redirect(url_for("login"))

    username = session["patient_user"]
    user_id = session["user_id"]

    user = get_user_from_db(user_id)
    if not user:
        return redirect(url_for("login"))

    # Fetch patient-related data
    patient = Patient.query.filter_by(username=username).first()
    appointments = Appointment.query.filter_by(mobile=username).all()

    blogs_count = 2  # Dummy placeholder
    reviews_count = 4
    appointment_dates = [a.appointment for a in appointments]

    return render_template("dashboard.html",
                       user=user,
                       username=user["username"],
                       appointments=appointments,
                       blogs_count=blogs_count,
                       reviews_count=reviews_count,
                       appointment_dates=appointment_dates)


@app.route("/consult")
def consult():
    username = session.get("username", "Guest")
    return render_template("consult.html", username=username)

@app.route("/chat")
def chat():
    username = session.get("username", "Guest")
    return render_template("chat.html", username=username)

@app.route("/api/logs")
def api_logs():
    try:
        with open("logs/error.log", "r") as f:
            logs = f.readlines()[-10:]  # Get last 10 lines
    except FileNotFoundError:
        logs = ["No logs found."]
    return jsonify({"logs": [log.strip() for log in logs]})

@app.route("/api/audits")
def api_audits():
    try:
        with open("logs/audit.log", "r") as f:
            audits = f.readlines()[-10:]  # Get last 10 lines
    except FileNotFoundError:
        audits = ["No audit logs found."]
    return jsonify({"audits": [audit.strip() for audit in audits]})

@app.route("/add_review")
def add_review():
    return render_template("add_review.html")

@app.route("/write_blog")
def write_blog():
    return render_template("write_blog.html")

@app.route("/grievance")
def grievance():
    return render_template("grievance.html")

@app.route("/offers")
def offers():
    return render_template("offers.html")

@app.route("/support")
def support():
    return render_template("support.html")

@app.route("/profile")
def profile():
    if "patient_user" not in session:
        return redirect(url_for("login"))
    return render_template("profile.html", username=session["patient_user"])

@app.route("/help")
def help():
    return render_template("help.html")


@app.route("/logout")
def logout():
    session.pop("patient_user", None)
    session.pop("chat_history", None)  # Clear LLaMA memory
    session.clear()
    return redirect(url_for("serve_index"))




@app.route('/pricing')
def pricing():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    referer = request.headers.get('Referer')
    if referer and not referer.endswith('/dashboard'):
        return redirect(url_for('dashboard'))  # fallback to dashboard

    return render_template('pricing.html')


@app.route('/read')
def read():
    return render_template('read.html')

@app.route('/buy')
def buy_plan():
    plan = request.args.get('plan', 'Standard Patient Plan')  # Default fallback
    return render_template('buy.html', plan=plan)


import logging
from logging.handlers import RotatingFileHandler

if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler('logs/error.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
))
file_handler.setLevel(logging.INFO)

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Application startup')


with app.app_context():
    db.create_all()
    send_logs_if_due()


if __name__ == "__main__":
    socketio.run(app, debug=True)