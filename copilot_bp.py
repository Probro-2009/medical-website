# 🔷 Flask Blueprint: AI Voice and Text Interaction
from flask import Flask, request, jsonify, send_file, Blueprint
import ollama
import tempfile
import os
import subprocess

copilot_bp = Blueprint('copilot_bp', __name__)


def query_llm(prompt, model="tinyllama"):
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response['message']['content'].strip()
        return reply
    except Exception as e:
        return f"Error: {str(e)}"

@copilot_bp.route("/developer/ai/voice", methods=["POST"])
def ai_voice_chat():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio_file = request.files['audio']

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        audio_path = temp_audio.name
        audio_file.save(audio_path)

    # Use Whisper to transcribe
    try:
        result = subprocess.run(
            ["whisper", audio_path, "--model", "base", "--language", "en", "--output_format", "txt"],
            capture_output=True,
            text=True
        )

        # Output is saved as .txt file next to the audio
        txt_path = audio_path.replace(".wav", ".txt")
        if not os.path.exists(txt_path):
            raise Exception("Whisper transcription failed")

        with open(txt_path, "r") as f:
            transcript = f.read().strip()

        print(f"🗣️ Transcription: {transcript}")
        os.remove(audio_path)
        os.remove(txt_path)

        response = query_llm(transcript, model="tinyllama")
        return jsonify({"prompt": transcript, "response": response})

    except Exception as e:
        os.remove(audio_path)
        return jsonify({"error": f"Whisper failed: {str(e)}"}), 500

@copilot_bp.route("/developer/ai", methods=["POST"])
def ai_text_chat():
    data = request.json
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "No prompt provided."}), 400

    response = query_llm(prompt, model="gemma:3")
    return jsonify({"response": response})