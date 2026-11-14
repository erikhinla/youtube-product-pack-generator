#!/usr/bin/env bash
# VPS setup for the RevAnew content machine. Idempotent.
set -euo pipefail

echo "== python deps =="
pip3 install --break-system-packages youtube-transcript-api 2>/dev/null || pip3 install youtube-transcript-api

echo "== ffmpeg present? =="
command -v ffmpeg || { echo "install ffmpeg with apt"; exit 1; }

echo "== blender (video lane, optional) =="
if command -v blender &>/dev/null || [ -x /opt/blender/blender ]; then
  echo "blender already present"
else
  echo "run 01_SCRIPTS/install-blender.sh to add the Blender render lane"
fi

echo "== keys =="
ENVF="$(dirname "$0")/../02_AUTOMATION/revanew_pipeline/.env"
[ -f "$ENVF" ] || { echo "no .env yet: cp .env.example .env and fill over SSH, never paste keys in chat"; }

echo "setup complete"
