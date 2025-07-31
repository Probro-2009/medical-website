
import sounddevice as sd
import numpy as np
import queue
import sys
import json
import ollama
import pyttsx3
from vosk import Model, KaldiRecognizer
import requests
import re

# 🔊 Setup fallback TTS using pyttsx3 (offline)
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 175)

def speak(text):
    print(f"🧠 Reply: {text}")
    tts_engine.say(text)
    tts_engine.runAndWait()

# 🎤 Setup Vosk for offline speech recognition
model = Model("vosk-model-small-en-us-0.15")  # Ensure this is downloaded and extracted
rec = KaldiRecognizer(model, 16000)
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(f"[Mic Error] {status}", file=sys.stderr)
    q.put(bytes(indata))

# 🌍 Web Search
SEARCH_URL = "https://api.duckduckgo.com/"

def perform_web_search(query):
    print(f"🌐 Searching: {query}")
    try:
        res = requests.get(SEARCH_URL, params={
            "q": query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1
        }, timeout=10)
        return res.json().get("AbstractText") or "No good answer found."
    except Exception as e:
        return f"Web search failed: {str(e)}"

# 🤖 LLM Query
def query_llama(prompt):
    try:
        print(f"🤖 Prompt to TinyLlama: {prompt}")
        res = ollama.chat(model="tinyllama:latest", messages=[{"role": "user", "content": prompt}])
        return res['message']['content'].strip()
    except Exception as e:
        return f"Error talking to TinyLlama: {e}"

# 🔁 Main Loop
def main():
    print("🎤 Speak clearly. Say 'Web search: ...' to trigger online lookup.")
    print("Press Ctrl+C to exit.\n")
    while True:
        try:
            print("🎙️ Listening...")
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback):
                text = ""
                while True:
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").strip()
                        break

            if not text:
                print("🤷 No input detected.")
                continue

            print(f"🧏 You said: {text}")

            match = re.match(r'(web search|search)[:\s]*(.+)', text, re.IGNORECASE)
            if match:
                query = match.group(2)
                reply = perform_web_search(query)
                speak(reply)
                continue

            reply = query_llama(text)
            speak(reply)

        except KeyboardInterrupt:
            print("\n👋 Exiting.")
            break

if __name__ == "__main__":
    main()
