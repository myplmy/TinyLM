/* Apply the fixed, record-by-record editorial rewrites for the A04 repeat5
 * greedy target set captured on 2026-09-10. This runner does not generate
 * prose: every replacement is stored explicitly in the adjacent part files.
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const toolDir = path.join(root, 'stage2_highdensity_dataset', 'tools');
const targetReportPath = path.join(
  root,
  'stage2_highdensity_dataset',
  'audit_reports',
  'machine',
  'TinyLM_Stage2_A04_Residual_Repeat5_Targets_2026-09-10.json'
);
const expectedSourceSet = 'bdb44662ab77ca9e3b1ae9d20e858fc34cf00bf2ac895aa82adc798f9be6c1d4';
const apply = process.argv.includes('--apply');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const sourcePattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const partPattern = /^repair_a04_greedy_1275_part\d+[a-z]*_data\.js$/;

const sourceFiles = fs.readdirSync(sourceDir).filter(file => sourcePattern.test(file)).sort();
const sourceSet = sha256(sourceFiles.map(file => sha256(fs.readFileSync(path.join(sourceDir, file)))).join(''));
if (sourceSet !== expectedSourceSet) {
  throw new Error(`source-set drift: expected ${expectedSourceSet}, got ${sourceSet}`);
}

const targetReport = JSON.parse(fs.readFileSync(targetReportPath, 'utf8'));
if (targetReport.greedy_rewrite_rows_to_leave_one_occurrence_each !== 1275) {
  throw new Error(`target report count drift: ${targetReport.greedy_rewrite_rows_to_leave_one_occurrence_each}`);
}
const expectedKeys = new Set(targetReport.greedy_rewrite_set.map(row => `${row.version}:${row.line}`));
const partFiles = fs.readdirSync(toolDir).filter(file => partPattern.test(file)).sort();
if (!partFiles.length) throw new Error('no fixed editorial part files found');
const edits = partFiles.flatMap(file => require(path.join(toolDir, file)));
const editKeys = new Set();
const byVersion = new Map();
for (const edit of edits) {
  if (!Array.isArray(edit) || edit.length !== 3) throw new Error(`invalid edit tuple: ${JSON.stringify(edit)}`);
  const [version, line, text] = edit;
  const key = `${version}:${line}`;
  if (editKeys.has(key)) throw new Error(`duplicate edit key: ${key}`);
  if (!expectedKeys.has(key)) throw new Error(`edit outside frozen greedy set: ${key}`);
  if (typeof text !== 'string' || text.length < 45 || text.length > 180 || !/[.!?]$/.test(text)) {
    throw new Error(`invalid editorial text shape at ${key}: length=${text && text.length}`);
  }
  if (/\p{Cc}/u.test(text)) throw new Error(`control character in edit ${key}`);
  editKeys.add(key);
  if (!byVersion.has(version)) byVersion.set(version, []);
  byVersion.get(version).push({ line, text });
}
if (edits.length !== 1275 || editKeys.size !== 1275) throw new Error(`fixed edit count must be 1275, got ${edits.length}`);
const missing = [...expectedKeys].filter(key => !editKeys.has(key));
if (missing.length) throw new Error(`missing frozen targets: ${missing.slice(0, 20).join(', ')}`);

const changed = [];
const fileBuffers = new Map();
for (const [version, versionEdits] of byVersion) {
  const file = sourceFiles.find(name => Number(name.match(sourcePattern)[1]) === version);
  if (!file) throw new Error(`missing source file for v${version}`);
  const target = path.join(sourceDir, file);
  const rows = fs.readFileSync(target, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  for (const { line, text } of versionEdits) {
    const row = rows[line - 1];
    if (!row) throw new Error(`${file}:${line} is missing`);
    if (!text.includes(row.primary)) throw new Error(`${file}:${line} replacement lost primary literal`);
    if (text === row.text) throw new Error(`${file}:${line} replacement did not change text`);
    rows[line - 1] = { ...row, text };
    changed.push({ version, line, primary: row.primary });
  }
  fileBuffers.set(target, rows.map(row => JSON.stringify(row)).join('\n') + '\n');
}

if (apply) {
  for (const [target, content] of fileBuffers) fs.writeFileSync(target, content, 'utf8');
}
const countsByVersion = Object.fromEntries([...byVersion].sort((a, b) => a[0] - b[0]).map(([version, versionEdits]) => [version, versionEdits.length]));
console.log(JSON.stringify({
  mode: apply ? 'APPLIED' : 'PREVIEW',
  source_set_before: sourceSet,
  part_files: partFiles,
  repaired_records: changed.length,
  counts_by_version: countsByVersion
}, null, 2));
