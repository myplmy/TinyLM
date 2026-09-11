#!/usr/bin/env node
'use strict';

/*
 * Stage 2 primary naturalness reviewer-assist.
 *
 * This program is deliberately read-only with respect to dataset sources.
 * It never edits JSONL, never invokes an LLM/API, and never manufactures a
 * replacement sentence.  It produces an evidence packet for the ChatGPT
 * reviewer, accepts that reviewer's explicit decision sidecar, then separates
 * direct-rewrite targets from the small set that still needs user judgement.
 *
 * Default input: stage2_highdensity_dataset/sources/train/*.source.jsonl
 * Default output: stdout.  Pass --out to write an audit JSON deliberately.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert');

const CONTROLLED_RELATIONS = new Set([
  'is_a', 'subclass_of', 'part_of', 'classification', 'boundary', 'contrast',
  'comparison', 'function', 'role', 'process', 'state', 'attribute', 'other'
]);
const TERM_KINDS = new Set([
  'common_term', 'technical_term', 'constructed_scenario', 'internal_defined'
]);
const DECISIONS = new Set(['direct_rewrite', 'keep', 'user_review']);
const STAGE2_AREA_CATALOG = Object.freeze([
  { code: 'A01', sourceAreaSlot: '11', slug: 'causal_structure' },
  { code: 'A02', sourceAreaSlot: '12', slug: 'conditional_dependency' },
  { code: 'A03', sourceAreaSlot: '13', slug: 'temporal_order' },
  { code: 'A04', sourceAreaSlot: '14', slug: 'state_transition' },
  { code: 'A05', sourceAreaSlot: '15', slug: 'modality_possibility' },
  { code: 'A06', sourceAreaSlot: '16', slug: 'relational_composition' }
]);
const DEFAULT_WARNING_RULES = path.join(
  process.cwd(), 'stage2_highdensity_dataset', 'tools', 'primary_naturalness_warning_rules_v1.json'
);

function usage() {
  return `Usage:
  node stage2_highdensity_dataset/tools/audit_stage2_primary_reviewer_assist.js [options]

Options:
  --source-dir <dir>       JSONL directory (default: stage2_highdensity_dataset/sources/train)
  --match <regexp>         File-name regexp (default: ^stage2_.*\\.source\\.jsonl$)
  --area <A01..A06|11..16|slug>
                           Narrow to one Stage2 area; intersects with --match
  --registry <jsonl>       Optional source-side term registry
  --require-registry       Treat missing/invalid registry coverage as HARD
  --decisions <jsonl>      Optional ChatGPT decision sidecar
  --warning-rules <json>   Advisory naturalness warning rules
  --out <json>             Write report JSON; omit to print JSON to stdout
  --max-candidates <n>     Per relation-set similarity candidate cap (default: 50000)
  --topic-warn <0..1>      primary+은/는 ratio review threshold (default: 0.30)
  --topic-hold <0..1>      primary+은/는 ratio HOLD threshold (default: 0.45)
  --self-test              Run in-memory regression checks only; writes nothing
  --help                   Show this help

Registry JSONL fields (sidecar; never added to canonical source rows):
  source_file, source_line, primary, term_kind, definition,
  provenance_kind, provenance_ref, review_status

Decision JSONL fields:
  review_key, decision (direct_rewrite|keep|user_review), rationale,
  affected_locators (required for a group-level direct_rewrite decision)
`;
}

function fail(message) {
  throw new Error(message);
}

function parseAreaSelector(value) {
  const requested = String(value || '').trim();
  const compact = requested.toLowerCase().replace(/[\s_-]/gu, '');
  const area = STAGE2_AREA_CATALOG.find(candidate =>
    compact === candidate.code.toLowerCase() ||
    compact === candidate.sourceAreaSlot ||
    compact === candidate.slug.replace(/_/gu, '')
  );
  if (!area) {
    fail(`--area must be one of ${STAGE2_AREA_CATALOG.map(candidate => `${candidate.code}/${candidate.sourceAreaSlot}/${candidate.slug}`).join(', ')}, got ${value}`);
  }
  return { ...area, requested };
}

function matchesArea(file, area) {
  if (!area) return true;
  return file.startsWith(`stage2_(${area.sourceAreaSlot})${area.slug}_`);
}

function parseFraction(value, name) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 1) {
    fail(`${name} must be a number in [0, 1], got ${value}`);
  }
  return parsed;
}

function parsePositiveInt(value, name) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) fail(`${name} must be a positive integer, got ${value}`);
  return parsed;
}

function parseArgs(argv) {
  const options = {
    sourceDir: path.join(process.cwd(), 'stage2_highdensity_dataset', 'sources', 'train'),
    match: '^stage2_.*\\.source\\.jsonl$',
    area: null,
    registry: null,
    requireRegistry: false,
    decisions: null,
    warningRules: DEFAULT_WARNING_RULES,
    out: null,
    maxCandidates: 50000,
    topicWarn: 0.30,
    topicHold: 0.45,
    selfTest: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--help' || arg === '-h') {
      console.log(usage());
      process.exit(0);
    }
    if (arg === '--self-test') { options.selfTest = true; continue; }
    if (arg === '--require-registry') { options.requireRegistry = true; continue; }
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) fail(`Missing value for ${arg}`);
    if (arg === '--source-dir') options.sourceDir = path.resolve(next);
    else if (arg === '--match') options.match = next;
    else if (arg === '--area') options.area = parseAreaSelector(next);
    else if (arg === '--registry') options.registry = path.resolve(next);
    else if (arg === '--decisions') options.decisions = path.resolve(next);
    else if (arg === '--warning-rules') options.warningRules = path.resolve(next);
    else if (arg === '--out') options.out = path.resolve(next);
    else if (arg === '--max-candidates') options.maxCandidates = parsePositiveInt(next, '--max-candidates');
    else if (arg === '--topic-warn') options.topicWarn = parseFraction(next, '--topic-warn');
    else if (arg === '--topic-hold') options.topicHold = parseFraction(next, '--topic-hold');
    else fail(`Unknown option ${arg}`);
    index += 1;
  }
  if (options.topicWarn > options.topicHold) fail('--topic-warn cannot exceed --topic-hold');
  if (options.requireRegistry && !options.registry) fail('--require-registry requires --registry');
  return options;
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function normalize(value) {
  return String(value || '').normalize('NFKC').toLowerCase();
}

function normalizeWarning(value) {
  return String(value || '').normalize('NFKC').replace(/\s+/gu, ' ').trim();
}

function loadWarningRules(rulePath) {
  if (!fs.existsSync(rulePath)) fail(`Warning-rule file does not exist: ${rulePath}`);
  const raw = fs.readFileSync(rulePath);
  let parsed;
  try { parsed = JSON.parse(raw.toString('utf8')); }
  catch (error) { fail(`Warning-rule JSON is invalid: ${error.message}`); }
  const requiredArrays = ['qualifier_exact_terms', 'qualifier_prefix_terms', 'primary_contains_terms', 'text_opaque_phrases'];
  for (const key of requiredArrays) if (!Array.isArray(parsed[key])) fail(`Warning-rule field ${key} must be an array`);
  return {
    path: rulePath,
    sha256: sha256(raw),
    schemaVersion: parsed.schema_version,
    mode: parsed.mode,
    qualifierExact: parsed.qualifier_exact_terms,
    qualifierPrefixes: parsed.qualifier_prefix_terms,
    primaryContains: parsed.primary_contains_terms,
    textOpaquePhrases: parsed.text_opaque_phrases,
    dashStyleReview: parsed.dash_style_review || {}
  };
}

function qualifierAfterDash(primary) {
  const match = normalizeWarning(primary).match(/\s+[—–-]\s+(.+)$/u);
  return match ? match[1] : null;
}

function addAdvisoryWarnings(row, rules) {
  if (typeof row.primary !== 'string' || typeof row.text !== 'string') return;
  const qualifier = qualifierAfterDash(row.primary);
  if (qualifier) {
    addFlag(row, 'WARNING', 'primary_dash_qualifier', { qualifier });
    const exact = rules.qualifierExact.find(rule => qualifier === normalizeWarning(rule.term));
    if (exact) {
      addFlag(row, 'WARNING', 'primary_warning_expression_exact', {
        expression: exact.term, category: exact.category, reason: exact.reason
      });
    } else {
      const prefix = rules.qualifierPrefixes.find(rule => qualifier === normalizeWarning(rule.prefix) || qualifier.startsWith(`${normalizeWarning(rule.prefix)} `));
      if (prefix) {
        addFlag(row, 'WARNING', 'primary_warning_expression_prefix', {
          expression: prefix.prefix, category: prefix.category, reason: prefix.reason, qualifier
        });
      }
    }
  }
  const normalizedPrimary = normalizeWarning(row.primary);
  for (const rule of rules.primaryContains) {
    if (normalizedPrimary.includes(normalizeWarning(rule.term))) {
      addFlag(row, 'WARNING', 'primary_warning_constructed_term', {
        expression: rule.term, category: rule.category, reason: rule.reason
      });
    }
  }
  const normalizedText = normalizeWarning(row.text);
  for (const rule of rules.textOpaquePhrases) {
    if (normalizedText.includes(normalizeWarning(rule.phrase))) {
      addFlag(row, 'WARNING', 'text_warning_opaque_record_keeping', {
        expression: rule.phrase, category: rule.category, reason: rule.reason
      });
    }
  }
}

function advisoryWarningSummary(rows, rules) {
  const warningRows = rows.filter(row => row.flags.some(flag => flag.severity === 'WARNING'));
  const all = warningRows.flatMap(row => row.flags
    .filter(flag => flag.severity === 'WARNING')
    .map(flag => ({ row, flag })));
  const summarize = (items, selector) => [...items.reduce((map, item) => {
    const key = selector(item);
    if (!map.has(key)) map.set(key, { value: key, assignments: 0, records: new Set(), examples: [] });
    const bucket = map.get(key);
    bucket.assignments += 1;
    bucket.records.add(locator(item.row));
    if (bucket.examples.length < 5) bucket.examples.push({ locator: locator(item.row), primary: item.row.primary, text: excerpt(item.row.text || '') });
    return map;
  }, new Map()).values()].map(bucket => ({
    value: bucket.value, assignments: bucket.assignments, records: bucket.records.size, examples: bucket.examples
  })).sort((left, right) => right.records - left.records || left.value.localeCompare(right.value));
  const dashRows = rows.filter(row => row.flags.some(flag => flag.code === 'primary_dash_qualifier'));
  const copiedParticles = Array.isArray(rules.dashStyleReview.copied_subject_particles)
    ? rules.dashStyleReview.copied_subject_particles : ['은', '는', '이', '가', '에서', '으로'];
  const coreReuseThreshold = Number.isInteger(rules.dashStyleReview.core_reuse_min_records)
    ? rules.dashStyleReview.core_reuse_min_records : 2;
  const coreGroups = new Map();
  for (const row of dashRows) {
    const core = primaryCore(row.primary);
    if (!coreGroups.has(core)) coreGroups.set(core, []);
    coreGroups.get(core).push(row);
  }
  const reusedCore = [...coreGroups.entries()].map(([core, members]) => ({
    core,
    records: members.length,
    distinct_qualifiers: new Set(members.map(member => qualifierAfterDash(member.primary))).size,
    examples: members.slice(0, 3).map(member => ({ locator: locator(member), primary: member.primary, text: excerpt(member.text || '') }))
  })).filter(group => group.records >= coreReuseThreshold)
    .sort((left, right) => right.records - left.records || right.distinct_qualifiers - left.distinct_qualifiers || left.core.localeCompare(right.core));
  const copiedIntoText = dashRows.filter(row => {
    const primary = normalizeWarning(row.primary);
    const text = normalizeWarning(row.text);
    if (!text.startsWith(primary)) return false;
    const rest = text.slice(primary.length);
    return copiedParticles.some(particle => rest.startsWith(particle));
  });
  return {
    mode: 'ADVISORY_WARNING_ONLY',
    rules: { path: path.relative(process.cwd(), rules.path).split(path.sep).join('/'), sha256: rules.sha256, schema_version: rules.schemaVersion },
    warning_records: warningRows.length,
    warning_assignments: all.length,
    primary_dash_records: dashRows.length,
    primary_dash_ratio: ratio(dashRows.length, rows.length),
    dash_style_review: {
      core_reuse_min_records: coreReuseThreshold,
      copied_subject_particles: copiedParticles,
      text_begins_exact_dash_primary_plus_particle_records: copiedIntoText.length,
      text_begins_exact_dash_primary_plus_particle_ratio: ratio(copiedIntoText.length, rows.length),
      repeated_core_groups: reusedCore.length,
      records_in_repeated_core_groups: reusedCore.reduce((total, group) => total + group.records, 0),
      top_repeated_core_groups: reusedCore.slice(0, 20),
      interpretation: 'This is an advisory style signal. A dash label copied into a sentence and a highly reused core can indicate a generated title pattern, but neither value alone proves that the underlying concept is false.'
    },
    by_code: summarize(all, item => item.flag.code),
    by_expression: summarize(all.filter(item => item.flag.evidence.expression), item => item.flag.evidence.expression),
    examples: all.slice(0, 20).map(item => ({
      locator: locator(item.row), primary: item.row.primary, code: item.flag.code, evidence: item.flag.evidence, text: excerpt(item.row.text || '')
    })),
    note: 'Warnings are evidence and statistics only. They neither alter source nor make structural gates fail by themselves.'
  };
}

function words(value) {
  return normalize(value).match(/[0-9A-Za-z가-힣]+/g) || [];
}

function relKey(relations) {
  return [...new Set(relations)].sort().join('|');
}

function fileKey(value) {
  return path.basename(String(value || '').replace(/\\/g, '/'));
}

function locator(row) {
  return `${row.file}:${row.line}`;
}

function primaryCore(primary) {
  return String(primary || '').split(/\s+[—–-]\s+/u, 1)[0].trim();
}

function topicParticleStart(row) {
  if (!row.text.startsWith(row.primary)) return false;
  const rest = row.text.slice(row.primary.length);
  return rest.startsWith('은') || rest.startsWith('는');
}

function excerpt(text, limit = 220) {
  return text.length <= limit ? text : `${text.slice(0, limit - 1)}…`;
}

function addFlag(row, severity, code, evidence = {}) {
  row.flags.push({ severity, code, evidence });
}

function parseJsonl(file, label) {
  const buffer = fs.readFileSync(file);
  const raw = buffer.toString('utf8');
  if (raw.charCodeAt(0) === 0xFEFF) fail(`${label}: UTF-8 BOM is not allowed: ${file}`);
  const lines = raw.split(/\r?\n/);
  if (lines.length && lines[lines.length - 1] === '') lines.pop();
  const records = [];
  lines.forEach((line, index) => {
    if (!line.trim()) fail(`${label}: blank line at ${file}:${index + 1}`);
    try { records.push(JSON.parse(line)); }
    catch (error) { fail(`${label}: invalid JSON at ${file}:${index + 1}: ${error.message}`); }
  });
  return { raw: buffer, records };
}

function loadRows(options) {
  if (!fs.existsSync(options.sourceDir)) fail(`Source directory does not exist: ${options.sourceDir}`);
  let matcher;
  try { matcher = new RegExp(options.match, 'u'); }
  catch (error) { fail(`Invalid --match regexp: ${error.message}`); }
  const files = fs.readdirSync(options.sourceDir)
    .filter(file => matcher.test(file) && matchesArea(file, options.area))
    .sort((left, right) => left.localeCompare(right, 'en', { numeric: true }));
  if (!files.length) {
    const areaNote = options.area ? ` and --area ${options.area.code} (${options.area.slug})` : '';
    fail(`No source files matched ${options.match}${areaNote} in ${options.sourceDir}`);
  }

  const rows = [];
  const fileDigests = {};
  for (const file of files) {
    const fullPath = path.join(options.sourceDir, file);
    const parsed = parseJsonl(fullPath, 'source');
    fileDigests[file] = sha256(parsed.raw);
    parsed.records.forEach((raw, index) => {
      const row = {
        file,
        line: index + 1,
        globalLine: rows.length + 1,
        primary: raw.primary,
        text: raw.text,
        relations: raw.relations,
        flags: [],
        raw
      };
      if (typeof row.primary !== 'string' || !row.primary.trim()) addFlag(row, 'HARD', 'missing_primary');
      if (typeof row.text !== 'string' || !row.text.trim()) addFlag(row, 'HARD', 'missing_text');
      if (!Array.isArray(row.relations)) addFlag(row, 'HARD', 'missing_relations');
      if (typeof row.primary === 'string' && typeof row.text === 'string' && !row.text.includes(row.primary)) {
        addFlag(row, 'HARD', 'primary_literal_missing');
      }
      if (Array.isArray(row.relations)) {
        const invalid = row.relations.filter(value => !CONTROLLED_RELATIONS.has(value));
        if (invalid.length) addFlag(row, 'HARD', 'uncontrolled_relation', { invalid });
        if (new Set(row.relations).size !== row.relations.length) addFlag(row, 'HARD', 'duplicate_relation');
      }
      rows.push(row);
    });
  }
  return { rows, files, fileDigests };
}

function readRegistry(registryPath) {
  if (!registryPath) return { byLocator: new Map(), problems: [], fileDigest: null };
  if (!fs.existsSync(registryPath)) fail(`Registry file does not exist: ${registryPath}`);
  const parsed = parseJsonl(registryPath, 'registry');
  const byLocator = new Map();
  const problems = [];
  parsed.records.forEach((record, index) => {
    const sourceFile = fileKey(record.source_file);
    const line = Number(record.source_line);
    if (!sourceFile || !Number.isInteger(line) || line <= 0) {
      problems.push({ line: index + 1, code: 'registry_locator_invalid' });
      return;
    }
    const key = `${sourceFile}:${line}`;
    if (byLocator.has(key)) problems.push({ line: index + 1, code: 'registry_locator_duplicate', locator: key });
    byLocator.set(key, record);
  });
  return { byLocator, problems, fileDigest: sha256(parsed.raw) };
}

function readDecisions(decisionPath) {
  if (!decisionPath) return { byKey: new Map(), problems: [], fileDigest: null };
  if (!fs.existsSync(decisionPath)) fail(`Decision file does not exist: ${decisionPath}`);
  const parsed = parseJsonl(decisionPath, 'decision');
  const byKey = new Map();
  const problems = [];
  parsed.records.forEach((record, index) => {
    if (typeof record.review_key !== 'string' || !record.review_key) {
      problems.push({ line: index + 1, code: 'decision_review_key_missing' });
      return;
    }
    if (!DECISIONS.has(record.decision)) {
      problems.push({ line: index + 1, code: 'decision_value_invalid', review_key: record.review_key });
      return;
    }
    if (byKey.has(record.review_key)) problems.push({ line: index + 1, code: 'decision_key_duplicate', review_key: record.review_key });
    byKey.set(record.review_key, record);
  });
  return { byKey, problems, fileDigest: sha256(parsed.raw) };
}

function checkRegistry(row, registry, options) {
  if (!options.registry) return;
  const entry = registry.byLocator.get(locator(row));
  row.registry = entry || null;
  if (!entry) {
    addFlag(row, options.requireRegistry ? 'HARD' : 'AI_REVIEW', 'registry_missing');
    return;
  }
  if (entry.primary !== row.primary) addFlag(row, 'HARD', 'registry_primary_mismatch', { registry_primary: entry.primary });
  if (!TERM_KINDS.has(entry.term_kind)) addFlag(row, options.requireRegistry ? 'HARD' : 'AI_REVIEW', 'registry_term_kind_invalid');
  if (typeof entry.definition !== 'string' || !entry.definition.trim()) {
    addFlag(row, options.requireRegistry ? 'HARD' : 'AI_REVIEW', 'registry_definition_missing');
  }
  if ((entry.term_kind === 'technical_term' || entry.term_kind === 'common_term') &&
      (typeof entry.provenance_ref !== 'string' || !entry.provenance_ref.trim())) {
    addFlag(row, options.requireRegistry ? 'HARD' : 'AI_REVIEW', 'registry_provenance_missing');
  }
  if (entry.term_kind === 'internal_defined' &&
      (typeof entry.definition !== 'string' || !entry.definition.trim())) {
    addFlag(row, options.requireRegistry ? 'HARD' : 'AI_REVIEW', 'internal_definition_missing');
  }
}

function lexicalSignals(rows, registry, options, warningRules) {
  for (const row of rows) {
    checkRegistry(row, registry, options);
    if (typeof row.primary !== 'string') continue;
    row.core = primaryCore(row.primary);
    row.coreTokens = row.core ? row.core.split(/\s+/u).filter(Boolean) : [];
    row.twoWord = row.coreTokens.length === 2
      ? { x1: row.coreTokens[0], x2: row.coreTokens[1], core: row.core }
      : null;
    row.startsPrimaryEunneun = typeof row.text === 'string' && topicParticleStart(row);

    const numeric = row.primary.match(/(\d+)$/u);
    if (numeric) {
      const suffix = Number(numeric[1]);
      if (suffix === row.line || suffix === row.globalLine) {
        addFlag(row, 'HARD', 'numeric_suffix_matches_source_ordinal', {
          suffix, source_line: row.line, global_line: row.globalLine
        });
      } else {
        addFlag(row, 'INFO', 'trailing_numeric_primary', { suffix });
      }
    }
    if (!/\s/u.test(row.core) && Array.from(row.core).length >= 10) {
      addFlag(row, 'INFO', 'long_no_space_primary', { length: Array.from(row.core).length });
    }
    if (/(구성|전이|상황|판정)$/u.test(row.core)) {
      addFlag(row, 'INFO', 'constructed_suffix_candidate', { suffix: row.core.match(/(구성|전이|상황|판정)$/u)[1] });
    }
    addAdvisoryWarnings(row, warningRules);
  }
}

function ratio(count, denominator) {
  return denominator ? Number((count / denominator).toFixed(9)) : null;
}

function examples(rows, indexes, limit = 5) {
  return indexes.slice(0, limit).map(index => ({
    locator: locator(rows[index]), primary: rows[index].primary, text: excerpt(rows[index].text || '')
  }));
}

function compositeMetrics(rows) {
  const style = { no_space: 0, one_token: 0, two_token_core: 0, three_or_more_token_core: 0 };
  const twoIndexes = [];
  rows.forEach((row, index) => {
    const tokenCount = row.coreTokens ? row.coreTokens.length : 0;
    if (!tokenCount) return;
    if (!/\s/u.test(row.core)) style.no_space += 1;
    if (tokenCount === 1) style.one_token += 1;
    else if (tokenCount === 2) { style.two_token_core += 1; twoIndexes.push(index); }
    else style.three_or_more_token_core += 1;
  });

  const x1Groups = new Map();
  const x2Groups = new Map();
  for (const index of twoIndexes) {
    const { x1, x2 } = rows[index].twoWord;
    if (!x1Groups.has(x1)) x1Groups.set(x1, []);
    if (!x2Groups.has(x2)) x2Groups.set(x2, []);
    x1Groups.get(x1).push(index);
    x2Groups.get(x2).push(index);
  }
  function summarizeGroups(groups, variantOf) {
    const entries = [];
    let recordsInVariedGroups = 0;
    for (const [value, indexes] of groups) {
      const variants = new Set(indexes.map(index => variantOf(rows[index].twoWord)));
      if (variants.size > 1) recordsInVariedGroups += indexes.length;
      entries.push({
        value,
        records: indexes.length,
        distinct_variants: variants.size,
        variants: [...variants].sort().slice(0, 12),
        examples: examples(rows, indexes)
      });
    }
    entries.sort((left, right) => right.records - left.records || right.distinct_variants - left.distinct_variants || left.value.localeCompare(right.value));
    return { entries, recordsInVariedGroups };
  }
  const x1 = summarizeGroups(x1Groups, pair => pair.x2);
  const x2 = summarizeGroups(x2Groups, pair => pair.x1);
  const twoCount = twoIndexes.length;
  return {
    core_style_counts: style,
    two_word_core_records: twoCount,
    two_word_core_ratio_all_records: ratio(twoCount, rows.length),
    same_x1_different_x2: {
      group_count: x1.entries.filter(entry => entry.distinct_variants > 1).length,
      records: x1.recordsInVariedGroups,
      ratio_within_two_word_core: ratio(x1.recordsInVariedGroups, twoCount),
      ratio_all_records: ratio(x1.recordsInVariedGroups, rows.length),
      top_groups: x1.entries.filter(entry => entry.distinct_variants > 1).slice(0, 20)
    },
    same_x2_different_x1: {
      group_count: x2.entries.filter(entry => entry.distinct_variants > 1).length,
      records: x2.recordsInVariedGroups,
      ratio_within_two_word_core: ratio(x2.recordsInVariedGroups, twoCount),
      ratio_all_records: ratio(x2.recordsInVariedGroups, rows.length),
      top_groups: x2.entries.filter(entry => entry.distinct_variants > 1).slice(0, 20)
    }
  };
}

function topicParticleMetrics(rows, options) {
  const hits = rows.filter(row => row.startsPrimaryEunneun);
  const rate = ratio(hits.length, rows.length);
  function assess(value) {
    if (value > options.topicHold) return 'HOLD_REWRITE_DIVERSITY';
    if (value > options.topicWarn) return 'REVIEW_DIVERSITY';
    return 'WITHIN_PROVISIONAL_RANGE';
  }
  const assessment = assess(rate);
  const byFile = new Map();
  rows.forEach(row => {
    if (!byFile.has(row.file)) byFile.set(row.file, { records: 0, hits: 0 });
    const item = byFile.get(row.file);
    item.records += 1;
    if (row.startsPrimaryEunneun) item.hits += 1;
  });
  return {
    count: hits.length,
    records: rows.length,
    rate,
    provisional_thresholds: { review_above: options.topicWarn, hold_above: options.topicHold },
    assessment,
    note: 'The ratio is a diversity gate, not a Korean grammar error rate. A threshold crossing requires family-level review rather than blind rewrites.',
    by_file: [...byFile.entries()].map(([file, item]) => {
      const fileRate = ratio(item.hits, item.records);
      return { file, ...item, rate: fileRate, assessment: assess(fileRate) };
    }),
    examples: hits.slice(0, 20).map(row => ({ locator: locator(row), primary: row.primary, text: excerpt(row.text || '') }))
  };
}

function maskPrimary(row) {
  const primary = String(row.primary || '');
  if (!primary) return String(row.text || '');
  return String(row.text || '').split(primary).join('<PRIMARY>');
}

function hash32(value, seed) {
  let hash = (2166136261 ^ seed) >>> 0;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}

function minHashSignature(tokenSet, width = 64) {
  const tokens = [...tokenSet];
  const signature = new Uint32Array(width);
  for (let index = 0; index < width; index += 1) {
    const seed = (0x9e3779b9 + Math.imul(index + 1, 0x85ebca6b)) >>> 0;
    let minimum = 0xffffffff;
    for (const token of tokens) minimum = Math.min(minimum, hash32(token, seed));
    signature[index] = minimum;
  }
  return signature;
}

function characterCounts(text) {
  const value = normalize(text);
  const counts = new Map();
  for (let size = 3; size <= 5; size += 1) {
    for (let index = 0; index <= value.length - size; index += 1) {
      const feature = value.slice(index, index + size);
      counts.set(feature, (counts.get(feature) || 0) + 1);
    }
  }
  return counts;
}

function jaccard(left, right) {
  const [small, large] = left.size <= right.size ? [left, right] : [right, left];
  let intersection = 0;
  for (const value of small) if (large.has(value)) intersection += 1;
  return intersection / (left.size + right.size - intersection || 1);
}

function collectCandidates(docs, maxCandidates) {
  const pairMap = new Map();
  const oversized = [];
  let capped = false;
  function add(left, right, method) {
    if (left === right) return;
    const a = Math.min(left, right);
    const b = Math.max(left, right);
    const key = `${a}:${b}`;
    if (!pairMap.has(key)) {
      if (pairMap.size >= maxCandidates) { capped = true; return; }
      pairMap.set(key, { a, b, methods: new Set() });
    }
    pairMap.get(key).methods.add(method);
  }
  const possible = docs.length * (docs.length - 1) / 2;
  if (possible <= maxCandidates) {
    for (let left = 0; left < docs.length; left += 1) {
      for (let right = left + 1; right < docs.length; right += 1) add(left, right, 'exhaustive_small_group');
    }
    return { pairs: [...pairMap.values()], capped, oversized, mode: 'exhaustive_small_group' };
  }

  const bands = 16;
  const rowsPerBand = 4;
  const buckets = new Map();
  docs.forEach((doc, index) => {
    doc.signature = minHashSignature(doc.wordSet, bands * rowsPerBand);
    for (let band = 0; band < bands; band += 1) {
      const start = band * rowsPerBand;
      const key = `${band}:${doc.signature[start]}:${doc.signature[start + 1]}:${doc.signature[start + 2]}:${doc.signature[start + 3]}`;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(index);
    }
  });
  for (const [key, indexes] of buckets) {
    if (indexes.length > 120) {
      oversized.push({ method: 'minhash_lsh', bucket: key, records: indexes.length });
      continue;
    }
    for (let left = 0; left < indexes.length; left += 1) {
      for (let right = left + 1; right < indexes.length; right += 1) add(indexes[left], indexes[right], 'minhash_lsh');
    }
  }

  for (const [field, method] of [['rawText', 'raw_5word_shingle'], ['maskedText', 'masked_5word_shingle']]) {
    const shingleBuckets = new Map();
    docs.forEach((doc, index) => {
      const tokenList = words(doc[field]);
      const shingles = new Set();
      for (let offset = 0; offset <= tokenList.length - 5; offset += 1) shingles.add(tokenList.slice(offset, offset + 5).join(' '));
      for (const shingle of shingles) {
        if (!shingleBuckets.has(shingle)) shingleBuckets.set(shingle, []);
        shingleBuckets.get(shingle).push(index);
      }
    });
    for (const [shingle, indexes] of shingleBuckets) {
      if (indexes.length > 120) {
        oversized.push({ method, shingle, records: indexes.length });
        continue;
      }
      for (let left = 0; left < indexes.length; left += 1) {
        for (let right = left + 1; right < indexes.length; right += 1) add(indexes[left], indexes[right], method);
      }
    }
  }
  return { pairs: [...pairMap.values()], capped, oversized, mode: 'minhash_lsh_plus_masked_5word_shingles' };
}

function charCosine(left, right, idf, cache, textField) {
  function weights(index) {
    if (cache.has(index)) return cache.get(index);
    const counts = characterCounts(index[textField]);
    let norm = 0;
    for (const [feature, count] of counts) {
      const weight = count * (idf.get(feature) || 1);
      norm += weight * weight;
    }
    const result = { counts, norm: Math.sqrt(norm) || 1 };
    cache.set(index, result);
    return result;
  }
  const a = weights(left);
  const b = weights(right);
  const [small, large] = a.counts.size <= b.counts.size ? [a, b] : [b, a];
  let dot = 0;
  for (const [feature, count] of small.counts) {
    const other = large.counts.get(feature);
    if (!other) continue;
    const weight = idf.get(feature) || 1;
    dot += count * other * weight * weight;
  }
  return dot / (a.norm * b.norm);
}

function pushTop(list, value, limit = 20) {
  list.push(value);
  if (list.length > limit * 2) {
    list.sort((left, right) => right.score - left.score);
    list.length = limit;
  }
}

function relationSetSimilarity(rows, options) {
  const groups = new Map();
  rows.forEach((row, index) => {
    if (!Array.isArray(row.relations)) return;
    const key = relKey(row.relations);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(index);
  });
  const output = [];
  for (const [relationSet, indexes] of [...groups.entries()].sort((left, right) => left[0].localeCompare(right[0]))) {
    const docs = indexes.map(index => {
      const rawText = String(rows[index].text || '');
      const maskedText = maskPrimary(rows[index]);
      const rawWordSet = new Set(words(rawText));
      const maskedWordSet = new Set(words(maskedText));
      return {
        rowIndex: index,
        rawText,
        maskedText,
        rawWordSet,
        maskedWordSet,
        // Candidate generation uses both views. Exact reported scores remain separate.
        wordSet: new Set([...rawWordSet, ...maskedWordSet])
      };
    });
    const candidates = collectCandidates(docs, options.maxCandidates);
    const rawDf = new Map();
    const maskedDf = new Map();
    for (const doc of docs) {
      for (const feature of characterCounts(doc.rawText).keys()) rawDf.set(feature, (rawDf.get(feature) || 0) + 1);
      for (const feature of characterCounts(doc.maskedText).keys()) maskedDf.set(feature, (maskedDf.get(feature) || 0) + 1);
    }
    function buildIdf(df) {
      const idf = new Map();
      for (const [feature, count] of df) idf.set(feature, Math.log((1 + docs.length) / (1 + count)) + 1);
      return idf;
    }
    const rawIdf = buildIdf(rawDf);
    const maskedIdf = buildIdf(maskedDf);
    const rawCharCache = new Map();
    const maskedCharCache = new Map();
    const scores = {
      rawJaccard: { maximum: { score: 0, pair: null }, thresholdPairs: 0, top: [] },
      rawTfidf: { maximum: { score: 0, pair: null }, thresholdPairs: 0, top: [] },
      maskedJaccard: { maximum: { score: 0, pair: null }, thresholdPairs: 0, top: [] },
      maskedTfidf: { maximum: { score: 0, pair: null }, thresholdPairs: 0, top: [] }
    };
    for (const pair of candidates.pairs) {
      const left = docs[pair.a];
      const right = docs[pair.b];
      const rawJac = jaccard(left.rawWordSet, right.rawWordSet);
      const maskedJac = jaccard(left.maskedWordSet, right.maskedWordSet);
      const rawTfidf = charCosine(left, right, rawIdf, rawCharCache, 'rawText');
      const maskedTfidf = charCosine(left, right, maskedIdf, maskedCharCache, 'maskedText');
      const pairMeta = {
        methods: [...pair.methods].sort(),
        left: rows[left.rowIndex],
        right: rows[right.rowIndex]
      };
      for (const [key, score, threshold] of [
        ['rawJaccard', rawJac, 0.60], ['rawTfidf', rawTfidf, 0.72],
        ['maskedJaccard', maskedJac, 0.60], ['maskedTfidf', maskedTfidf, 0.72]
      ]) {
        if (score > scores[key].maximum.score) scores[key].maximum = { score, pair: pairMeta };
        if (score >= threshold) { scores[key].thresholdPairs += 1; pushTop(scores[key].top, { score, pair: pairMeta }); }
      }
    }
    function serialize(value) {
      if (!value || !value.pair) return null;
      const pair = value.pair;
      return {
        score: Number(value.score.toFixed(9)), methods: pair.methods,
        left: { locator: locator(pair.left), primary: pair.left.primary, text: excerpt(pair.left.text || '') },
        right: { locator: locator(pair.right), primary: pair.right.primary, text: excerpt(pair.right.text || '') }
      };
    }
    output.push({
      relation_set: relationSet,
      records: docs.length,
      possible_pairs: docs.length * (docs.length - 1) / 2,
      candidate_search: {
        mode: candidates.mode,
        candidate_pairs_examined: candidates.pairs.length,
        capped: candidates.capped,
        oversized_buckets: candidates.oversized.slice(0, 20),
        note: 'For large groups this is deterministic MinHash/5-word candidate generation followed by exact scores on candidates; it is not an exhaustive all-pairs proof.'
      },
      raw_text_word_set_jaccard: {
        threshold: 0.60, pairs_ge_threshold: scores.rawJaccard.thresholdPairs,
        maximum: serialize(scores.rawJaccard.maximum), top_pairs: scores.rawJaccard.top.sort((a, b) => b.score - a.score).slice(0, 20).map(serialize)
      },
      raw_text_char_3_5_tfidf_cosine: {
        threshold: 0.72, pairs_ge_threshold: scores.rawTfidf.thresholdPairs,
        maximum: serialize(scores.rawTfidf.maximum), top_pairs: scores.rawTfidf.top.sort((a, b) => b.score - a.score).slice(0, 20).map(serialize)
      },
      masked_primary_word_set_jaccard: {
        threshold: 0.60, pairs_ge_threshold: scores.maskedJaccard.thresholdPairs,
        maximum: serialize(scores.maskedJaccard.maximum), top_pairs: scores.maskedJaccard.top.sort((a, b) => b.score - a.score).slice(0, 20).map(serialize)
      },
      masked_primary_char_3_5_tfidf_cosine: {
        threshold: 0.72, pairs_ge_threshold: scores.maskedTfidf.thresholdPairs,
        maximum: serialize(scores.maskedTfidf.maximum), top_pairs: scores.maskedTfidf.top.sort((a, b) => b.score - a.score).slice(0, 20).map(serialize)
      }
    });
  }
  return output;
}

function groupReviewItems(rows, composite, topic, relationSimilarity) {
  const items = [];
  if (topic.assessment !== 'WITHIN_PROVISIONAL_RANGE') {
    items.push({
      review_key: 'group:primary_topic_particle_ratio', kind: 'group', severity: topic.assessment.startsWith('HOLD') ? 'HARD' : 'AI_REVIEW',
      code: 'primary_eunneun_opening_concentration', evidence: { rate: topic.rate, thresholds: topic.provisional_thresholds, examples: topic.examples.slice(0, 10) }
    });
  }
  for (const file of topic.by_file.filter(item => item.assessment !== 'WITHIN_PROVISIONAL_RANGE')) {
    items.push({
      review_key: `group:primary_topic_particle_ratio:${file.file}`,
      kind: 'group', severity: file.assessment.startsWith('HOLD') ? 'HARD' : 'AI_REVIEW',
      code: 'file_primary_eunneun_opening_concentration', evidence: { file, thresholds: topic.provisional_thresholds }
    });
  }
  const twoCount = composite.two_word_core_records;
  const concentrationFloor = Math.max(10, Math.ceil(twoCount * 0.05));
  for (const group of composite.same_x1_different_x2.top_groups) {
    if (group.records >= concentrationFloor && group.distinct_variants >= 3) {
      items.push({ review_key: `group:x1:${group.value}`, kind: 'group', severity: 'AI_REVIEW', code: 'same_x1_multiple_x2_concentration', evidence: group });
    }
  }
  for (const group of composite.same_x2_different_x1.top_groups) {
    if (group.records >= concentrationFloor && group.distinct_variants >= 3) {
      items.push({ review_key: `group:x2:${group.value}`, kind: 'group', severity: 'AI_REVIEW', code: 'same_x2_multiple_x1_concentration', evidence: group });
    }
  }
  for (const group of relationSimilarity) {
    const rawJaccard = group.raw_text_word_set_jaccard;
    const rawTfidf = group.raw_text_char_3_5_tfidf_cosine;
    const jaccard = group.masked_primary_word_set_jaccard;
    const tfidf = group.masked_primary_char_3_5_tfidf_cosine;
    if (rawJaccard.pairs_ge_threshold || rawTfidf.pairs_ge_threshold || jaccard.pairs_ge_threshold || tfidf.pairs_ge_threshold || group.candidate_search.capped || group.candidate_search.oversized_buckets.length) {
      items.push({
        review_key: `group:relation_set:${group.relation_set}`,
        kind: 'group', severity: 'AI_REVIEW', code: 'same_relation_set_similarity_review',
        evidence: {
          relation_set: group.relation_set, records: group.records,
          raw_jaccard_pairs_ge_threshold: rawJaccard.pairs_ge_threshold,
          raw_tfidf_pairs_ge_threshold: rawTfidf.pairs_ge_threshold,
          jaccard_pairs_ge_threshold: jaccard.pairs_ge_threshold,
          tfidf_pairs_ge_threshold: tfidf.pairs_ge_threshold,
          candidate_search: group.candidate_search,
          examples: [...rawJaccard.top_pairs.slice(0, 2), ...rawTfidf.top_pairs.slice(0, 2), ...jaccard.top_pairs.slice(0, 2), ...tfidf.top_pairs.slice(0, 2)]
        }
      });
    }
  }
  return items;
}

function rowReviewItems(rows) {
  const items = [];
  for (const row of rows) {
    const reviewFlags = row.flags.filter(flag => flag.severity === 'HARD' || flag.severity === 'AI_REVIEW');
    if (!reviewFlags.length) continue;
    items.push({
      review_key: `row:${locator(row)}`,
      kind: 'row', locator: locator(row), severity: reviewFlags.some(flag => flag.severity === 'HARD') ? 'HARD' : 'AI_REVIEW',
      primary: row.primary, text: excerpt(row.text || ''), relations: row.relations,
      registry: row.registry || null, flags: reviewFlags
    });
  }
  return items;
}

function mergeDecisions(rowItems, groupItems, decisions) {
  const all = [...rowItems, ...groupItems];
  const direct = [];
  const user = [];
  const pending = [];
  const stale = [];
  const seenDecisionKeys = new Set();
  for (const item of all) {
    const decision = decisions.byKey.get(item.review_key);
    // A row-level HARD finding is mechanical (for example a source-line numeric
    // suffix or a schema violation).  It cannot be waived by a semantic review.
    if (item.kind === 'row' && item.severity === 'HARD') {
      if (decision) seenDecisionKeys.add(item.review_key);
      direct.push({
        ...item,
        decision: 'direct_rewrite',
        rationale: decision && decision.rationale
          ? decision.rationale
          : 'Deterministic HARD source error; source remains untouched until direct editorial rewrite.'
      });
      continue;
    }
    if (!decision) {
      pending.push(item);
      continue;
    }
    seenDecisionKeys.add(item.review_key);
    if (decision.decision === 'direct_rewrite') {
      if (item.kind === 'group' && (!Array.isArray(decision.affected_locators) || !decision.affected_locators.length)) {
        stale.push({ review_key: item.review_key, code: 'group_direct_rewrite_requires_affected_locators' });
      } else direct.push({ ...item, decision: decision.decision, rationale: decision.rationale || '', affected_locators: decision.affected_locators || [] });
    } else if (decision.decision === 'user_review') {
      user.push({ ...item, decision: decision.decision, rationale: decision.rationale || '' });
    }
  }
  for (const key of decisions.byKey.keys()) if (!seenDecisionKeys.has(key)) stale.push({ review_key: key, code: 'decision_key_not_in_current_review_packet' });
  return { direct, user, pending, stale };
}

function analyze(rows, files, fileDigests, registry, decisions, options, warningRules) {
  lexicalSignals(rows, registry, options, warningRules);
  const topic = topicParticleMetrics(rows, options);
  const composite = compositeMetrics(rows);
  const similarity = relationSetSimilarity(rows, options);
  const rowItems = rowReviewItems(rows);
  const groupItems = groupReviewItems(rows, composite, topic, similarity);
  const actions = mergeDecisions(rowItems, groupItems, decisions);
  const hardRows = rows.filter(row => row.flags.some(flag => flag.severity === 'HARD'));
  const sourceDigestMaterial = files.map(file => `${file}\t${fileDigests[file]}`).join('\n');
  return {
    audit: 'Stage2 primary naturalness reviewer-assist',
    audit_version: 2,
    execution_mode: 'read_only_source_scan',
    source_selection: {
      source_dir: options.sourceDir,
      filename_match: options.match,
      area: options.area ? {
        requested: options.area.requested,
        code: options.area.code,
        source_area_slot: options.area.sourceAreaSlot,
        slug: options.area.slug,
        rule: 'filename match AND exact Stage2 area filename prefix'
      } : null
    },
    source_set_sha256: sha256(sourceDigestMaterial),
    source_files: files.length,
    source_records: rows.length,
    source_file_sha256: fileDigests,
    registry: {
      supplied: Boolean(options.registry), require_registry: options.requireRegistry,
      sha256: registry.fileDigest, parse_problems: registry.problems,
      records: registry.byLocator.size,
      coverage: options.registry ? ratio(rows.filter(row => row.registry).length, rows.length) : null
    },
    primary_eunneun_opening: topic,
    x1_x2_composite: composite,
    same_relation_set_masked_similarity: similarity,
    naturalness_warnings: advisoryWarningSummary(rows, warningRules),
    hard_source_errors: hardRows.length,
    direct_rewrite_targets: actions.direct,
    chatgpt_review_queue: actions.pending,
    user_review_queue: actions.user,
    review_queue_counts: {
      direct_rewrite_targets: actions.direct.length,
      chatgpt_review_pending: actions.pending.length,
      chatgpt_review_pending_hard: actions.pending.filter(item => item.severity === 'HARD').length,
      user_review_pending: actions.user.length
    },
    stale_or_invalid_decisions: [...decisions.problems, ...actions.stale],
    review_protocol: {
      rule: 'The script supplies evidence only. ChatGPT reviews chatgpt_review_queue first and records direct_rewrite, keep, or user_review in a decision sidecar. Only user_review items are escalated to the user.',
      direct_rewrite: 'A direct target is an editorial task, not an automatic source mutation. Apply only a record-specific human/ChatGPT-authored patch, then rerun every relevant gate.',
      limitations: 'Lexical patterns, X1/X2 clusters, and approximate large-group similarity are review signals. They do not by themselves prove that a Korean term is unnatural.'
    }
  };
}

function runSelfTest() {
  const a04 = parseArgs(['--area', 'A04']);
  assert.equal(a04.area.code, 'A04');
  assert.equal(a04.area.sourceAreaSlot, '14');
  assert.equal(parseArgs(['--area', 'state_transition']).area.code, 'A04');
  assert(matchesArea('stage2_(14)state_transition_high_density_train_v01.source.jsonl', a04.area));
  assert(!matchesArea('stage2_(15)modality_possibility_high_density_train_v01.source.jsonl', a04.area));
  const rows = [
    { file: 'stage2_(99)fixture_v01.source.jsonl', line: 1, globalLine: 1, primary: '점검 대기1', text: '점검 대기1은 장비 점검이 끝날 때까지 유지된다.', relations: ['state', 'process'], flags: [], raw: {} },
    { file: 'stage2_(99)fixture_v01.source.jsonl', line: 2, globalLine: 2, primary: '항만 대기', text: '항만 대기에서는 반입 순서와 안전 확인을 함께 기록한다.', relations: ['state', 'process'], flags: [], raw: {} },
    { file: 'stage2_(99)fixture_v01.source.jsonl', line: 3, globalLine: 3, primary: '공항 대기', text: '공항 대기에서는 출발 순서와 안전 확인을 함께 기록한다.', relations: ['state', 'process'], flags: [], raw: {} },
    { file: 'stage2_(99)fixture_v01.source.jsonl', line: 4, globalLine: 4, primary: '항만 통행', text: '항만 통행은 반입 순서와 안전 확인을 함께 기록한다.', relations: ['state', 'process'], flags: [], raw: {} }
  ];
  const options = { registry: null, requireRegistry: false, maxCandidates: 2000, topicWarn: 0.30, topicHold: 0.45 };
  const warningRules = loadWarningRules(DEFAULT_WARNING_RULES);
  rows[1].primary = '항만 대기 — 또 안정';
  rows[1].text = '항만 대기 — 또 안정에서는 반입 순서와 안전 확인을 함께 기록한다.';
  const result = analyze(rows, ['stage2_(99)fixture_v01.source.jsonl'], { 'stage2_(99)fixture_v01.source.jsonl': 'fixture' }, { byLocator: new Map(), problems: [], fileDigest: null }, { byKey: new Map(), problems: [], fileDigest: null }, options, warningRules);
  assert.equal(result.source_records, 4);
  assert.equal(result.primary_eunneun_opening.count, 2);
  assert.equal(result.x1_x2_composite.two_word_core_records, 4);
  assert.equal(result.naturalness_warnings.primary_dash_records, 1);
  assert(result.naturalness_warnings.by_expression.some(item => item.value === '또 안정'));
  assert(result.direct_rewrite_targets.some(item => item.locator === 'stage2_(99)fixture_v01.source.jsonl:1'));
  assert.equal(result.same_relation_set_masked_similarity.length, 1);
  const mergeTest = mergeDecisions(
    [{ review_key: 'row:fixture:1', kind: 'row', severity: 'HARD' }],
    [{ review_key: 'group:fixture', kind: 'group', severity: 'AI_REVIEW' }],
    { byKey: new Map([
      ['row:fixture:1', { decision: 'keep', rationale: 'must not waive mechanical HARD' }],
      ['group:fixture', { decision: 'direct_rewrite', rationale: 'group target without rows' }]
    ]), problems: [], fileDigest: null }
  );
  assert.equal(mergeTest.direct.length, 1);
  assert.equal(mergeTest.stale.length, 1);
  console.log(JSON.stringify({ self_test: 'PASS', source_records: result.source_records, direct_rewrite_targets: result.direct_rewrite_targets.length }, null, 2));
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.selfTest) return runSelfTest();
  const { rows, files, fileDigests } = loadRows(options);
  const registry = readRegistry(options.registry);
  const decisions = readDecisions(options.decisions);
  const warningRules = loadWarningRules(options.warningRules);
  const result = analyze(rows, files, fileDigests, registry, decisions, options, warningRules);
  const payload = `${JSON.stringify(result, null, 2)}\n`;
  if (options.out) {
    fs.mkdirSync(path.dirname(options.out), { recursive: true });
    fs.writeFileSync(options.out, payload, 'utf8');
    console.error(`Wrote reviewer-assist report: ${options.out}`);
  } else {
    process.stdout.write(payload);
  }
}

try { main(); }
catch (error) {
  console.error(`ERROR: ${error.message}`);
  process.exitCode = 1;
}
