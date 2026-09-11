/* Apply fixed semantic compression edits to A04 files above the token-mean ceiling. */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const toolDir = path.join(root, 'stage2_highdensity_dataset', 'tools');
const expectedSourceSet = 'fbd5e4a68837c5d13ab50cbb5b43fc00a9e38244f0b8ca3eacb82b1ac0ca4013';
const expectedCounts = new Map([[18,1],[27,2],[34,4],[36,5],[43,3],[48,12],[57,4],[59,4],[60,12],[62,5],[63,4]]);
const apply = process.argv.includes('--apply');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const sourcePattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;

const sourceFiles = fs.readdirSync(sourceDir).filter(file => sourcePattern.test(file)).sort();
const sourceSet = sha256(sourceFiles.map(file => sha256(fs.readFileSync(path.join(sourceDir, file)))).join(''));
if (sourceSet !== expectedSourceSet) throw new Error(`source-set drift: expected ${expectedSourceSet}, got ${sourceSet}`);
const edits = require(path.join(toolDir, 'repair_a04_token_mean_editorial_data.js'));
const seen = new Set();
const byVersion = new Map();
for (const edit of edits) {
  if (!Array.isArray(edit) || edit.length !== 3) throw new Error(`invalid tuple: ${JSON.stringify(edit)}`);
  const [version, line, text] = edit;
  const key = `${version}:${line}`;
  if (seen.has(key) || !expectedCounts.has(version)) throw new Error(`duplicate/outside version: ${key}`);
  if (!Number.isInteger(line) || line < 1 || line > 150) throw new Error(`bad line: ${key}`);
  if (typeof text !== 'string' || text.length < 45 || text.length > 170 || !/[.!?]$/.test(text)) throw new Error(`bad text shape ${key}`);
  seen.add(key);
  if (!byVersion.has(version)) byVersion.set(version, []);
  byVersion.get(version).push({line, text});
}
for (const [version, count] of expectedCounts) {
  if ((byVersion.get(version) || []).length !== count) throw new Error(`edit count mismatch v${version}: expected ${count}`);
}
if (edits.length !== 56 || seen.size !== 56) throw new Error(`fixed edit count must be 56, got ${edits.length}`);

const buffers = new Map();
let oldChars = 0;
let newChars = 0;
for (const [version, list] of byVersion) {
  const file = sourceFiles.find(name => Number(name.match(sourcePattern)[1]) === version);
  const target = path.join(sourceDir, file);
  const rows = fs.readFileSync(target, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  for (const {line, text} of list) {
    const row = rows[line - 1];
    if (!text.includes(row.primary)) throw new Error(`primary lost ${version}:${line}`);
    if (text === row.text) throw new Error(`unchanged ${version}:${line}`);
    if (text.length >= row.text.length) throw new Error(`not shorter ${version}:${line}: ${row.text.length} -> ${text.length}`);
    oldChars += row.text.length;
    newChars += text.length;
    rows[line - 1] = {...row, text};
  }
  buffers.set(target, rows.map(JSON.stringify).join('\n') + '\n');
}
if (apply) for (const [target, content] of buffers) fs.writeFileSync(target, content, 'utf8');
console.log(JSON.stringify({mode: apply ? 'APPLIED' : 'PREVIEW', source_set_before: sourceSet,
  repaired_records: edits.length, chars_before: oldChars, chars_after: newChars, chars_removed: oldChars - newChars,
  counts_by_version: Object.fromEntries([...byVersion].sort((a,b)=>a[0]-b[0]).map(([v,a])=>[v,a.length]))}, null, 2));
