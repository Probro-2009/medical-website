from flask import Blueprint, render_template, session, redirect, request
from functools import wraps
import sqlite3
import os

dev_bp = Blueprint("dev", __name__, url_prefix="/dev")

# decorator to restrict access
def developer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "role" not in session or session["role"] != "developer":
            return redirect("/")  # or 403 page
        return f(*args, **kwargs)
    return decorated_function

@dev_bp.route("/")
def dev_dashboard():
    # Only runs after IP + password passes
    # Render developer dashboard
    return render_template("dev_dashboard.html", ...)

    db_path = os.path.join("instance", "users.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Users
    cursor.execute("SELECT username, full_name, email, role, registered_at, ip_address, user_agent FROM users")
    users = cursor.fetchall()

    # Audit Logs
    log_path = os.path.join("instance", "audit_logs.db")  # or same DB if merged
    conn2 = sqlite3.connect(log_path)
    c2 = conn2.cursor()
    c2.execute("SELECT username, action, module, ip_address, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 50")
    logs = c2.fetchall()

    # Estimate who is online: (requires `last_seen` timestamp updating periodically)
    online_users = []
    for user in users:
        # logic here can be improved with Redis or cache
        last_seen = session.get(f"{user[0]}_last_seen", None)
        online = "Online" if last_seen else "Offline"
        online_users.append((user[0], online))

    return render_template("dev_dashboard.html", users=users, logs=logs, online_status=online_users)
