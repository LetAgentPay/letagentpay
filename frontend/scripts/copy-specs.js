/**
 * Copy ASPS spec markdown files into public/asps/ for build-time rendering.
 *
 * Source of truth: docs/core/docs/*.md (monorepo)
 * After sync_repos.sh: docs/*.md (public repo)
 *
 * Tries both paths — monorepo first, then public repo layout.
 * Build-time copies are gitignored.
 */
const fs = require("fs");
const path = require("path");

const specs = [
  {
    name: "v1-spec.md",
    candidates: [
      "../docs/core/docs/agent_spending_policy_spec.md",
      "../docs/agent_spending_policy_spec.md",
    ],
  },
  {
    name: "v2-spec.md",
    candidates: [
      "../docs/core/docs/mission_policy_spec.md",
      "../docs/mission_policy_spec.md",
    ],
  },
];

const outDir = path.join(__dirname, "..", "public", "asps");
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

for (const { name, candidates } of specs) {
  const destPath = path.join(outDir, name);
  let found = false;

  for (const candidate of candidates) {
    const srcPath = path.join(__dirname, "..", candidate);
    if (fs.existsSync(srcPath)) {
      fs.copyFileSync(srcPath, destPath);
      console.log(`Copied ${candidate} → public/asps/${name}`);
      found = true;
      break;
    }
  }

  if (!found) {
    console.warn(`Warning: no source found for ${name}, creating placeholder`);
    fs.writeFileSync(destPath, `# ${name}\n\nSpecification not available in this build.\n`);
  }
}
