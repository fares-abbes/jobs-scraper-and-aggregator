from flask import Flask, jsonify
import json
import os

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "tanitjobs_data.json")

@app.route("/health", methods=["GET"])
def health() -> tuple:
    return {"status": "ok"}, 200

@app.route("/jobs", methods=["GET"])
def get_jobs():
    if not os.path.exists(DATA_FILE):
        return jsonify({"error": "data file not found", "file": DATA_FILE}), 404
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"count": len(data) if isinstance(data, list) else 0, "jobs": data})
    except json.JSONDecodeError as exc:  # malformed or empty file
        return jsonify({"error": "invalid json file", "details": str(exc)}), 500
    except Exception as exc:  # unexpected IO errors
        return jsonify({"error": "unable to read data file", "details": str(exc)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

