/* Post-editorial A04 corrections: token-boundary compression, one residual
 * TF-IDF pair, and human-reviewed numeric-primary particles. --apply writes.
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const apply = process.argv.includes('--apply');
const expectedSourceSet = '219aa2db9ec5b3b360492f0218a25aed181641ef0cf447f3adff7ab5aac4cfde';
const files = fs.readdirSync(sourceDir)
  .filter(file => /^stage2_\(14\)state_transition_high_density_train_v\d+\.source\.jsonl$/.test(file))
  .sort();
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const sourceSet = sha256(files.map(file => sha256(fs.readFileSync(path.join(sourceDir, file)))).join(''));
if (sourceSet !== expectedSourceSet) throw new Error(`source-set drift: expected ${expectedSourceSet}, got ${sourceSet}`);

const repairs = {
  34: {
    35: '저장장치 충전재개허용 조건판정은 정지 원인이 풀리고 온도·전압·예약 시간이 모두 허용될 때 전류를 다시 여는 결정이다. 원인 하나의 해제만으로 재개하지 않는다.',
    43: '저장장치 주파수상승흡수 조건판정은 계통 주파수가 상향 문턱을 일정 시간 넘을 때 흡수 출력을 늘리는 판단이다. 순간 첨두는 지속 조건에서 제외한다.',
    46: '저장장치 충전우선순위변경 조건판정은 새 요청의 긴급도·계약 등급이 더 높고 전환 비용도 감당할 때 순서를 바꾸는 판단이다. 동률이면 기존 배정을 유지한다.',
    47: '저장장치 충전계량개시 조건판정은 충전 지령, 계량기 초기값, 기준시각이 확인된 순간 새 검침 구간을 여는 결정이다. 시각이 어긋나면 개시를 보류한다.'
  },
  36: {
    36: '저장장치 충전경로진단 복구경로는 지령 전달 순서대로 변환기·접촉기·관리장치 허가를 시험한다. 끊긴 지점을 수리한 뒤 낮은 전류로 연결을 검증한다.',
    39: '저장장치 충전목표재계획 복구경로는 출력 포화 때 가용 전력과 남은 시간으로 도달 가능한 충전량을 다시 산정한다. 부품을 빨리 복구하면 기존 계획으로 돌아간다.',
    40: '저장장치 충전상한접근 중간상태는 충전율과 셀 전압의 상한 여유가 작아 전류를 줄였지만 휴지 검증 전인 단계다. 완료와 실패 모두 아직 확정할 수 없다.',
    53: '저장장치 저온셀회복불능 흡수상태는 히터를 가동해도 특정 셀 온도가 오르지 않아 충전 허가에 도달하지 못하는 상태다. 센서와 열전달 경로를 나눠 점검한다.'
  },
  54: {
    108: '클린룸 복구재시도108은 직전 공정 복원이 멈춘 장비 단계의 원인을 고친 뒤 시험 로트로 가동을 다시 여는 절차다. 오염 측정이 합격해야 양산 순서를 복원한다.'
  },
  59: {
    149: '전기버스 운영종료149는 운행·충전 기록을 마감하고 미정산 전력과 미귀고 차량을 확인하는 단계다. 남은 항목은 야간 인계 건으로 분류한다.'
  },
  60: {
    141: '발효 문서복귀141은 장비 원자료와 작업지가 일치해 누락 구간을 공식 배치 기록에 편입하는 과정이다. 상충값은 품질 담당의 판정을 기다린다.'
  },
  61: {
    142: '센터 최종승인142는 보완 시험이 모두 합격하고 잔류 경보 감시 계획도 마련되어 정상 부하를 허용하는 결정이다. 중요 서비스부터 단계적으로 되돌린다.'
  },
  62: {
    149: '항만 일일재개149는 장비 점검과 전일 정산을 끝낸 뒤 새 하역일의 작업 순번을 여는 과정이다. 미해결 위험 선석은 제외하고 대체 위치를 배정한다.'
  },
  63: {
    134: '축사 최종이탈134는 가스 초과와 질병 징후가 함께 남아 정상 사육 대신 격리를 유지하는 상태다. 검사값이 회복돼도 개체 관찰 기간을 따로 충족해야 한다.'
  },
  65: {
    132: '공항 안전점검132는 차단선 안에 작업차량과 이물질이 남지 않았는지 순찰한 뒤 활주로 개방을 검토하는 단계다. 구역별 확인자가 모두 응답해야 관제에 완료를 통보한다.'
  },
  67: {
    4: '도시열공급 열원가동004는 공급수 온도가 안정 방향으로 낮아져 과열 제한을 완화할 수 있는 전이다. 말단 온도까지 확인한 뒤 열원 출력을 단계적으로 되돌린다.'
  }
};

const changed = [];
for (const [versionText, changes] of Object.entries(repairs)) {
  const version = Number(versionText);
  const file = files.find(name => name.includes(`_v${String(version).padStart(2, '0')}.source.jsonl`));
  const filePath = path.join(sourceDir, file);
  const records = fs.readFileSync(filePath, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  for (const [lineText, text] of Object.entries(changes)) {
    const line = Number(lineText);
    const record = records[line - 1];
    if (!record || !text.includes(record.primary)) throw new Error(`${file}:${line} lost primary literal`);
    records[line - 1] = { ...record, text };
    changed.push({ version, line, primary: record.primary });
  }
  if (apply) fs.writeFileSync(filePath, records.map(record => JSON.stringify(record)).join('\n') + '\n', 'utf8');
}
console.log(JSON.stringify({ mode: apply ? 'APPLIED' : 'PREVIEW', source_set_before: sourceSet, repaired_records: changed.length, changed }, null, 2));
