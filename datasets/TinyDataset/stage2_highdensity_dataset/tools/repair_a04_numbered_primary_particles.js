/* Correct paired particles after A04 primaries whose trailing digits are record identifiers. */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const expectedSourceSet = '3bd115399c65941957c199db5cfa5f1d5ea822f002707420b565183fd007e0e7';
const expectedCorrections = 1522;
const apply = process.argv.includes('--apply');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const sourcePattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const particlePattern = /^(에서|으로|은|는|이|가|을|를|과|와|로|에|의)/;

function finalType(stem) {
  const cp = stem.codePointAt(stem.length - 1);
  if (!cp || cp < 0xac00 || cp > 0xd7a3) return null;
  const jong = (cp - 0xac00) % 28;
  if (jong === 0) return 'none';
  if (jong === 8) return 'rieul';
  return 'final';
}

function correctedParticle(type, particle) {
  if (!type || ['의', '에', '에서'].includes(particle)) return particle;
  if (particle === '으로') return type === 'none' || type === 'rieul' ? '로' : '으로';
  if (particle === '로') return type === 'final' ? '으로' : '로';
  const finalForm = {는:'은', 가:'이', 를:'을', 와:'과'};
  const openForm = {은:'는', 이:'가', 을:'를', 과:'와'};
  if (type === 'final' || type === 'rieul') return finalForm[particle] || particle;
  return openForm[particle] || particle;
}

function repairText(text, primary, type) {
  let cursor = 0;
  let output = '';
  let corrections = 0;
  const changes = new Map();
  while (true) {
    const start = text.indexOf(primary, cursor);
    if (start < 0) {
      output += text.slice(cursor);
      break;
    }
    output += text.slice(cursor, start) + primary;
    const afterPrimary = start + primary.length;
    const match = text.slice(afterPrimary).match(particlePattern);
    if (!match) {
      cursor = afterPrimary;
      continue;
    }
    const before = match[1];
    const after = correctedParticle(type, before);
    output += after;
    cursor = afterPrimary + before.length;
    if (after !== before) {
      corrections++;
      const key = `${before}->${after}`;
      changes.set(key, (changes.get(key) || 0) + 1);
    }
  }
  return {text: output, corrections, changes};
}

const sourceFiles = fs.readdirSync(sourceDir).filter(file => sourcePattern.test(file)).sort();
const sourceSet = sha256(sourceFiles.map(file => sha256(fs.readFileSync(path.join(sourceDir, file)))).join(''));
if (sourceSet !== expectedSourceSet) throw new Error(`source-set drift: expected ${expectedSourceSet}, got ${sourceSet}`);

const buffers = new Map();
const byVersion = new Map();
const changeKinds = new Map();
let correctedRows = 0;
let corrections = 0;
for (const file of sourceFiles) {
  const version = Number(file.match(sourcePattern)[1]);
  const target = path.join(sourceDir, file);
  const rows = fs.readFileSync(target, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  let fileRows = 0;
  let fileCorrections = 0;
  rows.forEach((row, index) => {
    const stem = row.primary.replace(/[0-9]+$/, '').trimEnd();
    if (stem === row.primary || !/[가-힣]$/.test(stem)) return;
    const result = repairText(row.text, row.primary, finalType(stem));
    if (!result.corrections) return;
    if (!result.text.includes(row.primary)) throw new Error(`primary lost v${version}:${index + 1}`);
    rows[index] = {...row, text: result.text};
    correctedRows++;
    corrections += result.corrections;
    fileRows++;
    fileCorrections += result.corrections;
    for (const [key, count] of result.changes) changeKinds.set(key, (changeKinds.get(key) || 0) + count);
  });
  if (fileCorrections) {
    buffers.set(target, rows.map(JSON.stringify).join('\n') + '\n');
    byVersion.set(version, {rows: fileRows, corrections: fileCorrections});
  }
}
if (corrections !== expectedCorrections) throw new Error(`correction count drift: expected ${expectedCorrections}, got ${corrections}`);
if (apply) for (const [target, content] of buffers) fs.writeFileSync(target, content, 'utf8');
console.log(JSON.stringify({mode: apply ? 'APPLIED' : 'PREVIEW', source_set_before: sourceSet,
  corrected_rows: correctedRows, corrected_occurrences: corrections, changed_files: buffers.size,
  change_kinds: Object.fromEntries([...changeKinds].sort()),
  counts_by_version: Object.fromEntries([...byVersion].sort((a,b)=>a[0]-b[0]))}, null, 2));
