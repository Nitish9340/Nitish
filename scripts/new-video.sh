#!/usr/bin/env bash
# Scaffold a new HyperFrames project under videos/<name> and make it renderable
# in Claude Code cloud sessions (CDN scripts vendored locally).
#
# Usage: scripts/new-video.sh <name> [extra `hyperframes init` flags]
#   e.g. scripts/new-video.sh launch-teaser --resolution portrait
#        scripts/new-video.sh interview-cut --video ~/in/interview.mp4
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <name> [hyperframes init flags...]" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$1"
shift

mkdir -p "$ROOT/videos"
cd "$ROOT/videos"
if [ -e "$NAME" ]; then
  echo "videos/$NAME already exists" >&2
  exit 1
fi

# Skills are committed under .claude/skills; don't let init re-sync them globally.
HYPERFRAMES_SKIP_SKILLS=1 npx --yes hyperframes@latest init "$NAME" --non-interactive "$@"
node "$ROOT/scripts/vendor-cdn.mjs" "$ROOT/videos/$NAME"

echo
echo "Ready: videos/$NAME"
echo "  cd videos/$NAME && npm run check && npm run render"
