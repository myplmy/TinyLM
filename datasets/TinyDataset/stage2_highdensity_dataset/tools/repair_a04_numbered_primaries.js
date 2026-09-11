/*
 * Replace the A04 generator's synthetic decimal suffixes in primary concepts.
 *
 * The affected rows are in state_transition train v49-v69.  The suffix is the
 * one-based source-row number, not part of the concept.  This repair keeps
 * source schema unchanged (primary/text/relations), replaces the literal in
 * text, and uses a short semantic qualifier only when removing the suffix
 * would collide with another primary.  Qualifiers are derived from the row's
 * existing meaning, never from the row number.
 *
 * Default mode is preview.  Pass --apply to rewrite the source files.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const pattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const apply = process.argv.includes('--apply');

const particlePattern = /^(에서|으로|은|는|이|가|을|를|과|와|로|에|의)/;
const stopWords = new Set([
  '것', '수', '때', '뒤', '후', '전', '안', '밖', '더', '다시', '서로',
  '현재', '이전', '다음', '모든', '일부', '각', '해당', '같은', '그',
  '상태', '과정', '변화', '전이', '단계', '중간', '기준', '범위', '정상', '대',
  '확인', '유지', '보존', '남기', '기록', '조정', '변경', '정한다',
]);

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

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
  const finalForm = { 는: '은', 가: '이', 를: '을', 와: '과' };
  const openForm = { 은: '는', 이: '가', 을: '를', 과: '와' };
  return type === 'final' || type === 'rieul'
    ? (finalForm[particle] || particle)
    : (openForm[particle] || particle);
}

function stripEnding(token) {
  let value = token.replace(/^[\u2018\u2019'"“”「」『』()[\]{}]+|[\u2018\u2019'"“”「」『』()[\]{}.,!?;:]+$/g, '');
  value = value.replace(/(으로부터|에서부터|에게서|한테서|까지|부터|에서|에게|한테|으로|로|처럼|보다|만큼|마다|에는|에도|으로는|은|는|이|가|을|를|과|와|의|에|만|로)$/u, '');
  value = value.replace(/(하며|하면서|하고|하지만|때문에|되어|되고|되는|되면|된|하는|한|할|해야|하려|기다리는|기다리며|머무는|남는|있는|없어|없고|이어|이어지는|줄어|높아|낮아|올라|내려|맞아|맞는|맞고|돌아가|돌아오는|들어가|넘어가|생겨|생긴|남아|받아|빠져|끝나|끝난|열려|닫혀|나뉘|바뀌|바뀐|붙어|붙은)$/u, '');
  return value;
}

function candidateTerms(text, oldPrimary) {
  const rest = text.replaceAll(oldPrimary, ' ');
  const firstTwo = rest.split(/[.!?]/u).slice(0, 2).join(' ');
  const raw = firstTwo.split(/\s+/u).map(stripEnding).filter(Boolean);
  const terms = [];
  for (const token of raw) {
    if (token.length < 2 || stopWords.has(token)) continue;
    if (/[0-9]/.test(token)) continue;
    if (!/[가-힣A-Za-z]/u.test(token)) continue;
    if (!terms.includes(token)) terms.push(token);
  }
  return terms;
}

function semanticKind(text) {
  if (/기다리|대기/.test(text)) return '대기';
  if (/촉발/.test(text) && /억제/.test(text)) return '촉발·억제';
  if (/부분|일부/.test(text) && /제한/.test(text)) return '부분 제한';
  if (/재시험|재검|재세정|재시도|재처리|다시/.test(text)) return '재처리';
  if (/복귀|돌아가|돌아오는|재개|회복/.test(text)) return '복귀';
  if (/실패|중단|차단|누락|제외|고장/.test(text)) return '제한';
  if (/상승|하강|감소|증가|낮아|올라|내려/.test(text)) return '수준 변화';
  if (/완료|정상화|확정/.test(text)) return '완료';
  if (/판정|평가/.test(text)) return '판정';
  if (/인계|배정/.test(text)) return '인계';
  if (/기록|저장|보존/.test(text)) return '기록';
  return '상태';
}

function subjectNoun(text, oldPrimary) {
  const rest = text.replaceAll(oldPrimary, ' ');
  const first = rest.split(/[.!?]/u)[0];
  const tokens = first.split(/\s+/u).filter(Boolean);
  const generic = new Set(['것', '수', '때', '뒤', '후', '전', '안', '밖', '중간', '상태', '과정', '변화', '전이', '단계', '기준', '범위', '모든', '일부', '각', '해당', '결과', '대', '자료', '시각', '시간', '값', '번호']);
  const likelyVerb = /(?:하|되|있|없|남|넘기|돌아|돌아가|연결|연결되|연결하|감소하|방출되|기다리|머무|올라|내려|생겨|붙어|바뀌|이어|끝나|열려|닫혀|나뉘|맞아|들어가|빠져|옮기|넘어가)$/u;
  for (const particle of ['이', '가', '은', '는']) {
    for (const token of tokens) {
      const match = token.match(new RegExp(`^(.*)${particle}$`, 'u'));
      if (!match) continue;
      const noun = match[1].replace(/[\u2018\u2019'"“”「」『』()[\]{}.,!?;:]+$/gu, '');
      if (noun.length >= 1 && !generic.has(noun) && !likelyVerb.test(noun) && /[가-힣A-Za-z]/u.test(noun)) return noun;
    }
  }
  return candidateTerms(text, oldPrimary).find(term => !generic.has(term)) || '운영';
}

function semanticAction(text) {
  const checks = [
    [/기다리/u, '대기'],
    [/촉발.*억제|억제.*촉발/u, '촉발·억제'],
    [/감소|줄어|낮아|하강/u, '감소'],
    [/상승|올라|높아|증가/u, '상승'],
    [/이동|넘어/u, '이동'],
    [/고정|포화/u, '포화'],
    [/방출되|방출|배출/u, '방출'],
    [/남아|잔류/u, '잔류'],
    [/재시험|재검|재세정|재시도|재처리/u, '재처리'],
    [/복귀|돌아|되돌/u, '복귀'],
    [/통과/u, '통과'],
    [/인계/u, '인계'],
    [/배정/u, '배정'],
    [/정지|중단|차단/u, '차단'],
    [/판정|평가|확정/u, '판정'],
    [/분배|분담/u, '분담'],
    [/계산/u, '계산'],
    [/안정|허용.*범위|관리.*범위/u, '안정'],
    [/조정|변경|바꾸/u, '조정'],
  ];
  return checks.find(([pattern]) => pattern.test(text))?.[1] || '상태';
}

function semanticCandidates(text, oldPrimary) {
  const terms = candidateTerms(text, oldPrimary);
  const subject = subjectNoun(text, oldPrimary);
  const action = semanticAction(text);
  const kind = semanticKind(text);
  const generic = new Set(['정도', '여부', '방식', '경우', '대상', '자료', '값', '시각', '시간', '구역', '번호', '원인', '결과', '상태', '과정', '변화', '전이', '단계']);
  const useful = terms.filter(term => !generic.has(term));
  const out = [];
  const add = (parts) => {
    const filtered = parts.filter(Boolean);
    if (filtered.length > 1 && filtered.some((part, index) => index > 0 && part === filtered[index - 1])) return;
    const phrase = filtered.join(' ').replace(/\s+/g, ' ').trim();
    if (!phrase || out.includes(phrase)) return;
    out.push(phrase);
  };
  add([subject, action]);
  add([subject, kind]);
  for (const term of useful) add([term, action]);
  for (let width = Math.min(3, useful.length); width >= 1; width--) {
    for (let i = 0; i + width <= useful.length; i++) add([...useful.slice(i, i + width), action]);
  }
  add([action]);
  return out;
}

function replacePrimary(text, oldPrimary, newPrimary) {
  const replaced = text.replaceAll(oldPrimary, newPrimary);
  const type = finalType(newPrimary.replace(/[^가-힣A-Za-z]+$/u, '').trim());
  if (!type) return replaced;
  let output = '';
  let cursor = 0;
  while (cursor < replaced.length) {
    const start = replaced.indexOf(newPrimary, cursor);
    if (start < 0) {
      output += replaced.slice(cursor);
      break;
    }
    output += replaced.slice(cursor, start + newPrimary.length);
    const after = start + newPrimary.length;
    const match = replaced.slice(after).match(particlePattern);
    if (!match) {
      cursor = after;
      continue;
    }
    const before = match[1];
    output += correctedParticle(type, before);
    cursor = after + before.length;
  }
  return output;
}

const files = fs.readdirSync(sourceDir).filter(file => pattern.test(file)).sort();
const allRows = [];
const fileRows = new Map();
for (const file of files) {
  const rows = fs.readFileSync(path.join(sourceDir, file), 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  fileRows.set(file, rows);
  rows.forEach((row, index) => {
    const match = row.primary.match(/^(.*?)([0-9]+)$/u);
    allRows.push({ file, line: index + 1, row, match });
  });
}

const numeric = allRows.filter(item => item.match && Number(item.match[2]) === item.line);
const numericMismatch = allRows.filter(item => item.match && Number(item.match[2]) !== item.line);
if (numericMismatch.length) {
  throw new Error(`numeric suffix did not match one-based source line for ${numericMismatch.length} rows`);
}
const used = new Set(allRows.filter(item => !item.match).map(item => item.row.primary));
const baseGroups = new Map();
for (const item of numeric) {
  const base = item.match[1];
  if (!baseGroups.has(base)) baseGroups.set(base, []);
  baseGroups.get(base).push(item);
}

const assignments = [];
const changesByFile = new Map();
for (const item of numeric) {
  const oldPrimary = item.row.primary;
  const base = item.match[1];
  const group = baseGroups.get(base);
  const mustQualify = group.length > 1 || used.has(base);
  let newPrimary = base;
  if (mustQualify) {
    const candidates = semanticCandidates(item.row.text, oldPrimary);
    const available = candidates.find(tag => !used.has(`${base} — ${tag}`));
    if (!available) {
      throw new Error(`no semantic qualifier available for ${item.file}:${item.line} ${oldPrimary}`);
    }
    newPrimary = `${base} — ${available}`;
  }
  if (used.has(newPrimary)) {
    throw new Error(`primary collision after repair: ${item.file}:${item.line} ${newPrimary}`);
  }
  used.add(newPrimary);
  assignments.push({ file: item.file, line: item.line, old_primary: oldPrimary, new_primary: newPrimary, qualified: newPrimary !== base });
  changesByFile.set(item.file, (changesByFile.get(item.file) || 0) + 1);
}

const byLocation = new Map(assignments.map(item => [`${item.file}:${item.line}`, item]));
const buffers = new Map();
for (const [file, rows] of fileRows) {
  const changed = rows.map((row, index) => {
    const assignment = byLocation.get(`${file}:${index + 1}`);
    if (!assignment) return row;
    const text = replacePrimary(row.text, assignment.old_primary, assignment.new_primary);
    if (!text.includes(assignment.new_primary)) throw new Error(`new primary missing from text: ${file}:${index + 1}`);
    return { ...row, primary: assignment.new_primary, text };
  });
  if (changed.length !== rows.length) throw new Error(`row count changed: ${file}`);
  const primaries = changed.map(row => row.primary);
  const texts = changed.map(row => row.text);
  if (new Set(primaries).size !== primaries.length) throw new Error(`duplicate primary after repair: ${file}`);
  if (new Set(texts).size !== texts.length) throw new Error(`duplicate text after repair: ${file}`);
  if (changed.some(row => /[0-9]+$/u.test(row.primary) || !row.text.includes(row.primary))) {
    throw new Error(`numeric primary or missing literal after repair: ${file}`);
  }
  buffers.set(file, changed.map(JSON.stringify).join('\n') + '\n');
}

const beforeHashes = Object.fromEntries(files.map(file => [file, sha256(fs.readFileSync(path.join(sourceDir, file)))]));
if (apply) {
  for (const [file, content] of buffers) fs.writeFileSync(path.join(sourceDir, file), content, 'utf8');
}

const report = {
  mode: apply ? 'APPLIED' : 'PREVIEW',
  scope: 'stage2_(14)state_transition_high_density_train_v49-v69',
  source_files: files.length,
  source_records: allRows.length,
  numbered_rows: numeric.length,
  qualified_rows: assignments.filter(item => item.qualified).length,
  changed_files: changesByFile.size,
  before_hashes: beforeHashes,
  assignments: assignments.slice(0, 40),
  qualified_examples: assignments.filter(item => item.qualified).slice(0, 80),
  assignment_count: assignments.length,
  note: 'Decimal suffixes matched the one-based source line. Qualifiers are semantic and were copied into text; no source schema keys were added.',
};
console.log(JSON.stringify(report, null, 2));
