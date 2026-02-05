#!/usr/bin/env python3
"""Internet connectivity health checker with failure action."""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

HEALTH_FILE = "/tmp/health_status"
ACTION_SCRIPT = "/action.sh"


def write_health_status(healthy: bool):
    """Write current health status to file for Docker healthcheck."""
    status = "healthy" if healthy else "unhealthy"
    with open(HEALTH_FILE, "w") as f:
        f.write(status)


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


def log(level: str, event: str, **kwargs):
    """Output a structured JSON log entry."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": level,
        "event": event,
        **kwargs,
    }
    print(json.dumps(entry), flush=True)


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


def main():
    config = load_config()
    log("info", "startup", config={
        "ping_targets": config.ping_targets,
        "check_interval_seconds": config.check_interval_seconds,
        "failure_threshold": config.failure_threshold,
        "cooldown_seconds": config.cooldown_seconds,
        "ping_timeout_seconds": config.ping_timeout_seconds,
    })


if __name__ == "__main__":
    main()
