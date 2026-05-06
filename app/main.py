from flask import Flask, request, jsonify, Response, g
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST, REGISTRY
)
import time, os, random, threading

app = Flask(__name__)

MODE    = os.getenv("MODE", "stable")
VERSION = os.getenv("APP_VERSION", "1.0.0")
START_TIME = time.time()

# ─── Metrics definitions ─────────────────────────────────
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"]
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request duration in seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)
UPTIME_G = Gauge("app_uptime_seconds", "Seconds since app started")
MODE_G   = Gauge("app_mode",           "Deployment mode: 0=stable 1=canary")
CHAOS_G  = Gauge("chaos_active",       "Chaos state: 0=none 1=slow 2=error")

# ─── Chaos state ─────────────────────────────────────────
chaos_lock = threading.Lock()
chaos = {"mode": None, "duration": 0, "rate": 0.0}


# ─── Helper ──────────────────────────────────────────────
def add_mode_header(response):
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response


# ─── Middleware ──────────────────────────────────────────
@app.before_request
def before():
    g.start = time.time()

    # Chaos injection only in canary, skip health + metrics routes
    if MODE != "canary" or request.path in ("/metrics", "/healthz"):
        return

    with chaos_lock:
        current  = chaos["mode"]
        duration = chaos["duration"]
        rate     = chaos["rate"]

    if current == "slow":
        time.sleep(duration)
    elif current == "error":
        if random.random() < rate:
            res = jsonify({"error": "simulated failure"})
            res.status_code = 500
            return add_mode_header(res)
    elif current == "recover":
        with chaos_lock:
            chaos["mode"] = None


@app.after_request
def after(response):
    duration = time.time() - getattr(g, "start", time.time())

    # Track all routes except /metrics itself to avoid noise
    if request.path != "/metrics":
        REQUESTS.labels(
            method=request.method,
            path=request.path,
            status_code=str(response.status_code)
        ).inc()
        LATENCY.observe(duration)

    # Keep state gauges current
    UPTIME_G.set(time.time() - START_TIME)
    MODE_G.set(1 if MODE == "canary" else 0)

    with chaos_lock:
        c = chaos["mode"]
    CHAOS_G.set(1 if c == "slow" else 2 if c == "error" else 0)

    return add_mode_header(response)


# ─── Routes ──────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "message":   f"Welcome! Running in {MODE} mode",
        "mode":      MODE,
        "version":   VERSION,
        "timestamp": time.time()
    })


@app.route("/healthz")
def health():
    return jsonify({
        "status":         "ok",
        "uptime_seconds": int(time.time() - START_TIME)
    })


@app.route("/metrics")
def metrics_endpoint():
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


@app.route("/chaos", methods=["POST"])
def chaos_control():
    if MODE != "canary":
        return jsonify({"error": "chaos only available in canary mode"}), 403

    data = request.get_json(silent=True)
    if not data or "mode" not in data:
        return jsonify({"error": "'mode' is required"}), 400

    mode = data["mode"]

    if mode == "slow":
        if "duration" not in data:
            return jsonify({"error": "'duration' required for slow mode"}), 400
        with chaos_lock:
            chaos["mode"]     = "slow"
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
            chaos["mode"]     = None
            chaos["duration"] = 0
            chaos["rate"]     = 0.0
        return jsonify({"status": "updated", "chaos": "recovered"})

    return jsonify({"error": f"unknown chaos mode: {mode}"}), 400


if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", 4000))
    app.run(host="0.0.0.0", port=port, threaded=True)