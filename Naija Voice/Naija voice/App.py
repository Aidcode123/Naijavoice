import asyncio
import uuid
from pathlib import Path

import edge_tts
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

VOICES = {
    "male": "en-NG-AbeoNeural",
    "female": "en-NG-EzinneNeural",
}


async def generate_speech(text, voice, rate, pitch):
    communicator = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )

    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = AUDIO_DIR / filename

    await communicator.save(str(filepath))

    return filename


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}

    text = data.get("text", "").strip()
    gender = data.get("gender", "male")

    try:
        rate_value = int(data.get("rate", -5))
        pitch_value = int(data.get("pitch", -15))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid voice settings."}), 400

    if not text:
        return jsonify({"error": "Please enter some text."}), 400

    if len(text) > 5000:
        return jsonify({"error": "Text must be under 5000 characters."}), 400

    if gender not in VOICES:
        return jsonify({"error": "Invalid voice selection."}), 400

    rate_value = max(-30, min(30, rate_value))
    pitch_value = max(-30, min(20, pitch_value))

    try:
        filename = asyncio.run(
            generate_speech(
                text,
                VOICES[gender],
                f"{rate_value:+d}%",
                f"{pitch_value:+d}Hz",
            )
        )

        return jsonify({
            "success": True,
            "audio_url": f"/audio/{filename}",
            "filename": filename,
        })

    except Exception:
        app.logger.exception("Speech generation failed")
        return jsonify({
            "error": "Speech generation failed. Check your internet connection."
        }), 500


@app.route("/audio/<filename>")
def serve_audio(filename):
    if Path(filename).name != filename or not filename.endswith(".mp3"):
        return "Invalid file", 400

    return send_from_directory(
        str(AUDIO_DIR),
        filename,
        mimetype="audio/mpeg",
    )


if __name__ == "__main__":
    print("NaijaVoice is starting...")
    print("Open http://127.0.0.1:5000 in your browser.")

    app.run(debug=True)