from flask import Blueprint, request, jsonify, render_template
from PIL import Image
import os
import io
import time
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
symptom_bp = Blueprint("symptom", __name__)

client = OpenAI(
    api_key=os.getenv("GORQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

@symptom_bp.route("/symptom", methods=["GET"])
def show_symptom_ui():
    return render_template("symptom.html")

def query_llava(image_bytes, prompt):
    base64_image = base64.b64encode(image_bytes).decode("utf-8") if image_bytes else None
    message_content = [{"type": "text", "text": prompt}]
    if base64_image:
        message_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

    response = client.chat.completions.create(
        model="llava-1.5-7b",
        messages=[{"role": "user", "content": message_content}],
        temperature=0.3,
        max_tokens=1000
    )
    return response.choices[0].message.content

@symptom_bp.route("/analyze_symptom", methods=["POST"])
def analyze_symptom():
    image_file = request.files.get('image')
    prompt = request.form.get("message", "").strip()

    if not prompt and not image_file:
        return jsonify({"response": "Please provide symptoms or upload an image."}), 400

    image_bytes = None
    image_path = None
    if image_file:
        try:
            image = Image.open(image_file).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()

            label = "symptom"
            folder = os.path.join("symptom-1o", "data", label)
            os.makedirs(folder, exist_ok=True)
            image_path = os.path.join(folder, f"img_{int(time.time())}.jpg")
            image.save(image_path)
        except Exception as e:
            return jsonify({"response": f"Image processing error: {str(e)}"}), 400

    try:
        reply = query_llava(image_bytes, prompt or "What does this image show?")
    except Exception as e:
        return jsonify({"response": f"AI error: {str(e)}"}), 500

    return jsonify({
        "response": reply,
        "diagnosis": reply,
        "image_saved_to": image_path
    })
