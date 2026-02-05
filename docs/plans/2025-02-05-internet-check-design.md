# Internet Health Check Container Design

## Overview

A lightweight Docker container that monitors internet connectivity by pinging multiple targets, and executes a user-provided script when connectivity is lost.

## Use Case

SFP modules (and similar network devices) occasionally lose internet connectivity and need to be rebooted. This container automates the detection and recovery process.

## Core Behavior

The container runs a continuous loop:

1. **Check phase**: Ping all configured target IPs
2. **Evaluate**: If ALL targets fail, increment failure counter; if ANY succeed, reset counter to 0
3. **Act**: If failure counter reaches threshold, execute the mounted failure script and enter cooldown
4. **Cooldown**: Sleep for configured duration, then reset failure counter and resume checking
5. **Wait**: Sleep for configured interval, repeat

## Configuration

All configuration via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PING_TARGETS` | Yes | - | Comma-separated IPs to ping (e.g., `8.8.8.8,1.1.1.1,9.9.9.9`) |
| `CHECK_INTERVAL_SECONDS` | No | `30` | Time between checks |
| `FAILURE_THRESHOLD` | No | `3` | Consecutive failures before action triggers |
| `COOLDOWN_SECONDS` | No | `300` | Wait time after action executes |
| `PING_TIMEOUT_SECONDS` | No | `5` | Timeout for each ping |

## Failure Action

The failure script is mounted at `/action.sh` and must be executable. The container executes it when the failure threshold is reached. The script receives no arguments and should handle its own logic (SSH commands, webhooks, etc.).

## JSON Logging

All output to stdout as newline-delimited JSON:

```json
{"ts":"2024-02-05T12:30:00Z","level":"info","event":"startup","config":{...}}
{"ts":"2024-02-05T12:30:00Z","level":"info","event":"check_started","targets":["8.8.8.8","1.1.1.1"]}
{"ts":"2024-02-05T12:30:01Z","level":"info","event":"check_result","target":"8.8.8.8","success":true,"latency_ms":12}
{"ts":"2024-02-05T12:30:01Z","level":"info","event":"check_result","target":"1.1.1.1","success":false,"error":"timeout"}
{"ts":"2024-02-05T12:30:01Z","level":"info","event":"check_complete","all_failed":false,"failure_count":0}
{"ts":"2024-02-05T12:30:01Z","level":"warn","event":"check_complete","all_failed":true,"failure_count":2}
{"ts":"2024-02-05T12:30:01Z","level":"error","event":"action_triggered","failure_count":3}
{"ts":"2024-02-05T12:30:05Z","level":"info","event":"action_complete","exit_code":0,"duration_ms":4200}
{"ts":"2024-02-05T12:30:05Z","level":"info","event":"cooldown_started","duration_seconds":300}
{"ts":"2024-02-05T12:35:05Z","level":"info","event":"cooldown_complete"}
```

## Docker Healthcheck

The container reports health based on connectivity status:

| Container State | Health Status |
|-----------------|---------------|
| Starting up (no checks yet) | Unhealthy |
| Last check: at least one target reachable | Healthy |
| Last check: all targets failed | Unhealthy |
| In cooldown after action | Unhealthy |

Implementation: Container writes state to `/tmp/health_status`, Dockerfile HEALTHCHECK reads it.

## Project Structure

```
internet-check/
├── Dockerfile
├── docker-compose.yml      # Example usage
├── src/
│   └── main.py            # All logic in single file
├── example-action.sh      # Sample failure script
└── README.md
```

## Technical Choices

- **Python 3.12 slim**: Small image, stdlib sufficient
- **No pip dependencies**: subprocess for ping, json for logging
- **Single file**: ~150 lines, simple enough not to split
- **Non-root user**: Security best practice
