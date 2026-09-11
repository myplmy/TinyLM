/*
 * Emits, but never applies, a TSV for human review of likely non-natural A04
 * qualifier labels.  It does not edit dataset records.
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const expectedSourceSet = '3abe86881c6f1bd64c26fcfae71f819c8365c4e6bc2460f049db234246718f3a';
const outputPath = path.join(root, 'stage2_highdensity_dataset', 'audit_reports', 'review', 'TinyLM_Stage2_A04_Term_Appropriateness_User_Review_2026-09-11.tsv');
const pattern = /^stage2_\(14\)state_transition_high_density_train_v\d+\.source\.jsonl$/;
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const replaceExisting = process.argv.includes('--replace-existing');

const rules = [
  { prefix: '처리에서', code: 'CONNECTIVE_FRAGMENT', focus: '조사·연결어가 아니라 상태명으로 읽히는 자연스러운 명사구인지 검토' },
  { prefix: '에서', code: 'CONNECTIVE_FRAGMENT', focus: '조사·연결어가 아니라 상태명으로 읽히는 자연스러운 명사구인지 검토' },
  { prefix: '않', code: 'NEGATION_FRAGMENT', focus: '부정 어미가 아니라 판정·상태의 자연스러운 명사구인지 검토' },
  { prefix: '추', code: 'TRUNCATED_FRAGMENT', focus: '절단된 어근이 아니라 완결된 개념명인지 검토' },
  { prefix: '또', code: 'TRUNCATED_FRAGMENT', focus: '절단된 어근이 아니라 완결된 개념명인지 검토' },
  { prefix: '가', code: 'TRUNCATED_FRAGMENT', focus: '절단된 조사·어근이 아니라 완결된 개념명인지 검토' },
  { prefix: '가리', code: 'VERB_STEM_COMPOSITE', focus: '동사 어간 결합 대신 상태·판정의 자연스러운 명사구가 필요한지 검토' },
  { prefix: '고르', code: 'VERB_STEM_COMPOSITE', focus: '동사 어간 결합 대신 상태·판정의 자연스러운 명사구가 필요한지 검토' },
  { prefix: '읽기', code: 'MEASUREMENT_TERM_REVIEW', focus: '읽기보다 측정값·관측값 등 도메인상 자연스러운 용어가 필요한지 검토' },
  { prefix: '바로잡', code: 'VERB_STEM_COMPOSITE', focus: '동사 어간 결합 대신 상태·판정의 자연스러운 명사구가 필요한지 검토' },
  { prefix: '미루', code: 'VERB_STEM_COMPOSITE', focus: '동사 어간 결합 대신 상태·판정의 자연스러운 명사구가 필요한지 검토' }
];
const manualTerms = [
  { term: '중간확정', code: 'SYNTHETIC_COMPOUND_REVIEW', focus: '도메인에서 실제 쓰는 용어인지, 전이 중간 기록이라는 뜻을 더 자연스러운 명사구로 바꿔야 하는지 검토' },
  { term: '차량통행', code: 'SYNTHETIC_COMPOUND_REVIEW', focus: '도메인에서 실제 쓰는 용어인지, 차량 통행량·차량 이동 등 더 자연스러운 명사구가 필요한지 검토' }
];

const files = fs.readdirSync(sourceDir).filter(file => pattern.test(file)).sort();
const digests = Object.fromEntries(files.map(file => [file, sha256(fs.readFileSync(path.join(sourceDir, file)))]));
const sourceSet = sha256(files.map(file => file + '\t' + digests[file]).join('\n'));
if (sourceSet !== expectedSourceSet) throw new Error('source-set drift: expected ' + expectedSourceSet + ', got ' + sourceSet);
if (fs.existsSync(outputPath) && !replaceExisting) throw new Error('review TSV already exists: ' + outputPath);

const clean = value => String(value).replace(/[\t\r\n]+/g, ' ').trim();
const rows = [];
for (const file of files) {
  const lines = fs.readFileSync(path.join(sourceDir, file), 'utf8').trimEnd().split(/\r?\n/);
  lines.forEach((line, index) => {
    const row = JSON.parse(line);
    const divider = row.primary.indexOf(' — ');
    const qualifier = divider < 0 ? '' : row.primary.slice(divider + 3);
    const rule = rules.find(item => qualifier === item.prefix || qualifier.startsWith(item.prefix + ' '));
    const manual = manualTerms.find(item => row.primary.includes(item.term));
    const selected = rule || manual;
    if (!selected) return;
    rows.push({
      locator: file + ':' + (index + 1),
      primary: row.primary,
      term_under_review: rule ? qualifier : manual.term,
      relations: row.relations.join('|'),
      text: row.text,
      ai_preliminary_reason: selected.code,
      ai_review_focus: selected.focus
    });
  });
}
rows.sort((left, right) => left.locator.localeCompare(right.locator));
const header = ['locator', 'primary', 'term_under_review', 'relations', 'text', 'ai_preliminary_reason', 'ai_review_focus', 'user_decision_Y_or_N'];
const tsv = [header.join('\t'), ...rows.map(row => [
  clean(row.locator), clean(row.primary), clean(row.term_under_review), clean(row.relations),
  clean(row.text), clean(row.ai_preliminary_reason), clean(row.ai_review_focus), 'PENDING'
].join('\t'))].join('\n') + '\n';

const relativeOutput = path.relative(root, outputPath).split(path.sep).join('/');
const patch = ['*** Begin Patch'];
if (fs.existsSync(outputPath)) {
  patch.push('*** Update File: ' + relativeOutput, '@@');
  for (const line of fs.readFileSync(outputPath, 'utf8').trimEnd().split(/\r?\n/)) patch.push('-' + line);
} else {
  patch.push('*** Add File: ' + relativeOutput);
}
for (const line of tsv.trimEnd().split('\n')) patch.push('+' + line);
patch.push('*** End Patch');
console.log(patch.join('\n'));
console.error(JSON.stringify({
  mode: 'EMIT_PATCH_ONLY',
  source_set_before: sourceSet,
  review_rows: rows.length,
  unique_qualifiers: new Set(rows.map(row => row.qualifier)).size,
  output: relativeOutput
}));
