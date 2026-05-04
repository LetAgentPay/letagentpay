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

// Copy markdown files.
//
// Convention: each post has two files in the source directory:
//   <slug>.md           — internal draft (planning notes, tone decisions, etc.)
//   <slug>-external.md  — public-facing version (the one we ship to readers)
//
// Rules:
//   - If <slug>-external.md exists → copy it to public/blog/<slug>.md (without
//     the suffix) and IGNORE the internal <slug>.md, even if present.
//   - If only <slug>.md exists (no external twin) → copy it as-is. Covers older
//     posts where the external content was merged back into the canonical file.
//
// This prevents leaks of internal drafts when both files are present.
const allMd = fs.readdirSync(srcDir).filter((f) => f.endsWith(".md"));
const externalSlugs = new Set(
  allMd
    .filter((f) => f.endsWith("-external.md"))
    .map((f) => f.replace(/-external\.md$/, ""))
);

const toCopy = [];
for (const file of allMd) {
  if (file.endsWith("-external.md")) {
    const slug = file.replace(/-external\.md$/, "");
    toCopy.push({ src: file, dest: `${slug}.md` });
  } else {
    const slug = file.replace(/\.md$/, "");
    if (!externalSlugs.has(slug)) {
      toCopy.push({ src: file, dest: file });
    }
  }
}

for (const { src, dest } of toCopy) {
  const destPath = path.join(outDir, dest);

  if (fs.existsSync(destPath) && fs.statSync(destPath).size > 200) {
    console.log(`Skipping blog/${dest} — already exists (${fs.statSync(destPath).size} bytes)`);
    continue;
  }

  fs.copyFileSync(path.join(srcDir, src), destPath);
  console.log(`Copied blog/${src} → public/blog/${dest}`);
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
