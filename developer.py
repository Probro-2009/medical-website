
from flask import Flask, request, render_template, jsonify, session, redirect
import requests
import subprocess
import os
from flask import Blueprint
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask import Blueprint, request, render_template, redirect, session, url_for, flash
from werkzeug.security import check_password_hash
import psycopg2
from models import db, User  # ✅ NO import from app.py
developer_bp = Blueprint('developer', __name__, url_prefix='/developer')

active_url = None

@developer_bp.route("/dashboard")
def dashboard():
    if not session.get("active_url"):
        return render_template("developer_dashboard.html", username="Developer")
    
    # Fetch sysmon data
    try:
        sysmon = requests.get(session["active_url"] + "/monitor-data").json()
    except:
        sysmon = {"cpu": "N/A", "memory": "N/A"}

    # Simulate Copilot connection (Gorq API)
    copilot = {"tips": [
        "Use chmod 600 on .env files",
        "Hash+Salt passwords with Argon2"
    ]}

    # Simulate GitHub logs (after OAuth flow ideally)
    logs = [
        "[12:03] Failed to connect DB",
        "[12:07] Timeout on /api/login",
        "[12:15] Missing token header"
    ]
    audits = [
        "[11:00] Admin updated config",
        "[11:20] Changed .env variables"
    ]

    # Simulated security score (e.g., from Zap scan or headers analysis)
    security_rating = 8.5

    return render_template("developer_dashboard.html",
                           username="Developer",
                           cpu=sysmon["cpu"],
                           memory=sysmon["memory"],
                           copilot=copilot,
                           logs=logs,
                           audits=audits,
                           security_rating=security_rating)

@developer_bp.route("/copilot")
def copilot_view():
    return render_template("co-pilot.html")

@developer_bp.route("/logs")
def view_logs():
    try:
        with open("logs/error.log", "r") as f:
            error_logs = f.read()
    except FileNotFoundError:
        error_logs = "No error logs found."
    return render_template("logs.html", error_logs=error_logs)

@developer_bp.route("/audits")
def view_audits():
    try:
        with open("logs/audit.log", "r") as f:
            audit_logs = f.read()
    except FileNotFoundError:
        audit_logs = "No audit logs found."
    return render_template("audits.html", audit_logs=audit_logs)

@developer_bp.route("/files")
def list_files():
    base_path = "uploads"  # or another folder
    files = os.listdir(base_path) if os.path.exists(base_path) else []
    return render_template("files.html", files=files, base_path=base_path)

@developer_bp.route("/security")
def security_report():
    headers_info = dict(request.headers)
    return render_template("security.html", headers=headers_info, rating=8.5)

@developer_bp.route("/apis")
def api_docs():
    apis = [
        {"endpoint": "/submit", "method": "POST", "desc": "Book appointment"},
        {"endpoint": "/respond", "method": "POST", "desc": "Doctor response"},
        {"endpoint": "/login", "method": "POST", "desc": "User login"},
        {"endpoint": "/register", "method": "POST", "desc": "User register"},
    ]
    return render_template("apis.html", apis=apis)

@developer_bp.route("/env")
def env_file():
    try:
        with open(".env", "r") as f:
            content = f.read()
    except:
        content = ".env not found or access denied."
    return render_template("env.html", content=content)

@developer_bp.route("/scan")
def scan_results():
    simulated_results = {
        "XSS": "No issues",
        "SQLi": "No issues",
        "Headers": "Missing CSP Header",
        "CSP": "Not enforced",
    }
    return render_template("scan.html", results=simulated_results)

@developer_bp.route("/errors")
def error_summary():
    try:
        with open("logs/error.log", "r") as f:
            lines = f.readlines()
        errors = [line for line in lines if "ERROR" in line or "Traceback" in line]
    except:
        errors = ["No error logs found."]
    return render_template("errors.html", errors=errors)




@developer_bp.route("/manage-access", methods=["GET", "POST"])
def manage_access():
    from app import User  # import here to avoid circular import

    if request.method == "POST":
        action = request.form.get("action")
        user_id = int(request.form.get("user_id"))
        is_admin = int(request.form.get("is_admin", 0))
        is_developer = int(request.form.get("is_developer", 0))

        user = User.query.get(user_id)
        if not user:
            flash("❌ User not found.")
            return redirect(url_for("developer.manage_access"))

        if action == "update_roles":
            user.is_admin = is_admin
            user.is_developer = is_developer
            flash("✅ Role updated.")
        elif action == "delete":
            db.session.delete(user)
            flash("❌ User deleted.")

        db.session.commit()

    users = User.query.order_by(User.id).all()
    return render_template("manage_access.html", users=users)

@developer_bp.route("/api/logs")
def api_logs():
    try:
        with open("logs/error.log", "r") as f:
            logs = f.readlines()[-10:]  # Get last 10 logs
    except FileNotFoundError:
        logs = ["No logs found."]
    return jsonify({"logs": [log.strip() for log in logs]})

@developer_bp.route("/api/audits")
def api_audits():
    try:
        with open("logs/audit.log", "r") as f:
            audits = f.readlines()[-10:]  # Get last 10 audit logs
    except FileNotFoundError:
        audits = ["No audit logs found."]
    return jsonify({"audits": [audit.strip() for audit in audits]})
