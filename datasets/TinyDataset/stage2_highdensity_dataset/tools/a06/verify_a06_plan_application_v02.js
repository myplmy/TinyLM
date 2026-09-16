'use strict';

/* Read-only check of a plan against the current source rows. */
const fs = require('node:fs');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..', '..', '..');
const PLAN_PATH = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06', 'A06_Semantic_Rewrite_Plan_v16_v52_2026-09-16.json');
const SOURCE_DIR = path.join(ROOT, 'stage2_highdensity_dataset', 'sources', 'train');
const plan = JSON.parse(fs.readFileSync(PLAN_PATH, 'utf8'));
const byVersion = new Map();
for (const row of plan.rows) {
  if (!byVersion.has(row.version)) byVersion.set(row.version, []);
  byVersion.get(row.version).push(row);
}
const result = [];
for (const [version, rows] of byVersion) {
  const file = rows[0].source_file;
  const lines = fs.readFileSync(path.join(SOURCE_DIR, file), 'utf8').split(/\r\n|\n|\r/u);
  if (lines.at(-1) === '') lines.pop();
  let applied = 0; let pending = 0; let mismatch = 0;
  const samples = [];
  for (const row of rows) {
    const actual = lines[row.source_line - 1];
    if (actual === row.new_line) applied += 1;
    else if (actual === row.old_line) pending += 1;
    else { mismatch += 1; if (samples.length < 8) samples.push({ source_line: row.source_line, actual: actual ? actual.slice(0, 160) : null, expected_old: row.old_line.slice(0, 160), expected_new: row.new_line.slice(0, 160) }); }
  }
  result.push({ version, file, rows: rows.length, applied, pending, mismatch, samples });
}
result.sort((a, b) => a.version - b.version);
process.stdout.write(`${JSON.stringify({ plan_rows: plan.rows.length, result }, null, 2)}\n`);
