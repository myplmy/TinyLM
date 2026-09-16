'use strict';

/*
 * Build a row-addressed A06 semantic/naturalness rewrite plan.
 *
 * This program does not edit source or registry.  It emits a JSON plan whose
 * old/new values are later applied through an explicit apply_patch source
 * patch and the line-preserving registry updater.  v01 is intentionally
 * excluded because it is the protected legacy package projection.
 */

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const SOURCE_DIR = path.join(ROOT, 'stage2_highdensity_dataset', 'sources', 'train');
const AUDIT_PATH = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06', 'A06_Semantic_Quality_Audit_Current_2026-09-16.json');
const OUTPUT = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06', 'A06_Semantic_Rewrite_Plan_v16_v52_2026-09-16.json');
const PREVIOUS_PLAN_PATH = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06', 'consolidated', 'A06_Semantic_Rewrite_Plan_PreSource_v02_2026-09-16.json');
const PREFIX = 'stage2_(16)relational_composition_high_density_train_v';

const QUALIFIER = {
  '신호 전달': '신호 경로',
  '대상 추적': '대상 식별',
  '연결 확인': '연결 순서',
  '출처 대조': '출처 확인',
  '범위 확인': '범위 기준',
  '순서 기록': '처리 순서',
  '상태 묶음': '상태 기준',
  '우선 처리': '우선순위',
  '운영 인계': '인계 기준',
  '회복 판정': '복구 조건',
  '경로 보존': '경로 추적',
  '결과 검증': '결과 확인',
  '영향 검토': '영향 범위',
  '중간 판정': '중간 단계',
  '예외 점검': '예외 기준',
  '분기 기록': '분기 조건',
  '독립 확인': '독립 경로',
};

const CUE_VARIANTS = {
  is_a: ['대상이 속한 상위 범주를 명시한다', '개체와 그 상위 종류를 구분한다', '상위 범주와 실제 대상을 함께 적는다'],
  subclass_of: ['하위 범주로 나뉘는 조건을 구분한다', '세부 종류가 어느 범주에 속하는지 적는다', '상위 체계 안의 하위 종류를 표시한다'],
  part_of: ['구성 부분이 어느 전체에 속하는지 확인한다', '구성 부분과 전체 단위를 나누어 적는다', '포함된 부분의 위치를 전체와 함께 기록한다'],
  classification: ['분류 기준과 적용 구간을 함께 표시한다', '분류 체계 안에서의 위치를 확인한다', '분류 항목을 정해진 기준으로 구분한다'],
  boundary: ['혼동하기 쉬운 대상의 경계를 구분한다', '서로 다른 대상을 섞지 않고 분리한다', '구분이 바뀌는 지점을 따로 표시한다'],
  contrast: ['서로 다른 선택지의 차이를 대조한다', '대립하는 지시를 나란히 놓고 대조한다', '충돌한 조건을 각각 기록한다'],
  comparison: ['기준값과 관측값의 차이를 비교한다', '두 수치의 차이를 같은 단위로 비교한다', '높고 낮은 정도를 나란히 확인한다'],
  function: ['각 요소가 맡은 기능을 설명한다', '작업이 수행하는 기능을 확인한다', '기능이 적용되는 지점을 기록한다'],
  role: ['담당 주체와 책임 범위를 명시한다', '작업자의 역할을 구분해 기록한다', '운영 담당자가 맡은 책임을 확인한다'],
  process: ['발생 순서와 이후 단계를 기록한다', '변화가 일어난 뒤의 진행을 적는다', '앞 단계와 다음 단계의 과정을 확인한다'],
  state: ['변경 전후의 상태를 따로 적는다', '각 시점의 상태를 구분한다', '현재 상태와 이전 상태를 함께 확인한다'],
  attribute: ['관련 값과 측정 시각을 보존한다', '관측 수치가 바뀐 시점을 남긴다', '측정된 성질을 원자료와 맞춘다'],
  other: ['근거가 부족한 연결은 미확정으로 남긴다', '확인된 사실만 관계로 기록한다', '결측 구간은 추가 확인 전까지 보류한다'],
};

/*
 * The legacy rows often ended with an opaque dash marker.  The rewrite plan
 * deliberately keeps the original concept as a quoted case description and
 * only applies phrase-level, particle-safe shortening to the primary label.
 * No arbitrary token extraction or synthetic row number is used.
 */
const SAFE_PHRASE_REPLACEMENTS = [
  ['유통 기한표', '유통기한표'],
  ['문 개폐 센서', '문 센서'],
  ['운송 차량', '운송차'],
  ['품질 검사표', '품질표'],
  ['온도 기록계', '온도계'],
  ['운항 회복표', '회복표'],
  ['제설제 저장소', '제설 저장소'],
  ['관측 담당자', '관측자'],
  ['질병 관찰표', '질병표'],
  ['사육 밀도표', '밀도표'],
  ['출하 검사표', '출하표'],
  ['서버 부하표', '부하표'],
  ['발전 예측표', '발전표'],
  ['순환수 펌프', '순환펌프'],
  ['전력 절체기', '절체기'],
  ['전기버스 배차표', '버스 배차표'],
  ['충전 대기열', '충전열'],
  ['가스 공급반', '가스반'],
  ['초순수 배관', '초순수관'],
  ['공정 엔지니어', '공정기술자'],
  ['파티클 계수기', '입자 계수기'],
  ['마취 준비표', '마취표'],
  ['수술실 배정표', '수술실표'],
  ['검체 운반함', '검체함'],
  ['선박 접안표', '접안표'],
  ['통관 기록', '통관표'],
  ['항만 관제기', '항만 관제'],
  ['출발 기록', '출발표'],
  ['항공기 대기열', '항공 대기열'],
  ['적설 관측표', '적설표'],
  ['제빙 장비', '제빙기'],
  ['현장 통제자', '현장 담당자'],
];

const LEADING_MODIFIERS = [
  '자동 ', '중앙 ', '야간 ', '새벽 ', '정상 ', '임시 ', '비상 ', '장기 ', '초기 ', '후속 ',
  '첫 ', '우천 ', '고부하 ', '저부하 ', '예외 ', '정기 ', '수동 ', '국소 ', '부분 ', '대체 ',
];

const SHORT_SUFFIXES = {
  direction: ['연결', '순서', '전달', '식별', '입력', '출력', '경로'],
  conflict: ['충돌', '우선', '출처', '분기', '조건', '대조', '판단'],
  partial: ['범위', '누락', '표본', '관측', '한계', '보류', '확인'],
  impact: ['영향', '변화', '전파', '반응', '범위', '제한', '결과'],
  cycle: ['순환', '회차', '되먹임', '복귀', '고리', '반복', '연결'],
};

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex').toUpperCase();
}

function normalize(value) {
  return String(value).normalize('NFKC').replace(/\s+/gu, ' ').trim();
}

function words(value) {
  return normalize(value).match(/[0-9A-Za-z가-힣]+/gu) || [];
}

function particle(value, pair) {
  const text = normalize(value);
  const last = text.match(/[가-힣]$/u);
  if (!last) return pair.endsWith('는') ? '는' : '를';
  const jong = (text.charCodeAt(text.length - 1) - 0xAC00) % 28;
  const hasBatchim = jong !== 0;
  if (pair === '은/는') return hasBatchim ? '은' : '는';
  if (pair === '이/가') return hasBatchim ? '이' : '가';
  if (pair === '을/를') return hasBatchim ? '을' : '를';
  if (pair === '과/와') return hasBatchim ? '과' : '와';
  return hasBatchim ? '으로' : '로';
}

function versionFromName(name) {
  const match = name.match(/_v(\d+)\.source\.psv$/u);
  return match ? Number(match[1]) : null;
}

function familyKind(version) {
  if ([16, 19, 25, 30, 35, 40, 45, 50].includes(version)) return 'direction';
  if ([17, 20, 23, 26, 31, 36, 41, 46, 51].includes(version)) return 'conflict';
  if ([18, 21, 24, 27, 32, 37, 42, 47, 52].includes(version)) return 'partial';
  if ([33, 38, 43, 48].includes(version)) return 'impact';
  return 'cycle';
}

function markerAndBase(concept) {
  const at = concept.indexOf(' — ');
  if (at < 0) return { base: concept, marker: null };
  return { base: concept.slice(0, at).trim(), marker: concept.slice(at + 3).trim() };
}

function normalizeBase(value) {
  let base = normalize(value);
  base = base.replace(/경계 이후에서/gu, '경계 통과 뒤');
  base = base.replace(/경계 이후/gu, '경계 통과 뒤');
  base = base.replace(/승인 전/gu, '승인 이전');
  base = base.replace(/복구 직후/gu, '복구 뒤');
  base = base.replace(/확인하는 복구 뒤/gu, '확인 뒤 복구');
  base = base.replace(/관측 공백에서/gu, '관측 공백 시');
  base = base.replace(/고부하 운전에 따른/gu, '고부하 운전의');
  base = base.replace(/저부하 운전에 따른/gu, '저부하 운전의');
  base = base.replace(/맞지 않는 화물의 보류 상태$/u, '불일치 화물 보류');
  base = base.replace(/^(.+?)의 일부 기록만으로 (.+?)(?:을|를) 추정하지 않은 경로$/u, (_, source, target) => `${source.replace(/ 기록$/u, '')} 기록 부족에 따른 ${target} 추정 보류`);
  base = base.replace(/(.+?)(?:을|를) 보류하는 (저부하 운전|고부하 운전)$/u, '$1 보류 $2');
  /* Turn an inanimate “meeting” clause into an ordinary conflict title. */
  base = base.replace(/^(.+?)(?:와|과) (.+?)(?:이|가) 만날 때 (.+?)(?:을|를) 보류하는 판단$/u, (_, first, second, third) => `${first}${particle(first, '과/와')} ${second}의 충돌 시 ${third} 보류 판단`);
  base = base.replace(/^(.+?)(?:와|과) (.+?)(?:이|가) 만날 때 (.+)$/u, (_, first, second, rest) => `${first}${particle(first, '과/와')} ${second}의 만남에서 ${rest}`);
  return base.replace(/\s+/gu, ' ').trim();
}

function compactBase(value, kind) {
  return normalizeBase(value);
}

function trimParticleEnding(value) {
  let result = normalize(value).replace(/\s+(?:에서|까지|사이의|사이|와|과|의|로|으로|에|뒤|후|중|시|때|를|을|가|이)$/u, '').trim();
  /* A character-level particle can remain when a long title is cut mid-token. */
  result = result.replace(/(?:에서|으로|까지|에|의|와|과|가|이|은|는|을|를)$/u, '').trim();
  return result;
}

function trimBaseForPrimary(value, maxLength) {
  const source = normalize(value);
  if (source.length <= maxLength) return trimParticleEnding(source);
  let cut = source.slice(0, maxLength);
  const boundary = cut.lastIndexOf(' ');
  if (boundary >= 10) cut = cut.slice(0, boundary);
  cut = trimParticleEnding(cut);
  /* If the cut ends in a predicate, keep the preceding noun phrase. */
  cut = cut.replace(/(?:맞지 않는|맞지 않|추정하지 않은|추정하지 않|보류하는|보류하|확인하는|확인하|이어지는|이어지|전달되는|전달되|가리키는|가리키|나타내는|나타내|되는|되|있는|있|없는|없)$/u, '').trim();
  cut = trimParticleEnding(cut);
  return cut || source.slice(0, maxLength).trim();
}

function primarySuffixes(kind, marker) {
  const markerMap = {
    '신호 전달': '신호', '대상 추적': '추적', '연결 확인': '연결', '출처 대조': '출처',
    '범위 확인': '범위', '순서 기록': '순서', '상태 묶음': '상태', '우선 처리': '우선',
    '운영 인계': '인계', '회복 판정': '복구', '경로 보존': '경로', '결과 검증': '결과',
    '영향 검토': '영향', '중간 판정': '중간', '예외 점검': '예외', '분기 기록': '분기',
    '독립 확인': '독립',
  };
  const preferred = markerMap[marker];
  const pool = SHORT_SUFFIXES[kind] || SHORT_SUFFIXES.direction;
  return preferred ? [preferred, ...pool.filter((item) => item !== preferred)] : pool;
}

function otherClause(otherType, variant) {
  if (!otherType) return '';
  const variants = [
    `‘${otherType}’ 조건이면 추가 자료를 확인할 때까지 해당 연결을 보류한다`,
    `‘${otherType}’ 상태에서는 확인된 사실만 남기고 추정은 보류한다`,
    `‘${otherType}’ 조건이 해소되기 전에는 다음 판단을 확정하지 않는다`,
    `‘${otherType}’이면 관측값과 추정값을 나누어 기록한다`,
  ];
  return variants[variant % variants.length];
}

function relationCues(relations, otherType, seed) {
  const clauses = [];
  for (let i = 0; i < relations.length; i += 1) {
    const relation = relations[i];
    const list = CUE_VARIANTS[relation] || CUE_VARIANTS.other;
    clauses.push(list[(seed + i) % list.length]);
  }
  if (otherType && !relations.includes('other')) clauses.push(otherClause(otherType, seed));
  return clauses;
}

function makePrimary(rawConcept, kind, ordinal, attempt = 0) {
  const { base, marker } = markerAndBase(rawConcept);
  const compact = compactBase(base, kind);
  /* A marker is removed, not replaced, when the case title already fits. */
  if (attempt === 0) {
    const title = trimBaseForPrimary(compact, 35);
    if (title.length > 0) return title;
  }
  const suffixes = primarySuffixes(kind, marker);
  let suffix = suffixes[(ordinal + attempt) % suffixes.length];
  let maxCore = Math.max(12, 35 - suffix.length - 1);
  let core = trimBaseForPrimary(compact, maxCore);
  /* Do not produce labels such as “... 연결 연결”. */
  if (core.endsWith(` ${suffix}`) || core === suffix) {
    suffix = suffixes[(ordinal + attempt + 1) % suffixes.length];
    maxCore = Math.max(12, 35 - suffix.length - 1);
    core = trimBaseForPrimary(compact, maxCore);
  }
  return normalize(`${core} ${suffix}`);
}

function makeText(primary, base, relations, otherType, kind, seed) {
  const anchor = normalize(base).replace(/\s+/gu, '·');
  const caseOpeners = [
    `운영 자료의 사례명은 ‘${anchor}’이다.`,
    `현장 기록에서 ‘${anchor}’ 사례를 먼저 읽는다.`,
    `검토표에는 ‘${anchor}’라는 사례가 남아 있다.`,
    `기록된 사례 ‘${anchor}’의 입력과 결과를 살핀다.`,
    `자료에 적힌 ‘${anchor}’ 사례를 시간 순으로 배열한다.`,
    `담당자는 ‘${anchor}’ 사례의 근거부터 확인한다.`,
  ];
  const p = `‘${primary}’ 관계`;
  const templates = {
    direction: [
      `입력 조건과 다음 단계의 시각을 확인한 뒤 ${p}의 앞뒤 순서를 비교한다. 중간 근거가 없으면 연결을 보류하고 확인된 순서만 기록한다.`,
      `출발 자료와 도착 자료의 순서를 맞추고 ${p}가 이어지는 조건을 확인한다. 한 단계라도 비면 다음 조치를 보류하며 확인 결과를 기록한다.`,
      `자료 사이의 전달 시점을 비교해 ${p}의 방향을 정한다. 순서가 맞지 않는 경우에는 경로를 보류하고 근거가 확인된 부분만 기록한다.`,
      `앞 단계의 조건을 확인한 후 ${p}가 다음 단계로 이어졌는지 살핀다. 시각이 빠진 연결은 보류하고 남은 사실을 기록한다.`,
      `입력과 결과를 시간 순으로 정리하면서 ${p}의 연결을 확인한다. 도착 근거가 없으면 판단을 보류하고 확인된 시각을 기록한다.`,
    ],
    conflict: [
      `자료의 조건이 서로 다르면 출처와 시각을 비교한다. ${p}의 우선 근거를 확인한 뒤 충돌한 조치는 보류하고 승인된 판단을 기록한다.`,
      `두 자료가 다른 결론을 가리키는 경우 각 근거를 따로 확인한다. ${p}의 적용 조건이 맞지 않으면 결정을 보류하고 차이를 기록한다.`,
      `변경된 지시와 기존 기록의 시점을 대조해 ${p}의 충돌 원인을 확인한다. 책임자가 승인하기 전에는 실행을 보류하고 판단을 기록한다.`,
      `출처별 조건을 나누어 읽은 뒤 ${p}에 적용할 기준을 정한다. 근거가 모자라면 조치를 보류하고 확인된 내용만 기록한다.`,
      `같은 사건에 대한 표현이 다르면 ${p}의 범위와 시각을 비교한다. 불일치가 풀릴 때까지 실행을 보류하고 두 결과를 기록한다.`,
    ],
    partial: [
      `관측 자료가 일부인 경우 확인값과 추정값을 나눈다. ${p}의 빈 구간은 추가 자료를 확인할 때까지 연결을 보류하고 미확인 단계는 기록한다.`,
      `자료가 끊긴 시점을 먼저 확인한 뒤 ${p}의 관측 범위를 정한다. 누락된 구간을 임의로 잇지 않고 판단을 보류하며 남은 사실을 기록한다.`,
      `한 채널의 값만 남은 경우 ${p}의 연결을 확정하지 않는다. 다른 자료가 확인될 때까지 조치를 보류하고 관측된 값만 기록한다.`,
      `기록된 시점과 비어 있는 시점을 나누어 ${p}의 범위를 살핀다. 근거가 부족한 단계는 보류하고 확인 결과를 기록한다.`,
      `부분 표본에서 확인되는 사실을 골라 ${p}의 가능한 경로를 적는다. 추가 확인 전에는 결론을 보류하고 누락을 기록한다.`,
    ],
    impact: [
      `변화가 발생한 조건과 시점을 먼저 확인한다. ${p}가 닿은 구간을 비교하고 근거가 약한 전파는 보류하며 직접 관측한 결과를 기록한다.`,
      `한 지점의 값이 바뀐 뒤 어느 구간이 달라졌는지 확인한다. ${p}의 영향이 확인되지 않으면 판단을 보류하고 변화 범위를 기록한다.`,
      `변경 전후의 자료를 대조해 ${p}의 반응 시점을 찾는다. 독립된 대상에는 결론을 확대하지 않고 확인된 결과만 기록한다.`,
      `변화가 멈춘 곳과 이어진 곳을 구분해 ${p}의 전파를 확인한다. 근거가 없는 구간은 보류하고 관측된 반응을 기록한다.`,
      `측정값이 기준을 벗어난 조건을 확인한 뒤 ${p}의 영향 범위를 비교한다. 확정할 수 없는 전파는 보류하고 제한을 기록한다.`,
    ],
    cycle: [
      `앞선 출력이 다음 입력으로 돌아오는 조건과 시점을 확인한다. ${p}의 이전 결과와 다음 입력을 비교하고 연결이 끊기면 순환을 보류해 기록한다.`,
      `한 회차의 결과가 이후 판단에 다시 쓰였는지 확인한다. ${p}의 되먹임 근거가 없으면 결론을 보류하고 독립 경로를 기록한다.`,
      `기록을 회차별로 나누어 ${p}의 앞뒤 방향을 비교한다. 회차가 비어 있으면 순환을 보류하고 확인된 회차만 기록한다.`,
      `조치 전후의 값을 맞춰 ${p}의 결과가 입력으로 돌아왔는지 확인한다. 동시 변화만으로는 확정하지 않고 근거를 기록한다.`,
      `반복 자료에서 다음 입력을 만든 이전 결과를 확인한다. ${p}의 고리가 끊겼다면 판단을 보류하고 남은 연결을 기록한다.`,
    ],
  };
  const lead = caseOpeners[seed % caseOpeners.length];
  const body = templates[kind][Math.floor(seed / caseOpeners.length) % templates[kind].length];
  const cues = relationCues(relations, otherType, seed + 1);
  const cueSentence = `${cues.join('. ')}.`;
  const limits = [
    '확인되지 않은 단계는 사실로 확정하지 않는다.',
    '자료가 어긋나면 추가 확인 전까지 판단을 보류한다.',
    '관측 범위를 넘는 결론은 기록하지 않는다.',
    '누락된 근거는 별도 항목으로 남긴다.',
  ];
  let text = `${lead} ${body} ${cueSentence} ${limits[(seed * 7) % limits.length]}`;
  if (otherType && !text.includes(otherType)) text += ` ${otherClause(otherType, seed + 2)}.`;
  return normalize(text);
}

function readRows(name) {
  const buffer = fs.readFileSync(path.join(SOURCE_DIR, name));
  const text = new TextDecoder('utf-8', { fatal: true }).decode(buffer);
  const lines = text.split(/\r\n|\n|\r/u);
  if (lines.at(-1) === '') lines.pop();
  if (lines[0] !== 'concept|relations|other_type|text') throw new Error(`${name}: unexpected header`);
  return { buffer, lines };
}

function main() {
  const audit = JSON.parse(fs.readFileSync(AUDIT_PATH, 'utf8'));
  const queued = new Map(audit.semantic.rewrite_queue.filter((row) => row.version >= 2).map((row) => [`${row.source_file}\u0000${row.source_line}`, row]));
  const previous = fs.existsSync(PREVIOUS_PLAN_PATH)
    ? JSON.parse(fs.readFileSync(PREVIOUS_PLAN_PATH, 'utf8'))
    : { rows: [] };
  const previousTargets = new Map((previous.rows || []).map((row) => [`${row.source_file}\u0000${row.source_line}`, row]));
  const sourceFiles = fs.readdirSync(SOURCE_DIR).filter((name) => name.startsWith(PREFIX) && name.endsWith('.source.psv')).sort((a, b) => versionFromName(a) - versionFromName(b));
  const rows = [];
  const fileGuards = [];
  const guardByFile = new Map();
  const records = [];
  const primarySeen = new Set();
  const textSeen = new Set();
  const primaryCollisions = [];
  const textCollisions = [];
  for (const name of sourceFiles) {
    const version = versionFromName(name);
    const { buffer, lines } = readRows(name);
    const guard = { file: name, bytes: buffer.length, sha256: sha256(buffer), rows: lines.length - 1 };
    fileGuards.push(guard);
    guardByFile.set(name, guard);
    for (let index = 1; index < lines.length; index += 1) {
      const line = lines[index];
      const cells = line.split('|');
      if (cells.length !== 4) throw new Error(`${name}:${index + 1}: expected four PSV fields`);
      const oldPrimary = cells[0].trim();
      const relations = cells[1].split(',').map((value) => value.trim()).filter(Boolean);
      const otherType = cells[2].trim();
      const oldText = cells[3].trim();
      const key = `${name}\u0000${index + 1}`;
      const queuedRow = queued.get(key);
      const previousTarget = previousTargets.get(key);
      const target = version >= 16 && (oldPrimary.includes(' — ') || Boolean(queuedRow && queuedRow.decision !== 'PASS_CANDIDATE') || Boolean(previousTarget));
      records.push({ name, version, index, line, cells, oldPrimary, relations, otherType, oldText, queuedRow, target, kind: familyKind(version) });
    }
  }
  /* Reserve every untouched primary/text first, including rows in later files. */
  for (const record of records) {
    if (!record.target) {
      primarySeen.add(record.oldPrimary);
      textSeen.add(record.oldText);
    }
  }
  for (const record of records) {
    if (!record.target) continue;
    const { name, version, index, line, cells, oldPrimary, relations, otherType, oldText, queuedRow, kind } = record;
    const baseInfo = markerAndBase(oldPrimary);
    const ordinal = index - 1;
    let attempt = 0;
    let newPrimary = previousTargets.has(`${name}\u0000${index + 1}`)
      ? oldPrimary
      : makePrimary(oldPrimary, kind, ordinal, attempt);
    while (primarySeen.has(newPrimary)) {
      primaryCollisions.push({ source_file: name, source_line: index + 1, candidate: newPrimary });
      attempt += 1;
      if (attempt > 100) throw new Error(`${name}:${index + 1}: unable to make unique primary`);
      newPrimary = makePrimary(oldPrimary, kind, ordinal, attempt);
    }
    primarySeen.add(newPrimary);
    const base = normalizeBase(baseInfo.base);
    const seed = (version * 151 + index) % 997;
    let textAttempt = 0;
    let newText = makeText(newPrimary, base, relations, otherType, kind, seed);
    while (textSeen.has(newText)) {
      textCollisions.push({ source_file: name, source_line: index + 1, candidate: newText });
      textAttempt += 1;
      if (textAttempt > 100) throw new Error(`${name}:${index + 1}: unable to make unique text`);
      newText = makeText(newPrimary, base, relations, otherType, kind, (seed + textAttempt * 19) % 997);
    }
    textSeen.add(newText);
    rows.push({
      source_file: name,
      source_line: index + 1,
      version,
      row: index,
      id: `S2-RCH-${String((version - 1) * 150 + index).padStart(5, '0')}`,
      family_kind: kind,
      relations,
      other_type: otherType || null,
      old_primary: oldPrimary,
      new_primary: newPrimary,
      old_text: oldText,
      new_text: newText,
      old_line: line,
      new_line: [newPrimary, cells[1], cells[2], newText].join('|'),
      source_sha256_before: guardByFile.get(name).sha256,
      audit_flags: queuedRow ? queuedRow.flags : [],
    });
  }
  const plan = {
    schema_version: 1,
    plan_id: 'S2-A06-SEMANTIC-REWRITE-V16-V52-2026-09-16',
    scope: 'A06 source v16~v52 only; v01~v15 preserved',
    generated_at: new Date().toISOString(),
    source_format: 'legacy PSV concept|relations|other_type|text',
    target_count: rows.length,
    expected_target_count: 5501,
    file_guards_before: fileGuards,
    source_audit_input: AUDIT_PATH,
    primary_collision_count: primaryCollisions.length,
    text_collision_count: textCollisions.length,
    collisions: { primary: primaryCollisions, text: textCollisions },
    rows,
    constraints: {
      preserve: ['id', 'row order', 'relations', 'other_type'],
      source_only: true,
      v01_immutable: true,
      registry_update_required_for_primary: true,
      apply_method: 'source rows through explicit apply_patch; registry through line-preserving updater',
      no_numeric_suffix: true,
      no_dash_marker: true,
    },
  };
  fs.writeFileSync(OUTPUT, `${JSON.stringify(plan, null, 2)}\n`, 'utf8');
  process.stdout.write(JSON.stringify({ output: OUTPUT, target_count: rows.length, expected_target_count: 5501, primary_collision_count: primaryCollisions.length, text_collision_count: textCollisions.length, file_count: fileGuards.length, source_rows: fileGuards.reduce((sum, item) => sum + item.rows, 0) }, null, 2));
}

main();
