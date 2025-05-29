from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, send_from_directory, redirect, url_for, render_template, session
from flask_sqlalchemy import SQLAlchemy
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

# ✅ Import the admin blueprint
from admin import admin_blueprint

app = Flask(__name__, static_folder="frontend/public")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '3f7a2c2b5e8a4a1c9d6e0f9c4b47f607'

# ✅ Register the blueprint
app.register_blueprint(admin_blueprint, url_prefix='/admin')



# Initialize SQLAlchemy
db = SQLAlchemy(app)

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

# Login database
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        patient = Patient.query.filter_by(username=username).first()
        if patient and patient.check_password(password):
            session["patient_user"] = username
            return redirect(url_for("dashboard"))
        else:
            return "Invalid username or password", 401
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if Patient.query.filter_by(username=username).first():
            return "Username already exists", 409

        new_patient = Patient(username=username)
        new_patient.set_password(password)

        db.session.add(new_patient)
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
    return render_template("consult.html")

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
    return redirect(url_for("serve_index"))


if __name__ == '__main__':
    from waitress import serve
    with app.app_context():
        db.create_all()
    serve(app, host="0.0.0.0", port=5000)
