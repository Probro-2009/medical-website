import os
import json
import secrets
import hashlib
import requests
import qrcode
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, send_file, url_for, current_app
from flask_apscheduler import APScheduler

fallback_bp = Blueprint("fallback", __name__, template_folder="templates")

GROQ_API_KEY = os.environ.get("API_KEY")
CHAT_HISTORY_DIR = 'chat_history'
EXPORT_DIR = 'chat_exports'

scheduler = APScheduler()

# Utility Functions
def get_chat_file_path(patient_id, chat_session_id):
    patient_dir = os.path.join(CHAT_HISTORY_DIR, patient_id)
    os.makedirs(patient_dir, exist_ok=True)
    return os.path.join(patient_dir, f"{chat_session_id}.json")

def get_metadata_file(patient_id, chat_session_id):
    return os.path.join(CHAT_HISTORY_DIR, patient_id, f"{chat_session_id}_meta.json")

def get_export_paths(patient_id, chat_session_id):
    export_folder = os.path.join(EXPORT_DIR, patient_id, chat_session_id)
    os.makedirs(export_folder, exist_ok=True)
    return {
        "pdf_path": os.path.join(export_folder, "chat.pdf"),
        "qr_path": os.path.join(export_folder, "qr.png"),
        "token_path": os.path.join(export_folder, "token.txt")
    }

def update_last_activity(patient_id, chat_session_id):
    meta_file = get_metadata_file(patient_id, chat_session_id)
    meta = {"expired": False, "last_activity": datetime.now().isoformat()}
    if os.path.exists(meta_file):
        with open(meta_file, "r") as f:
            meta = json.load(f)
    meta["last_activity"] = datetime.now().isoformat()
    with open(meta_file, "w") as f:
        json.dump(meta, f)

def is_chat_expired(patient_id, chat_session_id):
    meta_file = get_metadata_file(patient_id, chat_session_id)
    if not os.path.exists(meta_file):
        return False
    with open(meta_file, "r") as f:
        meta = json.load(f)
    if meta.get("expired", False):
        return True
    last_activity = datetime.fromisoformat(meta.get("last_activity"))
    if datetime.now() - last_activity > timedelta(hours=24):
        meta["expired"] = True
        with open(meta_file, "w") as f:
            json.dump(meta, f)
        return True
    return False

def generate_secure_token(patient_id, chat_session_id):
    raw = f"{patient_id}-{chat_session_id}-{secrets.token_hex(8)}"
    return hashlib.sha256(raw.encode()).hexdigest()

# Routes
@fallback_bp.route("/chat")
def consult_page():
    username = session.get("username", "User")
    user_id = session.get("user_id")
    chat_session_id = session.get("chat_session_id")
    session.permanent = True
    if not chat_session_id:
        session["chat_session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
    return render_template("chat.html", username=username, user_id=user_id, chat_session_id=session["chat_session_id"])

@fallback_bp.route("/consult/ai", methods=["POST"])
def consult_ai():
    import requests

    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "Please enter a message."}), 400

    patient_id = str(session.get("user_id"))
    chat_session_id = session.get("chat_session_id")

    if not patient_id or not chat_session_id:
        return jsonify({"response": "Session expired, please login again."}), 401

    if is_chat_expired(patient_id, chat_session_id):
        return jsonify({"response": "⚠️ This chat session has expired after 24 hours of inactivity."}), 403

    chat_file = get_chat_file_path(patient_id, chat_session_id)

    chat_history = []
    if os.path.exists(chat_file):
        with open(chat_file, "r") as f:
            chat_history = json.load(f)

    chat_history.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "system", "content": "You are a helpful medical assistant."}] + chat_history,
                "temperature": 0.7
            }
        )

        data = response.json()
        if "choices" not in data:
            return jsonify({"response": f"⚠️ Groq Error: {data.get('error', {}).get('message', 'Unknown error')}"})

        reply = data["choices"][0]["message"]["content"]
        chat_history.append({"role": "assistant", "content": reply})

        with open(chat_file, "w") as f:
            json.dump(chat_history, f)

        update_last_activity(patient_id, chat_session_id)
        return jsonify({"response": reply})

    except Exception as e:
        return jsonify({"response": f"⚠️ Error from Groq: {str(e)}"})


@fallback_bp.route("/chat-history/<patient_id>/<chat_session_id>/export", methods=["GET"])
def export_chat(patient_id, chat_session_id):
    chat_file = get_chat_file_path(patient_id, chat_session_id)
    if not os.path.exists(chat_file):
        return jsonify({"error": "Chat session not found."}), 404

    with open(chat_file, "r") as f:
        chat_history = json.load(f)

    paths = get_export_paths(patient_id, chat_session_id)

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    c = canvas.Canvas(paths["pdf_path"], pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Chat History - Patient ID: {patient_id}")
    y -= 30

    for msg in chat_history:
        text = f"{msg['role'].capitalize()}: {msg['content']}"
        for line in text.splitlines():
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 12)
            c.drawString(50, y, line[:90])
            y -= 20

    c.save()

    token = generate_secure_token(patient_id, chat_session_id)
    with open(paths["token_path"], "w") as f:
        f.write(token)

    share_url = url_for('fallback.shared_chat', token=token, _external=True)

    qr_img = qrcode.make(share_url)
    qr_img.save(paths["qr_path"])

    return jsonify({
        "pdf_url": url_for('fallback.download_chat_pdf', patient_id=patient_id, chat_session_id=chat_session_id, _external=True),
        "qr_url": url_for('fallback.get_qr_image', patient_id=patient_id, chat_session_id=chat_session_id, _external=True),
        "share_link": share_url
    })

@fallback_bp.route("/chat-history/<patient_id>/<chat_session_id>/pdf", methods=["GET"])
def download_chat_pdf(patient_id, chat_session_id):
    paths = get_export_paths(patient_id, chat_session_id)
    if not os.path.exists(paths["pdf_path"]):
        return "PDF not generated", 404
    return send_file(paths["pdf_path"], as_attachment=True)

@fallback_bp.route("/chat-history/<patient_id>/<chat_session_id>/qr", methods=["GET"])
def get_qr_image(patient_id, chat_session_id):
    paths = get_export_paths(patient_id, chat_session_id)
    if not os.path.exists(paths["qr_path"]):
        return "QR Code not generated", 404
    return send_file(paths["qr_path"], mimetype='image/png')

@fallback_bp.route("/chat/shared/<token>", methods=["GET"])
def shared_chat(token):
    for root, dirs, files in os.walk(EXPORT_DIR):
        if 'token.txt' in files:
            token_file = os.path.join(root, 'token.txt')
            with open(token_file, 'r') as f:
                saved_token = f.read().strip()
                if saved_token == token:
                    pdf_path = os.path.join(root, 'chat.pdf')
                    if os.path.exists(pdf_path):
                        return send_file(pdf_path, as_attachment=True)
    return "Invalid or expired link", 404

@scheduler.task('interval', id='ExpireChats', hours=1)
def expire_inactive_chats():
    for patient_id in os.listdir(CHAT_HISTORY_DIR):
        patient_dir = os.path.join(CHAT_HISTORY_DIR, patient_id)
        if not os.path.isdir(patient_dir):
            continue
        for file in os.listdir(patient_dir):
            if file.endswith("_meta.json"):
                meta_file = os.path.join(patient_dir, file)
                with open(meta_file, "r") as f:
                    meta = json.load(f)
                if meta.get("expired"):
                    continue
                last_activity = datetime.fromisoformat(meta.get("last_activity"))
                if datetime.now() - last_activity > timedelta(hours=24):
                    meta["expired"] = True
                    with open(meta_file, "w") as f:
                        json.dump(meta, f)
                    print(f"[Expired] {file}")

@scheduler.task('interval', id='CleanupOldChats', hours=24)
def cleanup_old_chats():
    retention_days = 7
    now = datetime.now()

    for patient_id in os.listdir(CHAT_HISTORY_DIR):
        patient_dir = os.path.join(CHAT_HISTORY_DIR, patient_id)
        if not os.path.isdir(patient_dir):
            continue
        for file in os.listdir(patient_dir):
            if file.endswith("_meta.json"):
                meta_file = os.path.join(patient_dir, file)
                with open(meta_file, "r") as f:
                    meta = json.load(f)
                if meta.get("expired"):
                    last_activity = datetime.fromisoformat(meta.get("last_activity"))
                    if now - last_activity > timedelta(days=retention_days):
                        chat_session_id = file.replace("_meta.json", "")
                        chat_file = get_chat_file_path(patient_id, chat_session_id)
                        if os.path.exists(chat_file):
                            os.remove(chat_file)
                        os.remove(meta_file)
                        export_dir = os.path.join(EXPORT_DIR, patient_id, chat_session_id)
                        if os.path.exists(export_dir):
                            import shutil
                            shutil.rmtree(export_dir)
                        print(f"[Deleted] Chat Session {chat_session_id} for Patient {patient_id}")

def init_app(app):
    scheduler.init_app(app)
    scheduler.start()
