# Video workspace (HyperFrames)

This repo is for making and editing videos with [HyperFrames](https://github.com/heygen-com/hyperframes):
compositions are HTML + CSS + GSAP, rendered to MP4 by headless Chrome + FFmpeg.

## Start here

- **Always load the `/hyperframes` skill first** for any video request (make, edit, caption, recut,
  animate, render). It routes to the right workflow. All 21 HyperFrames skills are committed in
  `.agents/skills/` (symlinked from `.claude/skills/`), so no install step is needed.
- Each video is its own project in `videos/<name>/`. That project's own `CLAUDE.md` (written by
  `hyperframes init`) has the per-project commands. `videos/hello-world/` is a minimal working sample.

## Creating a project

Use the wrapper, not bare `hyperframes init`. It makes the project renderable in cloud sessions:

```bash
scripts/new-video.sh <name>                          # blank 1920x1080
scripts/new-video.sh <name> --resolution portrait    # 1080x1920 (Reels/Shorts/TikTok)
scripts/new-video.sh <name> --video path/to/in.mp4 --skip-transcribe   # edit existing footage
scripts/new-video.sh <name> -e warm-grain            # start from an example template
```

Then, inside `videos/<name>/`: `npm run check` (lint, runtime, layout, contrast), then `npm run render`.
Output goes to `videos/<name>/renders/*.mp4`.

## Cloud session constraints (important)

The cloud environment's network policy blocks some hosts that HyperFrames uses by default:

| Blocked | Effect | What to do |
| --- | --- | --- |
| `cdn.jsdelivr.net`, `unpkg.com`, `cdnjs.cloudflare.com` | GSAP / Lottie / etc. fail to load: `sub_timeline_script_failure`, frozen timeline | **After any edit that adds a CDN `<script>`** (templates, `hyperframes add` blocks, or your own code), run `node scripts/vendor-cdn.mjs videos/<name>`. It copies the file from npm into `vendor/` and rewrites the URL. Use `--check` to list leftovers. |
| `huggingface.co` | `hyperframes transcribe` and local TTS can't download models | Pass `--skip-transcribe` to `init --video`. Ask the user for an `.srt`/`.vtt`/`.json` transcript and import it with `npx hyperframes transcribe <file>`, or have them allow `huggingface.co` in the environment's network settings. |
| Arbitrary image/font hosts | Remote images 404 at render time | Download assets into the project's `assets/` folder and reference them locally. |

npm, GitHub (`raw.githubusercontent.com`, used by `hyperframes add`), and Google Fonts work.
Asset paths inside a project must be relative to the **project root** (no `../`), even in
`compositions/*.html`.

## Delivering renders

- `renders/` is gitignored. When the user wants to keep a render, copy it to `exports/<name>.mp4`
  and commit it (GitHub rejects files over 100 MB; for longer videos, render at lower quality or
  tell the user).
- Send the finished MP4 to the user with `SendUserFile` so they can watch it right away.
- Input footage the user provides lives in the project folder (`init --video` copies it there).
