from flask import Blueprint, render_template, request, redirect, url_for, session
import datetime
import requests

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

def login_bp(User):  # This function returns a Blueprint configured for user login
    login = Blueprint('login', __name__, template_folder='templates')

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
