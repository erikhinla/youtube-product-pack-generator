#!/usr/bin/env bash
# Install headless Blender to /opt/blender (idempotent).
set -euo pipefail
if [ -x /opt/blender/blender ]; then echo "blender present: $(/opt/blender/blender --version | head -1)"; exit 0; fi
VER=$(curl -s https://download.blender.org/release/ | grep -oE 'Blender[0-9]+\.[0-9]+/' | sort -V | tail -1 | tr -d '/')
FILE=$(curl -s "https://download.blender.org/release/$VER/" | grep -oE 'blender-[0-9rc.]+-linux-x64\.tar\.xz' | sort -V | tail -1)
echo "installing $FILE"
curl -sL -o /tmp/blender.tar.xz "https://download.blender.org/release/$VER/$FILE"
mkdir -p /opt/blender
tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1
ln -sf /opt/blender/blender /usr/local/bin/blender
blender --version | head -1
