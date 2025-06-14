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
from admin import admin_blueprint
from video import video
from login import login_bp
from fallback import fallback_bp
from datetime import timedelta
from dev import dev_bp
from dotenv import load_dotenv


load_dotenv()

RECAPTCHA_SECRET = os.environ.get("RECAPTCHA_SECRET_KEY")
RECAPTCHA_SITE = os.environ.get("RECAPTCHA_SITE_KEY")

app = Flask(__name__, static_folder="frontend/public")
app.secret_key = '3f7a2c2b5e8a4a1c9d6e0f9c4b47f607'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
socketio = SocketIO(app)
db = SQLAlchemy(app)
app.permanent_session_lifetime = timedelta(hours=1)  # Optional

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    mobile = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)


# ✅ Now import blueprint and pass model
from login import login_bp
app.register_blueprint(login_bp(User))

# ✅ Register the blueprint
app.register_blueprint(admin_blueprint, url_prefix='/admin')
app.register_blueprint(video)
app.register_blueprint(fallback_bp)
app.register_blueprint(dev_bp)

class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # or password_hash if applicable




# Define the Appointment model
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    age = db.Column(db.String(10))
    gender = db.Column(db.String(10))
    mobile = db.Column(db.String(15), unique=True)
    appointment = db.Column(db.String(100))
    problem = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')
    preferred_time = db.Column(db.String(50), nullable=True)
    doctor_note = db.Column(db.Text, nullable=True)

with app.app_context():
    db.create_all()


def send_sms(mobile, message):
    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        'authorization': '5A8LlghQpXKu20CnBszbaI6yomNqrdcvDUHZV1F7RxiPMjk9J49HrE6gMkILO08e5mwvp24UitRh7ujW',
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

# Set allowed developer IP
ALLOWED_DEV_IP = "110.226.180.170"

@app.before_request
def restrict_dev_access():
    if request.path.startswith("/dev"):
        client_ip = request.remote_addr
        if client_ip != ALLOWED_DEV_IP:
            return "Access Denied: Unauthorized IP", 403
        if not session.get("dev_authenticated"):
            return redirect(url_for("dev_auth"))

# Route to the dev auth page (password or Windows Hello)@app.route("/dev_auth", methods=["GET", "POST"])
@app.route("/dev_auth", methods=["GET", "POST"])
def dev_auth():
    if request.method == "POST":
        password = request.form.get("password")
        recaptcha_response = request.form.get("g-recaptcha-response")

        # Verify reCAPTCHA
        verify_url = "https://www.google.com/recaptcha/api/siteverify"
        resp = requests.post(verify_url, data={
            'secret': RECAPTCHA_SECRET,
            'response': recaptcha_response
        })
        result = resp.json()

        if not result.get("success"):
            return render_template("dev_auth.html", error="reCAPTCHA failed.", sitekey=RECAPTCHA_SITE)

        if password == "abha0519$":
            session["dev_authenticated"] = True
            return redirect(url_for("dev.dev_dashboard"))
        else:
            return render_template("dev_auth.html", error="Incorrect password.", sitekey=RECAPTCHA_SITE)

    return render_template("dev_auth.html", sitekey=RECAPTCHA_SITE)
@app.route('/start_call')
def start_call():
    room_id = str(uuid.uuid4())[:8]  # Generate short unique ID
    return redirect(url_for('video.video_call', room_id=room_id))

import os
from flask import send_from_directory, abort

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
        smtp_password = "kmhv ghkx cpcq kshr"
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

    except Exception as e:
        print(f"❌ Email failed: {str(e)}")
        return f"Failed to send email: {str(e)}", 500

@app.route("/respond", methods=["POST"])
def respond():
    mobile = request.form.get('mobile')
    status = request.form.get('status')
    doctor_note = request.form.get('doctor_note')

    appointment = Appointment.query.filter_by(mobile=mobile).first()

    if appointment:
        appointment.status = 'Accepted' if status == 'accept' else 'Rejected'
        appointment.doctor_note = doctor_note
        db.session.commit()

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

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_email"] = user.email
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid email or password.")
            return render_template("login.html")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            return "❌ Username already taken", 409
        if User.query.filter_by(email=email).first():
            return "❌ Email already registered", 409

        # ✅ Create user and set hashed password
        user = User(username=username, email=email, mobile=mobile)
        user.set_password(password)  # ✅ sets hashed password

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "patient_user" not in session:
        return redirect(url_for("login"))

    username = session["patient_user"]

    # Fetch patient-related data
    patient = Patient.query.filter_by(username=username).first()
    appointments = Appointment.query.filter_by(mobile=username).all()  # or use patient.id if you link patients

    # Dummy data for now
    blogs_count = 2  # Replace with actual Blog.query.filter_by(author=patient.id).count() if you have Blog model
    reviews_count = 4

    # Extract appointment dates
    appointment_dates = [a.appointment for a in appointments]

    return render_template("dashboard.html", username=username,
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
    return redirect(url_for("serve_index"))

@app.route('/video_call')
def video_call():
    return render_template("video_call.html")

import requests
from flask import request, jsonify

@app.route("/webrtc_offer", methods=["POST"])
def webrtc_offer():
    offer_sdp = request.json.get("sdp")
    
    try:
        response = requests.post("http://localhost:8081", json={"sdp": offer_sdp})
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@socketio.on('join')
def handle_join(room):
    join_room(room)
    emit('joined', room=room)

@socketio.on('offer')
def handle_offer(room, offer):
    emit('offer', offer, room=room, include_self=False)

@socketio.on('answer')
def handle_answer(room, answer):
    emit('answer', answer, room=room, include_self=False)

@socketio.on('ice-candidate')
def handle_ice(room, candidate):
    emit('ice-candidate', candidate, room=room, include_self=False)





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host="0.0.0.0", port=5000)

