#!/usr/bin/env node
/**
 * Orphan guard (UI-8) — fail if any source module is unreachable from the app entry points.
 *
 * The strict ESLint gate (`--max-warnings 0`) only flags unused *locals/imports within a file*; it cannot see an
 * exported component/type/util that nothing imports. So dead modules accumulate silently (as the UI-5 v1.0 cleanup
 * found). This walks the static import graph (incl. dynamic `import()`) from src/main.tsx + src/App.tsx and reports
 * any reachable-from-nowhere module. Generated `*.gen.*` files are exempt.
 *
 * Run: `node scripts/find-orphans.mjs` (wired into `npm run check`). Exit 1 if orphans found.
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const SRC = path.join(ROOT, 'src');
const ENTRIES = ['src/main.tsx', 'src/App.tsx'];

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    return e.isDirectory() ? walk(p) : (/\.tsx?$/.test(e.name) ? [p] : []);
  });
}

function resolveSpec(spec, fromFile) {
  let s = spec.startsWith('@/') ? path.join(SRC, spec.slice(2)) : path.normalize(path.join(path.dirname(fromFile), spec));
  for (const cand of [`${s}.tsx`, `${s}.ts`, path.join(s, 'index.ts'), path.join(s, 'index.tsx'), s]) {
    if (fs.existsSync(cand) && fs.statSync(cand).isFile()) return path.normalize(cand);
  }
  return null;
}

const files = walk(SRC).map((f) => path.normalize(f));
const edges = new Map();
const importRe = /from\s+['"](@\/[^'"]+|\.[^'"]+)['"]/;
const dynRe = /import\(\s*['"](@\/[^'"]+|\.[^'"]+)['"]\s*\)/;
for (const f of files) {
  const deps = new Set();
  for (const line of fs.readFileSync(f, 'utf8').split('\n')) {
    if (/^\s*\/\//.test(line)) continue;
    for (const re of [importRe, dynRe]) {
      const m = line.match(re);
      if (m) { const r = resolveSpec(m[1], f); if (r) deps.add(r); }
    }
  }
  edges.set(f, deps);
}

const seen = new Set();
const stack = ENTRIES.map((e) => path.normalize(path.join(ROOT, e)));
while (stack.length) {
  const cur = stack.pop();
  if (seen.has(cur)) continue;
  seen.add(cur);
  for (const d of edges.get(cur) ?? []) stack.push(d);
}

const orphans = files.filter((f) => !seen.has(f) && !/\.gen\./.test(f)).sort();
if (orphans.length) {
  console.error(`✗ ${orphans.length} orphan module(s) unreachable from ${ENTRIES.join(' / ')}:`);
  for (const o of orphans) console.error(`  ${path.relative(ROOT, o)}`);
  console.error('Wire them up, delete them, or (if intentionally an entry) add to ENTRIES in scripts/find-orphans.mjs.');
  process.exit(1);
}
console.log('✓ no orphan modules');
