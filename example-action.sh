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
