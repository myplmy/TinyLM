/* Apply the fixed record-by-record rewrites for the last A04 repeat5 greedy set. */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const toolDir = path.join(root, 'stage2_highdensity_dataset', 'tools');
const reportPath = path.join(root, 'stage2_highdensity_dataset', 'audit_reports', 'machine',
  'TinyLM_Stage2_A04_Residual_Repeat5_After_Greedy219_2026-09-10.json');
const expectedSourceSet = 'b2d7a661c8199fd7a55f74d47785c4fdcb9077571f1c0e00111d7f2fbe7d4831';
const apply = process.argv.includes('--apply');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const sourcePattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;

const sourceFiles = fs.readdirSync(sourceDir).filter(file => sourcePattern.test(file)).sort();
const sourceSet = sha256(sourceFiles.map(file => sha256(fs.readFileSync(path.join(sourceDir, file)))).join(''));
if (sourceSet !== expectedSourceSet) throw new Error(`source-set drift: expected ${expectedSourceSet}, got ${sourceSet}`);
const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
if (report.greedy_rewrite_rows_to_leave_one_occurrence_each !== 20) throw new Error('last greedy target count drift');
const expected = new Set(report.greedy_rewrite_set.map(row => `${row.version}:${row.line}`));
const edits = require(path.join(toolDir, 'repair_a04_post_greedy20_data.js'));
const seen = new Set();
const byVersion = new Map();
for (const edit of edits) {
  if (!Array.isArray(edit) || edit.length !== 3) throw new Error(`invalid tuple: ${JSON.stringify(edit)}`);
  const [version, line, text] = edit;
  const key = `${version}:${line}`;
  if (seen.has(key) || !expected.has(key)) throw new Error(`duplicate/outside target: ${key}`);
  if (typeof text !== 'string' || text.length < 45 || text.length > 170 || !/[.!?]$/.test(text)) throw new Error(`bad text shape ${key}`);
  seen.add(key);
  if (!byVersion.has(version)) byVersion.set(version, []);
  byVersion.get(version).push({line, text});
}
if (edits.length !== 20 || seen.size !== 20) throw new Error(`fixed edit count must be 20, got ${edits.length}`);
const missing = [...expected].filter(key => !seen.has(key));
if (missing.length) throw new Error(`missing targets: ${missing.join(', ')}`);

const buffers = new Map();
for (const [version, list] of byVersion) {
  const file = sourceFiles.find(name => Number(name.match(sourcePattern)[1]) === version);
  const target = path.join(sourceDir, file);
  const rows = fs.readFileSync(target, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  for (const {line, text} of list) {
    const row = rows[line - 1];
    if (!text.includes(row.primary)) throw new Error(`primary lost ${version}:${line}`);
    if (text === row.text) throw new Error(`unchanged ${version}:${line}`);
    rows[line - 1] = {...row, text};
  }
  buffers.set(target, rows.map(JSON.stringify).join('\n') + '\n');
}
if (apply) for (const [target, content] of buffers) fs.writeFileSync(target, content, 'utf8');
console.log(JSON.stringify({mode: apply ? 'APPLIED' : 'PREVIEW', source_set_before: sourceSet,
  repaired_records: edits.length,
  counts_by_version: Object.fromEntries([...byVersion].sort((a,b)=>a[0]-b[0]).map(([v,a])=>[v,a.length]))}, null, 2));
