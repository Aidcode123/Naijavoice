import asyncio
import uuid
from pathlib import Path

import edge_tts
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

VOICES = {
    "male": "en-NG-AbeoNeural",
    "female": "en-NG-EzinneNeural",
}


async def generate_speech(text, voice, filename, rate, pitch):
    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch
    )
    await communicate.save(str(filename))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or request.form

    text = str(data.get("text", "")).strip()
    gender = str(data.get("gender", "male")).lower()

    try:
        rate_value = int(data.get("rate", -5))
        pitch_value = int(data.get("pitch", -15))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid speed or pitch."}), 400

    if not text:
        return jsonify({"error": "Please enter some text."}), 400

    if len(text) > 3000:
        return jsonify({"error": "Please keep your text under 3000 characters."}), 400

    voice = VOICES.get(gender)

    if not voice:
        return jsonify({"error": "Please choose a valid voice."}), 400

    rate_value = max(-30, min(30, rate_value))
    pitch_value = max(-30, min(20, pitch_value))

    rate = f"{rate_value:+d}%"
    pitch = f"{pitch_value:+d}Hz"

    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = AUDIO_DIR / filename

    try:
        asyncio.run(
            generate_speech(text, voice, filepath, rate, pitch)
        )

        return jsonify({
            "success": True,
            "audio_url": f"/audio/{filename}"
        })

    except Exception:
        app.logger.exception("Speech generation failed")
        return jsonify({
            "error": "Speech generation failed. Please try again."
        }), 500


@app.route("/audio/<filename>")
def audio(filename):
    if not filename.endswith(".mp3") or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid audio filename."}), 400

    return send_from_directory(AUDIO_DIR, filename)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
