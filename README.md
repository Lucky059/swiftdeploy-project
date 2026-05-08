
# SwiftDeploy 🚀

> A CLI tool that deploys your entire app stack from one configuration file.

Instead of manually writing Nginx configs and Docker Compose files, you edit one file (`manifest.yaml`) and SwiftDeploy generates everything else and manages your containers automatically.

---

## What You Need Before Starting

Make sure you have these installed on your machine:

| Tool | How to check | Install link |
|---|---|---|
| Docker | `docker --version` | [docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | `docker compose version` | Comes with Docker |
| Python 3 | `python3 --version` | [python.org](https://python.org) |
| Git | `git --version` | [git-scm.com](https://git-scm.com) |

---

## Step 1 — Get the Project

Open your terminal and run:

```bash
git clone https://github.com/Lucky059/swiftdeploy-project.git
```

Then go into the project folder:

```bash
cd swiftdeploy-project
```

---

## Step 2 — Install Python Dependencies

SwiftDeploy needs three Python libraries to run. Install them with:

```bash
pip install pyyaml jinja2 requests
```

> **What these do:**
> - `pyyaml` — reads the manifest.yaml file
> - `jinja2` — fills in the config file templates
> - `requests` — makes HTTP calls to the policy engine

---

## Step 3 — Make the CLI Executable

This tells your computer it is allowed to run the `swiftdeploy` file as a program:

```bash
chmod +x swiftdeploy
```

> You only need to do this once.

---

## Step 4 — Build the App Image

This builds the Docker image for your app. It takes 1-2 minutes the first time:

```bash
docker build -t lucky059-swiftdeploy:latest .
```

When it finishes you should see:
```
Successfully tagged lucky059-swiftdeploy:latest
```

---

## Step 5 — Deploy

This one command does everything:
- Checks if your machine is safe to deploy on
- Generates all config files from the manifest
- Starts all three containers (app, nginx, OPA)
- Waits until everything is healthy

```bash
./swiftdeploy deploy
```

When it works you will see:
```
✅ Stack is healthy and running!
   → App:     http://localhost:9090
   → Metrics: http://localhost:9090/metrics
   → OPA:     http://127.0.0.1:8181 (localhost only)
```

---

## Step 6 — Test It Is Working

Open a new terminal and run these:

```bash
# Should return a welcome message
curl http://localhost:9090/

# Should return status: ok
curl http://localhost:9090/healthz
```

Or just open your browser and go to **http://localhost:9090**

---

## All Available Commands

Once the app is deployed, here is everything you can do:

```bash
# Generate config files from manifest (done automatically by deploy)
./swiftdeploy init

# Check everything is ready before deploying
./swiftdeploy validate

# Start the full stack
./swiftdeploy deploy

# Switch app to canary (test) mode
./swiftdeploy promote canary

# Switch app back to stable (production) mode
./swiftdeploy promote stable

# See a live metrics dashboard in your terminal
./swiftdeploy status

# Generate a report of everything that happened
./swiftdeploy audit

# Stop and remove all containers
./swiftdeploy teardown

# Stop everything AND delete generated config files
./swiftdeploy teardown --clean
```

---

## Testing the API Endpoints

| URL | Method | What it returns |
|---|---|---|
| `http://localhost:9090/` | GET | Welcome message with mode and version |
| `http://localhost:9090/healthz` | GET | Health status and uptime in seconds |
| `http://localhost:9090/metrics` | GET | Live performance metrics |
| `http://localhost:9090/chaos` | POST | Inject chaos (canary mode only) |

---

## Testing Chaos (Fun Part 🔥)

Chaos lets you simulate a broken app to test how the system responds.

> ⚠️ You must be in canary mode first

```bash
# Step 1: Switch to canary mode
./swiftdeploy promote canary

# Step 2: Make 50% of requests fail
curl -X POST http://localhost:9090/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "error", "rate": 0.5}'

# Step 3: Watch the dashboard catch the failure
./swiftdeploy status

# Step 4: Recover back to normal
curl -X POST http://localhost:9090/chaos \
  -H "Content-Type: application/json" \
  -d '{"mode": "recover"}'
```

---

## When You Are Done

To stop everything and clean up:

```bash
./swiftdeploy teardown --clean
```

---

## Project Structure Explained

```
swiftdeploy-project/
│
├── manifest.yaml              ← THE ONLY FILE YOU EDIT
│                                 Everything else is generated from this
│
├── swiftdeploy                ← The CLI tool (run this)
│
├── Dockerfile                 ← Recipe for building the app image
│
├── app/
│   ├── main.py                ← The Flask web server
│   └── requirements.txt       ← App dependencies (flask, prometheus)
│
├── templates/
│   ├── nginx.conf.j2          ← Nginx config template
│   └── docker-compose.yml.j2  ← Docker Compose template
│
└── policies/
    ├── infrastructure.rego    ← Blocks deploy if disk/CPU unsafe
    ├── canary.rego            ← Blocks promote if error rate too high
    └── data.json              ← Threshold values for policies
```

> The files inside `templates/` are blueprints. When you run `./swiftdeploy init`,
> they get filled in with values from `manifest.yaml` and saved as
> `nginx.conf` and `docker-compose.yml` in the root folder.

---

## How the Three Containers Work Together

```
You visit http://localhost:9090
           │
           ▼
    ┌─────────────┐
    │    Nginx    │  ← The front door. Handles all public traffic.
    │  port 9090  │    You never talk to the app directly.
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │   Flask App │  ← The actual application.
    │  port 4000  │    Hidden from the outside world.
    │  (internal) │    Serves your API and metrics.
    └─────────────┘

    ┌─────────────┐
    │     OPA     │  ← The safety guard.
    │  port 8181  │    Decides if deploys and promotions
    │ (localhost) │    are safe. Never exposed publicly.
    └─────────────┘
```

---

## Common Errors and Fixes

**Error: `permission denied` when running `./swiftdeploy`**
```bash
chmod +x swiftdeploy
```

**Error: `docker image not found`**
```bash
docker build -t lucky059-swiftdeploy:latest .
```

**Error: `port already in use`**
```bash
# Something is already running on port 9090
# Stop the old stack first
./swiftdeploy teardown
# Then deploy again
./swiftdeploy deploy
```

**Error: `ModuleNotFoundError`**
```bash
pip install pyyaml jinja2 requests
```

**App deployed but OPA shows warning**
```bash
# Check OPA is running
docker ps | grep opa

# Check OPA logs
docker compose logs opa
```

---

## License

MIT:
