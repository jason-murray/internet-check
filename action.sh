#!/bin/bash
# Example failure action script
# This template shows how to SSH to a device and reboot it
# Customize for your specific use case

echo "Action triggered at $(date)"

# Example: SSH reboot (uncomment and customize)
# ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@192.168.11.1 "reboot"

echo "Action completed"
