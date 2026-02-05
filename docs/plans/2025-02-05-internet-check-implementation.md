# Internet Health Check Container Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Docker container that monitors internet connectivity and executes a failure script when all ping targets are unreachable.

**Architecture:** Single Python script with main loop that pings targets, tracks consecutive failures, executes mounted action script on threshold breach, and enters cooldown. JSON structured logging to stdout, file-based health status for Docker healthcheck.

**Tech Stack:** Python 3.12 (stdlib only), Docker

---

### Task 1: Project Setup

**Files:**
- Create: `src/main.py`
- Create: `.gitignore`

**Step 1: Create project structure**

```bash
mkdir -p src
```

**Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.env
```

**Step 3: Create empty main.py with entrypoint**

```python
#!/usr/bin/env python3
"""Internet connectivity health checker with failure action."""

def main():
    pass

if __name__ == "__main__":
    main()
```

**Step 4: Verify it runs**

Run: `python3 src/main.py`
Expected: Exits cleanly with no output

**Step 5: Commit**

```bash
git init
git add .gitignore src/main.py
git commit -m "chore: initial project setup"
```

---

### Task 2: Configuration Loading

**Files:**
- Modify: `src/main.py`

**Step 1: Add configuration dataclass and loader**

```python
#!/usr/bin/env python3
"""Internet connectivity health checker with failure action."""

import os
import sys
from dataclasses import dataclass


@dataclass
class Config:
    ping_targets: list[str]
    check_interval_seconds: int
    failure_threshold: int
    cooldown_seconds: int
    ping_timeout_seconds: int


def load_config() -> Config:
    """Load configuration from environment variables."""
    ping_targets_raw = os.environ.get("PING_TARGETS", "")
    if not ping_targets_raw:
        print('{"level":"error","event":"config_error","message":"PING_TARGETS is required"}')
        sys.exit(1)

    ping_targets = [t.strip() for t in ping_targets_raw.split(",") if t.strip()]
    if not ping_targets:
        print('{"level":"error","event":"config_error","message":"PING_TARGETS must contain at least one target"}')
        sys.exit(1)

    return Config(
        ping_targets=ping_targets,
        check_interval_seconds=int(os.environ.get("CHECK_INTERVAL_SECONDS", "30")),
        failure_threshold=int(os.environ.get("FAILURE_THRESHOLD", "3")),
        cooldown_seconds=int(os.environ.get("COOLDOWN_SECONDS", "300")),
        ping_timeout_seconds=int(os.environ.get("PING_TIMEOUT_SECONDS", "5")),
    )


def main():
    config = load_config()
    print(f"Config loaded: {config}")


if __name__ == "__main__":
    main()
```

**Step 2: Test config loading**

Run: `PING_TARGETS="8.8.8.8,1.1.1.1" python3 src/main.py`
Expected: Prints config with targets and defaults

Run: `python3 src/main.py`
Expected: Prints error JSON and exits with code 1

**Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: add configuration loading from environment"
```

---

### Task 3: JSON Logging

**Files:**
- Modify: `src/main.py`

**Step 1: Add JSON logging function**

Add after imports:

```python
import json
from datetime import datetime, timezone


def log(level: str, event: str, **kwargs):
    """Output a structured JSON log entry."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": level,
        "event": event,
        **kwargs,
    }
    print(json.dumps(entry), flush=True)
```

**Step 2: Update config error handling to use log()**

Replace the print statements in load_config:

```python
def load_config() -> Config:
    """Load configuration from environment variables."""
    ping_targets_raw = os.environ.get("PING_TARGETS", "")
    if not ping_targets_raw:
        log("error", "config_error", message="PING_TARGETS is required")
        sys.exit(1)

    ping_targets = [t.strip() for t in ping_targets_raw.split(",") if t.strip()]
    if not ping_targets:
        log("error", "config_error", message="PING_TARGETS must contain at least one target")
        sys.exit(1)

    return Config(
        ping_targets=ping_targets,
        check_interval_seconds=int(os.environ.get("CHECK_INTERVAL_SECONDS", "30")),
        failure_threshold=int(os.environ.get("FAILURE_THRESHOLD", "3")),
        cooldown_seconds=int(os.environ.get("COOLDOWN_SECONDS", "300")),
        ping_timeout_seconds=int(os.environ.get("PING_TIMEOUT_SECONDS", "5")),
    )
```

**Step 3: Add startup log to main()**

```python
def main():
    config = load_config()
    log("info", "startup", config={
        "ping_targets": config.ping_targets,
        "check_interval_seconds": config.check_interval_seconds,
        "failure_threshold": config.failure_threshold,
        "cooldown_seconds": config.cooldown_seconds,
        "ping_timeout_seconds": config.ping_timeout_seconds,
    })
```

**Step 4: Test logging output**

Run: `PING_TARGETS="8.8.8.8,1.1.1.1" python3 src/main.py`
Expected: JSON with ts, level="info", event="startup", config object

Run: `python3 src/main.py`
Expected: JSON with level="error", event="config_error"

**Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat: add JSON structured logging"
```

---

### Task 4: Ping Implementation

**Files:**
- Modify: `src/main.py`

**Step 1: Add ping function**

Add after log():

```python
import subprocess
import time


def ping(target: str, timeout_seconds: int) -> tuple[bool, int | None, str | None]:
    """
    Ping a target and return (success, latency_ms, error).
    """
    start = time.monotonic()
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout_seconds), target],
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 1,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        if result.returncode == 0:
            return True, latency_ms, None
        else:
            return False, None, "unreachable"
    except subprocess.TimeoutExpired:
        return False, None, "timeout"
    except Exception as e:
        return False, None, str(e)
```

**Step 2: Add check_connectivity function**

Add after ping():

```python
def check_connectivity(targets: list[str], timeout_seconds: int) -> bool:
    """
    Ping all targets. Returns True if ANY target is reachable.
    """
    log("info", "check_started", targets=targets)

    any_success = False
    for target in targets:
        success, latency_ms, error = ping(target, timeout_seconds)
        if success:
            log("info", "check_result", target=target, success=True, latency_ms=latency_ms)
            any_success = True
        else:
            log("info", "check_result", target=target, success=False, error=error)

    return any_success
```

**Step 3: Test ping in main()**

Temporarily update main():

```python
def main():
    config = load_config()
    log("info", "startup", config={
        "ping_targets": config.ping_targets,
        "check_interval_seconds": config.check_interval_seconds,
        "failure_threshold": config.failure_threshold,
        "cooldown_seconds": config.cooldown_seconds,
        "ping_timeout_seconds": config.ping_timeout_seconds,
    })

    # Temporary test
    result = check_connectivity(config.ping_targets, config.ping_timeout_seconds)
    print(f"Any reachable: {result}")
```

**Step 4: Test ping functionality**

Run: `PING_TARGETS="8.8.8.8,1.1.1.1" python3 src/main.py`
Expected: JSON logs for check_started, check_result for each target, then "Any reachable: True"

Run: `PING_TARGETS="192.0.2.1" PING_TIMEOUT_SECONDS=2 python3 src/main.py`
Expected: check_result with success=False, then "Any reachable: False" (192.0.2.1 is TEST-NET, unreachable)

**Step 5: Remove temporary test code from main()**

```python
def main():
    config = load_config()
    log("info", "startup", config={
        "ping_targets": config.ping_targets,
        "check_interval_seconds": config.check_interval_seconds,
        "failure_threshold": config.failure_threshold,
        "cooldown_seconds": config.cooldown_seconds,
        "ping_timeout_seconds": config.ping_timeout_seconds,
    })
```

**Step 6: Commit**

```bash
git add src/main.py
git commit -m "feat: add ping and connectivity check"
```

---

### Task 5: Health Status File

**Files:**
- Modify: `src/main.py`

**Step 1: Add health status constants and function**

Add after imports:

```python
HEALTH_FILE = "/tmp/health_status"


def write_health_status(healthy: bool):
    """Write current health status to file for Docker healthcheck."""
    status = "healthy" if healthy else "unhealthy"
    with open(HEALTH_FILE, "w") as f:
        f.write(status)
```

**Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add health status file for Docker healthcheck"
```

---

### Task 6: Action Execution

**Files:**
- Modify: `src/main.py`

**Step 1: Add action script constant and execution function**

Add after HEALTH_FILE:

```python
ACTION_SCRIPT = "/action.sh"


def execute_action() -> tuple[int, int]:
    """
    Execute the failure action script.
    Returns (exit_code, duration_ms).
    """
    log("error", "action_triggered")
    start = time.monotonic()

    try:
        result = subprocess.run(
            [ACTION_SCRIPT],
            capture_output=True,
            text=True,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        log("info", "action_complete", exit_code=result.returncode, duration_ms=duration_ms)
        if result.stdout:
            log("info", "action_stdout", output=result.stdout.strip())
        if result.stderr:
            log("warn", "action_stderr", output=result.stderr.strip())
        return result.returncode, duration_ms
    except FileNotFoundError:
        duration_ms = int((time.monotonic() - start) * 1000)
        log("error", "action_failed", error="action script not found", path=ACTION_SCRIPT)
        return 127, duration_ms
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        log("error", "action_failed", error=str(e))
        return 1, duration_ms
```

**Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add failure action script execution"
```

---

### Task 7: Main Loop

**Files:**
- Modify: `src/main.py`

**Step 1: Implement the main monitoring loop**

Replace main():

```python
def main():
    config = load_config()
    log("info", "startup", config={
        "ping_targets": config.ping_targets,
        "check_interval_seconds": config.check_interval_seconds,
        "failure_threshold": config.failure_threshold,
        "cooldown_seconds": config.cooldown_seconds,
        "ping_timeout_seconds": config.ping_timeout_seconds,
    })

    failure_count = 0

    while True:
        any_reachable = check_connectivity(config.ping_targets, config.ping_timeout_seconds)

        if any_reachable:
            failure_count = 0
            write_health_status(healthy=True)
            log("info", "check_complete", all_failed=False, failure_count=failure_count)
        else:
            failure_count += 1
            write_health_status(healthy=False)
            level = "warn" if failure_count < config.failure_threshold else "error"
            log(level, "check_complete", all_failed=True, failure_count=failure_count)

            if failure_count >= config.failure_threshold:
                execute_action()

                # Enter cooldown
                log("info", "cooldown_started", duration_seconds=config.cooldown_seconds)
                time.sleep(config.cooldown_seconds)
                log("info", "cooldown_complete")

                # Reset after cooldown
                failure_count = 0
                write_health_status(healthy=False)  # Still unhealthy until next successful check
                continue  # Skip the normal sleep, go straight to next check

        time.sleep(config.check_interval_seconds)


if __name__ == "__main__":
    main()
```

**Step 2: Test main loop (briefly)**

Run: `PING_TARGETS="8.8.8.8" CHECK_INTERVAL_SECONDS=5 python3 src/main.py`
Expected: Logs startup, then check cycles every 5 seconds. Ctrl+C to stop.

**Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: implement main monitoring loop"
```

---

### Task 8: Dockerfile

**Files:**
- Create: `Dockerfile`

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

# Install iputils-ping for ping command
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy application
COPY src/main.py .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=1 \
    CMD cat /tmp/health_status 2>/dev/null | grep -q "healthy" || exit 1

# Switch to non-root user
USER appuser

ENTRYPOINT ["python3", "main.py"]
```

**Step 2: Build and test image**

Run: `docker build -t internet-check .`
Expected: Builds successfully

Run: `docker run --rm -e PING_TARGETS="8.8.8.8,1.1.1.1" internet-check`
Expected: JSON logs showing startup and check cycles. Ctrl+C to stop.

**Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile"
```

---

### Task 9: Docker Compose Example

**Files:**
- Create: `docker-compose.yml`
- Create: `example-action.sh`

**Step 1: Create example action script**

```bash
#!/bin/bash
# Example failure action script
# This template shows how to SSH to a device and reboot it
# Customize for your specific use case

echo "Action triggered at $(date)"

# Example: SSH reboot (uncomment and customize)
# ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 user@192.168.1.1 "reboot"

# Example: Send notification via curl (uncomment and customize)
# curl -X POST https://ntfy.sh/your-topic -d "Internet down - rebooting modem"

echo "Action completed"
```

**Step 2: Create docker-compose.yml**

```yaml
services:
  internet-check:
    build: .
    container_name: internet-check
    restart: unless-stopped
    environment:
      - PING_TARGETS=8.8.8.8,1.1.1.1,9.9.9.9
      - CHECK_INTERVAL_SECONDS=30
      - FAILURE_THRESHOLD=3
      - COOLDOWN_SECONDS=300
      - PING_TIMEOUT_SECONDS=5
    volumes:
      - ./example-action.sh:/action.sh:ro
    # Uncomment if your action script needs SSH access:
    # - ~/.ssh/id_rsa:/home/appuser/.ssh/id_rsa:ro
```

**Step 3: Make example script executable and test**

Run: `chmod +x example-action.sh`
Run: `docker compose up --build`
Expected: Container starts, logs health checks

**Step 4: Commit**

```bash
git add docker-compose.yml example-action.sh
git commit -m "feat: add docker-compose example and sample action script"
```

---

### Task 10: README

**Files:**
- Create: `README.md`

**Step 1: Create README**

```markdown
# Internet Health Check

A lightweight Docker container that monitors internet connectivity and executes a custom action when connectivity is lost.

## Quick Start

1. Create your action script:

```bash
#!/bin/bash
# Runs when internet connectivity is lost
ssh user@192.168.1.1 "reboot"
```

2. Run the container:

```bash
docker run -d \
  -e PING_TARGETS="8.8.8.8,1.1.1.1,9.9.9.9" \
  -v /path/to/your/action.sh:/action.sh:ro \
  internet-check
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PING_TARGETS` | Yes | - | Comma-separated IPs to ping |
| `CHECK_INTERVAL_SECONDS` | No | `30` | Seconds between connectivity checks |
| `FAILURE_THRESHOLD` | No | `3` | Consecutive failures before action triggers |
| `COOLDOWN_SECONDS` | No | `300` | Seconds to wait after action before resuming checks |
| `PING_TIMEOUT_SECONDS` | No | `5` | Timeout for each ping |

## How It Works

1. Pings all configured targets
2. If **all** targets fail, increments failure counter
3. If **any** target succeeds, resets failure counter to 0
4. When failure counter reaches threshold, executes `/action.sh`
5. Enters cooldown period, then resumes monitoring

## Docker Compose

```yaml
services:
  internet-check:
    build: .
    restart: unless-stopped
    environment:
      - PING_TARGETS=8.8.8.8,1.1.1.1,9.9.9.9
      - CHECK_INTERVAL_SECONDS=30
      - FAILURE_THRESHOLD=3
      - COOLDOWN_SECONDS=300
    volumes:
      - ./action.sh:/action.sh:ro
      # For SSH-based actions:
      # - ~/.ssh/id_rsa:/home/appuser/.ssh/id_rsa:ro
```

## Health Check

The container reports health status via Docker's HEALTHCHECK:

- **Healthy**: At least one target was reachable on last check
- **Unhealthy**: All targets failed or container is in cooldown

```bash
docker ps  # Shows health status
docker inspect --format='{{.State.Health.Status}}' internet-check
```

## Logging

JSON structured logs to stdout:

```json
{"ts":"2024-02-05T12:30:00Z","level":"info","event":"startup","config":{...}}
{"ts":"2024-02-05T12:30:01Z","level":"info","event":"check_result","target":"8.8.8.8","success":true,"latency_ms":12}
{"ts":"2024-02-05T12:30:01Z","level":"error","event":"action_triggered"}
```

## Example Action Scripts

### SSH Reboot

```bash
#!/bin/bash
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 admin@192.168.1.1 "reboot"
```

### Notification Only

```bash
#!/bin/bash
curl -X POST https://ntfy.sh/my-alerts -d "Internet connectivity lost"
```

### Multiple Actions

```bash
#!/bin/bash
curl -X POST https://ntfy.sh/my-alerts -d "Internet down - rebooting modem"
sleep 2
ssh admin@192.168.1.1 "reboot"
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

## Final Verification

Run through complete workflow:

```bash
# Build
docker compose build

# Run with real targets (should stay healthy)
docker compose up -d
docker logs -f internet-check

# Check health
docker ps

# Stop
docker compose down
```
