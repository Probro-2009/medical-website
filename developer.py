from flask import Flask, request, render_template, jsonify, session, redirect
import requests
import subprocess
import os
from flask import Blueprint
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room

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


