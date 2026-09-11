/* Small editorial pass for three qualifiers that created adjacent duplicates. */
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const apply = process.argv.includes('--apply');
const overrides = new Map([
  [
    'stage2_(14)state_transition_high_density_train_v55.source.jsonl:26',
    {
      oldPrimary: '열공급 축열조 — 축열조 대기',
      primary: '열공급 축열조 — 충전 명령 대기',
      text: '열공급 축열조 — 충전 명령 대기는 축열조가 충전·방전 명령을 기다리는 상태이며, 저장 온도와 탱크 번호를 남기고 충전 임계값과 방전 순서를 조정한다.',
    },
  ],
  [
    'stage2_(14)state_transition_high_density_train_v66.source.jsonl:45',
    {
      oldPrimary: '반도체 열처리 — 열처리 상태',
      primary: '반도체 열처리 — 온도 보정 상태',
      text: '반도체 열처리 — 온도 보정 상태의 열처리 온도 보정 뒤 반도체 열처리 점검을 새로 시작한다. 오차가 계속되면 현 상태를 유지하고 추가 확인을 받는다.',
    },
  ],
  [
    'stage2_(14)state_transition_high_density_train_v69.source.jsonl:63',
    {
      oldPrimary: '수술실감염통제 손위생 — 손위생 상태',
      primary: '수술실감염통제 손위생 — 위생 기준 판정',
      text: '수술실감염통제 손위생 — 위생 기준 판정은 손 씻기 절차가 정해진 위생 기준을 만족하는지 판단하는 상태다. 기준을 넘은 관측치는 재확인 대상으로 표시한다.',
    },
  ],
]);

const changed = [];
for (const [location, item] of overrides) {
  const [file, lineText] = location.split(':');
  const lineNumber = Number(lineText);
  const target = path.join(sourceDir, file);
  const rows = fs.readFileSync(target, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  const row = rows[lineNumber - 1];
  if (!row || row.primary !== item.oldPrimary) throw new Error(`${location}: old primary mismatch`);
  if (!row.text.includes(item.oldPrimary)) throw new Error(`${location}: old primary missing from text`);
  rows[lineNumber - 1] = { ...row, primary: item.primary, text: item.text };
  if (!rows[lineNumber - 1].text.includes(item.primary)) throw new Error(`${location}: new primary missing from text`);
  changed.push({ location, old_primary: item.oldPrimary, new_primary: item.primary });
  if (apply) fs.writeFileSync(target, rows.map(JSON.stringify).join('\n') + '\n', 'utf8');
}

console.log(JSON.stringify({ mode: apply ? 'APPLIED' : 'PREVIEW', changed }, null, 2));
