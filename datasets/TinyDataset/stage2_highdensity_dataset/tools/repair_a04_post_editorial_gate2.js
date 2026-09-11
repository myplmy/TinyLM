/* Final two token-boundary compressions after the residual editorial pass. */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const apply = process.argv.includes('--apply');
const expectedSourceSet = 'c7c07a7f8b62926481b11b126e5f4a8a3888737e4c620175872b261dd7c45c59';
const files = fs.readdirSync(sourceDir).filter(file => /^stage2_\(14\)state_transition_high_density_train_v\d+\.source\.jsonl$/.test(file)).sort();
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const sourceSet = sha256(files.map(file => sha256(fs.readFileSync(path.join(sourceDir, file)))).join(''));
if (sourceSet !== expectedSourceSet) throw new Error(`source-set drift: ${sourceSet}`);
const repairs = {
  34: { 35: '저장장치 충전재개허용 조건판정은 정지 원인 해소와 온도·전압·예약 시간의 허용을 모두 요구한다. 한 조건이라도 모자라면 전류를 열지 않는다.' },
  36: { 36: '저장장치 충전경로진단 복구경로는 변환기·접촉기·관리장치 허가를 순서대로 시험한다. 끊긴 지점을 고친 뒤 저율 전류로 연결을 확인한다.' }
};
const changed = [];
for (const [versionText, edits] of Object.entries(repairs)) {
  const version = Number(versionText);
  const file = files.find(name => name.includes(`_v${String(version).padStart(2, '0')}.source.jsonl`));
  const filePath = path.join(sourceDir, file);
  const records = fs.readFileSync(filePath, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  for (const [lineText, text] of Object.entries(edits)) {
    const line = Number(lineText), record = records[line - 1];
    if (!record || !text.includes(record.primary)) throw new Error(`${file}:${line} lost primary literal`);
    records[line - 1] = { ...record, text };
    changed.push({ version, line, primary: record.primary });
  }
  if (apply) fs.writeFileSync(filePath, records.map(record => JSON.stringify(record)).join('\n') + '\n', 'utf8');
}
console.log(JSON.stringify({ mode: apply ? 'APPLIED' : 'PREVIEW', source_set_before: sourceSet, repaired_records: changed.length, changed }, null, 2));
