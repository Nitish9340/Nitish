# One-shot Windows setup: installs the tools HyperFrames needs, clones this
# repo, then starts Claude Code with the reel-style editing task.
#
# Run in PowerShell:
#   irm https://raw.githubusercontent.com/Nitish9340/Nitish/claude/hyperframes-video-setup-ipg9kg/scripts/setup-windows.ps1 | iex
# (or download this file and run:  powershell -ExecutionPolicy Bypass -File setup-windows.ps1)

$ErrorActionPreference = 'Stop'

$RepoUrl = 'https://github.com/Nitish9340/Nitish.git'
$Branch  = 'claude/hyperframes-video-setup-ipg9kg'
$RepoDir = 'D:\Nitish'
$RawDir  = 'D:\Build Fast With AI Files\October\5_10_26\286_5_10_26_FDE_Video\Assets\1. Videos\1. Raw Videos'

function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
              [Environment]::GetEnvironmentVariable('Path', 'User') + ';' +
              "$env:USERPROFILE\.local\bin"
}

function Ensure-Tool($Command, $WingetId) {
  if (Get-Command $Command -ErrorAction SilentlyContinue) { Write-Host "  ok  $Command"; return }
  Write-Host "  installing $WingetId ..."
  winget install --id $WingetId -e --accept-source-agreements --accept-package-agreements
  Refresh-Path
  if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
    throw "$Command still not found after installing $WingetId. Close PowerShell, open a new one, and run this script again."
  }
}

Write-Host "`n[1/5] Tools" -ForegroundColor Cyan
Refresh-Path
Ensure-Tool git    Git.Git
Ensure-Tool node   OpenJS.NodeJS.LTS
Ensure-Tool ffmpeg Gyan.FFmpeg

$nodeMajor = [int]((node -v).TrimStart('v').Split('.')[0])
if ($nodeMajor -lt 22) {
  Write-Host "  Node $nodeMajor is too old (need 22+), upgrading ..."
  winget upgrade --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
  Refresh-Path
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  Write-Host "  installing Claude Code ..."
  Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
  Refresh-Path
}
Write-Host "  ok  claude"

Write-Host "`n[2/5] Repo -> $RepoDir" -ForegroundColor Cyan
if (Test-Path "$RepoDir\.git") {
  git -C $RepoDir fetch origin $Branch
  git -C $RepoDir checkout $Branch
  git -C $RepoDir pull --ff-only origin $Branch
} else {
  git clone -b $Branch $RepoUrl $RepoDir
}

Write-Host "`n[3/5] HyperFrames renderer (headless Chrome)" -ForegroundColor Cyan
Set-Location $RepoDir
# npx.cmd, not npx: the .ps1 shim is blocked under the default execution policy.
npx.cmd --yes hyperframes@latest browser ensure
npx.cmd --yes hyperframes@latest doctor

Write-Host "`n[4/5] Input files" -ForegroundColor Cyan
$reel = Get-ChildItem "$env:USERPROFILE\Downloads\*" -Include *.mp4, *.mov -File |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($reel) {
  $answer = Read-Host "  Reference reel = '$($reel.Name)' (newest video in Downloads). Use it? [Y/n]"
  $ReelPath = if ($answer -match '^[nN]') { (Read-Host '  Full path to the reference reel').Trim('"') } else { $reel.FullName }
} else {
  $ReelPath = (Read-Host '  No video found in Downloads. Full path to the reference reel').Trim('"')
}
if (-not (Test-Path $ReelPath)) { throw "Reference reel not found: $ReelPath" }

if (-not (Test-Path $RawDir)) {
  $RawDir = (Read-Host "  Raw video folder not found. Full path to it").Trim('"')
  if (-not (Test-Path $RawDir)) { throw "Raw video folder not found: $RawDir" }
}
$raws = Get-ChildItem $RawDir -File | Where-Object { $_.Extension -match '^\.(mp4|mov|mkv|m4v|avi)$' }
Write-Host "  raw clips: $($raws.Count) in $RawDir"
$raws | ForEach-Object { Write-Host "    - $($_.Name)" }

Write-Host "`n[5/5] Starting Claude Code ..." -ForegroundColor Cyan
# Single line, no double quotes: Windows PowerShell 5.1 mangles embedded quotes in native-command arguments.
$prompt = "Using /hyperframes: decode the editing style of the reference reel at '$ReelPath' - cuts, pacing, captions, motion graphics, transitions, music and sound effects - and write the breakdown down first. Then edit my raw footage in '$RawDir' in the same style and with the same energy, as a 9:16 Reel. Keep my content original, but make the editing, motion and sound feel equally engaging and professional. Render the final MP4 and tell me where it is."
claude $prompt
