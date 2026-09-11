/* Apply the final fixed v48 compression edits. */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const toolDir = path.join(root, 'stage2_highdensity_dataset', 'tools');
const expectedSourceSet = '12af2649634edb7d2f6eb9f082e75b4217ce6a3438f0b4dcf54b9ce5f9d1edc3';
const apply = process.argv.includes('--apply');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const sourcePattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const sourceFiles = fs.readdirSync(sourceDir).filter(file => sourcePattern.test(file)).sort();
const sourceSet = sha256(sourceFiles.map(file => sha256(fs.readFileSync(path.join(sourceDir, file)))).join(''));
if (sourceSet !== expectedSourceSet) throw new Error(`source-set drift: expected ${expectedSourceSet}, got ${sourceSet}`);
const edits = require(path.join(toolDir, 'repair_a04_token_mean_v48_followup_data.js'));
const target = path.join(sourceDir, 'stage2_(14)state_transition_high_density_train_v48.source.jsonl');
const rows = fs.readFileSync(target, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
const seen = new Set();
let oldChars = 0;
let newChars = 0;
for (const [version, line, text] of edits) {
  const key = `${version}:${line}`;
  if (version !== 48 || seen.has(key)) throw new Error(`duplicate/outside target: ${key}`);
  if (typeof text !== 'string' || text.length < 45 || !/[.!?]$/.test(text)) throw new Error(`bad text shape ${key}`);
  const row = rows[line - 1];
  if (!text.includes(row.primary)) throw new Error(`primary lost ${key}`);
  if (text.length >= row.text.length) throw new Error(`not shorter ${key}: ${row.text.length} -> ${text.length}`);
  seen.add(key);
  oldChars += row.text.length;
  newChars += text.length;
  rows[line - 1] = {...row, text};
}
if (edits.length !== 3 || seen.size !== 3) throw new Error(`fixed edit count must be 3, got ${edits.length}`);
if (apply) fs.writeFileSync(target, rows.map(JSON.stringify).join('\n') + '\n', 'utf8');
console.log(JSON.stringify({mode: apply ? 'APPLIED' : 'PREVIEW', source_set_before: sourceSet,
  repaired_records: edits.length, chars_before: oldChars, chars_after: newChars, chars_removed: oldChars - newChars}, null, 2));
