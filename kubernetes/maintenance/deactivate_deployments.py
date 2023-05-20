#!/usr/bin/env python3

import os
import subprocess

deployments = [
"../apps/unifi-controller/resources/unifi-controller.deployment.yaml",
"../apps/bitwarden/resources/bitwarden.deployment.yaml",
"../apps/jackett/resources/jackett.deployment.yaml",
"../apps/transmission/resources/transmission.deployment.yaml",
"../apps/radarr/resources/radarr.deployment.yaml",
"../apps/home-assistant/resources/home-assistant-deployment.yaml",
"../apps/lidarr/resources/lidarr.deployment.yaml",
"../apps/plex/resources/plex.deployment.yaml",
"../apps/sonarr/resources/sonarr-deployment.yaml",
"../apps/logitech-media-server/resources/lms.deployment.yaml",
]
cmd = ["kubectl","apply"]
for d in deployments:
    cmd.append("-f")
    cmd.append(d)

subprocess.run(cmd)