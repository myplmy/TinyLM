/*
 * Read-only A04 row inspector.  It shares the canonical tokenizer logic used
 * by audit_stage2_a04_source.js and never mutates datasets or audit reports.
 * Example: node stage2_highdensity_dataset/tools/inspect_a04_token_targets.js --versions 58,62 --limit 30
 */
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const versionsArg = process.argv.indexOf('--versions');
const limitArg = process.argv.indexOf('--limit');
const versions = versionsArg >= 0
  ? new Set(process.argv[versionsArg + 1].split(',').map(value => Number(value)))
  : null;
const limit = limitArg >= 0 ? Number(process.argv[limitArg + 1]) : 30;
if (!Number.isInteger(limit) || limit <= 0) throw new Error('--limit must be a positive integer');

const tokPath = path.resolve(root, '..', '..', 'data_cache', 'tok-ko-en-32768.json');
const model = JSON.parse(fs.readFileSync(tokPath, 'utf8')).model;
const byteValues = [], unicodeValues = [];
for (let value = 33; value <= 126; value += 1) { byteValues.push(value); unicodeValues.push(value); }
for (let value = 161; value <= 172; value += 1) { byteValues.push(value); unicodeValues.push(value); }
for (let value = 174; value <= 255; value += 1) { byteValues.push(value); unicodeValues.push(value); }
let extra = 0;
const encoder = new Map();
for (let index = 0; index < byteValues.length; index += 1) encoder.set(byteValues[index], String.fromCodePoint(unicodeValues[index]));
const used = new Set(byteValues);
for (let value = 0; value < 256; value += 1) if (!used.has(value)) { encoder.set(value, String.fromCodePoint(256 + extra)); extra += 1; }
const ranks = new Map(model.merges.map((pair, index) => [pair[0] + '\u0000' + pair[1], index]));
const tokenPattern = /'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+/gu;
const cache = new Map();
function bpe(token) {
  if (cache.has(token)) return cache.get(token);
  let word = Array.from(token);
  while (word.length > 1) {
    let best = null, bestRank = Number.POSITIVE_INFINITY;
    for (let index = 0; index < word.length - 1; index += 1) {
      const pair = word[index] + '\u0000' + word[index + 1];
      const rank = ranks.has(pair) ? ranks.get(pair) : Number.POSITIVE_INFINITY;
      if (rank < bestRank) { bestRank = rank; best = [word[index], word[index + 1]]; }
    }
    if (!best || bestRank === Number.POSITIVE_INFINITY) break;
    const next = [];
    for (let index = 0; index < word.length;) {
      if (index < word.length - 1 && word[index] === best[0] && word[index + 1] === best[1]) { next.push(word[index] + word[index + 1]); index += 2; }
      else { next.push(word[index]); index += 1; }
    }
    word = next;
  }
  cache.set(token, word);
  return word;
}
function count(text) {
  let total = 0;
  for (const piece of text.match(tokenPattern) || []) {
    let encoded = '';
    for (const byte of Buffer.from(piece, 'utf8')) encoded += encoder.get(byte);
    total += bpe(encoded).length;
  }
  return total + 1; // canonical audit counts EOS.
}
const pattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const files = fs.readdirSync(sourceDir).filter(file => pattern.test(file)).sort();
const result = [];
for (const file of files) {
  const version = Number(file.match(pattern)[1]);
  if (versions && !versions.has(version)) continue;
  const rows = fs.readFileSync(path.join(sourceDir, file), 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  result.push({
    file,
    version,
    rows: rows.map((row, index) => ({ line: index + 1, tokens_plus_eos: count(row.text), chars: row.text.length, primary: row.primary, text: row.text }))
      .sort((left, right) => right.tokens_plus_eos - left.tokens_plus_eos || left.line - right.line)
      .slice(0, limit)
  });
}
console.log(JSON.stringify({ audit: 'A04 canonical token target inspection', tokenizer: path.relative(root, tokPath), limit, result }, null, 2));
