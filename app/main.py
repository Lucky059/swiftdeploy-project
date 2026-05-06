from flask import Flask, request, jsonify, Response, g
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
import os
import random
import threading

app = Flask(__name__)

MODE = os.getenv("MODE", "stable")
VERSION = os.getenv("APP_VERSION", "1.0.0")
START_TIME = time.time()

# ---------------- METRICS ----------------

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status_code"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency")

UPTIME = Gauge("app_uptime_seconds", "App uptime")
MODE_G = Gauge("app_mode", "0=stable,1=canary")
CHAOS_G = Gauge("chaos_active", "0=none,1=slow,2=error")

# ---------------- CHAOS ----------------

chaos_lock = threading.Lock()
chaos = {"mode": None, "duration": 0, "rate": 0.0}

# ---------------- MIDDLEWARE ----------------

@app.before_request
def start_timer():
    g.start = time.time()

@app.after_request
def metrics(response):
    duration = time.time() - g.start

    LATENCY.observe(duration)
    REQUESTS.labels(request.method, request.path, response.status_code).inc()

    UPTIME.set(time.time() - START_TIME)
    MODE_G.set(1 if MODE == "canary" else 0)

    with chaos_lock:
        c = chaos["mode"]

    CHAOS_G.set(1 if c == "slow" else 2 if c == "error" else 0)

    return response

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return jsonify({
        "message": "SwiftDeploy running",
        "mode": MODE,
        "version": VERSION
    })

@app.route("/healthz")
def health():
    return jsonify({"status": "ok"})

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# ---------------- CHAOS CONTROL ----------------

@app.route("/chaos", methods=["POST"])
def chaos_control():
    data = request.get_json()

    if MODE != "canary":
        return jsonify({"error": "not in canary mode"}), 403

    mode = data.get("mode")

    if mode == "slow":
        with chaos_lock:
            chaos["mode"] = "slow"
            chaos["duration"] = float(data["duration"])
        return jsonify({"status": "slow activated"})

    if mode == "error":
        with chaos_lock:
            chaos["mode"] = "error"
            chaos["rate"] = float(data["rate"])
        return jsonify({"status": "error injection active"})

    if mode == "recover":
        with chaos_lock:
            chaos["mode"] = None
        return jsonify({"status": "recovered"})

    return jsonify({"error": "invalid mode"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("APP_PORT", 3000)))
