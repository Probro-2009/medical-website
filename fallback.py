from flask import Blueprint, render_template, request, jsonify, session
import requests
import os
from dotenv import load_dotenv
load_dotenv()

fallback_bp = Blueprint("fallback", __name__, template_folder="templates")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
@fallback_bp.route("/chat")
def consult_page():
    username = session.get("username", "User")
    session.permanent = True
    if "chat_history" not in session:
        session["chat_history"] = []
    return render_template("chat.html", username=username)


@fallback_bp.route("/consult/ai", methods=["POST"])
def consult_ai():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "Please enter a message."}), 400

    # Initialize memory if not already
    if "chat_history" not in session:
        session["chat_history"] = []

    session["chat_history"].append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "system", "content": "You are a helpful medical assistant."}] + session["chat_history"],
                "temperature": 0.7
            }
        )

        data = response.json()
        if "choices" not in data:
            return jsonify({"response": f"⚠️ Groq Error: {data.get('error', {}).get('message', 'Unknown error')}"})

        reply = data["choices"][0]["message"]["content"]
        session["chat_history"].append({"role": "assistant", "content": reply})
        return jsonify({"response": reply})

    except Exception as e:
        return jsonify({"response": f"⚠️ Error from Groq: {str(e)}"})