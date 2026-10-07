#!/bin/bash
# Prepare a Claude Code cloud session for HyperFrames: cache the CLI and the
# Chrome Headless Shell it renders with. FFmpeg is preinstalled in the image.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Pre-warm the npx cache so the first `npx hyperframes ...` is instant.
npx --yes hyperframes@latest --version >/dev/null

# Download Chrome Headless Shell (no-op when already cached).
npx --yes hyperframes@latest browser ensure >/dev/null

echo "HyperFrames ready: $(npx --yes hyperframes@latest --version 2>/dev/null | head -1)"
