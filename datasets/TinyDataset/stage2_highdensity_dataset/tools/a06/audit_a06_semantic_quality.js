#!/usr/bin/env node
'use strict';

/*
 * A06-only semantic-quality reviewer assistant.
 *
 * This program is deliberately read-only with respect to A06 source and its
 * registry.  It may write only a versioned JSON report beneath the A06 machine
 * audit directory.  Its deterministic flags are a review queue, not proof
 * that a Korean sentence is natural or that an operational fact is true.
 */

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const AREA = 'A06';
const PREFIX = 'stage2_(16)relational_composition_high_density_train_v';
const HEADER = 'concept|relations|other_type|text';
const CONTROLLED = [
  'is_a', 'subclass_of', 'part_of', 'classification', 'boundary', 'contrast',
  'comparison', 'function', 'role', 'process', 'state', 'attribute', 'other',
];
const CONTROLLED_SET = new Set(CONTROLLED);
const UTF8 = new TextDecoder('utf-8', { fatal: true });
const TOOL_DIR = __dirname;
const DATASET_ROOT = path.resolve(TOOL_DIR, '..', '..');
const DEFAULT_SOURCE_DIR = path.join(DATASET_ROOT, 'sources', 'train');
const DEFAULT_REGISTRY = path.join(DATASET_ROOT, 'sources', 'term_registry', 'stage2_(16)relational_composition_train_registry_v01_v52.jsonl');
const DEFAULT_RESERVATION = path.resolve(DATASET_ROOT, '..', 'stage1_highdensity_dataset', 'TinyLM_Stage2_Stage10_Concept_Family_Reservation.json');
const OUTPUT_ROOT = path.join(DATASET_ROOT, 'audit_reports', 'machine', 'a06');
const FIXTURE_ROOT = path.join(TOOL_DIR, 'fixtures');

const GENERIC_SCAFFOLDS = [
  '예외 목록을 검토',
  '통상 처리와 제한 처리',
  '한 번의 예외를 영구 규칙',
  '기본 경로가 열려 있어도',
  '일부 조치를 보류',
  '두 기록을 대조',
  '기본 지시와 예외 지시',
  '서로 다른 출처를 하나의 사실',
  '경보가 겹치',
  '나머지 항목을 대기',
  '정책 기록과 현장 신호',
  '한쪽을 지워 단일 경로',
  '두 담당자의 표',
  '최신성 판단과 내용의 타당성',
  '일치하는 기록과 어긋난 기록',
  '승인되지 않은 예외는 실행 근거',
  '기본 순서가 예외 승인',
  '변경되지 않은 단계는 원래 순서',
];

const OPAQUE_PLACEHOLDERS = [
  '기본 경로', '예외 목록', '일부 조치', '두 관계', '한쪽', '나머지 항목',
  '기본 순서', '적용 범위', '통상 처리', '제한 처리', '대기 항목',
];

const RELATION_CUES = {
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

const STOP_WORDS = new Set([
  '은', '는', '이', '가', '을', '를', '에', '의', '과', '와', '도', '로', '으로',
  '그리고', '하지만', '그러나', '또한', '때문에', '따라서', '그', '이', '저', '한',
  '한다', '했다', '한다는', '있는', '없는', '되면', '되어', '한다면', '한다는',
]);

function fail(message) {
  throw new Error(message);
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex').toUpperCase();
}

function isWithin(candidate, root) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function decodeUtf8(buffer, label) {
  if (buffer.length >= 3 && buffer[0] === 0xef && buffer[1] === 0xbb && buffer[2] === 0xbf) {
    fail(`${label}: UTF-8 BOM is not allowed`);
  }
  try {
    return UTF8.decode(buffer);
  } catch (error) {
    fail(`${label}: invalid UTF-8 (${error.message})`);
  }
}

function normalize(value) {
  return String(value).normalize('NFKC').replace(/\s+/gu, ' ').trim();
}

function words(value) {
  return normalize(value).match(/[0-9A-Za-z가-힣]+/gu) || [];
}

function contentTerms(value) {
  return words(value)
    .map((word) => word.toLowerCase())
    .filter((word) => word.length >= 2 && !STOP_WORDS.has(word));
}

function versionOf(filename) {
  const match = filename.match(/_v(\d+)\.source\.psv$/u);
  return match ? Number(match[1]) : null;
}

function idFor(version, row) {
  if (!Number.isInteger(version) || version < 1) return null;
  return `S2-RCH-${String((version - 1) * 150 + row).padStart(5, '0')}`;
}

function locatorKey(file, line) {
  return `${file}\u0000${line}`;
}

function topEntries(counter, limit = 20) {
  return [...counter.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], 'ko'))
    .slice(0, limit)
    .map(([value, count]) => ({ value, count }));
}

function addCounter(counter, key, amount = 1) {
  counter.set(key, (counter.get(key) || 0) + amount);
}

function addSample(bucket, value, maximum = 12) {
  if (bucket.length < maximum) bucket.push(value);
}

function particleForPrimary(primary) {
  const compact = normalize(primary);
  const match = compact.match(/[가-힣]$/u);
  if (!match) return null;
  const code = compact.charCodeAt(compact.length - 1) - 0xac00;
  const jong = code % 28;
  return jong === 0 ? '는' : '은';
}

function hasAdjacentRepeatedToken(value) {
  const matched = normalize(value).match(/(?:^|\s)([0-9A-Za-z가-힣]{2,})\s+\1(?:\s|$)/u);
  return matched ? matched[1] : null;
}

function factsFromText(text) {
  return {
    trigger_or_condition: /(?:면|때|경우|후|뒤|동안|상태|조건|충돌|결측|불일치)/u.test(text),
    decision_or_action: /(?:보류|선택|조정|분리|확인|우선|차단|열|닫|감속|기동|중단|전환|배정|조절)/u.test(text),
    consequence_or_limit: /(?:유지|제한|방지|보존|막|확정하지|불가|가능|아닌|남긴다|기록한다)/u.test(text),
  };
}

function primaryFlags(primary) {
  const flags = [];
  if (/\s—\s/u.test(primary)) flags.push('DASH_MARKER_PRIMARY');
  if (/[가-힣A-Za-z]\d+$/u.test(primary)) flags.push('NUMERIC_SUFFIX_PRIMARY');
  if (primary.length >= 38) flags.push('OVERLONG_COMPOSITE_PRIMARY');
  if (/(?:센서|제어기|기록|지시|밸브|팬|예보).{0,18}만날 때/u.test(primary)) flags.push('INANIMATE_MEETING_COMPOUND');
  if (/(?:경계 이후|승인 전|복구 직후).{0,14}(?:조정|경로|판단|기준)/u.test(primary)) flags.push('UNRESOLVED_QUALIFIER_PRIMARY');
  return flags;
}

function semanticReview(doc) {
  const flags = primaryFlags(doc.concept);
  const mechanical = new Set(['DASH_MARKER_PRIMARY', 'NUMERIC_SUFFIX_PRIMARY']);
  const repeated = hasAdjacentRepeatedToken(`${doc.concept} ${doc.text}`);
  if (repeated) flags.push('ADJACENT_REPEATED_TOKEN');

  const matchedScaffolds = GENERIC_SCAFFOLDS.filter((needle) => doc.text.includes(needle));
  if (matchedScaffolds.length) flags.push('GENERIC_SCAFFOLD');
  const matchedPlaceholders = OPAQUE_PLACEHOLDERS.filter((needle) => doc.text.includes(needle));
  if (matchedPlaceholders.length) flags.push('UNGROUNDED_PLACEHOLDER');

  const facts = factsFromText(doc.text);
  const missingFacts = Object.entries(facts).filter(([, present]) => !present).map(([name]) => name);
  if (missingFacts.length >= 2) flags.push('FACT_CHAIN_WEAK');

  const relationCueGaps = doc.relations.filter((relation) => {
    if (relation === 'other' && doc.other_type) return doc.text.includes(doc.other_type) ? false : !RELATION_CUES.other.test(doc.text);
    const cue = RELATION_CUES[relation];
    return cue ? !cue.test(doc.text) : false;
  });
  if (relationCueGaps.length >= 2) flags.push('RELATION_CUE_GAPS');

  const uniqueFlags = [...new Set(flags)];
  const clearRewrite = uniqueFlags.some((flag) => mechanical.has(flag) || flag === 'ADJACENT_REPEATED_TOKEN' || flag === 'GENERIC_SCAFFOLD');
  let decision = clearRewrite ? 'REWRITE_REQUIRED' : (uniqueFlags.length ? 'SEMANTIC_REVIEW_REQUIRED' : 'PASS_CANDIDATE');
  if (doc.version === 1 && decision !== 'PASS_CANDIDATE') decision = 'PACKAGE_PROJECTION_HOLD';

  return {
    flags: uniqueFlags,
    matched_scaffolds: matchedScaffolds,
    matched_placeholders: matchedPlaceholders,
    facts,
    missing_fact_cues: missingFacts,
    relation_cue_gaps: relationCueGaps,
    decision,
  };
}

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) fail(`unexpected positional argument: ${token}`);
    const name = token.slice(2);
    if (name === 'help') {
      args.help = true;
      continue;
    }
    if (Object.hasOwn(args, name)) fail(`duplicate option: --${name}`);
    const value = argv[index + 1];
    if (value === undefined || value.startsWith('--')) fail(`missing value for --${name}`);
    args[name] = value;
    index += 1;
  }
  return args;
}

function printUsage() {
  process.stdout.write([
    'A06 semantic-quality reviewer assistant (read-only for source and registry)',
    '',
    'Production:',
    '  node audit_a06_semantic_quality.js --out <A06-machine-report.json>',
    '',
    'Fixture:',
    '  node audit_a06_semantic_quality.js --fixture-input <tools/a06/fixtures/*.psv> --out <A06-machine-report.json>',
    '',
    'The output path must remain under stage2_highdensity_dataset/audit_reports/machine/a06/.',
  ].join('\n'));
}

function expectedFiles() {
  return Array.from({ length: 52 }, (_, index) => `${PREFIX}${String(index + 1).padStart(2, '0')}.source.psv`);
}

function readReservation() {
  const raw = fs.readFileSync(DEFAULT_RESERVATION);
  const document = JSON.parse(decodeUtf8(raw, DEFAULT_RESERVATION));
  const rows = document.reservations.filter((row) => row.stage === 2 && row.file_area_slot === 16 && row.split === 'train');
  return new Map(rows.map((row) => [Number(String(row.version).replace(/^v/u, '')), row]));
}

function readSourceFiles(options, errors) {
  const reservation = options.fixture ? new Map() : readReservation();
  const sourceFiles = [];
  if (options.fixture) {
    const fixture = path.resolve(options.fixture);
    if (!isWithin(fixture, FIXTURE_ROOT) || !fixture.endsWith('.psv')) {
      fail('--fixture-input must be a .psv file below tools/a06/fixtures/');
    }
    sourceFiles.push({ name: path.basename(fixture), full: fixture, version: 0, fixture: true });
  } else {
    const actual = fs.readdirSync(DEFAULT_SOURCE_DIR)
      .filter((name) => name.startsWith(PREFIX) && /^stage2_\(16\)relational_composition_high_density_train_v\d+\.source\.(?:psv|jsonl)$/u.test(name));
    const expected = expectedFiles();
    const actualByVersion = new Map();
    for (const name of actual) {
      const version = Number((name.match(/_v(\d+)\.source\.(?:psv|jsonl)$/u) || [])[1]);
      if (!actualByVersion.has(version)) actualByVersion.set(version, []);
      actualByVersion.get(version).push(name);
    }
    for (const name of expected) {
      if (!actual.includes(name)) addSample(errors.missing_files, name, 60);
      else sourceFiles.push({ name, full: path.join(DEFAULT_SOURCE_DIR, name), version: versionOf(name), fixture: false });
    }
    for (const [version, names] of actualByVersion) {
      if (names.length > 1) addSample(errors.duplicate_source_formats, { version, files: names.sort() }, 60);
    }
    for (const name of actual) if (!expected.includes(name)) addSample(errors.unexpected_files, name, 60);
  }
  return { reservation, sourceFiles };
}

function parseSource(options) {
  const errors = {
    missing_files: [], unexpected_files: [], duplicate_source_formats: [], utf8: [], bom: [], header: [],
    row_count: [], blank_rows: [], columns: [], control_characters: [], empty_concept: [], empty_text: [],
    concept_literal_missing: [], concept_duplicate: [], text_duplicate: [], relation_controlled: [],
    relation_cardinality: [], relation_internal_duplicate: [], other_type_rule: [], registry: [],
  };
  const { reservation, sourceFiles } = readSourceFiles(options, errors);
  const docs = [];
  const fileSummaries = [];
  const concepts = new Map();
  const texts = new Map();
  const relationCounts = new Map(CONTROLLED.map((relation) => [relation, 0]));
  const otherTypes = new Map();
  const sourceHashes = [];

  for (const item of sourceFiles) {
    const buffer = fs.readFileSync(item.full);
    sourceHashes.push({ file: item.name, sha256: sha256(buffer) });
    if (buffer.length >= 3 && buffer[0] === 0xef && buffer[1] === 0xbb && buffer[2] === 0xbf) addSample(errors.bom, { file: item.name });
    let decoded;
    try {
      decoded = decodeUtf8(buffer, item.full);
    } catch (error) {
      addSample(errors.utf8, { file: item.name, message: error.message }, 60);
      continue;
    }
    const lines = decoded.split(/\r\n|\n|\r/u);
    if (lines.length && lines[lines.length - 1] === '') lines.pop();
    if (lines[0] !== HEADER) addSample(errors.header, { file: item.name, actual: lines[0] || '' }, 60);
    const rows = lines.slice(1);
    if (!item.fixture && rows.length !== 150) addSample(errors.row_count, { file: item.name, actual: rows.length, expected: 150 }, 60);
    const reservationRow = reservation.get(item.version);
    if (!item.fixture && !reservationRow) addSample(errors.row_count, { file: item.name, actual: rows.length, expected: 'reservation missing' }, 60);

    let parsedRows = 0;
    for (let index = 0; index < rows.length; index += 1) {
      const line = rows[index];
      const sourceLine = index + 2;
      const locator = { source_file: item.name, source_line: sourceLine, version: item.version, row: index + 1, id: idFor(item.version, index + 1) };
      if (line === '') {
        addSample(errors.blank_rows, locator, 60);
        continue;
      }
      const cells = line.split('|');
      if (cells.length !== 4) {
        addSample(errors.columns, { ...locator, columns: cells.length }, 60);
        continue;
      }
      const concept = cells[0].trim();
      const relations = cells[1].trim() ? cells[1].split(',').map((value) => value.trim()).filter(Boolean) : [];
      const otherType = cells[2].trim();
      const text = cells[3].trim();
      const doc = { ...locator, concept, relations, other_type: otherType, text, family: reservationRow ? reservationRow.concept_family : 'fixture' };
      parsedRows += 1;
      docs.push(doc);
      if (/[^\S\r\n]/u.test('') && false) fail('unreachable');
      if (/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u.test(line)) addSample(errors.control_characters, locator, 60);
      if (!concept) addSample(errors.empty_concept, locator, 60);
      if (!text) addSample(errors.empty_text, locator, 60);
      if (concept && !text.includes(concept)) addSample(errors.concept_literal_missing, locator, 60);
      if (concepts.has(normalize(concept))) addSample(errors.concept_duplicate, { ...locator, first: concepts.get(normalize(concept)) }, 60);
      else concepts.set(normalize(concept), locator);
      if (texts.has(normalize(text))) addSample(errors.text_duplicate, { ...locator, first: texts.get(normalize(text)) }, 60);
      else texts.set(normalize(text), locator);
      if (relations.length < 2 || relations.length > 5) addSample(errors.relation_cardinality, { ...locator, count: relations.length }, 60);
      const seen = new Set();
      for (const relation of relations) {
        addCounter(relationCounts, relation);
        if (!CONTROLLED_SET.has(relation)) addSample(errors.relation_controlled, { ...locator, relation }, 60);
        if (seen.has(relation)) addSample(errors.relation_internal_duplicate, { ...locator, relation }, 60);
        seen.add(relation);
      }
      if (relations.includes('other')) {
        if (!otherType) addSample(errors.other_type_rule, { ...locator, reason: 'other_without_other_type' }, 60);
        else addCounter(otherTypes, otherType);
      } else if (otherType) {
        addSample(errors.other_type_rule, { ...locator, reason: 'other_type_without_other_relation', other_type: otherType }, 60);
      }
    }
    fileSummaries.push({ file: item.name, version: item.version, records: parsedRows, sha256: sourceHashes[sourceHashes.length - 1].sha256, family: reservationRow ? reservationRow.concept_family : 'fixture' });
  }

  const sourceSetHash = sha256(Buffer.from(sourceHashes.sort((left, right) => left.file.localeCompare(right.file)).map((row) => `${row.file}\t${row.sha256}`).join('\n'), 'utf8'));
  return { docs, errors, file_summaries: fileSummaries, source_hashes: sourceHashes, source_set_sha256: sourceSetHash, relation_counts: relationCounts, other_types: otherTypes };
}

function verifyRegistry(options, docs, errors) {
  if (options.fixture) return { checked: false, reason: 'fixture mode has no canonical registry', sha256: null, rows: 0, mismatch_count: 0 };
  const buffer = fs.readFileSync(DEFAULT_REGISTRY);
  const registryHash = sha256(buffer);
  let decoded;
  try {
    decoded = decodeUtf8(buffer, DEFAULT_REGISTRY);
  } catch (error) {
    addSample(errors.registry, { reason: 'invalid_utf8', message: error.message }, 60);
    return { checked: true, sha256: registryHash, rows: 0, mismatch_count: 1 };
  }
  const byLocator = new Map(docs.map((doc) => [locatorKey(doc.source_file, doc.source_line), doc]));
  const seen = new Set();
  let rows = 0;
  let mismatchCount = 0;
  const lines = decoded.split(/\r\n|\n|\r/u);
  if (lines.length && lines[lines.length - 1] === '') lines.pop();
  for (let index = 0; index < lines.length; index += 1) {
    if (!lines[index]) {
      mismatchCount += 1;
      addSample(errors.registry, { line: index + 1, reason: 'blank_jsonl_row' }, 60);
      continue;
    }
    let row;
    try {
      row = JSON.parse(lines[index]);
    } catch (error) {
      mismatchCount += 1;
      addSample(errors.registry, { line: index + 1, reason: 'invalid_json', message: error.message }, 60);
      continue;
    }
    rows += 1;
    const key = locatorKey(row.source_file, row.source_line);
    const source = byLocator.get(key);
    if (seen.has(key)) {
      mismatchCount += 1;
      addSample(errors.registry, { line: index + 1, reason: 'duplicate_locator', source_file: row.source_file, source_line: row.source_line }, 60);
    }
    seen.add(key);
    if (!source) {
      mismatchCount += 1;
      addSample(errors.registry, { line: index + 1, reason: 'registry_locator_not_in_source', source_file: row.source_file, source_line: row.source_line }, 60);
    } else if (row.primary !== source.concept) {
      mismatchCount += 1;
      addSample(errors.registry, { line: index + 1, reason: 'concept_primary_mismatch', source_file: row.source_file, source_line: row.source_line, source_concept: source.concept, registry_primary: row.primary }, 60);
    }
  }
  for (const [key, doc] of byLocator) {
    if (!seen.has(key)) {
      mismatchCount += 1;
      addSample(errors.registry, { reason: 'source_locator_not_in_registry', source_file: doc.source_file, source_line: doc.source_line }, 60);
    }
  }
  return { checked: true, sha256: registryHash, rows, mismatch_count: mismatchCount };
}

function compareSets(left, right) {
  let intersection = 0;
  const smaller = left.size <= right.size ? left : right;
  const larger = left.size <= right.size ? right : left;
  for (const item of smaller) if (larger.has(item)) intersection += 1;
  const union = left.size + right.size - intersection;
  return union ? intersection / union : 1;
}

function cosine(left, right) {
  const smaller = left.weights.size <= right.weights.size ? left : right;
  const larger = left.weights.size <= right.weights.size ? right : left;
  let dot = 0;
  for (const [term, weight] of smaller.weights) dot += weight * (larger.weights.get(term) || 0);
  return left.norm && right.norm ? dot / (left.norm * right.norm) : 0;
}

function keepTop(list, entry, limit = 160) {
  if (list.length < limit) {
    list.push(entry);
    list.sort((left, right) => right.score - left.score || left.left.id.localeCompare(right.left.id));
    return;
  }
  const lowest = list[list.length - 1];
  if (entry.score > lowest.score) {
    list[list.length - 1] = entry;
    list.sort((left, right) => right.score - left.score || left.left.id.localeCompare(right.left.id));
  }
}

function similarityReview(docs) {
  const df = new Map();
  const records = docs.map((doc) => {
    const skeleton = normalize(doc.text.split(doc.concept).join('{PRIMARY}'));
    const terms = contentTerms(skeleton);
    const tf = new Map();
    for (const term of terms) addCounter(tf, term);
    for (const term of tf.keys()) addCounter(df, term);
    return { doc, skeleton, terms: new Set(tf.keys()), tf, weights: new Map(), norm: 0 };
  });
  const total = records.length || 1;
  for (const record of records) {
    let squared = 0;
    for (const [term, frequency] of record.tf) {
      const idf = Math.log((total + 1) / ((df.get(term) || 0) + 1)) + 1;
      const weight = (1 + Math.log(frequency)) * idf;
      record.weights.set(term, weight);
      squared += weight * weight;
    }
    record.norm = Math.sqrt(squared);
  }
  const skeletons = new Map();
  const relationBuckets = new Map();
  for (const record of records) {
    if (!skeletons.has(record.skeleton)) skeletons.set(record.skeleton, []);
    skeletons.get(record.skeleton).push(record.doc);
    const key = [...record.doc.relations].sort().join(',');
    if (!relationBuckets.has(key)) relationBuckets.set(key, []);
    relationBuckets.get(key).push(record);
  }
  const repeatedSkeletons = [...skeletons.entries()]
    .filter(([, rows]) => rows.length > 1)
    .sort((left, right) => right[1].length - left[1].length || left[0].localeCompare(right[0], 'ko'))
    .slice(0, 80)
    .map(([skeleton, rows]) => ({ skeleton, count: rows.length, locators: rows.slice(0, 12).map((doc) => ({ source_file: doc.source_file, source_line: doc.source_line, id: doc.id })) }));

  let pairTotal = 0;
  let jaccardAtThreshold = 0;
  let tfidfAtThreshold = 0;
  let maxJaccard = 0;
  let maxTfidf = 0;
  const topJaccard = [];
  const topTfidf = [];
  for (const [relationSet, bucket] of relationBuckets) {
    for (let leftIndex = 0; leftIndex < bucket.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < bucket.length; rightIndex += 1) {
        pairTotal += 1;
        const left = bucket[leftIndex];
        const right = bucket[rightIndex];
        const jaccard = compareSets(left.terms, right.terms);
        const tfidf = cosine(left, right);
        maxJaccard = Math.max(maxJaccard, jaccard);
        maxTfidf = Math.max(maxTfidf, tfidf);
        const pair = {
          relation_set: relationSet,
          left: { id: left.doc.id, source_file: left.doc.source_file, source_line: left.doc.source_line, concept: left.doc.concept },
          right: { id: right.doc.id, source_file: right.doc.source_file, source_line: right.doc.source_line, concept: right.doc.concept },
        };
        if (jaccard >= 0.75) {
          jaccardAtThreshold += 1;
          keepTop(topJaccard, { ...pair, score: Number(jaccard.toFixed(6)) });
        }
        if (tfidf >= 0.85) {
          tfidfAtThreshold += 1;
          keepTop(topTfidf, { ...pair, score: Number(tfidf.toFixed(6)) });
        }
      }
    }
  }
  return {
    method: 'same controlled-relation set; primary removed; Korean word-set Jaccard and unigrams TF-IDF cosine',
    pair_total: pairTotal,
    word_jaccard_threshold: 0.75,
    word_jaccard_at_or_above_threshold: jaccardAtThreshold,
    word_jaccard_max: Number(maxJaccard.toFixed(6)),
    tfidf_cosine_threshold: 0.85,
    tfidf_cosine_at_or_above_threshold: tfidfAtThreshold,
    tfidf_cosine_max: Number(maxTfidf.toFixed(6)),
    top_word_jaccard_pairs: topJaccard,
    top_tfidf_pairs: topTfidf,
    repeated_primary_removed_skeletons: repeatedSkeletons,
  };
}

function countHardErrors(errors) {
  return Object.values(errors).reduce((sum, value) => sum + (Array.isArray(value) ? value.length : 0), 0);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printUsage();
    return;
  }
  if (Object.keys(args).some((name) => !['out', 'fixture-input'].includes(name))) fail('only --out and optional --fixture-input are supported');
  if (!args.out) fail('--out is required');
  const output = path.resolve(args.out);
  if (!isWithin(output, OUTPUT_ROOT) || !output.endsWith('.json')) fail('--out must be a .json file below audit_reports/machine/a06/');
  const options = { fixture: args['fixture-input'] || null };
  const parsed = parseSource(options);
  const registry = verifyRegistry(options, parsed.docs, parsed.errors);
  const semanticRows = parsed.docs.map((doc) => ({ ...doc, review: semanticReview(doc) }));
  const flagCounts = new Map();
  const decisionCounts = new Map();
  const relationCueGapCounts = new Map();
  const primaryStart = { total: 0, starts_with_primary_particle: 0, wrong_particle: 0 };
  const scenarioCues = { trigger_or_condition: 0, decision_or_action: 0, consequence_or_limit: 0 };
  for (const row of semanticRows) {
    addCounter(decisionCounts, row.review.decision);
    for (const flag of row.review.flags) addCounter(flagCounts, flag);
    for (const relation of row.review.relation_cue_gaps) addCounter(relationCueGapCounts, relation);
    for (const [name, present] of Object.entries(row.review.facts)) if (present) scenarioCues[name] += 1;
    const expectedParticle = particleForPrimary(row.concept);
    if (expectedParticle && (row.text.startsWith(`${row.concept}은`) || row.text.startsWith(`${row.concept}는`))) {
      primaryStart.total += 1;
      primaryStart.starts_with_primary_particle += 1;
      const actualParticle = row.text.slice(row.concept.length, row.concept.length + 1);
      if (actualParticle !== expectedParticle) primaryStart.wrong_particle += 1;
    }
  }
  primaryStart.rate_percent = semanticRows.length ? Number((primaryStart.starts_with_primary_particle / semanticRows.length * 100).toFixed(4)) : 0;
  const similarity = similarityReview(semanticRows);
  const queue = semanticRows
    .filter((row) => row.review.decision !== 'PASS_CANDIDATE')
    .map((row) => ({
      id: row.id,
      source_file: row.source_file,
      source_line: row.source_line,
      version: row.version,
      family: row.family,
      concept: row.concept,
      relations: row.relations,
      other_type: row.other_type || null,
      text: row.text,
      decision: row.review.decision,
      flags: row.review.flags,
      matched_scaffolds: row.review.matched_scaffolds,
      matched_placeholders: row.review.matched_placeholders,
      missing_fact_cues: row.review.missing_fact_cues,
      relation_cue_gaps: row.review.relation_cue_gaps,
    }));
  const structureHardErrors = countHardErrors(parsed.errors);
  const report = {
    schema_version: 1,
    tool: 'audit_a06_semantic_quality.js',
    area: AREA,
    generated_at: new Date().toISOString(),
    scope: {
      source_only: true,
      source_format: options.fixture ? 'fixture PSV' : 'legacy PSV concept|relations|other_type|text',
      registry_checked: registry.checked,
      package_projection: 'NOT_RUN; v01 has a protected package and non-pass v01 source rows are reported as PACKAGE_PROJECTION_HOLD',
      excluded: ['other areas', 'package train/val', 'manifest', 'central ledger', 'checkpoint', 'shared audit tools'],
    },
    evidence_limit: 'The source contains constructed training scenarios, not independently verified operational records. Deterministic signals identify wording, scaffolding, and cue gaps; they do not prove factual truth or natural Korean acceptance. A human/LLM row review is still required before a semantic rewrite.',
    inputs: {
      files: parsed.file_summaries,
      source_set_sha256: parsed.source_set_sha256,
      registry_sha256: registry.sha256,
      registry_rows: registry.rows,
    },
    structural: {
      verdict: structureHardErrors === 0 ? 'PASS' : 'FAIL',
      hard_error_count: structureHardErrors,
      errors: parsed.errors,
      controlled_relation_distribution: Object.fromEntries(CONTROLLED.map((relation) => [relation, parsed.relation_counts.get(relation) || 0])),
      other_type_top_5: topEntries(parsed.other_types, 5),
    },
    semantic: {
      verdict: queue.length === 0 ? 'PASS_CANDIDATE_REQUIRES_HUMAN_CONFIRMATION' : 'HOLD_REWRITE_QUEUE_PRESENT',
      decision_distribution: Object.fromEntries(topEntries(decisionCounts, 20).map(({ value, count }) => [value, count])),
      flag_distribution: Object.fromEntries(topEntries(flagCounts, 80).map(({ value, count }) => [value, count])),
      relation_cue_gap_distribution: Object.fromEntries(topEntries(relationCueGapCounts, 20).map(({ value, count }) => [value, count])),
      primary_particle_start: primaryStart,
      primary_particle_gate: primaryStart.rate_percent > 45 ? 'HOLD_OVER_45_PERCENT' : (primaryStart.rate_percent > 30 ? 'REVIEW_OVER_30_PERCENT' : 'WITHIN_ADVISORY_RANGE'),
      scenario_cue_counts: scenarioCues,
      similarity,
      rewrite_queue_count: queue.length,
      rewrite_queue: queue,
    },
  };
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(JSON.stringify({
    output,
    structural_verdict: report.structural.verdict,
    hard_error_count: report.structural.hard_error_count,
    semantic_verdict: report.semantic.verdict,
    rewrite_queue_count: report.semantic.rewrite_queue_count,
    source_records: semanticRows.length,
  }, null, 2));
}

try {
  main();
} catch (error) {
  process.stderr.write(`A06 semantic-quality audit failed: ${error.message}\n`);
  process.exitCode = 1;
}
