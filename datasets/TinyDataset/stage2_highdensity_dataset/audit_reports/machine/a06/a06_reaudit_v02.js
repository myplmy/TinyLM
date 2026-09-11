/*
 * A06-only re-audit helper.
 *
 * This is deliberately read-only with respect to source data.  It reads the
 * 52 legacy PSV source files for Stage2 A06 and writes one A06 machine report
 * supplied with --out.  It never edits source, package, registry, manifest,
 * central ledger, or shared audit tools.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const ROOT = path.resolve(__dirname, "../../../../");
const SOURCE_DIR = path.join(ROOT, "stage2_highdensity_dataset", "sources", "train");
const RESERVATION_PATH = path.join(ROOT, "stage1_highdensity_dataset", "TinyLM_Stage2_Stage10_Concept_Family_Reservation.json");
const REGISTRY_PATH = path.join(ROOT, "stage2_highdensity_dataset", "sources", "term_registry", "stage2_(16)relational_composition_train_registry_v01_v52.jsonl");
const MANIFEST_PATH = path.join(ROOT, "stage2_highdensity_dataset", "PREPARATION_MANIFEST.json");
const CENTRAL_LEDGER_PATH = path.join(ROOT, "stage1_highdensity_dataset", "TinyLM_Stage2_Stage10_Actual3M_Expansion_Work_Ledger_2026-09-02.md");
const SHARED_AUDITOR_PATH = path.join(ROOT, "stage2_highdensity_dataset", "tools", "audit_stage2_primary_reviewer_assist.js");
const PREFIX = "stage2_(16)relational_composition_high_density_train_v";
const HEADER = "concept|relations|other_type|text";
const CONTROLLED = [
  "is_a", "subclass_of", "part_of", "classification", "boundary", "contrast",
  "comparison", "function", "role", "process", "state", "attribute", "other",
];
const CONTROLLED_SET = new Set(CONTROLLED);

function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex").toUpperCase();
}

function fileSha(file) {
  return sha256(fs.readFileSync(file));
}

function normalize(value) {
  return String(value).normalize("NFKC").replace(/\s+/g, " ").trim();
}

function words(value) {
  return normalize(value).match(/[0-9A-Za-z가-힣]+/g) || [];
}

function versionOf(name) {
  const m = name.match(/_v(\d+)\.source\.psv$/);
  return m ? Number(m[1]) : null;
}

function idFor(version, row) {
  return `S2-RCH-${String((version - 1) * 150 + row).padStart(5, "0")}`;
}

function pairLabel(doc) {
  return { file: doc.file, line: doc.line, id: doc.id, concept: doc.concept };
}

function topCounts(map, limit = 20) {
  return Object.entries(map)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([value, count]) => ({ value, count }));
}

function jaccard(a, b) {
  const smaller = a.size <= b.size ? a : b;
  const larger = a.size <= b.size ? b : a;
  let intersection = 0;
  for (const x of smaller) if (larger.has(x)) intersection += 1;
  const union = a.size + b.size - intersection;
  return union ? intersection / union : 1;
}

function cosine(a, b) {
  const smaller = a.size <= b.size ? a : b;
  const larger = a.size <= b.size ? b : a;
  let dot = 0;
  for (const [key, value] of smaller) dot += value * (larger.get(key) || 0);
  let na = 0;
  let nb = 0;
  for (const value of a.values()) na += value * value;
  for (const value of b.values()) nb += value * value;
  return na && nb ? dot / Math.sqrt(na * nb) : 0;
}

function charTf(value) {
  const s = normalize(value).replace(/\s+/g, " ");
  const out = new Map();
  for (let n = 3; n <= 5; n += 1) {
    for (let i = 0; i + n <= s.length; i += 1) {
      const gram = s.slice(i, i + n);
      out.set(gram, (out.get(gram) || 0) + 1);
    }
  }
  return out;
}

function batchimInfo(lastHangul) {
  if (!lastHangul || !/[가-힣]/.test(lastHangul)) return null;
  const code = lastHangul.charCodeAt(0) - 0xac00;
  if (code < 0 || code > 11171) return null;
  const jong = code % 28;
  return { hasBatchim: jong !== 0, isRieul: jong === 8 };
}

function suspiciousRoToken(token) {
  if (!token || !token.endsWith("로") || token.length < 2) return null;
  // Common lexical nouns ending in "로" are not particles.  The A06
  // generated source uses these as ordinary nouns (for example 경로/선로/
  // 통로); keep them out of the review queue.  All other matches are only
  // candidates and still require row-level reading before any edit.
  const lexicalNouns = new Set(["경로", "선로", "통로", "점검로"]);
  if (lexicalNouns.has(token)) return null;
  const stem = token.slice(0, -1);
  const last = stem.slice(-1);
  const info = batchimInfo(last);
  if (!info || !info.hasBatchim || info.isRieul) return null;
  return { token, expected: `${stem}으로` };
}

function parseArgs() {
  const out = { phase: "post", out: null, before: null };
  for (let i = 2; i < process.argv.length; i += 1) {
    const arg = process.argv[i];
    if (arg === "--out") out.out = process.argv[++i];
    else if (arg === "--before") out.before = process.argv[++i];
    else if (arg === "--phase") out.phase = process.argv[++i];
  }
  if (!out.out) throw new Error("--out PATH is required");
  return out;
}

function readSource() {
  const expected = Array.from({ length: 52 }, (_, i) => `${PREFIX}${String(i + 1).padStart(2, "0")}.source.psv`);
  const actual = fs.readdirSync(SOURCE_DIR).filter((n) => n.startsWith(PREFIX) && /\.source\.(psv|jsonl)$/.test(n)).sort();
  const errors = {
    missing_files: expected.filter((x) => !actual.includes(x)),
    unexpected_files: actual.filter((x) => !expected.includes(x)),
    duplicate_format_versions: [],
    utf8: [], header: [], columns: [], blank_rows: [], control_characters: [],
    empty_concept: [], empty_text: [], concept_literal_missing: [],
    concept_duplicate: [], concept_normalized_duplicate: [], text_duplicate: [],
    text_normalized_duplicate: [], numeric_suffix: [], relation_controlled: [],
    relation_cardinality: [], relation_internal_duplicate: [], other_type_rule: [],
    other_type_text_mismatch: [], row_count: [], reservation_mismatch: [], registry: [],
  };
  const byVersion = new Map();
  for (const name of actual) {
    const version = versionOf(name);
    if (version != null) {
      if (byVersion.has(version)) errors.duplicate_format_versions.push({ version, files: [byVersion.get(version), name] });
      byVersion.set(version, name);
    }
  }
  const docs = [];
  const files = [];
  const reservations = (() => {
    try {
      const obj = JSON.parse(fs.readFileSync(RESERVATION_PATH, "utf8"));
      return new Map(obj.reservations.filter((x) => x.stage === 2 && x.file_area_slot === 16 && x.split === "train").map((x) => [x.version, x]));
    } catch (error) {
      return new Map();
    }
  })();
  const globalConcept = new Map();
  const globalConceptNorm = new Map();
  const globalText = new Map();
  const globalTextNorm = new Map();
  const relationCounts = Object.fromEntries(CONTROLLED.map((x) => [x, 0]));
  const otherTypeCounts = {};
  const otherTypeExamples = {};
  const familyCounts = {};
  const malformedCounts = {};
  const malformedPatterns = [
    "기록를", "팬가", "하면도", "불이 항목은", "순환하지 않은 경로", "장치은", "센서은",
  ];
  for (const p of malformedPatterns) malformedCounts[p] = 0;
  let totalRows = 0;
  let totalChars = 0;
  let totalWordUnits = 0;

  for (const name of expected) {
    if (!actual.includes(name)) continue;
    const version = versionOf(name);
    const full = path.join(SOURCE_DIR, name);
    const buffer = fs.readFileSync(full);
    let decoded;
    try {
      decoded = new TextDecoder("utf-8", { fatal: true }).decode(buffer);
    } catch (error) {
      errors.utf8.push({ file: name, message: String(error.message || error) });
      continue;
    }
    const lines = decoded.split(/\r?\n/);
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    if (lines[0] !== HEADER) errors.header.push({ file: name, actual: lines[0] || "" });
    const rowLines = lines.slice(1);
    if (rowLines.length !== 150) errors.row_count.push({ file: name, actual: rowLines.length, expected: 150 });
    const reservation = reservations.get(`v${String(version).padStart(2, "0")}`);
    if (!reservation) errors.reservation_mismatch.push({ file: name, reason: "reservation_missing" });
    else {
      if (reservation.record_count !== 150 || reservation.filename !== name.replace(/\.source\.psv$/, ".json")) {
        errors.reservation_mismatch.push({ file: name, reservation });
      }
      familyCounts[reservation.concept_family] = (familyCounts[reservation.concept_family] || 0) + 1;
    }
    const fileDocs = [];
    for (let i = 0; i < rowLines.length; i += 1) {
      const line = rowLines[i];
      const physicalLine = i + 2;
      if (!line) {
        errors.blank_rows.push({ file: name, line: physicalLine });
        continue;
      }
      const cells = line.split("|");
      if (cells.length !== 4) {
        errors.columns.push({ file: name, line: physicalLine, columns: cells.length });
        continue;
      }
      const concept = cells[0].trim();
      const relationText = cells[1].trim();
      const otherType = cells[2].trim();
      const text = cells[3].trim();
      const relations = relationText ? relationText.split(",").map((x) => x.trim()).filter(Boolean) : [];
      const doc = { file: name, version, line: physicalLine, row: i + 1, id: idFor(version, i + 1), concept, relations, otherType, text };
      docs.push(doc); fileDocs.push(doc); totalRows += 1; totalChars += text.length; totalWordUnits += words(text).length;
      if (!concept) errors.empty_concept.push(pairLabel(doc));
      if (!text) errors.empty_text.push(pairLabel(doc));
      if (concept && !text.includes(concept)) errors.concept_literal_missing.push(pairLabel(doc));
      if (/^[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/.test(concept + relationText + otherType + text) || /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/.test(concept + relationText + otherType + text)) {
        errors.control_characters.push(pairLabel(doc));
      }
      if (/[가-힣A-Za-z]\d+/.test(concept) || /[가-힣A-Za-z]\d+/.test(text)) errors.numeric_suffix.push(pairLabel(doc));
      if (relations.length < 2 || relations.length > 5) errors.relation_cardinality.push({ ...pairLabel(doc), count: relations.length });
      const seenRelations = new Set();
      for (const relation of relations) {
        relationCounts[relation] = (relationCounts[relation] || 0) + 1;
        if (!CONTROLLED_SET.has(relation)) errors.relation_controlled.push({ ...pairLabel(doc), relation });
        if (seenRelations.has(relation)) errors.relation_internal_duplicate.push({ ...pairLabel(doc), relation });
        seenRelations.add(relation);
      }
      if (relations.includes("other")) {
        if (!otherType) errors.other_type_rule.push({ ...pairLabel(doc), reason: "other_without_other_type" });
        else {
          otherTypeCounts[otherType] = (otherTypeCounts[otherType] || 0) + 1;
          if (!otherTypeExamples[otherType]) otherTypeExamples[otherType] = pairLabel(doc);
          if (!text.includes(otherType)) errors.other_type_text_mismatch.push({ ...pairLabel(doc), other_type: otherType });
        }
      } else if (otherType) {
        errors.other_type_rule.push({ ...pairLabel(doc), reason: "other_type_without_other_relation", other_type: otherType });
      }
      const normConcept = normalize(concept);
      const normText = normalize(text);
      if (globalConcept.has(concept)) errors.concept_duplicate.push({ ...pairLabel(doc), first: globalConcept.get(concept) });
      else globalConcept.set(concept, pairLabel(doc));
      if (globalConceptNorm.has(normConcept)) errors.concept_normalized_duplicate.push({ ...pairLabel(doc), first: globalConceptNorm.get(normConcept) });
      else globalConceptNorm.set(normConcept, pairLabel(doc));
      if (globalText.has(text)) errors.text_duplicate.push({ ...pairLabel(doc), first: globalText.get(text) });
      else globalText.set(text, pairLabel(doc));
      if (globalTextNorm.has(normText)) errors.text_normalized_duplicate.push({ ...pairLabel(doc), first: globalTextNorm.get(normText) });
      else globalTextNorm.set(normText, pairLabel(doc));
      for (const p of malformedPatterns) if ((concept + " " + text).includes(p)) malformedCounts[p] += 1;
    }
    files.push({
      file: name, version, records: fileDocs.length, sha256: sha256(buffer), bytes: buffer.length,
      first_id: idFor(version, 1), last_id: idFor(version, 150),
    });
  }
  return { errors, docs, files, relationCounts, otherTypeCounts, otherTypeExamples, familyCounts, malformedCounts, totalRows, totalChars, totalWordUnits, actual };
}

function buildAnalyses(data) {
  const { docs } = data;
  const repeated5 = new Map();
  const opening4 = new Map();
  const skeletonCounts = new Map();
  const coreGroups = new Map();
  const duplicateWords = [];
  const duplicateWordCounts = {};
  const roCandidates = [];
  const roCounts = {};
  const primaryStartCounts = { 은: 0, 는: 0 };
  const primaryStartExamples = [];
  const dashPrimaryRows = [];
  const sameCoreRows = [];
  const markerCounts = {};
  const wordSets = [];
  const charTfs = [];
  const charDf = new Map();
  const relationBuckets = new Map();
  const relationCue = {
    part_of: ["부분", "전체", "포함", "구성", "일부", "안에"],
    process: ["과정", "뒤", "후", "전", "이어", "변화", "진행", "순서", "단계", "거쳐"],
    state: ["상태", "열려", "닫혀", "대기", "유지", "보류", "안정", "확인된", "결측"],
    role: ["역할", "담당", "관리자", "운영자", "기술자", "조사원", "담당자", "제어기"],
    function: ["기능", "사용", "작동", "수행", "담당", "처리", "조정", "제어", "추적", "검증"],
    boundary: ["구분", "구별", "경계", "다르", "혼동", "구분하", "가르", "대조"],
    comparison: ["비교", "보다", "더", "덜", "차이", "우선", "먼저", "높", "낮", "상한", "하한"],
    classification: ["분류", "분류표", "범주", "종류", "기준", "항목", "목록", "체계"],
    attribute: ["값", "수치", "측정", "온도", "압력", "수위", "비율", "특성", "속성", "채널"],
    other: [], contrast: ["반대", "대비", "서로 다른", "충돌", "대조", "상충"],
  };
  const cueMissing = Object.fromEntries(Object.keys(relationCue).map((x) => [x, 0]));
  const cueMissingExamples = Object.fromEntries(Object.keys(relationCue).map((x) => [x, []]));

  for (const doc of docs) {
    const ws = words(doc.text);
    const wset = new Set(ws);
    wordSets.push(wset);
    const tf = charTf(doc.text);
    charTfs.push(tf);
    for (const term of tf.keys()) charDf.set(term, (charDf.get(term) || 0) + 1);
    for (let i = 0; i + 5 <= ws.length; i += 1) {
      const key = ws.slice(i, i + 5).join(" ");
      if (!repeated5.has(key)) repeated5.set(key, []);
      repeated5.get(key).push(pairLabel(doc));
    }
    if (ws.length >= 4) {
      const key = ws.slice(0, 4).join(" ");
      if (!opening4.has(key)) opening4.set(key, []);
      opening4.get(key).push(pairLabel(doc));
    }
    for (let i = 1; i < ws.length; i += 1) {
      if (ws[i] === ws[i - 1]) {
        duplicateWords.push({ ...pairLabel(doc), word: ws[i], position: i + 1 });
        duplicateWordCounts[ws[i]] = (duplicateWordCounts[ws[i]] || 0) + 1;
      }
    }
    for (const token of words(doc.concept + " " + doc.text)) {
      const hit = suspiciousRoToken(token);
      if (hit) {
        roCandidates.push({ ...pairLabel(doc), token: hit.token, expected: hit.expected });
        roCounts[hit.token] = (roCounts[hit.token] || 0) + 1;
      }
    }
    const start = normalize(doc.text);
    if (start.startsWith(`${doc.concept}은`)) { primaryStartCounts.은 += 1; primaryStartExamples.push({ ...pairLabel(doc), particle: "은" }); }
    if (start.startsWith(`${doc.concept}는`)) { primaryStartCounts.는 += 1; primaryStartExamples.push({ ...pairLabel(doc), particle: "는" }); }
    const core = normalize(doc.concept).split(" — ")[0];
    const skeleton = normalize(doc.text).split(normalize(doc.concept)).join("{PRIMARY}");
    skeletonCounts.set(skeleton, (skeletonCounts.get(skeleton) || []).concat([pairLabel(doc)]));
    coreGroups.set(core, (coreGroups.get(core) || []).concat([pairLabel(doc)]));
    if (doc.concept.includes(" — ")) {
      dashPrimaryRows.push(pairLabel(doc));
      const marker = doc.concept.split(" — ").slice(1).join(" — ");
      markerCounts[marker] = (markerCounts[marker] || 0) + 1;
    }
    const signature = [...new Set(doc.relations)].sort().join(",");
    if (!relationBuckets.has(signature)) relationBuckets.set(signature, []);
    relationBuckets.get(signature).push(doc);
    for (const relation of doc.relations) {
      const cues = relationCue[relation] || [];
      if (cues.length && !cues.some((cue) => doc.text.includes(cue))) {
        cueMissing[relation] = (cueMissing[relation] || 0) + 1;
        if (cueMissingExamples[relation].length < 10) cueMissingExamples[relation].push(pairLabel(doc));
      }
    }
  }
  const repeated5Groups = [...repeated5.entries()].filter(([, rows]) => rows.length > 1);
  const opening4Groups = [...opening4.entries()].filter(([, rows]) => rows.length > 1);
  const skeletonGroups = [...skeletonCounts.entries()].filter(([, rows]) => rows.length > 1);
  const coreRepeated = [...coreGroups.entries()].filter(([, rows]) => rows.length > 1);
  const coreCrossVersion = coreRepeated.filter(([, rows]) => new Set(rows.map((x) => x.file)).size > 1);
  const coreRowsRepeated = coreRepeated.reduce((n, [, rows]) => n + rows.length, 0);

  const idf = new Map();
  for (const [term, df] of charDf.entries()) idf.set(term, Math.log((docs.length + 1) / (df + 1)) + 1);
  const charVectors = charTfs.map((tf) => {
    const out = new Map();
    for (const [term, count] of tf.entries()) out.set(term, count * (idf.get(term) || 0));
    return out;
  });
  const sim = {
    potential_pairs: 0, evaluated_pairs: 0,
    word_jaccard: { max: { score: -1 }, ge_090: 0, ge_095: 0, ge_097: 0, top: [] },
    char_3_5gram_tfidf_cosine: { max: { score: -1 }, ge_090: 0, ge_095: 0, ge_097: 0, top: [] },
  };
  const topPush = (arr, item, limit = 50) => { arr.push(item); arr.sort((a, b) => b.score - a.score); if (arr.length > limit) arr.length = limit; };
  for (const [signature, bucket] of relationBuckets.entries()) {
    for (let i = 0; i < bucket.length; i += 1) {
      const a = bucket[i];
      const ai = docs.indexOf(a);
      for (let j = i + 1; j < bucket.length; j += 1) {
        const b = bucket[j];
        const bi = docs.indexOf(b);
        sim.potential_pairs += 1; sim.evaluated_pairs += 1;
        const jScore = jaccard(wordSets[ai], wordSets[bi]);
        const cScore = cosine(charVectors[ai], charVectors[bi]);
        const coreA = normalize(a.concept).split(" — ")[0];
        const coreB = normalize(b.concept).split(" — ")[0];
        const sameCore = coreA === coreB;
        const skeletonA = normalize(a.text).split(normalize(a.concept)).join("{PRIMARY}");
        const skeletonB = normalize(b.text).split(normalize(b.concept)).join("{PRIMARY}");
        const sameSkeleton = skeletonA === skeletonB;
        const base = { a: pairLabel(a), b: pairLabel(b), relation_signature: signature, sameCore, sameSkeleton };
        if (jScore >= 0.90) sim.word_jaccard.ge_090 += 1;
        if (jScore >= 0.95) sim.word_jaccard.ge_095 += 1;
        if (jScore >= 0.97) sim.word_jaccard.ge_097 += 1;
        topPush(sim.word_jaccard.top, { ...base, score: jScore });
        if (jScore > sim.word_jaccard.max.score) sim.word_jaccard.max = { ...base, score: jScore };
        if (cScore >= 0.90) sim.char_3_5gram_tfidf_cosine.ge_090 += 1;
        if (cScore >= 0.95) sim.char_3_5gram_tfidf_cosine.ge_095 += 1;
        if (cScore >= 0.97) sim.char_3_5gram_tfidf_cosine.ge_097 += 1;
        topPush(sim.char_3_5gram_tfidf_cosine.top, { ...base, score: cScore });
        if (cScore > sim.char_3_5gram_tfidf_cosine.max.score) sim.char_3_5gram_tfidf_cosine.max = { ...base, score: cScore };
      }
    }
  }

  const toCountList = (map, limit = 50) => [...map.entries()].map(([value, rows]) => ({ value, count: rows.length, examples: rows.slice(0, 3) })).sort((a, b) => b.count - a.count || a.value.localeCompare(b.value)).slice(0, limit);
  return {
    duplicate_words: { row_count: duplicateWords.length, token_counts: topCounts(duplicateWordCounts, 50), rows: duplicateWords },
    ro_particle_candidates: { occurrence_count: roCandidates.length, record_count: new Set(roCandidates.map((x) => `${x.file}:${x.line}`)).size, token_counts: topCounts(roCounts, 50), rows: roCandidates },
    primary_start: { count: primaryStartCounts.은 + primaryStartCounts.는, ratio: docs.length ? (primaryStartCounts.은 + primaryStartCounts.는) / docs.length : 0, particle_counts: primaryStartCounts, examples: primaryStartExamples.slice(0, 30) },
    dash_primary: { count: dashPrimaryRows.length, ratio: docs.length ? dashPrimaryRows.length / docs.length : 0, marker_counts: markerCounts },
    repeated_5gram: { distinct_groups: repeated5Groups.length, total_occurrences: repeated5Groups.reduce((n, [, rows]) => n + rows.length, 0), top: toCountList(repeated5, 30) },
    repeated_4gram_opening: { distinct_groups: opening4Groups.length, total_occurrences: opening4Groups.reduce((n, [, rows]) => n + rows.length, 0), top: toCountList(opening4, 30) },
    skeleton: { distinct: skeletonCounts.size, repeated_group_count: skeletonGroups.length, repeated_record_count: skeletonGroups.reduce((n, [, rows]) => n + rows.length, 0), top: toCountList(skeletonCounts, 30) },
    core: { distinct: coreGroups.size, repeated_group_count: coreRepeated.length, repeated_record_count: coreRowsRepeated, max_group_size: coreRepeated.reduce((m, [, rows]) => Math.max(m, rows.length), 0), cross_version_group_count: coreCrossVersion.length, top: toCountList(coreGroups, 30) },
    similarity: sim,
    relation_cue_triage: { missing_counts: cueMissing, examples: cueMissingExamples },
    relation_bucket_counts: [...relationBuckets.entries()].map(([signature, rows]) => ({ signature, records: rows.length })).sort((a, b) => b.records - a.records),
  };
}

function registryAudit(data) {
  const errors = [];
  const rows = [];
  if (!fs.existsSync(REGISTRY_PATH)) return { record_count: 0, parse_errors: 0, errors: [{ reason: "registry_missing" }] };
  const lines = fs.readFileSync(REGISTRY_PATH, "utf8").split(/\r?\n/).filter(Boolean);
  let parseErrors = 0;
  for (let i = 0; i < lines.length; i += 1) {
    try { rows.push(JSON.parse(lines[i])); } catch (error) { parseErrors += 1; errors.push({ line: i + 1, reason: "json_parse" }); }
  }
  const docMap = new Map(data.docs.map((d) => [`${d.file}:${d.line}`, d]));
  for (const row of rows) {
    const key = `${row.source_file}:${row.source_line}`;
    const doc = docMap.get(key);
    if (!doc) errors.push({ key, reason: "source_locator_missing" });
    else if (row.primary !== doc.concept) errors.push({ key, reason: "primary_mismatch", registry: row.primary, source: doc.concept });
  }
  if (rows.length !== data.docs.length) errors.push({ reason: "record_count_mismatch", registry: rows.length, source: data.docs.length });
  return { record_count: rows.length, parse_errors: parseErrors, mismatch_count: errors.length, errors: errors.slice(0, 100) };
}

function protectedHashes() {
  const out = {};
  for (const [name, file] of [["manifest", MANIFEST_PATH], ["central_ledger", CENTRAL_LEDGER_PATH], ["shared_auditor", SHARED_AUDITOR_PATH]]) {
    out[name] = fs.existsSync(file) ? fileSha(file) : null;
  }
  return out;
}

function loadBefore(pathValue) {
  if (!pathValue || !fs.existsSync(pathValue)) return null;
  try { return JSON.parse(fs.readFileSync(pathValue, "utf8")); } catch (_) { return null; }
}

function main() {
  const args = parseArgs();
  const data = readSource();
  const analyses = buildAnalyses(data);
  const before = loadBefore(args.before);
  const beforeFiles = before && before.files ? new Map(before.files.map((x) => [x.file, x.sha256])) : new Map();
  const changedFiles = data.files.map((x) => ({ file: x.file, before_sha256: beforeFiles.get(x.file) || null, after_sha256: x.sha256, changed: beforeFiles.has(x.file) ? beforeFiles.get(x.file) !== x.sha256 : null })).filter((x) => x.changed !== false);
  const structuralCounts = {};
  for (const [key, value] of Object.entries(data.errors)) structuralCounts[key] = Array.isArray(value) ? value.length : value;
  const relationTotal = Object.values(data.relationCounts).reduce((a, b) => a + b, 0);
  const legacyOnlyMismatchKeys = new Set(["other_type_text_mismatch"]);
  const hardStructuralCount = Object.entries(structuralCounts)
    .filter(([key]) => !legacyOnlyMismatchKeys.has(key))
    .reduce((n, [, value]) => n + value, 0);
  const legacyWarningCount = data.errors.other_type_text_mismatch.length;
  const report = {
    audit_id: `A06_REAUDIT_V02_${args.phase.toUpperCase()}`,
    generated_at: new Date().toISOString(),
    phase: args.phase,
    scope: { area: "A06", split: "train", source_format: "legacy_psv", expected_files: 52, expected_records: 7800, actual_files: data.files.length, actual_records: data.totalRows },
    files: data.files,
    source_set_sha256: sha256(Buffer.from(data.files.map((x) => `${x.file}\t${x.sha256}`).sort().join("\n"), "utf8")),
    changed_files: changedFiles,
    structural_errors: data.errors,
    structural_error_counts: structuralCounts,
    relation_audit: { counts: data.relationCounts, total_labels: relationTotal, controlled_vocabulary: CONTROLLED },
    other_type_audit: { top5: topCounts(data.otherTypeCounts, 5), distinct_types: Object.keys(data.otherTypeCounts).length, examples: data.otherTypeExamples },
    diversity_audit: analyses,
    size_audit: { total_text_chars: data.totalChars, total_word_units: data.totalWordUnits, average_word_units: data.totalRows ? data.totalWordUnits / data.totalRows : 0 },
    registry_audit: registryAudit(data),
    split_leakage: { status: "NOT_RUN_SOURCE_ONLY", reason: "A06 validation source is outside this task scope" },
    protected_scope: protectedHashes(),
    verdict: {
      structural: hardStructuralCount === 0 ? (legacyWarningCount ? "PASS_WITH_LEGACY_WARNING" : "PASS") : "FAIL",
      structural_hard_error_count: hardStructuralCount,
      legacy_warning_count: legacyWarningCount,
      semantic_naturalness: "HOLD",
      packaging: "NOT_RUN_SOURCE_ONLY",
      note: "Similarity, relation-cue, duplicate-word, and particle flags are advisory until record-level review is completed.",
    },
  };
  fs.mkdirSync(path.dirname(args.out), { recursive: true });
  fs.writeFileSync(args.out, JSON.stringify(report, null, 2) + "\n", "utf8");
  process.stdout.write(JSON.stringify({ out: args.out, source_set_sha256: report.source_set_sha256, files: data.files.length, records: data.totalRows, structural: report.verdict.structural, duplicate_word_rows: analyses.duplicate_words.row_count, ro_candidate_records: analyses.ro_particle_candidates.record_count, jaccard_ge95: analyses.similarity.word_jaccard.ge_095, tfidf_ge95: analyses.similarity.char_3_5gram_tfidf_cosine.ge_095 }, null, 2) + "\n");
}

main();
