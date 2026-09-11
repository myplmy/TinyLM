/* A06-only read-only source audit.
 * This script writes only the A06 audit JSON/Markdown reports supplied on the
 * command line (or the canonical A06 audit paths below). It never edits source
 * files, packages, shared audit tools, manifests, or the central ledger.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const ROOT = path.resolve(__dirname, "../../../../");
const SOURCE_DIR = path.join(ROOT, "stage2_highdensity_dataset", "sources", "train");
const RESERVATION_PATH = path.join(ROOT, "stage1_highdensity_dataset", "TinyLM_Stage2_Stage10_Concept_Family_Reservation.json");
const REGISTRY_PATH = path.join(ROOT, "stage2_highdensity_dataset", "sources", "term_registry", "stage2_(16)relational_composition_train_registry_v01_v52.jsonl");
const OUT_JSON = path.join(__dirname, "TinyLM_Stage2_A06_RelationalComposition_Source_Audit_2026-09-11.json");
const OUT_MD = path.join(ROOT, "stage2_highdensity_dataset", "audit_reports", "a06", "TinyLM_Stage2_A06_RelationalComposition_Source_Audit_2026-09-11.md");

const CONTROLLED = [
  "is_a", "subclass_of", "part_of", "classification", "boundary", "contrast",
  "comparison", "function", "role", "process", "state", "attribute", "other",
];
const CONTROLLED_SET = new Set(CONTROLLED);
const EXPECTED_HEADER = "concept|relations|other_type|text";
const SOURCE_PREFIX = "stage2_(16)relational_composition_high_density_train_v";

function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex").toUpperCase();
}

function decodeUtf8(buffer) {
  return new TextDecoder("utf-8", { fatal: true }).decode(buffer);
}

function normalize(value) {
  return String(value).normalize("NFKC").replace(/\s+/g, " ").trim();
}

function words(value) {
  return normalize(value).match(/[0-9A-Za-z가-힣]+/g) || [];
}

function charNgrams(value) {
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

function particleForLastHangul(value) {
  const compact = String(value).trim();
  const m = compact.match(/[가-힣]$/);
  if (!m) return null;
  const code = compact.charCodeAt(compact.length - 1) - 0xac00;
  const hasBatchim = code >= 0 && code <= 11171 && code % 28 !== 0;
  return hasBatchim ? { 은는: "은", 이가: "이", 을를: "을", 과와: "과", 로: "으로" } : { 은는: "는", 이가: "가", 을를: "를", 과와: "와", 로: "로" };
}

function versionOf(filename) {
  const marker = "_v";
  const at = filename.lastIndexOf(marker);
  if (at < 0) return null;
  const tail = filename.slice(at + marker.length).split(".")[0];
  const n = Number(tail);
  return Number.isInteger(n) ? n : null;
}

function idFor(row, version) {
  const number = (version - 1) * 150 + row;
  return `S2-RCH-${String(number).padStart(5, "0")}`;
}

function addCount(map, key, amount = 1) {
  map[key] = (map[key] || 0) + amount;
}

function topCounts(map, limit = 20) {
  return Object.entries(map)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([value, count]) => ({ value, count }));
}

function pairLabel(doc) {
  return { file: doc.file, line: doc.line, id: doc.id, concept: doc.concept };
}

function jaccard(a, b) {
  const smaller = a.size <= b.size ? a : b;
  const larger = a.size <= b.size ? b : a;
  let intersection = 0;
  for (const item of smaller) if (larger.has(item)) intersection += 1;
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

function sentenceSkeleton(text, concept) {
  return normalize(text).split(normalize(concept)).join("{PRIMARY}");
}

function readReservation() {
  const reservation = JSON.parse(fs.readFileSync(RESERVATION_PATH, "utf8"));
  const rows = reservation.reservations.filter((x) => x.stage === 2 && x.file_area_slot === 16 && x.split === "train");
  return new Map(rows.map((x) => [x.version, x]));
}

function main() {
  const reservations = readReservation();
  const allNames = fs.readdirSync(SOURCE_DIR)
    .filter((name) => name.startsWith(SOURCE_PREFIX) && name.endsWith(".source.psv"))
    .sort();
  const expectedNames = Array.from({ length: 52 }, (_, i) => `${SOURCE_PREFIX}${String(i + 1).padStart(2, "0")}.source.psv`);
  const files = [];
  const docs = [];
  const errors = {
    missing_files: [],
    unexpected_files: allNames.filter((x) => !expectedNames.includes(x)),
    utf8: [],
    header: [],
    columns: [],
    control_characters: [],
    empty_concept: [],
    empty_text: [],
    concept_literal_missing: [],
    concept_duplicate: [],
    concept_normalized_duplicate: [],
    text_duplicate: [],
    text_normalized_duplicate: [],
    numeric_suffix: [],
    relation_controlled: [],
    relation_cardinality: [],
    relation_internal_duplicate: [],
    other_type_rule: [],
    other_type_text_mismatch: [],
    row_count: [],
    reservation_mismatch: [],
    registry: [],
  };
  for (const name of expectedNames) if (!allNames.includes(name)) errors.missing_files.push(name);

  const conceptSeen = new Map();
  const conceptNormSeen = new Map();
  const textSeen = new Map();
  const textNormSeen = new Map();
  const relationCounts = Object.fromEntries(CONTROLLED.map((x) => [x, 0]));
  const otherTypeCounts = {};
  const otherTypeExamples = {};
  const familyCounts = {};
  const relationBuckets = new Map();
  const skeletonCounts = {};
  const ngram5Counts = {};
  const opening4Counts = {};
  const twoCore = [];
  let chars = 0;
  let wordCount = 0;
  let textStartsWithPrimaryParticle = 0;
  const startParticleCounts = { 은: 0, 는: 0 };
  let particleExpectedChecks = 0;
  let particleMismatchCount = 0;
  const particleMismatchExamples = [];
  const malformedPatterns = [
    "기록를", "팬가", "하면도", "불이 항목은", "순환하지 않은 경로", "장치은", "센서은",
  ];
  const malformedPatternCounts = Object.fromEntries(malformedPatterns.map((x) => [x, 0]));
  let totalRows = 0;

  for (const name of expectedNames) {
    if (!allNames.includes(name)) continue;
    const version = versionOf(name);
    const full = path.join(SOURCE_DIR, name);
    const buffer = fs.readFileSync(full);
    const fileHash = sha256(buffer);
    let decoded;
    try {
      decoded = decodeUtf8(buffer);
    } catch (error) {
      errors.utf8.push({ file: name, message: String(error.message || error) });
      continue;
    }
    const lines = decoded.split(/\r?\n/);
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    if (lines[0] !== EXPECTED_HEADER) errors.header.push({ file: name, actual: lines[0] || "" });
    const rowLines = lines.slice(1);
    const reservation = reservations.get(`v${String(version).padStart(2, "0")}`);
    if (!reservation) errors.reservation_mismatch.push({ file: name, reason: "reservation_missing" });
    else {
      const expectedPackageName = name.replace(/\.source\.psv$/, ".json");
      if (reservation.filename !== expectedPackageName || reservation.record_count !== 150) {
        errors.reservation_mismatch.push({ file: name, expectedPackageName, reservation });
      }
      addCount(familyCounts, reservation.concept_family);
    }
    const fileDocs = [];
    const fileRelationCounts = Object.fromEntries(CONTROLLED.map((x) => [x, 0]));
    for (let i = 0; i < rowLines.length; i += 1) {
      const physicalLine = i + 2;
      const line = rowLines[i];
      if (!line) continue;
      const cells = line.split("|");
      if (cells.length !== 4) {
        errors.columns.push({ file: name, line: physicalLine, columns: cells.length });
        continue;
      }
      const concept = cells[0].trim();
      const relationText = cells[1].trim();
      const otherType = cells[2].trim();
      const text = cells[3].trim();
      const relationList = relationText ? relationText.split(",").map((x) => x.trim()).filter(Boolean) : [];
      const doc = { file: name, version, line: physicalLine, row: i + 1, id: idFor(i + 1, version), concept, relations: relationList, otherType, text };
      fileDocs.push(doc);
      docs.push(doc);
      totalRows += 1;
      chars += text.length;
      wordCount += words(text).length;
      if (!concept) errors.empty_concept.push(pairLabel(doc));
      if (!text) errors.empty_text.push(pairLabel(doc));
      if (concept && !text.includes(concept)) errors.concept_literal_missing.push(pairLabel(doc));
      if (/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/.test(concept + relationText + otherType + text)) errors.control_characters.push(pairLabel(doc));
      if (/[가-힣A-Za-z]\d+/.test(concept) || /[가-힣A-Za-z]\d+/.test(text)) errors.numeric_suffix.push(pairLabel(doc));
      const seenRelations = new Set();
      if (relationList.length < 2 || relationList.length > 5) errors.relation_cardinality.push({ ...pairLabel(doc), count: relationList.length });
      for (const relation of relationList) {
        if (!CONTROLLED_SET.has(relation)) errors.relation_controlled.push({ ...pairLabel(doc), relation });
        addCount(relationCounts, relation);
        addCount(fileRelationCounts, relation);
        if (seenRelations.has(relation)) errors.relation_internal_duplicate.push({ ...pairLabel(doc), relation });
        seenRelations.add(relation);
      }
      if (relationList.includes("other")) {
        if (!otherType) errors.other_type_rule.push({ ...pairLabel(doc), reason: "other_without_other_type" });
        else {
          addCount(otherTypeCounts, otherType);
          if (!otherTypeExamples[otherType]) otherTypeExamples[otherType] = pairLabel(doc);
          if (!text.includes(otherType)) errors.other_type_text_mismatch.push({ ...pairLabel(doc), other_type: otherType });
        }
      } else if (otherType) {
        errors.other_type_rule.push({ ...pairLabel(doc), reason: "other_type_without_other_relation", other_type: otherType });
      }
      const normConcept = normalize(concept);
      const normText = normalize(text);
      if (conceptSeen.has(concept)) errors.concept_duplicate.push({ ...pairLabel(doc), first: conceptSeen.get(concept) });
      else conceptSeen.set(concept, pairLabel(doc));
      if (conceptNormSeen.has(normConcept)) errors.concept_normalized_duplicate.push({ ...pairLabel(doc), first: conceptNormSeen.get(normConcept) });
      else conceptNormSeen.set(normConcept, pairLabel(doc));
      if (textSeen.has(text)) errors.text_duplicate.push({ ...pairLabel(doc), first: textSeen.get(text) });
      else textSeen.set(text, pairLabel(doc));
      if (textNormSeen.has(normText)) errors.text_normalized_duplicate.push({ ...pairLabel(doc), first: textNormSeen.get(normText) });
      else textNormSeen.set(normText, pairLabel(doc));
      const signature = [...new Set(relationList)].sort().join(",");
      doc.relationSignature = signature;
      doc.wordSet = new Set(words(text));
      if (!relationBuckets.has(signature)) relationBuckets.set(signature, []);
      relationBuckets.get(signature).push(doc);
      addCount(skeletonCounts, sentenceSkeleton(text, concept));
      const tokenWords = words(text);
      for (let k = 0; k + 5 <= tokenWords.length; k += 1) addCount(ngram5Counts, tokenWords.slice(k, k + 5).join(" "));
      if (tokenWords.length >= 4) addCount(opening4Counts, tokenWords.slice(0, 4).join(" "));
      const core = concept.split(" — ")[0].trim();
      const coreTokens = core ? core.split(/\s+/) : [];
      if (coreTokens.length === 2) twoCore.push({ ...doc, x1: coreTokens[0], x2: coreTokens[1] });
      const expected = particleForLastHangul(concept);
      let occurrence = text.indexOf(concept);
      let firstOccurrence = true;
      while (occurrence >= 0) {
        const actual = text.charAt(occurrence + concept.length);
        if ((actual === "은" || actual === "는") && expected) {
          particleExpectedChecks += 1;
          if (actual !== expected.은는) {
            particleMismatchCount += 1;
            if (particleMismatchExamples.length < 20) particleMismatchExamples.push({ ...pairLabel(doc), actual, expected: expected.은는 });
          }
        }
        if (firstOccurrence && (occurrence === 0) && (actual === "은" || actual === "는")) {
          textStartsWithPrimaryParticle += 1;
          startParticleCounts[actual] += 1;
        }
        firstOccurrence = false;
        occurrence = text.indexOf(concept, occurrence + Math.max(1, concept.length));
      }
      for (const pattern of malformedPatterns) if (text.includes(pattern) || concept.includes(pattern)) malformedPatternCounts[pattern] += 1;
    }
    if (fileDocs.length !== 150) errors.row_count.push({ file: name, rows: fileDocs.length });
    if (reservation && fileDocs.length) {
      const actualRange = `${fileDocs[0].id} ~ ${fileDocs[fileDocs.length - 1].id}`;
      if (reservation.id_range !== actualRange) errors.reservation_mismatch.push({ file: name, expected_id_range: reservation.id_range, actual_id_range: actualRange });
    }
    const fileTextChars = fileDocs.reduce((sum, x) => sum + x.text.length, 0);
    const fileWords = fileDocs.reduce((sum, x) => sum + words(x.text).length, 0);
    files.push({
      version: `v${String(version).padStart(2, "0")}`,
      file: name,
      id_range: fileDocs.length ? `${fileDocs[0].id} ~ ${fileDocs[fileDocs.length - 1].id}` : null,
      records: fileDocs.length,
      concept_family: reservation ? reservation.concept_family : null,
      domain: reservation ? reservation.domain : null,
      semantic_axis: reservation ? reservation.semantic_axis : null,
      origin: reservation ? reservation.origin : null,
      relation_counts: fileRelationCounts,
      source_sha256: fileHash,
      text_characters: fileTextChars,
      word_units: fileWords,
      avg_text_characters: fileDocs.length ? Number((fileTextChars / fileDocs.length).toFixed(2)) : 0,
      avg_word_units: fileDocs.length ? Number((fileWords / fileDocs.length).toFixed(2)) : 0,
      package_expected: reservation ? reservation.filename : null,
      package_present: fs.existsSync(path.join(ROOT, "stage2_highdensity_dataset", "train", reservation ? reservation.filename : "")),
    });
  }

  const sortedHashMaterial = files.slice().sort((a, b) => a.file.localeCompare(b.file)).map((x) => `${x.file}\t${x.source_sha256}`).join("\n");
  const sourceSetSha = sha256(Buffer.from(sortedHashMaterial, "utf8"));
  const repeated5 = topCounts(ngram5Counts, 20);
  const repeatedOpening4 = topCounts(opening4Counts, 20);
  const repeatedSkeletons = topCounts(skeletonCounts, 20);

  function groupStats(key) {
    const groups = new Map();
    for (const row of twoCore) {
      if (!groups.has(row[key])) groups.set(row[key], []);
      groups.get(row[key]).push(row);
    }
    const repeated = [...groups.entries()].filter(([, rows]) => rows.length > 1);
    const differing = repeated.filter(([, rows]) => new Set(rows.map((x) => key === "x1" ? x.x2 : x.x1)).size > 1);
    return {
      distinct_values: groups.size,
      repeated_group_count: repeated.length,
      repeated_record_count: repeated.reduce((sum, [, rows]) => sum + rows.length, 0),
      differing_other_token_group_count: differing.length,
      differing_other_token_record_count: differing.reduce((sum, [, rows]) => sum + rows.length, 0),
      examples: differing.slice(0, 5).map(([value, rows]) => ({ value, other_values: [...new Set(rows.map((x) => key === "x1" ? x.x2 : x.x1))].slice(0, 8), records: rows.slice(0, 4).map(pairLabel) })),
    };
  }

  const tfidfDocs = docs.map((doc) => ({ doc, grams: charNgrams(doc.text) }));
  const df = new Map();
  for (const item of tfidfDocs) for (const key of item.grams.keys()) df.set(key, (df.get(key) || 0) + 1);
  const tfidfVectors = tfidfDocs.map(({ doc, grams }) => {
    const vector = new Map();
    for (const [key, count] of grams) {
      const idf = Math.log((docs.length + 1) / ((df.get(key) || 0) + 1)) + 1;
      vector.set(key, (1 + Math.log(count)) * idf);
    }
    return { doc, vector };
  });
  const vectorByDoc = new Map(tfidfVectors.map((x) => [x.doc, x.vector]));
  let jaccardPotential = 0;
  let jaccardEvaluated = 0;
  let tfidfPotential = 0;
  let tfidfEvaluated = 0;
  const PAIR_CAP = 200000;
  let maxJaccard = { score: -1, a: null, b: null };
  let maxCosine = { score: -1, a: null, b: null };
  for (const bucket of relationBuckets.values()) {
    const potential = bucket.length * (bucket.length - 1) / 2;
    jaccardPotential += potential;
    const jStride = potential > PAIR_CAP ? Math.ceil(potential / PAIR_CAP) : 1;
    let pairIndex = 0;
    for (let i = 0; i < bucket.length; i += 1) {
      for (let j = i + 1; j < bucket.length; j += 1) {
        if (pairIndex % jStride === 0) {
          const score = jaccard(bucket[i].wordSet, bucket[j].wordSet);
          jaccardEvaluated += 1;
          if (score > maxJaccard.score) maxJaccard = { score, a: pairLabel(bucket[i]), b: pairLabel(bucket[j]), relation_signature: bucket[i].relationSignature };
        }
        pairIndex += 1;
      }
    }
    tfidfPotential += potential;
    const tStride = potential > PAIR_CAP ? Math.ceil(potential / PAIR_CAP) : 1;
    pairIndex = 0;
    for (let i = 0; i < bucket.length; i += 1) {
      for (let j = i + 1; j < bucket.length; j += 1) {
        if (pairIndex % tStride === 0) {
          const score = cosine(vectorByDoc.get(bucket[i]), vectorByDoc.get(bucket[j]));
          tfidfEvaluated += 1;
          if (score > maxCosine.score) maxCosine = { score, a: pairLabel(bucket[i]), b: pairLabel(bucket[j]), relation_signature: bucket[i].relationSignature };
        }
        pairIndex += 1;
      }
    }
  }

  const registry = { path: REGISTRY_PATH, exists: fs.existsSync(REGISTRY_PATH), records: 0, parse_errors: [], mismatches: [] };
  if (registry.exists) {
    const lines = fs.readFileSync(REGISTRY_PATH, "utf8").split(/\r?\n/).filter(Boolean);
    for (let i = 0; i < lines.length; i += 1) {
      try {
        const row = JSON.parse(lines[i]);
        registry.records += 1;
        const sourceDoc = docs.find((x) => x.file === row.source_file && x.line === row.source_line);
        if (!sourceDoc || sourceDoc.concept !== row.primary) registry.mismatches.push({ registry_line: i + 1, source_file: row.source_file, source_line: row.source_line, primary: row.primary });
      } catch (error) {
        registry.parse_errors.push({ line: i + 1, message: String(error.message || error) });
      }
    }
  }

  const packageFiles = expectedNames.map((name) => name.replace(/\.source\.psv$/, ".json"));
  const presentPackages = packageFiles.filter((name) => fs.existsSync(path.join(ROOT, "stage2_highdensity_dataset", "train", name)));
  const packageProjection = { file: packageFiles[0], present: presentPackages.includes(packageFiles[0]), checked: false, parse_error: null, record_count: null, mismatches: [] };
  if (packageProjection.present) {
    try {
      const packageJson = JSON.parse(fs.readFileSync(path.join(ROOT, "stage2_highdensity_dataset", "train", packageFiles[0]), "utf8"));
      packageProjection.checked = true;
      packageProjection.record_count = Array.isArray(packageJson.records) ? packageJson.records.length : null;
      const sourceRows = docs.filter((x) => x.version === 1).sort((a, b) => a.row - b.row);
      if (!Array.isArray(packageJson.records) || packageJson.records.length !== sourceRows.length) packageProjection.mismatches.push({ reason: "record_count" });
      else for (let i = 0; i < sourceRows.length; i += 1) {
        const sourceRow = sourceRows[i];
        const packageRow = packageJson.records[i];
        const packageRelations = Array.isArray(packageRow.relations) ? packageRow.relations.slice().sort().join(",") : "";
        if (!packageRow || sourceRow.concept !== (Array.isArray(packageRow.concepts) ? packageRow.concepts[0] : "") || sourceRow.text !== packageRow.text || sourceRow.relationSignature !== packageRelations) packageProjection.mismatches.push({ row: i + 1, id: sourceRow.id });
      }
    } catch (error) {
      packageProjection.parse_error = String(error.message || error);
    }
  }
  const valDir = path.join(ROOT, "stage2_highdensity_dataset", "sources", "val");
  const valA06 = fs.existsSync(valDir) ? fs.readdirSync(valDir).filter((x) => x.startsWith("stage2_(16)") && x.endsWith(".source.psv")) : [];

  const report = {
    audit_id: "S2-A06-SOURCE-AUDIT-2026-09-11",
    generated_at: new Date().toISOString(),
    scope: {
      stage: 2,
      area_code: "A06",
      area_slug: "relational_composition",
      split: "train source only",
      source_format: "PSV concept|relations|other_type|text",
      expected_versions: "v01~v52",
      expected_records: 7800,
      source_only_policy: true,
      package_and_checkpoint_write: false,
    },
    reservation: {
      reservation_count: reservations.size,
      family_count: Object.keys(familyCounts).length,
      duplicate_family_count: Object.values(familyCounts).filter((x) => x > 1).length,
      origins_by_version: files.map((x) => ({ version: x.version, origin: x.origin, family: x.concept_family })),
    },
    source_set: {
      files_found: files.length,
      rows_found: totalRows,
      expected_files: expectedNames.length,
      expected_rows: 7800,
      source_set_sha256: sourceSetSha,
      file_hash_count: files.length,
      missing_files: errors.missing_files,
      unexpected_files: errors.unexpected_files,
    },
    files,
    structural_errors: {
      utf8: errors.utf8,
      header: errors.header,
      columns: errors.columns,
      control_characters: errors.control_characters,
      empty_concept: errors.empty_concept,
      empty_text: errors.empty_text,
      concept_literal_missing: errors.concept_literal_missing,
      row_count: errors.row_count,
      reservation_mismatch: errors.reservation_mismatch,
      numeric_suffix: errors.numeric_suffix,
    },
    relation_audit: {
      controlled_vocabulary: CONTROLLED,
      counts: relationCounts,
      controlled_value_errors: errors.relation_controlled,
      cardinality_errors: errors.relation_cardinality,
      internal_duplicate_errors: errors.relation_internal_duplicate,
      per_record_min: 2,
      per_record_max: 5,
    },
    other_type_audit: {
      rule_errors: errors.other_type_rule,
      text_literal_mismatch_count: errors.other_type_text_mismatch.length,
      text_literal_mismatch_examples: errors.other_type_text_mismatch.slice(0, 20),
      mismatch_versions: [...new Set(errors.other_type_text_mismatch.map((x) => x.file))],
      top_types: topCounts(otherTypeCounts, 10).map((x) => ({ ...x, representative: otherTypeExamples[x.value] })),
    },
    duplicate_audit: {
      exact_concept_errors: errors.concept_duplicate,
      normalized_concept_errors: errors.concept_normalized_duplicate,
      exact_text_errors: errors.text_duplicate,
      normalized_text_errors: errors.text_normalized_duplicate,
    },
    diversity_audit: {
      repeated_5gram_distinct_count: Object.values(ngram5Counts).filter((x) => x > 1).length,
      repeated_5gram_total_occurrences: Object.entries(ngram5Counts).filter(([, count]) => count > 1).reduce((sum, [, count]) => sum + count, 0),
      repeated_5gram_top20: repeated5,
      repeated_4gram_opening_distinct_count: Object.values(opening4Counts).filter((x) => x > 1).length,
      repeated_4gram_opening_top20: repeatedOpening4,
      boilerplate_skeleton_distinct_count: Object.keys(skeletonCounts).length,
      boilerplate_skeleton_top20: repeatedSkeletons,
      malformed_pattern_counts: malformedPatternCounts,
      exact_duplicate_error_count: errors.text_duplicate.length,
      normalized_duplicate_error_count: errors.text_normalized_duplicate.length,
    },
    similarity_audit: {
      grouping: "same sorted relation-set only",
      relation_bucket_count: relationBuckets.size,
      relation_bucket_top10: [...relationBuckets.entries()].map(([signature, rows]) => ({ signature, records: rows.length })).sort((a, b) => b.records - a.records).slice(0, 10),
      word_jaccard: {
        potential_pairs: jaccardPotential,
        evaluated_pairs: jaccardEvaluated,
        complete: jaccardPotential === jaccardEvaluated,
        pair_cap_per_bucket: PAIR_CAP,
        max: maxJaccard.score < 0 ? null : { score: Number(maxJaccard.score.toFixed(6)), ...maxJaccard },
      },
      char_3_5gram_tfidf_cosine: {
        potential_pairs: tfidfPotential,
        evaluated_pairs: tfidfEvaluated,
        complete: tfidfPotential === tfidfEvaluated,
        pair_cap_per_bucket: PAIR_CAP,
        max: maxCosine.score < 0 ? null : { score: Number(maxCosine.score.toFixed(6)), ...maxCosine },
      },
    },
    primary_audit: {
      primary_literal_present_count: docs.length - errors.concept_literal_missing.length,
      primary_start_with_eun_neun_count: textStartsWithPrimaryParticle,
      primary_start_with_eun_neun_ratio: totalRows ? Number((textStartsWithPrimaryParticle / totalRows).toFixed(6)) : 0,
      start_particle_counts: startParticleCounts,
      particle_expected_checks: particleExpectedChecks,
      particle_mismatch_count: particleMismatchCount,
      particle_mismatch_examples: particleMismatchExamples,
      two_token_core_count: twoCore.length,
      two_token_core_ratio: totalRows ? Number((twoCore.length / totalRows).toFixed(6)) : 0,
      same_x1_group_stats: groupStats("x1"),
      same_x2_group_stats: groupStats("x2"),
    },
    size_audit: {
      total_text_characters: chars,
      total_word_units: wordCount,
      avg_text_characters_per_record: totalRows ? Number((chars / totalRows).toFixed(2)) : 0,
      avg_word_units_per_record: totalRows ? Number((wordCount / totalRows).toFixed(2)) : 0,
      tokenizer_measured: false,
      tokenizer_note: "[0-9A-Za-z가-힣]+ word-unit proxy only; no model tokenizer was run",
      per_file_min_avg_word_units: files.length ? Math.min(...files.map((x) => x.avg_word_units)) : 0,
      per_file_max_avg_word_units: files.length ? Math.max(...files.map((x) => x.avg_word_units)) : 0,
    },
    registry_audit: registry,
    package_projection_audit: packageProjection,
    split_leakage: {
      status: valA06.length ? "VAL_SOURCE_PRESENT_READ_ONLY_COMPARISON_REQUIRED" : "NOT_RUN_NO_A06_VAL_SOURCE",
      a06_val_source_files_found: valA06,
      exact_text: null,
      exact_primary: null,
      primary_relation_set: null,
      common_5gram: null,
    },
    generation_provenance: {
      v01: "legacy source preserved; existing package not rewritten",
      v02_v52: "bounded A06 draft generation followed by A06-only text/particle repair; no direct row-by-row human authorship evidence",
      semantic_review_status: "PENDING_MANUAL_SEMANTIC_REVIEW",
      direct_authoring_gate: "HOLD",
      note: "Structural audit is machine evidence. Guide §10 direct-authoring and meaning agreement still require human review before packaging.",
    },
    protected_scope: {
      common_audit_tool_modified: false,
      central_ledger_modified: false,
      manifest_modified: false,
      other_area_files_modified_by_this_audit: false,
      package_files_written: false,
    },
    error_summary: Object.fromEntries(Object.entries(errors).map(([key, value]) => [key, Array.isArray(value) ? value.length : 0])),
    verdict: {
      structural_gate: [
        errors.missing_files.length, errors.unexpected_files.length, errors.utf8.length, errors.header.length,
        errors.columns.length, errors.control_characters.length, errors.empty_concept.length, errors.empty_text.length,
        errors.concept_literal_missing.length, errors.row_count.length, errors.reservation_mismatch.length,
        errors.numeric_suffix.length, errors.relation_controlled.length, errors.relation_cardinality.length,
        errors.relation_internal_duplicate.length, errors.other_type_rule.length, errors.concept_duplicate.length,
        errors.concept_normalized_duplicate.length, errors.text_duplicate.length, errors.text_normalized_duplicate.length,
        registry.parse_errors.length, registry.mismatches.length, packageProjection.parse_error ? 1 : 0, packageProjection.mismatches.length,
      ].every((x) => x === 0) ? "PASS" : "FAIL",
      legacy_preservation_warning: errors.other_type_text_mismatch.length ? "WARN_V01_LEGACY_MISMATCHES_UNFIXED" : "NONE",
      semantic_naturalness_gate: "HOLD",
      packaging_gate: "NOT_RUN_SOURCE_ONLY",
    },
  };

  fs.mkdirSync(path.dirname(OUT_JSON), { recursive: true });
  fs.mkdirSync(path.dirname(OUT_MD), { recursive: true });
  fs.writeFileSync(OUT_JSON, JSON.stringify(report, null, 2) + "\n", "utf8");

  const e = report.error_summary;
  const lines = [];
  lines.push("# Stage2 A06 relational_composition source 감사 보고서 (2026-09-11)");
  lines.push("");
  lines.push("## 결론");
  lines.push("");
  lines.push(`- 범위: train source v01~v52, ${report.source_set.rows_found.toLocaleString()}건 / ${report.source_set.files_found}파일`);
  lines.push(`- 구조 gate: **${report.verdict.structural_gate}** (오류 요약은 아래 표와 JSON 정본 참조)`);
  lines.push(`- v01 보존 경고: **${report.verdict.legacy_preservation_warning}** (v01의 기존 other_type 문구 불일치 ${report.other_type_audit.text_literal_mismatch_count}건은 보존 규칙상 수정하지 않음)`);
  lines.push(`- 의미·자연성 gate: **${report.verdict.semantic_naturalness_gate}** — v02~v52는 기계 초안+범위 제한 교정이며 Guide §10 직접작성 증거가 없어 포장 전 사람의 의미 검토가 필요`);
  lines.push(`- 패키징: **${report.verdict.packaging_gate}** (A06 source-only 지시; 현재 package 존재 ${presentPackages.length}/52, 신규 package 미작성)`);
  lines.push(`- 기존 v01 source→package projection: ${packageProjection.checked ? `검사 ${packageProjection.record_count}건, 불일치 ${packageProjection.mismatches.length}건` : "검사 불가"}`);
  lines.push("");
  lines.push("## 파일·누적");
  lines.push("");
  lines.push("| version | records | ID 범위 | concept family | origin | source SHA-256 | 평균 문자 | 평균 word-unit |");
  lines.push("|---|---:|---|---|---|---|---:|---:|");
  for (const f of files) lines.push(`| ${f.version} | ${f.records} | ${f.id_range} | ${f.concept_family} | ${f.origin} | ${f.source_sha256} | ${f.avg_text_characters} | ${f.avg_word_units} |`);
  lines.push("");
  lines.push(`- source-set SHA-256: \`${sourceSetSha}\``);
  lines.push(`- 전체 text 문자: ${chars.toLocaleString()} / word-unit: ${wordCount.toLocaleString()} / 평균 word-unit: ${(wordCount / Math.max(totalRows, 1)).toFixed(2)}`);
  lines.push("");
  lines.push("## 오류·무결성 수치");
  lines.push("");
  lines.push("| 검사 | 건수 |");
  lines.push("|---|---:|");
  for (const [key, value] of Object.entries(e)) lines.push(`| ${key} | ${value} |`);
  lines.push("");
  lines.push("## Relations 분포 (13개 고정 어휘)");
  lines.push("");
  lines.push("| relation | count |");
  lines.push("|---|---:|");
  for (const relation of CONTROLLED) lines.push(`| ${relation} | ${relationCounts[relation]} |`);
  lines.push("");
  lines.push("## other 유형 상위");
  lines.push("");
  if (report.other_type_audit.top_types.length === 0) lines.push("- 해당 없음");
  else for (const item of report.other_type_audit.top_types.slice(0, 5)) lines.push(`- ${item.value}: ${item.count}건 (대표: ${item.representative ? item.representative.concept : "-"})`);
  lines.push("");
  lines.push("## 다양성·유사도");
  lines.push("");
  lines.push(`- 반복 5어절 distinct: ${report.diversity_audit.repeated_5gram_distinct_count}, 반복 occurrence: ${report.diversity_audit.repeated_5gram_total_occurrences}`);
  lines.push(`- 반복 4어절 도입부 distinct: ${report.diversity_audit.repeated_4gram_opening_distinct_count}`);
  lines.push(`- primary 치환 후 boilerplate skeleton distinct: ${report.diversity_audit.boilerplate_skeleton_distinct_count}`);
  lines.push(`- 동일 relation-set word Jaccard 최대: ${report.similarity_audit.word_jaccard.max ? report.similarity_audit.word_jaccard.max.score : "N/A"} (평가 ${report.similarity_audit.word_jaccard.evaluated_pairs}/${report.similarity_audit.word_jaccard.potential_pairs})`);
  lines.push(`- 동일 relation-set 문자 3~5-gram TF-IDF cosine 최대: ${report.similarity_audit.char_3_5gram_tfidf_cosine.max ? report.similarity_audit.char_3_5gram_tfidf_cosine.max.score : "N/A"} (평가 ${report.similarity_audit.char_3_5gram_tfidf_cosine.evaluated_pairs}/${report.similarity_audit.char_3_5gram_tfidf_cosine.potential_pairs})`);
  lines.push(`- 알려진 오염 후보: ${JSON.stringify(report.diversity_audit.malformed_pattern_counts)}`);
  lines.push("");
  lines.push("## Primary·조사·2단어 core");
  lines.push("");
  lines.push(`- primary literal 누락: ${errors.concept_literal_missing.length}건`);
  lines.push(`- text가 primary+은/는으로 시작: ${textStartsWithPrimaryParticle}/${totalRows} (${(textStartsWithPrimaryParticle / Math.max(totalRows, 1) * 100).toFixed(2)}%)`);
  lines.push(`- 직접 조사 후보 검사: ${particleExpectedChecks}건, 예상 불일치 ${particleMismatchCount}건`);
  lines.push(`- 2단어 core: ${twoCore.length}/${totalRows} (${(twoCore.length / Math.max(totalRows, 1) * 100).toFixed(2)}%)`);
  lines.push(`- 동일 X1·다른 X2: ${report.primary_audit.same_x1_group_stats.differing_other_token_group_count}개 그룹 / ${report.primary_audit.same_x1_group_stats.differing_other_token_record_count}건`);
  lines.push(`- 동일 X2·다른 X1: ${report.primary_audit.same_x2_group_stats.differing_other_token_group_count}개 그룹 / ${report.primary_audit.same_x2_group_stats.differing_other_token_record_count}건`);
  lines.push("");
  lines.push("## 범위·보호 파일");
  lines.push("");
  lines.push(`- A06 registry: ${registry.records}건, JSON parse 오류 ${registry.parse_errors.length}, source 대응 불일치 ${registry.mismatches.length}`);
  lines.push(`- A06 validation source: ${valA06.length ? valA06.join(", ") : "없음 — split leakage 비교는 NOT_RUN"}`);
  lines.push("- 중앙 원장·manifest·공용 감사기·다른 영역 파일: 이 감사에서 쓰기 금지 및 미수정");
  lines.push("");
  lines.push("정량 정본은 같은 디렉터리의 JSON 보고서입니다. 이 보고서는 source-only 진행물이며, 의미 검토와 사용자의 최종 승인 전에는 corpus 확정으로 해석하지 않습니다.");
  fs.writeFileSync(OUT_MD, lines.join("\n") + "\n", "utf8");
  console.log(JSON.stringify({ outJson: OUT_JSON, outMd: OUT_MD, files: files.length, rows: totalRows, structuralGate: report.verdict.structural_gate, legacyWarning: report.verdict.legacy_preservation_warning, jaccard: report.similarity_audit.word_jaccard.max, cosine: report.similarity_audit.char_3_5gram_tfidf_cosine.max }, null, 2));
}

main();
