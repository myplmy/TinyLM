/* One-shot A04 v66~v69 diversity repair.
 * Default is preview only; pass --apply to write the four explicitly scoped source files.
 * The repair changes text only and keeps primary, relations, IDs, order, and row count intact.
 */
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const versions = [66, 67, 68, 69];
const apply = process.argv.includes('--apply');

function sourcePath(version) {
  return path.join(sourceDir, `stage2_(14)state_transition_high_density_train_v${String(version).padStart(2, '0')}.source.jsonl`);
}

function subjectOf(primary) {
  return primary.replace(/\d+$/, '');
}

// Explicit metric reservation prevents a source wording change from becoming
// an accidental parser dependency during a later repair rerun.
const metricsByVersion = {
  66: ['세정액 농도', '레지스트 점도', '현상액 온도', '식각가스 유량', '플라즈마 세기', '증착막 두께', '배선 저항', '이온 주입량', '열처리 온도', '세정수 유량', '챔버 압력', '클린룸 차압', '필터 차압', '입자 수', '표면 오염도', '이송 시각', '포드 보관온도', '마스크 정렬값', '노광 초점', '정렬 오차', '선폭', '막 두께', '결함 수', '수율', '로트 위치', '레시피 버전', '정비 주기', '누설 농도', '화학물질 잔량', '폐액 수위'],
  67: ['공급수 온도', '펌프 회전수', '주배관 압력', '열교환 온도차', '축열조 잔량', '수송유량', '밸브 개도', '실내 열사용량', '상가 열사용량', '공공건물 부하', '검침 시각', '수요 예측값', '외기 온도', '조정 압력', '누수량', '전환 유량', '연료 잔량', '배출 농도', '정비 주기', '공사 구간', '복구 진행도', '요금 검침값', '민원 건수', '공급 제한량', '비상 출력', '밸브 해제압력', '수요 조정폭', '센터 응답시간', '열손실률', '회의 결정시각'],
  68: ['표층 수온', '해수 염분', '유의파고', '풍속', '풍향', '기압', '파향', '조류 속도', '조류 방향', '수중 소음', '클로로필', '탁도', '용존산소', '수심', '해저 고도', '선박 식별값', 'AIS 수신률', '부표 좌표', '표류 거리', '계류 장력', '배터리 잔량', '충전 전류', '통신 지연', '위성 송신률', '경보 점수', '적조 농도', '파고 경보', '재부팅 시각', '회수 위치', '재배치 좌표'],
  69: ['배정표 상태', '식별밴드 번호', '동의서 서명', '금식 시작시각', '알레르기 표기', '감염 선별값', '검사 결과', '마취 위험도', '수술전실 압력', '기구 멸균도', '멸균 지시값', '수술복 착용', '손위생', '수술실 차압', '필터 교체시각', '절개 표시', '타임아웃 기록', '시작 시각', '검체 라벨', '출혈량', '수혈', '환자 체온', '수술 경과시간', '회복 점수', '회복실 청결도', '검체 보관온도', '정리 완료도', '감염 보고시각', '항생제 투여량', '퇴실 점수']
};

/*
 * These are direct, meaning-level prose forms rather than an ID suffix swap.
 * Every five-record concept group receives a different form; groups in another
 * family rotate by a different offset.  {{P}}/{{M}}/{{S}} stand for primary,
 * measured property, and the primary with its numeric suffix removed.
 */
const forms = [
  [
    '{{P}}의 {{M}} 판정은 {{S}}의 추가 표본이 올 때까지 대기 상태다. 관측 시각과 원자료를 남겨 다음 확인 순서를 잡는다.',
    '{{P}}에서는 {{M}}을 첫 수치만으로 확정하지 않는다. {{S}} 이력을 분리 보관한 뒤 비교 기준이 갖춰지면 다시 판단한다.',
    '{{P}}의 {{M}}은 초기 측정 단계에 머문다. {{S}} 기록을 재검토 목록으로 옮기고 누락된 표본의 도착을 기다린다.',
    '{{P}}는 {{M}} 확인을 잠시 멈춘 상태를 가리킨다. {{S}}의 채집 조건과 읽은 값을 함께 적어 후속 점검에 넘긴다.',
    '{{P}}의 {{M}}은 보류 표시에 남는다. {{S}} 자료의 시간 순서를 맞춘 뒤 검증 담당이 다음 조치를 선택한다.',
    '{{P}}는 {{M}}의 근거가 충분하지 않은 대기 전이다. {{S}} 관측값과 장비 상태를 묶어 확인 차례를 다시 세운다.',
    '{{P}}의 {{M}} 기록은 아직 결론으로 쓰지 않는다. {{S}}의 최근 표본을 모은 뒤 재측정 여부를 결정한다.',
    '{{P}}에서는 {{M}} 검증을 다음 관찰 주기로 넘긴다. {{S}}의 원시 자료와 수집 시각을 보존해 비교 가능하게 한다.',
    '{{P}}의 {{M}}은 점검 시작 전의 임시 값이다. {{S}} 이력의 빈칸을 확인하고 남은 항목을 채운 뒤 판정한다.',
    '{{P}}는 {{M}} 확인을 위한 대기 상태를 설명한다. {{S}} 목록에 확인자와 시각을 적어 처리 순서를 고정한다.',
    '{{P}}의 {{M}}은 표본 검토가 끝나지 않아 보류된다. {{S}}의 수집 경로를 확인해 다음 측정 위치를 정한다.',
    '{{P}}에서는 {{M}} 판정을 유예하고 {{S}} 자료를 정렬한다. 서로 다른 시각의 값은 같은 기준으로 맞춘 뒤 살핀다.',
    '{{P}}의 {{M}}은 확인 자료가 모일 때까지 임시 상태다. {{S}} 기록의 출처를 표시해 재검토 범위를 좁힌다.',
    '{{P}}는 {{M}}을 다시 읽기 전의 대기 표지다. {{S}} 관측 이력과 장비 응답을 대조해 확인 순번을 배정한다.',
    '{{P}}의 {{M}} 확인은 보조 자료를 기다린다. {{S}}의 앞선 값과 새 표본을 이어 붙여 다음 판정에 사용한다.'
  ],
  [
    'P의 M 변동은 S 전환을 검토하게 한다. 예비 수단의 준비 상태를 확인한 뒤 변경 여부를 정한다.',
    'P는 M 이상 신호가 들어왔을 때의 갈림길이다. S 대체 경로와 현재 여력을 비교해 대응을 선택한다.',
    'P의 M 변화는 S 운전 방식을 다시 고를 근거다. 보유 자원과 경보 시각을 확인해 전환을 승인하거나 미룬다.',
    'P는 M이 기준에서 벗어나며 시작되는 상태 변화다. S 예비 장치의 가용성을 살핀 뒤 작업 방향을 정한다.',
    'P의 M 경보는 S 처리 순서의 재검토를 요구한다. 사용 가능한 대안과 부담 수준을 함께 보고 결론낸다.',
    'P에서는 M의 급격한 변화를 전환 신호로 읽는다. S의 여분 설비가 준비됐는지 확인해 다음 단계로 넘긴다.',
    'P의 M 이탈은 S 운전을 조정할 수 있는 조건이다. 장비 여력과 통보 시각을 근거로 대응 폭을 고른다.',
    'P는 M의 비정상 읽기가 나타난 전이다. S 대체 수단의 상태를 점검한 뒤 유지와 전환을 가른다.',
    'P의 M 신호는 S 절차를 바꿀지 판단하는 출발점이다. 예비 자원과 현장 상황을 대조해 결정을 남긴다.',
    'P에서는 M 이상이 S 전환 후보를 만든다. 가능한 조치의 준비 시간을 확인해 실행 순서를 잡는다.',
    'P의 M 변화는 S 운영 선택지를 좁힌다. 경보 발생 시각과 자원 잔량으로 적절한 대응을 택한다.',
    'P는 M 값의 흔들림을 처리 전환으로 연결하는 상태다. S의 대체 방안이 준비되지 않았으면 판단을 보류한다.',
    'P의 M 초과는 S 작업을 재배치할 단서다. 지원 수단의 상태를 살펴 제한과 전환 중 하나를 고른다.',
    'P에서는 M 이상을 확인하고 S 대안을 검토한다. 준비된 자원의 범위를 따져 조치 시작 시점을 정한다.',
    'P의 M 변동은 S 절차의 방향을 바꾸는 계기다. 예비 경로와 현장 부담을 확인해 다음 선택을 기록한다.'
  ],
  [
    'P의 M은 S 기준 범위와 대조한다. 벗어난 값은 재측정 목록으로 보내고 원인을 구분한다.',
    'P에서는 M을 S의 허용선과 맞춰 본다. 차이가 확인되면 해당 읽기를 격리해 다시 검증한다.',
    'P의 M 검증은 S 기준표와 현재 값을 비교하는 과정이다. 불일치한 표본은 별도 점검으로 돌린다.',
    'P는 M이 S의 설정값을 만족하는지 가르는 상태다. 범위를 넘은 관측치는 재확인 대상으로 표시한다.',
    'P의 M은 S 기준선에 비추어 판정한다. 어긋난 자료는 원인 확인 전까지 후속 처리에서 뺀다.',
    'P에서는 M 읽기를 S의 정상 구간과 비교한다. 값이 다르면 장비와 표본을 분리해 재측정한다.',
    'P의 M 대조는 S 운영 기준을 기준으로 이뤄진다. 편차가 큰 기록은 검증 대기열에 넣는다.',
    'P는 M 값과 S 허용 범위를 맞춰 보는 단계다. 이탈값은 재수집 여부를 검토하도록 넘긴다.',
    'P의 M은 S 관리 한계와 비교해야 한다. 기준 밖 수치는 즉시 확정하지 않고 추가 확인을 받는다.',
    'P에서는 M의 현재값과 S 참조값을 나란히 둔다. 차이가 남은 항목은 원인별로 분류한다.',
    'P의 M 판정은 S의 허용 편차를 따른다. 벗어난 자료에는 재검사 표시를 붙여 추적한다.',
    'P는 M이 S 기준을 통과하는지 점검하는 상태다. 비교에서 탈락한 값은 격리 목록에 남긴다.',
    'P의 M 읽기는 S 설정 구간과 맞춰 확인한다. 허용선을 넘으면 재측정 순서로 되돌린다.',
    'P에서는 M을 S의 기준값과 비교해 상태를 가른다. 불일치 자료는 독립 확인을 거친다.',
    'P의 M은 S 제한 안에 있는지로 평가한다. 범위 밖 표본은 다음 작업에 쓰지 않고 다시 살핀다.'
  ],
  [
    'P의 M이 안정되면 S 운전 재개를 검토한다. 보정 전후 기록을 맞춰 적용 순서를 고친다.',
    'P에서는 M 회복 뒤 S를 정상 흐름으로 돌릴지 살핀다. 변화 이력을 비교해 보정 항목을 갱신한다.',
    'P의 M 하락은 S 재가동을 논의할 수 있는 신호다. 이전 값과 현재 값을 대조해 처리 순서를 조정한다.',
    'P는 M이 안정 구간으로 돌아온 뒤의 복귀 상태다. S 기록을 다시 읽고 남은 보정 작업을 정한다.',
    'P의 M 회복은 S 운전 제한을 풀지 검토하게 한다. 교정 이력과 확인값으로 다음 단계를 배치한다.',
    'P에서는 M이 가라앉은 뒤 S 정상화를 준비한다. 관측 자료의 앞뒤를 확인해 수정할 순서를 고른다.',
    'P의 M 안정은 S 복귀 후보를 만든다. 보정 기록을 재검토해 적용 범위와 우선순위를 정한다.',
    'P는 M 감소 후 S 처리를 다시 여는 전이다. 이전 측정과 새 결과를 맞춰 변경 목록을 고친다.',
    'P의 M이 허용선 안으로 돌아오면 S 재개를 검토한다. 수정 전 자료와 후속 값을 비교해 순서를 재배열한다.',
    'P에서는 M 안정 신호 뒤 S의 정상 운전 가능성을 평가한다. 보정 근거를 정리해 실행 차례를 정한다.',
    'P의 M 회복은 S 작업을 재개할 단서다. 최근 기록과 교정 내역을 함께 보고 조정 항목을 고른다.',
    'P는 M 하락 이후 S의 제한을 완화하는 상태다. 확인값을 대조해 보정 순서와 담당을 정한다.',
    'P의 M이 안정된 뒤 S 복귀를 준비한다. 앞선 편차와 보정 결과를 확인해 적용 목록을 다듬는다.',
    'P에서는 M 회복을 근거로 S 정상화를 검토한다. 기록의 시간 순서를 맞춘 뒤 변경 우선순위를 정한다.',
    'P의 M 감소는 S 재가동을 다시 살필 시점이다. 교정 전후 값을 비교해 다음 조치를 조절한다.'
  ],
  [
    'P의 M 보정이 끝나면 S 점검을 다시 연다. 새 불일치가 나타날 경우 다음 처리를 보류한다.',
    'P에서는 M을 조정한 뒤 S 확인 단계로 넘긴다. 추가 이상이 남으면 관찰 상태를 유지한다.',
    'P의 M 교정 후에는 S 상태를 재검사한다. 기록이 맞지 않으면 후속 작업을 잠시 멈춘다.',
    'P는 M 보완을 마치고 S 점검으로 되돌아간 상태다. 남은 편차가 있으면 처리 순서를 미룬다.',
    'P의 M 수정은 S 검증을 재개하는 계기다. 새 경보가 확인되면 다음 전환을 허용하지 않는다.',
    'P에서는 M 보정 뒤 S의 확인 절차를 이어 간다. 불일치 자료가 있으면 대기 표지를 남긴다.',
    'P의 M 정리가 끝나면 S 점검 결과를 다시 받는다. 이상 신호가 남아 있으면 다음 단계를 늦춘다.',
    'P는 M 조정 후 S 관찰을 재개하는 전이다. 확인값이 어긋나면 후속 처리를 보류한다.',
    'P의 M 보정 뒤 S 점검을 새로 시작한다. 오차가 계속되면 현 상태를 유지하고 추가 확인을 받는다.',
    'P에서는 M을 바로잡은 후 S 검사를 다시 시행한다. 남은 경보는 다음 처리의 시작을 막는다.',
    'P의 M 교정은 S 재점검으로 이어진다. 자료가 일치하지 않으면 처리 순서를 나중으로 미룬다.',
    'P는 M 보완 뒤 S 상태를 확인하는 단계다. 불안정한 신호가 나오면 관찰을 계속한다.',
    'P의 M 조정 후 S 검증을 다시 개시한다. 새 편차가 발견되면 다음 전환을 대기시킨다.',
    'P에서는 M 보정 결과로 S 점검을 재개한다. 이력의 불일치가 남으면 현재 상태를 고정한다.',
    'P의 M 수정 뒤 S 확인을 한 번 더 진행한다. 추가 이상이 나오면 후속 작업을 멈춰 둔다.'
  ]
];

// A second, independently authored set removes the old 15-group cycle.  It
// deliberately changes both the evidence and the transition action so that
// records 75 places apart do not merely exchange their primary literal.
const secondaryForms = [
  [
    'P의 M 자료는 S 이력과 맞춰야 하므로 판정을 잠시 중단한다. 수집 경로를 표시해 재확인 담당에게 전달한다.',
    'P의 M 확인은 S의 두 번째 읽기를 기다린다. 이전 전송 기록을 보관하고 대조할 항목을 지정한다.',
    'P의 M은 S 검토표에 임시로 표시한다. 결손값의 위치를 밝혀 다음 관측에서 보완한다.',
    'P의 M 처리에는 S 표본의 출처가 더 필요하다. 시간대별 자료를 분류한 뒤 판정 순번을 정한다.',
    'P의 M 판단은 S의 원본 기록이 도착할 때까지 유보한다. 확인 시각과 장비 응답을 함께 남긴다.',
    'P의 M은 S 점검 전에 보류 목록에 넣는다. 추가 관찰이 끝나면 비교 기준을 적용한다.',
    'P의 M 정보는 S 자료의 누락 여부를 확인하는 동안 열린다. 읽은 값과 수집 시각을 연결해 둔다.',
    'P의 M 확인은 S의 재측정 요청으로 이어진다. 앞선 기록을 보존해 변화 경로를 추적한다.',
    'P의 M은 S 표본이 불완전해 즉시 확정하지 않는다. 빈 항목을 채울 담당과 순서를 적는다.',
    'P의 M 판정은 S 관찰 자료를 묶은 뒤 진행한다. 서로 다른 시간의 값은 별도로 표시한다.',
    'P의 M 확인은 S 기록의 출처 검증을 먼저 요구한다. 수집 조건과 확인자를 남겨 다음 차례로 넘긴다.',
    'P의 M은 S 이력의 마지막 값이 정리될 때까지 대기한다. 재검토 범위와 보류 이유를 표시한다.',
    'P의 M 자료는 S의 보조 관측과 함께 살핀다. 아직 맞지 않는 항목은 확인 목록에 유지한다.',
    'P의 M은 S 관련 기록을 보완한 후에만 결론낸다. 원자료와 처리 시각을 나란히 저장한다.',
    'P의 M 처리에는 S의 추가 읽기가 필요하다. 보류 사유를 적고 다음 검사 순서를 조정한다.'
  ],
  [
    'P의 M 변화는 S 운전에 제한을 둘지를 알리는 신호다. 대체 설비의 준비도를 확인하고 대응 폭을 결정한다.',
    'P의 M 이상은 S 절차를 바꿀 수 있는 계기다. 남은 자원과 경보 시간을 살펴 실행 여부를 정한다.',
    'P의 M 이탈은 S 작업의 우선순위를 새로 정하게 한다. 가능한 대안과 현장 부담을 비교한다.',
    'P의 M 경향은 S 운전 전환을 검토하는 단서다. 보조 수단의 가용 범위를 확인해 시작 시점을 고른다.',
    'P의 M 신호는 S 처리 방향을 재평가하게 한다. 예비 경로와 현재 용량을 대조해 조치를 택한다.',
    'P의 M 변동은 S 대응책을 선택하기 전의 상태다. 장비 여력과 통보 순서를 확인해 결정을 남긴다.',
    'P의 M 초과는 S 역할 배치를 조정할 수 있다. 지원 수단의 준비 여부에 따라 전환을 열거나 닫는다.',
    'P의 M 이상값은 S 운전 변경을 고려하게 한다. 대체 경로의 응답 시간과 부담을 살펴 본다.',
    'P의 M 변화는 S의 다음 단계를 결정하는 입력이다. 예비 자원의 상태를 확인해 보류와 실행을 가른다.',
    'P의 M 이탈은 S 절차에 경고를 붙인다. 준비된 장비와 필요한 시간을 비교해 대응 순서를 정한다.',
    'P의 M 경보는 S 작업을 제한하거나 옮길 근거다. 사용 가능한 지원책을 검토한 뒤 범위를 결정한다.',
    'P의 M 흔들림은 S 전환 후보를 만든다. 현장 여력과 대안의 준비 상태를 확인해 판단한다.',
    'P의 M 이상은 S 운영 선택지를 다시 열어 둔다. 자원 잔량과 경보 시각을 근거로 조치를 고른다.',
    'P의 M 변화는 S 처리의 갈림길이다. 대체 수단의 상태를 보고 유지와 전환 중 하나를 정한다.',
    'P의 M 신호는 S 운전에 새 제약을 더한다. 예비 장치와 담당자 준비를 확인해 순서를 배치한다.'
  ],
  [
    'P의 M은 S 기준표의 해당 구간과 맞춘다. 편차가 난 표본은 재확인 경로로 분리한다.',
    'P의 M 확인은 S 관리값과의 차이를 계산하는 단계다. 이탈 수치는 원인 점검 목록에 남긴다.',
    'P의 M 값은 S 참조 범위 안인지로 가른다. 경계를 넘은 읽기는 독립 측정을 요청한다.',
    'P의 M 대조는 S의 설정 한계를 따른다. 차이가 큰 기록은 후속 판단에서 잠시 제외한다.',
    'P의 M은 S 허용 구간에 비추어 상태를 정한다. 맞지 않는 표본은 재수집 대상으로 넘긴다.',
    'P의 M 검사는 S 기준값과 현재 읽기를 나란히 둔다. 불일치 항목은 검증 대기열로 보낸다.',
    'P의 M은 S의 정상 폭을 벗어나는지 확인한다. 이탈한 자료는 장비 점검과 함께 다시 읽는다.',
    'P의 M 비교에서는 S의 상하한을 적용한다. 허용선을 넘은 값에는 재검사 표시를 붙인다.',
    'P의 M은 S 기준과 얼마나 떨어졌는지로 평가한다. 큰 편차는 원인별로 나누어 확인한다.',
    'P의 M 판정은 S 참조값의 범위를 사용한다. 범위 밖 관측치는 재측정 순서로 되돌린다.',
    'P의 M 검증은 S 관리 기준에 따라 이뤄진다. 맞지 않는 수치는 확정 전에 다시 확인한다.',
    'P의 M 읽기는 S 제한값을 통과하는지 점검한다. 탈락한 항목은 별도 목록으로 옮긴다.',
    'P의 M은 S 운전 기준과 대조해 분류한다. 경계 밖 자료는 추가 표본을 받아 판정한다.',
    'P의 M 비교는 S 허용 편차를 기준으로 한다. 차이가 남으면 재확인 담당에게 넘긴다.',
    'P의 M은 S의 기준 구간 안에 있는지 확인한다. 벗어난 값은 원인 확인 뒤에만 사용한다.'
  ],
  [
    'P의 M이 회복되면 S 운전 제한을 완화할지 살핀다. 이전 이상과 새 결과를 맞춰 적용 순서를 정한다.',
    'P의 M 안정은 S 복구 절차를 시작할 단서다. 보정 이력과 현재 값을 비교해 작업을 배치한다.',
    'P의 M 하락 뒤에는 S를 정상 경로로 돌릴 수 있는지 검토한다. 교정 근거를 정리해 우선순위를 조절한다.',
    'P의 M이 기준 안으로 돌아오면 S 재개 여부를 판단한다. 앞선 편차와 확인값을 대조해 범위를 고친다.',
    'P의 M 감소는 S 운전 복원을 논의하는 상태다. 변화 기록을 다시 읽고 남은 수정 항목을 고른다.',
    'P의 M 안정 신호는 S 제한을 풀 후보가 된다. 보정 전후의 이력을 맞춰 실행 차례를 잡는다.',
    'P의 M 회복 뒤 S 처리를 다시 열지 검토한다. 측정 흐름과 교정 내역을 보아 적용 범위를 정한다.',
    'P의 M이 정상 폭에 들어오면 S 복귀를 준비한다. 과거 이탈값과 새 읽기를 비교해 순서를 바꾼다.',
    'P의 M 안정은 S 정상화를 위한 출발점이다. 수정 자료를 검토해 담당과 진행 순서를 정한다.',
    'P의 M 하락은 S 운전 재개를 살필 시점이다. 보정 기록을 정리하고 남은 제약을 확인한다.',
    'P의 M이 회복되면 S의 다음 단계가 다시 열린다. 교정 결과와 확인 시각을 대조해 계획을 다듬는다.',
    'P의 M 감소 뒤 S 제한을 조정할 수 있다. 이전 자료와 현재 측정을 이어 보정 목록을 고친다.',
    'P의 M 안정은 S 복구 후보를 만든다. 변화 원인과 확인값을 같이 보아 적용 순서를 정한다.',
    'P의 M 회복은 S를 재가동할 근거가 된다. 기록의 시간대를 맞추고 조정할 항목을 선택한다.',
    'P의 M이 정상 범위에 머물면 S 복귀를 검토한다. 보정 내역과 새 표본을 비교해 차례를 배치한다.'
  ],
  [
    'P의 M 보완 뒤에는 S 확인 결과를 다시 받는다. 새 이상이 있으면 후속 전환을 늦춘다.',
    'P의 M 조정은 S 재검사의 시작점이다. 남은 불일치는 관찰 목록에 두고 처리하지 않는다.',
    'P의 M 교정 후 S 상태를 한 번 더 점검한다. 편차가 이어지면 다음 작업을 멈춘다.',
    'P의 M 수정이 끝나면 S 검증을 다시 시행한다. 경보가 남으면 현재 절차를 유지한다.',
    'P의 M 보정은 S 점검으로 이어진다. 자료가 맞지 않으면 처리 순서를 뒤로 미룬다.',
    'P의 M을 정리한 뒤 S 상태를 재확인한다. 새로운 오차는 다음 단계의 시작을 막는다.',
    'P의 M 교정 뒤 S 관찰을 재개한다. 불안정한 읽기가 나오면 대기 표시를 남긴다.',
    'P의 M 보완은 S 검사를 다시 여는 전이다. 이력이 어긋나면 추가 확인을 받는다.',
    'P의 M을 바로잡은 후 S 점검을 계속한다. 남은 경보는 후속 조치를 보류하게 한다.',
    'P의 M 수정 뒤 S 검증 결과를 다시 살핀다. 새 편차가 보이면 상태를 고정한다.',
    'P의 M 보정은 S 확인 과정을 새로 시작한다. 이상이 지속되면 관찰을 연장한다.',
    'P의 M 교정 후 S 점검 항목을 재배치한다. 맞지 않는 자료는 다음 처리에서 뺀다.',
    'P의 M 조정 뒤 S 상태를 다시 평가한다. 불일치가 남으면 전환을 허용하지 않는다.',
    'P의 M 보완이 끝나면 S 검사를 이어 간다. 확인값이 흔들리면 후속 작업을 늦춘다.',
    'P의 M을 수정한 다음 S 재점검을 진행한다. 추가 이상은 대기 상태를 유지하게 한다.'
  ]
];

function rewrite(primary, subject, metric, group, localSlot, version) {
  const variant = (group + (version - 66) * 7) % 30;
  const collection = variant < 15 ? forms : secondaryForms;
  const form = collection[localSlot][variant % 15];
  if (!form) throw new Error(`Unexpected local slot ${localSlot}`);
  // The older entries use bare P/M/S; first normalize them to protected
  // placeholders so an ASCII letter inside a supplied primary (for example
  // AIS) can never be rewritten by a later replacement.
  const protectedForm = form
    .replace(/(?<!\{)P(?!\})/g, '{{P}}')
    .replace(/(?<!\{)M(?!\})/g, '{{M}}')
    .replace(/(?<!\{)S(?!\})/g, '{{S}}')
    // Numeric primary suffixes make a direct P+particle form awkward.  The
    // added lexical heads keep the primary literal while providing a natural
    // Korean attachment site.  Measured properties use a real 받침 check.
    .replaceAll('{{P}}에서는', '{{P_PROCESS_LOC}}')
    .replaceAll('{{P}}는', '{{P_ITEM_TOPIC}}')
    .replaceAll('{{M}}은', '{{M_TOPIC}}')
    .replaceAll('{{M}}을', '{{M_OBJECT}}')
    .replaceAll('{{M}}이', '{{M_SUBJECT}}');
  const finalType = word => {
    const cp = word.codePointAt(word.length - 1);
    if (!cp || cp < 0xac00 || cp > 0xd7a3) return 'none';
    return (cp - 0xac00) % 28 === 0 ? 'none' : 'final';
  };
  const paired = (word, consonant, vowel) => `${word}${finalType(word) === 'final' ? consonant : vowel}`;
  return protectedForm
    .replaceAll('{{P_PROCESS_LOC}}', `${primary}의 처리에서는`)
    .replaceAll('{{P_ITEM_TOPIC}}', `${primary} 항목은`)
    .replaceAll('{{M_TOPIC}}', paired(metric, '은', '는'))
    .replaceAll('{{M_OBJECT}}', paired(metric, '을', '를'))
    .replaceAll('{{M_SUBJECT}}', paired(metric, '이', '가'))
    .replaceAll('{{P}}', primary)
    .replaceAll('{{M}}', metric)
    .replaceAll('{{S}}', subject);
}

const summary = [];
for (const version of versions) {
  const file = sourcePath(version);
  const rows = fs.readFileSync(file, 'utf8').trimEnd().split(/\r?\n/).map(JSON.parse);
  if (rows.length !== 150) throw new Error(`${path.basename(file)} has ${rows.length} rows`);
  const rewritten = rows.map((row, index) => {
    const group = Math.floor(index / 5);
    const metric = metricsByVersion[version][group];
    if (!metric) throw new Error(`Missing metric reservation for v${version}, group ${group + 1}`);
    // The full medical primary is already present verbatim at the start of a
    // row.  Repeating its shared program prefix in every later clause makes
    // v69 exceed its token budget without adding meaning, so only its final
    // operational noun is used as the later reference.
    const rawSubject = subjectOf(row.primary);
    const subject = version === 69 ? rawSubject.split(/\s+/).at(-1) : rawSubject;
    const text = rewrite(row.primary, subject, metric, group, index % 5, version);
    if (!text.includes(row.primary)) throw new Error(`Primary literal missing: ${row.primary}`);
    return { ...row, text };
  });
  const uniqueTexts = new Set(rewritten.map(row => row.text));
  if (uniqueTexts.size !== rewritten.length) throw new Error(`${path.basename(file)} created duplicate text`);
  summary.push({
    file: path.basename(file),
    records: rewritten.length,
    chars_min: Math.min(...rewritten.map(row => row.text.length)),
    chars_mean: Number((rewritten.reduce((sum, row) => sum + row.text.length, 0) / rewritten.length).toFixed(3)),
    chars_max: Math.max(...rewritten.map(row => row.text.length)),
    preview: rewritten.slice(0, 2).map(row => ({ primary: row.primary, text: row.text }))
  });
  if (apply) fs.writeFileSync(file, rewritten.map(row => JSON.stringify(row)).join('\n') + '\n', 'utf8');
}
console.log(JSON.stringify({ mode: apply ? 'APPLIED' : 'PREVIEW', files: versions.length, rewritten_records: versions.length * 150, summary }, null, 2));
