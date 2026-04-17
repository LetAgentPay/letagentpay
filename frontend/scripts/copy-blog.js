/**
 * Copy blog markdown files and cover images into public/blog/ for build-time rendering.
 *
 * Source of truth: docs/internal/blog/*.md + docs/internal/blog/covers/* (monorepo)
 * After sync_repos.sh: docs/internal/blog/*.md + covers/* (enterprise repo)
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

// Copy markdown files (excluding -external versions)
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

// Copy cover images
const coversDir = path.join(srcDir, "covers");
const outCoversDir = path.join(outDir, "covers");

if (fs.existsSync(coversDir)) {
  if (!fs.existsSync(outCoversDir)) {
    fs.mkdirSync(outCoversDir, { recursive: true });
  }

  const covers = fs.readdirSync(coversDir).filter((f) => !f.startsWith("."));

  for (const file of covers) {
    const destPath = path.join(outCoversDir, file);

    if (fs.existsSync(destPath) && fs.statSync(destPath).size > 200) {
      console.log(`Skipping blog/covers/${file} — already exists`);
      continue;
    }

    fs.copyFileSync(path.join(coversDir, file), destPath);
    console.log(`Copied blog/covers/${file} → public/blog/covers/${file}`);
  }
}
