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
