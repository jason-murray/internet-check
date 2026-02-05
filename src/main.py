#!/usr/bin/env python3
"""Internet connectivity health checker with failure action."""

import json
import os
import sys
from dataclasses import dataclass
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
