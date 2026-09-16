'use strict';

/* Emit an apply_patch document; this tool never writes a canonical source. */
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const SOURCE_DIR = path.join(ROOT, 'stage2_highdensity_dataset', 'sources', 'train');
const PLAN_PATH = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06', 'A06_Semantic_Rewrite_Plan_v16_v52_2026-09-16.json');
function fail(message) { throw new Error(message); }
function args(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) fail(`unexpected argument ${token}`);
    const key = token.slice(2);
    const value = argv[i + 1];
    if (value === undefined || value.startsWith('--')) fail(`missing value for --${key}`);
    out[key] = value;
    i += 1;
  }
  return out;
}
const options = args(process.argv.slice(2));
if (!options.version) fail('--version is required');
const version = Number(options.version);
if (!Number.isInteger(version) || version < 16 || version > 52) fail('--version must be 16..52');
const plan = JSON.parse(fs.readFileSync(PLAN_PATH, 'utf8'));
const rows = plan.rows.filter((row) => row.version === version);
if (!rows.length) fail(`no plan rows for v${version}`);
const canonical = path.join(SOURCE_DIR, `stage2_(16)relational_composition_high_density_train_v${version}.source.psv`);
const targetFile = options['target-file'] ? path.resolve(options['target-file']) : canonical;
const text = fs.readFileSync(targetFile, 'utf8');
const lines = text.split(/\r\n|\n|\r/u);
if (lines.at(-1) === '') lines.pop();
const patchFile = targetFile.replace(/\\/gu, '/');
let patch = `*** Begin Patch\n*** Update File: ${patchFile}\n`;
const offset = options.offset ? Number(options.offset) : 0;
if (!Number.isInteger(offset) || offset < 0 || offset >= rows.length) fail('--offset is invalid');
const limit = options.limit ? Number(options.limit) : Math.min(60, rows.length - offset);
if (!Number.isInteger(limit) || limit < 1 || offset + limit > rows.length) fail('--limit is invalid');
for (const row of rows.slice(offset, offset + limit)) {
  const actual = lines[row.source_line - 1];
  if (actual !== row.old_line) fail(`${row.source_file}:${row.source_line}: precondition old line mismatch`);
  const count = lines.filter((line) => line === row.old_line).length;
  if (count !== 1) fail(`${row.source_file}:${row.source_line}: old line occurs ${count} times`);
  if (row.new_line.includes('\r') || row.new_line.includes('\n')) fail(`${row.source_file}:${row.source_line}: newline in replacement`);
  patch += `@@\n-${row.old_line}\n+${row.new_line}\n`;
}
patch += '*** End Patch\n';
process.stdout.write(patch);
