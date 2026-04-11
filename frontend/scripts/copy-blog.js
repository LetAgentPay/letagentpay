/**
 * Copy blog markdown files into public/blog/ for build-time rendering.
 *
 * Source of truth: docs/internal/blog/*.md (monorepo)
 * After sync_repos.sh: docs/internal/blog/*.md (enterprise repo)
 *
 * If files already exist in public/blog/ (e.g. copied by CI before Docker build),
 * they are NOT overwritten.
 */
const fs = require("fs");
const path = require("path");

const candidates = [
  "../docs/internal/blog",
  "../docs/blog",
];

const outDir = path.join(__dirname, "..", "public", "blog");
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

let srcDir = null;
for (const candidate of candidates) {
  const abs = path.join(__dirname, "..", candidate);
  if (fs.existsSync(abs)) {
    srcDir = abs;
    break;
  }
}

if (!srcDir) {
  console.log("No blog source directory found, skipping blog copy");
  process.exit(0);
}

const files = fs.readdirSync(srcDir).filter((f) => f.endsWith(".md") && !f.includes("-external"));

for (const file of files) {
  const destPath = path.join(outDir, file);

  if (fs.existsSync(destPath) && fs.statSync(destPath).size > 200) {
    console.log(`Skipping blog/${file} — already exists (${fs.statSync(destPath).size} bytes)`);
    continue;
  }

  fs.copyFileSync(path.join(srcDir, file), destPath);
  console.log(`Copied blog/${file} → public/blog/${file}`);
}
