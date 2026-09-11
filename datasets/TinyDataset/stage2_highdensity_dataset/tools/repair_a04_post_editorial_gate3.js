/* Exact token-boundary compression for A04 v34/v36. --apply writes. */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const root = process.cwd();
const dir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const apply = process.argv.includes('--apply');
const expected = 'b6fa3242fecc4c0953b1b0ce37bcf463fb821a20b2462c5eb48ae73d952379dc';
const files = fs.readdirSync(dir).filter(file => /^stage2_\(14\)state_transition_high_density_train_v\d+\.source\.jsonl$/.test(file)).sort();
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const actual = sha(files.map(file => sha(fs.readFileSync(path.join(dir, file)))).join(''));
if (actual !== expected) throw new Error(`source-set drift: ${actual}`);
const repairs = {
  34: {
    35: '저장장치 충전재개허용 조건판정은 정지 원인이 풀리고 온도·전압·예약 시간이 허용될 때만 전류를 다시 연다.',
    43: '저장장치 주파수상승흡수 조건판정은 주파수가 상향 문턱을 일정 시간 넘을 때 흡수 출력을 늘리고 순간 첨두는 제외한다.'
  },
  36: {
    36: '저장장치 충전경로진단 복구경로는 변환기·접촉기·허가를 점검해 끊긴 지점을 고친 뒤 저율 전류로 확인한다.',
    39: '저장장치 충전목표재계획 복구경로는 출력 포화 때 가용 전력과 남은 시간으로 목표량을 다시 산정한다. 부품이 복구되면 기존 계획으로 돌아간다.'
  }
};
const changed = [];
for (const [versionText, edits] of Object.entries(repairs)) {
  const version = Number(versionText);
  const file = files.find(name => name.includes(`_v${String(version).padStart(2, '0')}.source.jsonl`));
  const target = path.join(dir, file);
  const records = fs.readFileSync(target, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  for (const [lineText, text] of Object.entries(edits)) {
    const line = Number(lineText), row = records[line - 1];
    if (!row || !text.includes(row.primary)) throw new Error(`${file}:${line} lost primary`);
    records[line - 1] = { ...row, text };
    changed.push({ version, line, primary: row.primary });
  }
  if (apply) fs.writeFileSync(target, records.map(row => JSON.stringify(row)).join('\n') + '\n', 'utf8');
}
console.log(JSON.stringify({ mode: apply ? 'APPLIED' : 'PREVIEW', source_set_before: actual, repaired_records: changed.length, changed }, null, 2));
