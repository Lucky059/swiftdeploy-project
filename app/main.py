from flask import Flask, request, jsonify, g
import os, time, random, threading

app = Flask(__name__)

MODE = os.getenv("MODE", "stable")
VERSION = os.getenv("APP_VERSION", "1.0.0")
START_TIME = time.time()

# Thread-safe chaos state
chaos_lock = threading.Lock()
chaos = {
    "mode": None,
    "duration": 0,
    "rate": 0.0
}


def add_mode_header(response):
    """Add X-Mode header if running in canary mode."""
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response


@app.before_request
def chaos_injection():
    """Inject chaos behaviour before handling request (canary only)."""
    if MODE != "canary":
        return

    with chaos_lock:
        current_mode = chaos["mode"]
        duration = chaos["duration"]
        rate = chaos["rate"]

    if current_mode == "slow":
        time.sleep(duration)

    elif current_mode == "error":
        if random.random() < rate:
            res = jsonify({"error": "simulated failure", "mode": "chaos-error"})
            res.status_code = 500
            return add_mode_header(res)

    elif current_mode == "recover":
        with chaos_lock:
            chaos["mode"] = None


@app.after_request
def after_request(response):
    """Add X-Mode header to every response in canary mode."""
    return add_mode_header(response)


@app.route("/")
def home():
    return jsonify({
        "message": f"Welcome! Running in {MODE} mode",
        "mode": MODE,
        "version": VERSION,
        "timestamp": time.time()
    })


@app.route("/healthz")
def health():
    uptime = int(time.time() - START_TIME)
    return jsonify({
        "status": "ok",
        "uptime_seconds": uptime
    })


@app.route("/chaos", methods=["POST"])
def chaos_control():
    if MODE != "canary":
        return jsonify({"error": "chaos endpoint only available in canary mode"}), 403

    data = request.get_json(silent=True)
    if not data or "mode" not in data:
        return jsonify({"error": "invalid request body, 'mode' is required"}), 400

    mode = data["mode"]

    if mode == "slow":
        if "duration" not in data:
            return jsonify({"error": "'duration' required for slow mode"}), 400
        with chaos_lock:
            chaos["mode"] = "slow"
            chaos["duration"] = float(data["duration"])
        return jsonify({"status": "updated", "chaos": "slow", "duration": data["duration"]})

    elif mode == "error":
        if "rate" not in data:
            return jsonify({"error": "'rate' required for error mode"}), 400
        with chaos_lock:
            chaos["mode"] = "error"
            chaos["rate"] = float(data["rate"])
        return jsonify({"status": "updated", "chaos": "error", "rate": data["rate"]})

    elif mode == "recover":
        with chaos_lock:
            chaos["mode"] = None
            chaos["duration"] = 0
            chaos["rate"] = 0.0
        return jsonify({"status": "updated", "chaos": "recovered"})

    else:
        return jsonify({"error": f"unknown chaos mode: {mode}"}), 400


if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", 3000))
    app.run(host="0.0.0.0", port=port)