# Video workspace

Make and edit videos by chatting with Claude Code, powered by
[HyperFrames](https://github.com/heygen-com/hyperframes) (HTML → MP4).

## Use it

Open this repo in Claude Code (web or CLI) and ask, for example:

- "Using /hyperframes, make a 15-second portrait promo for https://example.com"
- "Add captions to `videos/interview/interview.mp4`" (attach an `.srt` if you have one)
- "Make a 6-second logo sting with our brand colors"
- "Change the title in `videos/hello-world` to 'Launch day' and re-render"

Claude will create a project under `videos/<name>/`, preview it, and render an MP4.

## What's set up

| Path | Purpose |
| --- | --- |
| `.agents/skills/`, `.claude/skills/` | All HyperFrames agent skills (`/hyperframes` is the entry point) |
| `.claude/hooks/session-start.sh` | Cloud sessions: caches the HyperFrames CLI and Chrome Headless Shell |
| `scripts/new-video.sh` | Scaffold a project in `videos/` and make it render offline |
| `scripts/vendor-cdn.mjs` | Swap CDN script URLs for local copies (cloud sessions block those CDNs) |
| `videos/hello-world/` | Minimal working sample |
| `exports/` | Finished renders worth keeping |

## Run it yourself

**Windows, one command** (installs Git, Node, FFmpeg, Claude Code, clones this repo, starts the edit):

```powershell
irm https://raw.githubusercontent.com/Nitish9340/Nitish/claude/hyperframes-video-setup-ipg9kg/scripts/setup-windows.ps1 | iex
```

Manual setup:

Requires Node.js 22+ and FFmpeg.

```bash
scripts/new-video.sh my-video
cd videos/my-video
npx hyperframes preview   # live preview in the browser
npm run check             # validate
npm run render            # → renders/*.mp4
```

Update the skills: `npx skills update -p` (tracked in `skills-lock.json`).
