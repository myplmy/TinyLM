/*
 * Emits, but never applies, the final bounded A04 token-range correction.
 * It preserves row order, IDs, relations and all non-text fields.
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const expectedSourceSet = '48395dfd1b4a8d59cb56e36812cd78f22457d1116e00c4bee5e0f2763fc6610e';
const pattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');

const edits = [
  [62, 79, '항만 위험물복귀 — 농도 이동', '항만 위험물복귀 — 농도 이동은 누출 검사 합격 때 위험물 이동을 재개하되 잔류 농도가 높으면 격리를 유지한다. 합격값·농도를 기록한다.'],
  [62, 81, '항만 통관복귀 — 서류 재처리', '항만 통관복귀 — 서류 재처리는 보완 서류 합격 뒤 반출을 열되 새 불일치가 있으면 막는다. 합격 시각·보류 항목을 남긴다.'],
  [62, 87, '항만 운영이탈 — 야드 상태', '항만 운영이탈 — 야드 상태는 혼잡·기상으로 하역을 제한한 상태다. 반출로가 확보되면 완화를 검토한다.'],
  [65, 69, '공항 활주로검사 — 지속 촉발·억제', '공항 활주로검사 — 지속 촉발·억제는 검사 시작 신호로 표면 점검을 열고 적설 지속이면 보류한다. 신호 시각·적설량을 기록한다.'],
  [65, 79, '공항 제빙노즐복귀 — 분사량 복귀', '공항 제빙노즐복귀 — 분사량 복귀는 분사량 회복 때 제빙을 시작하고 재막힘이면 멈춘다. 분사량·재발점을 남긴다.'],
  [66, 4, '반도체 웨이퍼세정 — 농도 안정', '반도체 웨이퍼세정 — 농도 안정은 세정액 농도가 안정된 뒤 웨이퍼 처리 재개를 검토한다. 보정 수치·시각으로 로트 순서를 정한다.'],
  [67, 72, '도시열공급 누수감시 — 누수량 이동', '도시열공급 누수감시 — 누수량 이동은 누수량이 경보선을 넘으면 차단조와 우회 공급조를 바꾼다. 예비 관로 압력으로 범위를 정한다.'],

  [69, 6, '수술실감염통제 환자확인 — 식별밴드 상태', '수술실감염통제 환자확인 — 식별밴드 상태는 식별밴드 번호가 불확실해 재확인을 요청한 단계다. 접수·교체 이력으로 변화를 추적한다.'],
  [69, 9, '수술실감염통제 환자확인 — 밴드 이동', '수술실감염통제 환자확인 — 밴드 이동은 밴드 번호가 등록값과 맞아 확인 복귀를 준비한다. 이전 불일치와 새 읽기를 대조한다.'],
  [69, 23, '수술실감염통제 알레르기확인 — 환자 상태', '수술실감염통제 알레르기확인 — 환자 상태는 환자 표기를 병력·관리 기준과 검증한다. 맞지 않으면 투여 전 다시 확인한다.'],
  [69, 27, '수술실감염통제 감염선별 — 선별값 이동', '수술실감염통제 감염선별 — 선별값 이동은 선별값 변동 때문에 격리와 일반 동선을 고른다. 음압실 여력·재검 준비로 이동을 정한다.'],
  [69, 44, '수술실감염통제 수술전실 — 압력 이동', '수술실감염통제 수술전실 — 압력 이동은 전실 압력이 안정되면 격리 해제를 심사한다. 공조 보정·차압으로 이동 차례를 정한다.'],
  [69, 56, '수술실감염통제 수술복장 — 수술복 재처리', '수술실감염통제 수술복장 — 수술복 재처리는 초기 복장 확인만 있어 판정을 미룬 상태다. 누락 인원의 확인을 기다린다.'],
  [69, 62, '수술실감염통제 손위생 — 확인 차단', '수술실감염통제 손위생 — 확인 차단은 손소독 확인 미달로 무균 구역 진입을 멈춘 상태다. 공급·관찰 뒤 재진입을 본다.'],
  [69, 65, '수술실감염통제 손위생 — 보완 재처리', '수술실감염통제 손위생 — 보완 재처리는 보완 교육·재검 뒤 손위생 기록을 점검 체계에 넣는다. 편차 항목은 참여 승인과 분리한다.'],
  [69, 93, '수술실감염통제 검체표기 — 라벨 판정', '수술실감염통제 검체표기 — 라벨 판정은 라벨을 환자·검사 참조값과 대조한다. 차이는 환자·채취자·용기 원인으로 분류한다.'],
  [69, 98, '수술실감염통제 출혈관리 — 출혈량 재처리', '수술실감염통제 출혈관리 — 출혈량 재처리는 출혈량이 허용편차 안인지 본다. 이탈 자료는 흡인량·거즈량으로 다시 확인한다.'],
  [69, 101, '수술실감염통제 수혈확인 — 혈액백 판정', '수술실감염통제 수혈확인 — 혈액백 판정은 혈액백·환자·투여 시각의 순서가 달라 수혈 판단을 미룬 상태다. 두 확인자가 기준시각을 맞춘다.'],
  [69, 102, '수술실감염통제 수혈확인 — 수혈값 상태', '수술실감염통제 수혈확인 — 수혈값 상태는 수혈값 변동 때문에 투입 경로 전환을 검토한다. 대체 제제가 없으면 투여를 보류한다.'],
  [69, 103, '수술실감염통제 수혈확인 — 정보 통과', '수술실감염통제 수혈확인 — 정보 통과는 혈액제제와 환자 정보가 기준을 충족하는지 점검한다. 불일치 항목은 투여에서 격리한다.'],
  [69, 106, '수술실감염통제 체온관리 — 체온 상태', '수술실감염통제 체온관리 — 체온 상태는 서로 다른 위치의 체온이 모일 때까지 결론을 보류한다. 시각·기기 출처로 보온 조치를 정한다.'],
  [69, 116, '수술실감염통제 마취회복 — 의식 판정', '수술실감염통제 마취회복 — 의식 판정은 의식·호흡·혈압으로 퇴실 조건을 판단한다. 누락 활력값은 다시 확인한다.'],
  [69, 118, '수술실감염통제 마취회복 — 점수 판정', '수술실감염통제 마취회복 — 점수 판정은 회복 점수가 제한 안인지 평가한다. 범위 밖 표본은 활력징후와 다시 확인한다.'],
  [69, 124, '수술실감염통제 회복실감염 — 청결도 복귀', '수술실감염통제 회복실감염 — 청결도 복귀는 회복실 청결도가 돌아오면 운전 제한 완화를 검토한다. 이전 이상과 새 결과로 순서를 정한다.'],
  [69, 127, '수술실감염통제 수술후검체 — 보관온도 상태', '수술실감염통제 수술후검체 — 보관온도 상태는 보관온도 이상으로 검체 이송 절차를 바꿀지 판단한다. 냉장 자원·경보 시점으로 결정한다.'],
  [69, 130, '수술실감염통제 수술후검체 — 냉장온도 조정', '수술실감염통제 수술후검체 — 냉장온도 조정은 냉장온도 보정 뒤 보관 상태를 다시 검사한다. 불일치 검체는 격리를 유지한다.'],
  [69, 150, '수술실감염통제 퇴실판정 — 점수 재처리', '수술실감염통제 퇴실판정 — 점수 재처리는 점수 정리 뒤 환자 상태를 다시 확인한다. 새 오차면 이송을 막고 활력·의식을 평가한다.']
];

const files = fs.readdirSync(sourceDir).filter(file => pattern.test(file)).sort();
const digests = Object.fromEntries(files.map(file => [file, sha256(fs.readFileSync(path.join(sourceDir, file)))]));
const sourceSet = sha256(files.map(file => file + '\t' + digests[file]).join('\n'));
if (sourceSet !== expectedSourceSet) throw new Error('source-set drift: expected ' + expectedSourceSet + ', got ' + sourceSet);
const patchByFile = new Map();
const seen = new Set();
for (const [version, line, primary, text] of edits) {
  const key = version + ':' + line;
  if (seen.has(key)) throw new Error('duplicate edit: ' + key);
  seen.add(key);
  const file = files.find(name => Number(name.match(pattern)[1]) === version);
  const rows = fs.readFileSync(path.join(sourceDir, file), 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  const row = rows[line - 1];
  if (!row || row.primary !== primary) throw new Error('primary drift at ' + key);
  const next = { ...row, text };
  if (!next.text.includes(next.primary)) throw new Error('primary literal lost at ' + key);
  if (!patchByFile.has(file)) patchByFile.set(file, []);
  patchByFile.get(file).push({ line, oldLine: JSON.stringify(row), newLine: JSON.stringify(next) });
}
const output = ['*** Begin Patch'];
for (const [file, changes] of [...patchByFile.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
  output.push('*** Update File: ' + path.join(sourceDir, file));
  for (const change of changes.sort((a, b) => a.line - b.line)) {
    output.push('@@');
    output.push('-' + change.oldLine);
    output.push('+' + change.newLine);
  }
}
output.push('*** End Patch');
console.log(output.join('\n'));
console.error(JSON.stringify({ mode: 'EMIT_PATCH_ONLY', source_set_before: sourceSet, edited_rows: edits.length }));
