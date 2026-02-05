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
