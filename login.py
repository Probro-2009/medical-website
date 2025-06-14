from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from werkzeug.security import check_password_hash
import datetime
import requests

def login_bp(User):
    login = Blueprint('login', __name__, template_folder='templates')

def get_location(ip):
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json")
        data = response.json()
        return f"{data['city']}, {data['region']}, {data['country_name']}"
    except:
        return "Unknown"


def get_client_info(request):
    ip = request.remote_addr
    user_agent = request.headers.get("User-Agent")
    return ip, user_agent

# On register
ip, agent = get_client_info(request)
cursor.execute("INSERT INTO users (username, ..., ip_address, user_agent, registered_at) VALUES (?, ?, ?, ?, ?)",
               (username, ..., ip, agent, datetime.datetime.now()))


    @login.route('/login', methods=['GET', 'POST'])
    def login_view():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            user = User.query.filter_by(email=email).first()

            if not user:
                print(f"[❌] Login failed: No user found with email {email}")
                return redirect(url_for('login.login_error'))

            if not user.check_password(password):
                print(f"[❌] Login failed: Incorrect password for email {email}")
                return redirect(url_for('login.login_error'))

            # ✅ Successful login
            session['user_id'] = user.id
            session['username'] = user.username
            session["patient_user"] = user.username  # ✅ this line is needed for /dashboard
            print(f"[✅] Login success for {email}")
            return redirect(url_for('dashboard'))

        return render_template('login.html')

    @login.route('/login_error')
    def login_error():
        return render_template('login_error.html')  # Separate page for invalid login

    return login
