#!/usr/bin/env bash
# Rebuild index.html from the edit sources, then carve the music bed under the voice.
# Needs @hyperframes/core for the carve: pass its install dir as $1 (default: ./node_modules).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 edit/build_edl.py >/dev/null
python3 edit/build_index.py
node ../../.agents/skills/hyperframes-audio/scripts/carve.mjs --comp index.html --bed music --strength 0.5 --core "${1:-.}" | tail -4
