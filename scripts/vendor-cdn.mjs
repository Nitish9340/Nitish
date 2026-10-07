#!/usr/bin/env node
// Replace CDN <script>/<link> URLs in a HyperFrames project with local copies.
//
// Claude Code cloud sessions block jsdelivr/unpkg/cdnjs, so headless Chrome
// can't load GSAP & co. during `check`/`render`. The npm registry IS
// reachable, so we `npm pack` each referenced package, copy the referenced
// file into <project>/vendor/<pkg>@<version>/<path>, and rewrite the URL to a
// project-root-relative path (HyperFrames resolves sub-composition asset paths
// against the project root, and its linter rejects "../"). Idempotent.
//
// Usage: node scripts/vendor-cdn.mjs <project-dir> [--check]
//   --check  only list CDN URLs still present; exit 1 if any remain

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const args = process.argv.slice(2);
const checkOnly = args.includes("--check");
const projectDir = path.resolve(args.find((a) => !a.startsWith("--")) ?? ".");

if (!fs.existsSync(path.join(projectDir, "index.html"))) {
  console.error(`No index.html in ${projectDir} — pass a HyperFrames project directory.`);
  process.exit(2);
}

// cdnjs library names that map 1:1 onto npm packages (cdnjs path -> npm dist path).
const CDNJS_TO_NPM = {
  gsap: (file) => ({ pkg: "gsap", file: `dist/${file}` }),
  "lottie-web": (file) => ({ pkg: "lottie-web", file: `build/player/${file}` }),
  "animejs": (file) => ({ pkg: "animejs", file: `lib/${file}` }),
};

const URL_RE =
  /https:\/\/(?:cdn\.jsdelivr\.net\/npm\/|unpkg\.com\/|cdnjs\.cloudflare\.com\/ajax\/libs\/)[^"'`\s)]+/g;

function parse(url) {
  const u = new URL(url);
  if (u.hostname === "cdnjs.cloudflare.com") {
    const [, , , lib, version, ...rest] = u.pathname.split("/");
    const map = CDNJS_TO_NPM[lib];
    if (!map || !rest.length) return null;
    const { pkg, file } = map(rest.join("/"));
    return { pkg, version, file };
  }
  let p = u.pathname.replace(/^\/npm\//, "/").slice(1);
  const scoped = p.startsWith("@");
  const parts = p.split("/");
  const nameVer = scoped ? `${parts[0]}/${parts[1]}` : parts[0];
  const file = parts.slice(scoped ? 2 : 1).join("/");
  const at = nameVer.lastIndexOf("@");
  if (at <= 0) return null; // unpinned version — can't vendor reproducibly
  const pkg = nameVer.slice(0, at);
  const version = nameVer.slice(at + 1);
  if (!file || file.endsWith("+esm") || u.search) return null;
  return { pkg, version, file };
}

const packCache = new Map();
function fetchPackage(pkg, version) {
  const key = `${pkg}@${version}`;
  if (packCache.has(key)) return packCache.get(key);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "hf-vendor-"));
  const tgz = execFileSync("npm", ["pack", key, "--silent", "--pack-destination", tmp], {
    encoding: "utf8",
  })
    .trim()
    .split("\n")
    .pop();
  execFileSync("tar", ["-xzf", path.join(tmp, tgz), "-C", tmp]);
  const dir = path.join(tmp, "package");
  packCache.set(key, dir);
  return dir;
}

function htmlFiles(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (["node_modules", "vendor", "renders", ".git"].includes(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...htmlFiles(full));
    else if (entry.name.endsWith(".html")) out.push(full);
  }
  return out;
}

let remaining = 0;
let vendored = 0;
for (const file of htmlFiles(projectDir)) {
  let html = fs.readFileSync(file, "utf8");
  const urls = [...new Set(html.match(URL_RE) ?? [])];
  if (!urls.length) continue;
  for (const url of urls) {
    const rel = path.relative(projectDir, file);
    const spec = parse(url);
    if (checkOnly || !spec) {
      remaining++;
      console.log(`${checkOnly ? "CDN" : "SKIP (vendor by hand)"}  ${rel}: ${url}`);
      continue;
    }
    // Version may be a range like "3" — resolve to the exact packed version.
    const pkgDir = fetchPackage(spec.pkg, spec.version);
    const exact = JSON.parse(fs.readFileSync(path.join(pkgDir, "package.json"), "utf8")).version;
    const src = path.join(pkgDir, spec.file);
    if (!fs.existsSync(src)) {
      remaining++;
      console.log(`SKIP (file not in npm package)  ${rel}: ${url}`);
      continue;
    }
    const dest = path.join(projectDir, "vendor", `${spec.pkg}@${exact}`, spec.file);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
    const local = path.relative(projectDir, dest).split(path.sep).join("/");
    html = html.split(url).join(local);
    vendored++;
    console.log(`vendored  ${rel}: ${url} -> ${local}`);
  }
  if (!checkOnly) fs.writeFileSync(file, html);
}

console.log(
  checkOnly
    ? `${remaining} CDN reference(s) remaining.`
    : `${vendored} reference(s) vendored, ${remaining} left for manual handling.`,
);
process.exit(remaining ? 1 : 0);
