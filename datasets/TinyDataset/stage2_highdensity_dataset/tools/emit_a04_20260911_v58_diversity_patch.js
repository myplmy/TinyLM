/*
 * Emits, but never applies, the first bounded A04 correction patch.
 * Source mutation remains an explicit platform apply_patch operation.
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const expectedSourceSet = 'f465f9c6e8d793dfebee44cbae47e04b98e7842f33e0cb3622291554d50c5d97';
const pattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');

// [version, 1-based line, expected primary, replacement text, optional replacement primary]
const edits = [
  [55, 129, '열공급 최종확인', '열공급 최종확인은 여러 측정값이 기준에 맞아 공급 인계가 가능한 상태다. 검사 횟수와 담당자를 남긴다.'],
  [56, 103, '해양 부표 수질안정 — 염분·탁도·수온 상태', '해양 부표 수질안정 — 복합 수질지표 안정은 여러 수질 지표가 관측 구간마다 고르게 유지된 상태다. 시료 식별값과 채수 시각으로 다음 관측을 정한다.', '해양 부표 수질안정 — 복합 수질지표 안정'],

  [58, 4, '산림 예찰징후 — 가뭄 촉발·억제', '산림 예찰징후 — 가뭄 촉발·억제에서는 수액 감소가 피해 단계를 올리고 일시 가뭄이 병해충 판정을 미룬다. 수액값·토양 수분을 기록한다.'],
  [58, 7, '산림 예찰징후 — 균열 촉발·억제', '산림 예찰징후 — 균열 촉발·억제는 껍질 균열로 병원체 검사를 열지만 생장 균열은 과잉 방제를 막는다. 균열 폭·수종 정보를 기록한다.'],
  [58, 10, '산림 예찰징후 — 병반 촉발·억제', '산림 예찰징후 — 병반 촉발·억제에서 병반 가장자리 확대는 감염 경계를 세우게 하고 봉합 흔적은 새 감염 판단을 막는다. 병반 면적·관찰일을 기록한다.'],
  [58, 12, '산림 예찰징후 — 유입 촉발·억제', '산림 예찰징후 — 유입 촉발·억제는 포획량 증가로 성충 발생을 확인하되 우연 유입은 지역 발생 판정에서 제외한다. 포획량과 트랩 위치를 남긴다.'],
  [58, 14, '산림 예찰징후 — 면적 촉발·억제', '산림 예찰징후 — 면적 촉발·억제는 수관 갈변 면적이 커지면 피해 등급을 올리고 계절성 갈변은 비가역 판정에서 뺀다. 면적값과 수종을 저장한다.'],
  [58, 15, '산림 예찰징후 — 감소 촉발·억제', '산림 예찰징후 — 감소 촉발·억제는 송진 감소로 수세 저하를 의심하되 강우 직후 변화는 장기 쇠약 판정에서 뺀다. 분비량과 강우 시각을 남긴다.'],
  [58, 16, '산림 예찰징후 — 증가 촉발·억제', '산림 예찰징후 — 증가 촉발·억제는 천공구 증가로 침입 확산을 의심하지만 이전 구멍만으로 현재 확산을 판단하지 않는다. 구멍 수·지점을 적는다.'],
  [58, 22, '산림 예찰징후 — 유실 촉발·억제', '산림 예찰징후 — 유실 촉발·억제는 집중호우 뒤 유실로 뿌리 노출을 확인하되 복구 토사가 있으면 확대 판단을 막는다. 유실 깊이·강우량을 기록한다.'],
  [58, 24, '산림 예찰징후 — 건조 촉발·억제', '산림 예찰징후 — 건조 촉발·억제는 경계 건조가 심해지면 가장자리 피해를 경계하고 차광막 설치 뒤에는 확대 판단을 늦춘다. 습도와 위치를 남긴다.'],
  [58, 25, '산림 예찰징후 — 지연 촉발·억제', '산림 예찰징후 — 지연 촉발·억제에서는 생존율 저하가 보식을 열고 일시 활착 지연이 보식을 멈춘다. 생존율·조사일을 보관한다.'],
  [58, 27, '산림 예찰징후 — 발육 촉발·억제', '산림 예찰징후 — 발육 촉발·억제에서는 발육 단계가 성충 방제를 앞당기지만 우화 전 유충이 살포를 늦춘다. 발육 등급과 기온을 남긴다.'],
  [58, 28, '산림 예찰징후 — 포식성 촉발·억제', '산림 예찰징후 — 포식성 촉발·억제는 포식성 천적 증가 때 화학 처치를 줄이고 피해 증가 때 보완 방제를 시작한다. 천적 수와 피해율을 남긴다.'],
  [58, 34, '산림 예찰징후 — 계류 촉발·억제', '산림 예찰징후 — 계류 촉발·억제는 계류 탁도가 오르면 토사 유입을 조사하고 침사지 정비 뒤에는 추가 유입 판정을 늦춘다. 탁도와 측정 시각을 기록한다.'],
  [58, 36, '산림 예찰징후 — 연속성 촉발·억제', '산림 예찰징후 — 연속성 촉발·억제는 병반 연결이 길어지면 격리구역을 넓히고 자연 단절이 있으면 확대를 멈춘다. 연결도와 지형 단절을 기록한다.'],
  [58, 37, '산림 예찰징후 — 표본 촉발·억제', '산림 예찰징후 — 표본 촉발·억제는 배양 속도 증가로 활성 전환을 검토하며 대조 배양이 멈추면 확정을 보류한다. 배양 시간·온도를 기록한다.'],
  [58, 39, '산림 예찰징후 — 정지 촉발·억제', '산림 예찰징후 — 정지 촉발·억제는 둘레 생장이 멈추면 장기 피해를 검토하고 생장이 돌아오면 판정을 미룬다. 둘레값과 측정 시각을 적는다.'],
  [58, 43, '산림 예찰징후 — 수관 촉발·억제', '산림 예찰징후 — 수관 촉발·억제는 수관 회복이 보이면 방제 종료를 검토하지만 새 병반이 있으면 계속한다. 회복 지표·병반 면적을 남긴다.'],
  [58, 45, '산림 예찰징후 — 방제 촉발·억제', '산림 예찰징후 — 방제 촉발·억제는 방제 뒤 개체 수 감소로 복구 전환을 시작하지만 잔존 개체가 있으면 전환하지 않는다. 수량과 처리 시각을 남긴다.'],
  [58, 46, '산림 예찰징후 — 손상 촉발·억제', '산림 예찰징후 — 손상 촉발·억제는 잎 손상 감소로 회복을 검토하되 고사점 증가 때는 중단한다. 손상률과 처리량을 적는다.'],
  [58, 47, '산림 예찰징후 — 잔류량 촉발·억제', '산림 예찰징후 — 잔류량 촉발·억제는 토양 잔류량 초과 때 복원 조치를 시작하며 희석된 경우 확대 조치를 멈춘다. 잔류값·측정 위치를 남긴다.'],
  [58, 49, '산림 예찰징후 — 복구 촉발·억제', '산림 예찰징후 — 복구 촉발·억제는 식재 활착률 상승으로 정상화를 검토하고 건조가 재발하면 보류한다. 활착률과 토양 수분을 저장한다.'],
  [58, 52, '산림 복구판정 — 신호 촉발·억제', '산림 복구판정 — 신호 촉발·억제는 생존 신호가 회복 판정을 열고 뿌리 괴사가 있으면 손실 판정을 늦춘다. 생존율·괴사 등급을 보관한다.'],
  [58, 59, '산림 복구판정 — 재발견 촉발·억제', '산림 복구판정 — 재발견 촉발·억제는 개체 밀도 하락으로 방제 종료를 검토하되 유충 재발견이면 종료를 보류한다. 밀도와 발견 시각을 적는다.'],
  [58, 67, '산림 복구판정 — 감소 촉발·억제', '산림 복구판정 — 감소 촉발·억제는 침식률 저하로 식생 회복을 검토하되 강우 재증가면 보류한다. 침식률·강우량을 기록한다.'],
  [58, 69, '산림 복구판정 — 활착 촉발·억제', '산림 복구판정 — 활착 촉발·억제는 수변 식생 활착으로 완충대 회복을 열고 유실 묘목이 남으면 미룬다. 활착률·유실 수를 저장한다.'],
  [58, 73, '산림 복구판정 — 산불 촉발·억제', '산림 복구판정 — 산불 촉발·억제는 산불 뒤 수분 회복 때 발아를 관찰하되 표토 유실이 크면 보강부터 한다. 수분값과 유실 깊이를 남긴다.'],
  [58, 77, '산림 복구판정 — 천적 촉발·억제', '산림 복구판정 — 천적 촉발·억제는 천적·기주 균형이 돌아오면 화학 처치를 멈추며 기주 급증 시 계속한다. 천적 비율과 기주 수를 남긴다.'],
  [58, 95, '산림 복구판정 — 방제 촉발·억제', '산림 복구판정 — 방제 촉발·억제는 수종 생존율 상승으로 처리 완화를 열고 생존율 하락이 보이면 유지한다. 생존율·수종 정보를 기록한다.'],
  [58, 105, '산림 회복기록 — 재검출 촉발·억제', '산림 회복기록 — 재검출 촉발·억제는 수질 시험이 정상화되면 하류 감시를 완화하되 독성이 다시 나오면 유지한다. 시험값과 채취 위치를 기록한다.'],
  [58, 113, '산림 회복기록 — 면적 촉발·억제', '산림 회복기록 — 면적 촉발·억제는 피복 증가로 완충대 회복을 검토하고 유실 면적이 크면 미룬다. 피복률·유실 면적을 남긴다.'],

  [64, 63, '터널 신호이탈 — 지연 촉발·억제', '터널 신호이탈 — 지연 촉발·억제는 신호 도착이 늦어지면 수동 신호로 바꾸되 인력이 부족하면 전환을 늦춘다. 지연값·인력 상태를 남긴다.'],
  [64, 84, '터널 교대확인 — 인계 누락 점검', '터널 교대확인 — 교대 전 기록 대조는 관제 화면과 순찰 결과를 대조해 미처리 통제·배수 항목을 찾는 점검이다. 불일치가 없을 때 교대를 기록한다.', '터널 교대확인 — 교대 전 기록 대조']
];

const files = fs.readdirSync(sourceDir).filter(file => pattern.test(file)).sort();
const digests = Object.fromEntries(files.map(file => [file, sha256(fs.readFileSync(path.join(sourceDir, file)))]));
const sourceSet = sha256(files.map(file => file + '\t' + digests[file]).join('\n'));
if (sourceSet !== expectedSourceSet) throw new Error('source-set drift: expected ' + expectedSourceSet + ', got ' + sourceSet);
const seen = new Set();
const patchByFile = new Map();
for (const [version, line, primary, text, newPrimary] of edits) {
  const key = version + ':' + line;
  if (seen.has(key)) throw new Error('duplicate edit: ' + key);
  seen.add(key);
  const file = files.find(name => Number(name.match(pattern)[1]) === version);
  if (!file) throw new Error('missing version v' + version);
  const rows = fs.readFileSync(path.join(sourceDir, file), 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  const row = rows[line - 1];
  if (!row || row.primary !== primary) throw new Error('primary drift at ' + key);
  const next = { ...row, primary: newPrimary || row.primary, text };
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
console.error(JSON.stringify({ mode: 'EMIT_PATCH_ONLY', source_set_before: sourceSet, edited_rows: edits.length, primary_edits: edits.filter(edit => edit[4]).length }));
