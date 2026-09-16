'use strict';

/* Read-only preflight for the A06 row-level rewrite plan. */
const fs = require('node:fs');
const path = require('node:path');

const planPath = path.resolve(__dirname, '..', '..', 'audit_reports', 'machine', 'a06', 'A06_Semantic_Rewrite_Plan_v16_v52_2026-09-16.json');
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const rows = plan.rows;
const relationCues = {
  is_a: /(?:종류|범주|분류|에 속|이다)/u,
  subclass_of: /(?:하위|상위|종류|범주|에 속)/u,
  part_of: /(?:일부|구성|포함|거쳐|사이|까지)/u,
  classification: /(?:분류|구분|범주|기준)/u,
  boundary: /(?:구분|혼동|아닌|별도|경계|분리)/u,
  contrast: /(?:반면|대신|서로 다른|둘 다|우선|대조|충돌)/u,
  comparison: /(?:보다|더 |덜 |우선|낮|높|상한|하한|차이)/u,
  function: /(?:역할|기능|위해|담당|한다)/u,
  role: /(?:역할|담당|책임|운영자|작업자|정비자|관리자|제어기|센서)/u,
  process: /(?:면|때|후|뒤|과정|이어|거쳐|면서)/u,
  state: /(?:상태|대기|열림|닫힘|가동|정지|보류|승인)/u,
  attribute: /(?:값|온도|수위|시간|용량|압력|농도|기록|수치)/u,
  other: /(?:결측|불일치|상충|누락|확인되지)/u,
};
const scaffolds = [
  '예외 목록을 검토', '통상 처리와 제한 처리', '한 번의 예외를 영구 규칙', '기본 경로가 열려 있어도',
  '일부 조치를 보류', '두 기록을 대조', '기본 지시와 예외 지시', '서로 다른 출처를 하나의 사실',
  '경보가 겹치', '나머지 항목을 대기', '정책 기록과 현장 신호', '한쪽을 지워 단일 경로',
  '두 담당자의 표', '최신성 판단과 내용의 타당성', '일치하는 기록과 어긋난 기록',
  '승인되지 않은 예외는 실행 근거', '기본 순서가 예외 승인', '변경되지 않은 단계는 원래 순서',
];
const placeholders = ['기본 경로', '예외 목록', '일부 조치', '두 관계', '한쪽', '나머지 항목', '기본 순서', '적용 범위', '통상 처리', '제한 처리', '대기 항목'];
/* Only unmistakable doubled particles are warnings; “결과와” and “경로로” are natural. */
const malformed = /(?:과과|와와|의의|에에|에서에|에의|으로로)/u;
function facts(text) {
  return {
    trigger_or_condition: /(?:면|때|경우|후|뒤|동안|상태|조건|충돌|결측|불일치)/u.test(text),
    decision_or_action: /(?:보류|선택|조정|분리|확인|우선|차단|열|닫|감속|기동|중단|전환|배정|조절)/u.test(text),
    consequence_or_limit: /(?:유지|제한|방지|보존|막|확정하지|불가|가능|아닌|남긴다|기록한다)/u.test(text),
  };
}
function adjacent(text) {
  const m = text.match(/(?:^|\s)([0-9A-Za-z가-힣]{2,})\s+\1(?:\s|$)/u);
  return m ? m[1] : null;
}

const primarySeen = new Map();
const textSeen = new Map();
const issues = [];
const relationGap = new Map();
const versions = new Map();
let primaryInText = 0;
let otherInText = 0;
let primaryParticleStart = 0;
let maxPrimary = 0;
let maxText = 0;
for (const row of rows) {
  const version = row.version;
  if (!versions.has(version)) versions.set(version, []);
  versions.get(version).push(row);
  maxPrimary = Math.max(maxPrimary, row.new_primary.length);
  maxText = Math.max(maxText, row.new_text.length);
  if (primarySeen.has(row.new_primary)) issues.push({ type: 'PRIMARY_DUPLICATE', row, first: primarySeen.get(row.new_primary) });
  else primarySeen.set(row.new_primary, row);
  if (textSeen.has(row.new_text)) issues.push({ type: 'TEXT_DUPLICATE', row, first: textSeen.get(row.new_text) });
  else textSeen.set(row.new_text, row);
  if (row.new_text.includes(row.new_primary)) primaryInText += 1;
  if (row.other_type && row.new_text.includes(row.other_type)) otherInText += 1;
  if (row.new_text.startsWith(`${row.new_primary}은`) || row.new_text.startsWith(`${row.new_primary}는`)) primaryParticleStart += 1;
  if (row.new_primary.includes(' — ') || /[가-힣A-Za-z]\d+$/u.test(row.new_primary)) issues.push({ type: 'PRIMARY_MARKER_OR_NUMERIC', row });
  if (malformed.test(row.new_primary) || malformed.test(row.new_text)) issues.push({ type: 'MALFORMED_PARTICLE', row });
  if (scaffolds.some((needle) => row.new_text.includes(needle))) issues.push({ type: 'GENERIC_SCAFFOLD', row });
  if (placeholders.some((needle) => row.new_text.includes(needle))) issues.push({ type: 'OPAQUE_PLACEHOLDER', row });
  if (adjacent(`${row.new_primary} ${row.new_text}`)) issues.push({ type: 'ADJACENT_REPEAT', row });
  const f = facts(row.new_text);
  if (Object.values(f).filter(Boolean).length < 2) issues.push({ type: 'FACT_CHAIN_WEAK', row, facts: f });
  for (const relation of row.relations) {
    if (relation === 'other' && row.other_type && row.new_text.includes(row.other_type)) continue;
    if (relationCues[relation] && !relationCues[relation].test(row.new_text)) {
      relationGap.set(relation, (relationGap.get(relation) || 0) + 1);
    }
  }
}

const issueCounts = {};
for (const issue of issues) issueCounts[issue.type] = (issueCounts[issue.type] || 0) + 1;
const versionCounts = Object.fromEntries([...versions.entries()].map(([v, rs]) => [v, rs.length]));
const samples = {};
for (const v of [16, 17, 18, 19, 30, 31, 32, 33, 34, 52]) {
  samples[v] = (versions.get(v) || []).slice(0, 2).map((row) => ({
    source_file: row.source_file,
    source_line: row.source_line,
    old_primary: row.old_primary,
    new_primary: row.new_primary,
    new_text: row.new_text,
  }));
}
const report = {
  plan_path: planPath,
  target_count: rows.length,
  expected_target_count: plan.expected_target_count,
  version_target_counts: versionCounts,
  primary_unique: primarySeen.size === rows.length,
  text_unique: textSeen.size === rows.length,
  primary_in_text_count: primaryInText,
  other_type_in_text_count: otherInText,
  primary_particle_start_count: primaryParticleStart,
  primary_particle_start_rate_percent: Number((primaryParticleStart / Math.max(rows.length, 1) * 100).toFixed(4)),
  max_primary_length: maxPrimary,
  max_text_length: maxText,
  relation_cue_gaps: Object.fromEntries([...relationGap.entries()].sort()),
  issue_counts: issueCounts,
  issue_samples: issues.slice(0, 30).map((issue) => ({ type: issue.type, source_file: issue.row.source_file, source_line: issue.row.source_line, new_primary: issue.row.new_primary, new_text: issue.row.new_text })),
  samples,
};
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
