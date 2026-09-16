const fs = require('fs');
const crypto = require('crypto');

const [,, startArg, endArg, expectedRegistrySha] = process.argv;
const start = Number(startArg), end = Number(endArg);
if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end < start || end > 150) throw new Error('usage');
const sourcePath = 'stage2_highdensity_dataset/sources/train/stage2_(15)modality_possibility_high_density_train_v41.source.jsonl';
const registryPath = 'stage2_highdensity_dataset/sources/term_registry/stage2_(15)modality_possibility_train_registry_v01_v69.jsonl';
const sourceName = sourcePath.split('/').pop();
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
const source = fs.readFileSync(sourcePath, 'utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse);
if (source.length !== 150) throw new Error(`source rows=${source.length}`);
const live = fs.readFileSync(registryPath);
if (expectedRegistrySha && sha(live) !== expectedRegistrySha.toUpperCase()) throw new Error(`registry precondition ${sha(live)} != ${expectedRegistrySha}`);
let out = live;
let changed = 0;
for (let n = start; n <= end; n++) {
  const anchor = Buffer.from(`"source_file":"${sourceName}","source_line":${n},`, 'ascii');
  const a = out.indexOf(anchor);
  if (a < 0 || out.indexOf(anchor, a + 1) >= 0) throw new Error(`anchor row ${n}`);
  const key = Buffer.from('"primary":"', 'ascii');
  const marker = Buffer.from('","term_kind"', 'ascii');
  const relKey = out.slice(a + anchor.length).indexOf(key);
  if (relKey < 0) throw new Error(`primary key row ${n}`);
  const ps = a + anchor.length + relKey + key.length;
  const relMarker = out.slice(ps).indexOf(marker);
  if (relMarker < 0) throw new Error(`primary end row ${n}`);
  const pe = ps + relMarker;
  const replacement = Buffer.from(JSON.stringify(source[n - 1].primary).slice(1, -1), 'utf8');
  if (!out.slice(ps, pe).equals(replacement)) changed++;
  out = Buffer.concat([out.slice(0, ps), replacement, out.slice(pe)]);
}
for (const line of out.toString('utf8').split(/\r?\n/).filter(Boolean)) JSON.parse(line);
const tmp = `${registryPath}.sync_v41_${start}_${end}.tmp`;
fs.writeFileSync(tmp, out);
if (sha(fs.readFileSync(tmp)) !== sha(out)) throw new Error('temp SHA mismatch');
console.log(JSON.stringify({ start, end, changed, before_sha: sha(live), temp: tmp, after_sha: sha(out) }));
