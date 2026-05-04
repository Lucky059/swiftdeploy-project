# SwiftDeploy 

A declarative CLI deployment tool that manages your entire container stack from a single configuration file. Write what you want, SwiftDeploy figures out how to make it happen.

---

## The Idea

Most deployment setups require you to manually write Nginx configs, Docker Compose files, and manage containers by hand. SwiftDeploy flips that — you describe your deployment once in `manifest.yaml`, and the tool generates everything else and manages the full lifecycle.

```
manifest.yaml  →  swiftdeploy init  →  nginx.conf + docker-compose.yml
                  swiftdeploy deploy →  running stack
                  swiftdeploy promote canary  →  zero-downtime mode switch
                  swiftdeploy teardown  →  clean removal
```

---

## Project Structure

```
swiftdeploy-project/
├── manifest.yaml                   # The only file you edit
├── swiftdeploy                     # The CLI tool
├── Dockerfile                      # Builds the API image
├── README.md
├── app/
│   ├── main.py                     # Flask API service
│   └── requirements.txt
└── templates/
    ├── nginx.conf.j2               # Nginx template
    └── docker-compose.yml.j2       # Docker Compose template
```

> `nginx.conf` and `docker-compose.yml` are auto-generated in the project root by `./swiftdeploy init`. Do not edit them manually.

---

## Prerequisites

- Docker + Docker Compose
- Python 3.x
- PyYAML and Jinja2: `pip install pyyaml jinja2`

---

## Setup & Running

```bash
# 1. Clone the repo
git clone https://github.com/Lucky059/swiftdeploy-project.git
cd swiftdeploy-project

# 2. Install Python dependencies
pip install pyyaml jinja2

# 3. Make CLI executable
chmod +x swiftdeploy

# 4. Build the app image
docker build -t lucky059-swiftdeploy:latest .

# 5. Deploy
./swiftdeploy deploy
```

App is now live at **http://localhost:9090**

---

## manifest.yaml

The single source of truth. Every generated file derives from this.

```yaml
services:
  name: api
  image: lucky059-swiftdeploy:latest
  port: 4000
  mode: stable
  version: "1.0.0"
  restart_policy: always

nginx:
  image: nginx:latest
  port: 9090
  proxy_timeout: 30

network:
  name: swiftdeploy-net
  driver_type: bridge

volumes:
  logs: app-logs
```

---

## CLI Subcommands

### `init`
Reads `manifest.yaml` and generates `nginx.conf` and `docker-compose.yml` from templates.

```bash
./swiftdeploy init
```
```
🔧 [init] Generating config files from manifest...
  → nginx.conf generated
  → docker-compose.yml generated
✅ init complete.
```

---

### `validate`
Runs 5 pre-flight checks and exits non-zero on any failure.

```bash
./swiftdeploy validate
```
```
🔍 [validate] Running pre-flight checks...

  ✅ PASS | manifest.yaml exists and is valid YAML
  ✅ PASS | All required fields are present and non-empty
  ✅ PASS | Docker image 'lucky059-swiftdeploy:latest' exists locally
  ✅ PASS | Nginx port 9090 is free
  ✅ PASS | nginx.conf syntax is valid

✅ All checks passed. Ready to deploy.
```

| # | Check |
|---|-------|
| 1 | `manifest.yaml` exists and is valid YAML |
| 2 | All required fields are present and non-empty |
| 3 | Docker image from manifest exists locally |
| 4 | Nginx port is not already bound on the host |
| 5 | Generated `nginx.conf` is syntactically valid |

---

### `deploy`
Runs `init`, starts the full stack, and blocks until health checks pass or 60s timeout.

```bash
./swiftdeploy deploy
```
```
🚀 [deploy] Starting stack...

✔ Container swiftdeploy-app    Healthy
✔ Container swiftdeploy-nginx  Started

✅ Stack is healthy and running!
   → App available at: http://localhost:9090
```

---

### `promote`
Switches deployment mode with a rolling restart of the app container only. Nginx stays up — zero downtime.

```bash
./swiftdeploy promote canary
./swiftdeploy promote stable
```

What happens under the hood:
1. Updates `mode` in `manifest.yaml` in-place
2. Regenerates `docker-compose.yml` with new `MODE` env var
3. Restarts only the app container
4. Hits `/healthz` to confirm the new mode is active

```
🔄 [promote] Switching to 'canary' mode...

  → manifest.yaml updated: mode = canary
  → nginx.conf generated
  → docker-compose.yml generated
  → 'api' container restarted

✅ Successfully promoted to 'canary' mode.
```

---

### `teardown`
Removes all containers, networks, and volumes.

```bash
./swiftdeploy teardown           # stop everything
./swiftdeploy teardown --clean   # stop everything + delete generated configs
```

---

## API Endpoints

All traffic goes through Nginx on port **9090**. The app port (4000) is never exposed directly.

### `GET /`
Welcome message with current mode, version, and timestamp.

```bash
curl http://localhost:9090/
```
```json
{
  "message": "Welcome! Running in stable mode",
  "mode": "stable",
  "version": "1.0.0",
  "timestamp": 1777924063.26
}
```

### `GET /healthz`
Liveness check with process uptime.

```bash
curl http://localhost:9090/healthz
```
```json
{
  "status": "ok",
  "uptime_seconds": 160
}
```

### `POST /chaos` *(canary only)*
Simulates degraded behaviour for resilience testing.

```bash
# Slow — sleep 3 seconds before responding
curl -X POST http://localhost:9090/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "slow", "duration": 3}'

# Error — return 500 on 50% of requests
curl -X POST http://localhost:9090/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "error", "rate": 0.5}'

# Recover — cancel all active chaos
curl -X POST http://localhost:9090/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "recover"}'
```

---

## Deployment Modes

| Mode | Behaviour |
|---|---|
| `stable` | Normal production mode |
| `canary` | Adds `X-Mode: canary` to every response, activates `/chaos` endpoint |

```bash
# Promote to canary
./swiftdeploy promote canary

# Confirm mode via header
curl -I http://localhost:9090/
# X-Mode: canary
# X-Deployed-By: swiftdeploy

# Roll back
./swiftdeploy promote stable
```

---

## How Nginx Is Configured

Generated from `templates/nginx.conf.j2` using values from `manifest.yaml`:

- Listens on `nginx.port`
- Timeouts set from `nginx.proxy_timeout`
- Adds `X-Deployed-By: swiftdeploy` to every response
- Forwards `X-Mode` header from upstream to client
- Returns JSON error bodies on 502/503/504:

```json
{"error": "Bad Gateway", "code": "502", "service": "api", "contact": "admin@swiftdeploy.io"}
```

- Access logs in ISO format:
```
2026-05-04T19:30:01+00:00 | 200 | 0.001s | 172.18.0.2:4000 | GET / HTTP/1.1
```

---

## Security Practices

- App container runs as non-root user (`app`)
- All Linux capabilities dropped (`cap_drop: ALL`)
- `no-new-privileges` enforced
- App port never published to host — only Nginx is exposed
- Named volume for log persistence
- Health check with start period and retry policy
- Alpine-based image (under 300MB)

---

## Architecture

```
         Internet / Host
               │
         port 9090 (public)
               │
     ┌─────────▼──────────┐
     │       Nginx         │
     │  swiftdeploy-nginx  │
     │  X-Deployed-By ✓    │
     │  JSON errors ✓      │
     └─────────┬──────────┘
               │ swiftdeploy-net (bridge)
     ┌─────────▼──────────┐
     │     Flask API       │
     │  swiftdeploy-app    │
     │  port 4000          │
     │  (not exposed)      │
     └────────────────────┘
```

---

## License

MIT
