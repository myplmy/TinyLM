/*
 * Emits, but never applies, a narrow A04 source patch.
 *
 * The caller must pass the emitted unified patch to the platform apply_patch
 * mechanism.  That keeps source writes reviewable and avoids direct fs writes.
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const expectedSourceSet = 'd234152b63fd2d9ac85462938dcf7d8146b1b44301a7d61cbcc8e1a586f211db';
const pattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');

const edits = [
  {
    version: 49, line: 145, primary: '데이터센터 중간확정',
    text: '데이터센터 중간확정은 센서·명령 상태를 전이 중간의 기준 기록으로 묶는 과정이다. 기록자·시각을 남겨 후속 변경의 기준을 정한다.'
  },
  {
    version: 52, line: 10, primary: '터널 배수펌프 — 증가 촉발·억제',
    text: '터널 배수펌프 — 증가 촉발·억제는 진동 증가로 펌프를 멈추고 우회 배수로로 침수를 막는 전이다. 진동값·시각을 기록해 밸브 순서를 정한다.'
  },
  {
    version: 52, line: 82, primary: '터널 배수전원 — 상승 촉발·억제',
    text: '터널 배수전원 — 상승 촉발·억제는 수위 상승 때 펌프 전원을 투입하되 누전 감시가 작동하면 보류하는 전이다. 수위·누전값을 남겨 차단 순서를 정한다.'
  },
  {
    version: 52, line: 84, primary: '터널 배수전원 — 온도 촉발·억제',
    text: '터널 배수전원 — 온도 촉발·억제는 전압 저하로 비상 회로를 절체하되 높은 배터리 온도면 출력을 낮추는 전이다. 전압·온도를 남겨 부하 순서를 정한다.'
  },
  {
    version: 55, line: 17, primary: '열공급 배관압력 — 급증 촉발·억제',
    text: '열공급 배관압력 — 급증 촉발·억제는 수요 급증으로 압력이 내려갈 때 밸브를 조절해 하강을 막는 전이다. 수요량·조절 시각으로 펌프 출력을 정한다.'
  },
  {
    version: 55, line: 129, primary: '열공급 최종확인',
    text: '열공급 최종확인은 반복 측정이 기준을 만족해 일반 공급을 인계할 수 있는 상태다. 횟수·검사자를 남겨 감시 주기를 정한다.'
  },
  {
    version: 56, line: 48, primary: '해양 부표 수질안정 — 염분·탁도·수온 안정',
    text: '해양 부표 수질안정 — 염분·탁도·수온 안정은 염분·탁도·수온이 관측 범위에 머문 상태다. 시료 번호·시각을 남겨 채수 간격과 경보 수준을 정한다.'
  },
  {
    version: 58, line: 63, primary: '산림 복구판정 — 재개 촉발·억제',
    text: '산림 복구판정 — 재개 촉발·억제에서는 줄기 생장 재개가 회복 관찰을 열고 둘레 감소가 이를 보류한다. 둘레·날짜를 기록해 비료 투입 시점을 정한다.'
  },
  {
    version: 58, line: 73, primary: '산림 복구판정 — 산불 촉발·억제',
    text: '산림 복구판정 — 산불 촉발·억제는 토양 수분 회복이 발아 관찰을 시작하게 하지만 표토 유실은 이를 막는 전이다. 수분·유실 깊이를 남겨 보강 구역을 정한다.'
  },
  {
    version: 58, line: 125, primary: '산림 회복기록 — 뿌리 촉발·억제',
    text: '산림 회복기록 — 뿌리 촉발·억제는 뿌리 활력 상승으로 이식 제한을 완화하되 활력 하락이면 보류하는 전이다. 활력 지수·토양 수분으로 이식 시기를 정한다.'
  },
  {
    version: 59, line: 90, primary: '전기버스 충전품질 — 지연 촉발·억제',
    text: '전기버스 충전품질 — 지연 촉발·억제는 통신 지연 때 출력 간격을 바꾸고 지연이 회복되면 원래 설정으로 돌리는 전이다. 지연값·회복 시각으로 포트 순서를 정한다.'
  },
  {
    version: 60, line: 137, primary: '발효 출하복귀 — 보완 촉발·억제',
    text: '발효 출하복귀 — 보완 촉발·억제는 보완 검사 합격 때 출하를 재개하고 신규 오염이면 보류하는 전이다. 합격 결과·시각을 남겨 포장 순서를 정한다.'
  },
  {
    version: 62, line: 90, primary: '항만 교대확인 — 찾 인계', newPrimary: '항만 교대확인 — 인계 누락 점검',
    text: '항만 교대확인 — 인계 누락 점검은 인계 목록과 야드·선석 상태를 대조해 누락된 위험·화물을 확인하는 점검이다. 담당자를 정한 뒤 교대를 승인한다.'
  },
  {
    version: 62, line: 94, primary: '항만 안전복귀 — 안정 촉발·억제',
    text: '항만 안전복귀 — 안정 촉발·억제는 기상이 안정되면 순찰을 재개하되 잔류 위험이 있으면 보류하는 전이다. 풍속·위험값으로 통제 범위를 정한다.'
  },
  {
    version: 63, line: 130, primary: '축사 교대확인 — 찾 인계', newPrimary: '축사 교대확인 — 인계 누락 점검',
    text: '축사 교대확인 — 인계 누락 점검은 인계표와 축사 배치를 대조해 빠진 치료·급수 항목을 확인하는 검사다. 현장 표지가 맞으면 교대를 기록한다.'
  },
  {
    version: 64, line: 63, primary: '터널 신호이탈 — 지연 촉발·억제',
    text: '터널 신호이탈 — 지연 촉발·억제는 통신 지연 시 수동 신호로 전환하되 인력 부족이면 전환을 늦추는 과정이다. 지연값·인력 상태를 남겨 역할을 정한다.'
  },
  {
    version: 64, line: 84, primary: '터널 교대확인 — 찾 인계', newPrimary: '터널 교대확인 — 인계 누락 점검',
    text: '터널 교대확인 — 인계 누락 점검은 인계 목록과 관제 화면·순찰 결과를 대조해 누락된 통제·배수 항목을 확인하는 점검이다. 불일치가 없어야 교대를 기록한다.'
  },
  {
    version: 65, line: 66, primary: '공항 항공기출발 — 합격 촉발·억제',
    text: '공항 항공기출발 — 합격 촉발·억제는 마찰 시험 합격 때 출발을 허용하고 적설 초과면 보류하는 전이다. 시험값·적설량을 남겨 관제 순서를 정한다.'
  },
  {
    version: 65, line: 71, primary: '공항 활주로검사 — 재시험 촉발·억제',
    text: '공항 활주로검사 — 재시험 촉발·억제는 재시험 합격 때 운항을 승인하고 재결빙이면 승인을 보류하는 전이다. 합격값·재결빙 시각으로 감시 순서를 정한다.'
  },
  {
    version: 65, line: 83, primary: '공항 안전복귀 — 결빙 복귀',
    text: '공항 안전복귀 — 결빙 복귀는 점검 합격 뒤 접근을 허용하되 재결빙 여부를 감시하는 과정이다. 합격값·재발 시각으로 접근 구역을 정한다.'
  },
  {
    version: 67, line: 90, primary: '도시열공급 배출가스 — 살피 포화', newPrimary: '도시열공급 배출가스 — 보정 후 재검토',
    text: '도시열공급 배출가스 — 보정 후 재검토는 보정한 농도 자료와 환경 검증 결과를 다시 대조하는 단계다. 새 편차가 있으면 출력을 유지하고 추가 표본을 요청한다.'
  },
  {
    version: 68, line: 55, primary: '해양부표 클로로필 — 살피 포화', newPrimary: '해양부표 클로로필 — 보정 후 재검토',
    text: '해양부표 클로로필 — 보정 후 재검토는 보정한 농도 자료와 채수·광학검사 결과를 다시 대조하는 단계다. 새 편차가 있으면 분석을 요청한다.'
  }
];

const files = fs.readdirSync(sourceDir).filter(file => pattern.test(file)).sort();
const fileDigests = Object.fromEntries(files.map(file => [file, sha256(fs.readFileSync(path.join(sourceDir, file)))]));
const sourceSet = sha256(files.map(file => `${file}\t${fileDigests[file]}`).join('\n'));
if (sourceSet !== expectedSourceSet) {
  throw new Error(`source-set drift: expected ${expectedSourceSet}, got ${sourceSet}`);
}

const duplicateEdits = new Set();
const patchByFile = new Map();
for (const edit of edits) {
  const key = `${edit.version}:${edit.line}`;
  if (duplicateEdits.has(key)) throw new Error(`duplicate edit: ${key}`);
  duplicateEdits.add(key);
  const file = files.find(name => Number(name.match(pattern)[1]) === edit.version);
  if (!file) throw new Error(`missing version v${edit.version}`);
  const target = path.join(sourceDir, file);
  const rows = fs.readFileSync(target, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  const row = rows[edit.line - 1];
  if (!row || row.primary !== edit.primary) throw new Error(`primary drift at ${key}`);
  const next = { ...row, primary: edit.newPrimary || row.primary, text: edit.text };
  if (!next.text.includes(next.primary)) throw new Error(`primary literal lost at ${key}`);
  if (next.text === row.text && next.primary === row.primary) throw new Error(`no-op at ${key}`);
  if (!patchByFile.has(file)) patchByFile.set(file, []);
  patchByFile.get(file).push({ line: edit.line, oldLine: JSON.stringify(row), newLine: JSON.stringify(next) });
}

const output = ['*** Begin Patch'];
for (const [file, changes] of [...patchByFile.entries()].sort((left, right) => left[0].localeCompare(right[0]))) {
  output.push(`*** Update File: ${path.join(sourceDir, file)}`);
  for (const change of changes.sort((left, right) => left.line - right.line)) {
    output.push('@@');
    output.push(`-${change.oldLine}`);
    output.push(`+${change.newLine}`);
  }
}
output.push('*** End Patch');
console.log(output.join('\n'));
console.error(JSON.stringify({
  mode: 'EMIT_PATCH_ONLY', source_set_before: sourceSet, edited_rows: edits.length,
  primary_edits: edits.filter(edit => edit.newPrimary).length,
  text_only_edits: edits.filter(edit => !edit.newPrimary).length
}));
