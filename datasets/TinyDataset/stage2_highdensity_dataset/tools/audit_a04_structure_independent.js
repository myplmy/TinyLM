/* Independent read-only structure/integrity audit for Stage2 A04 source. */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const trainDir = path.join(root, 'stage2_highdensity_dataset', 'train');
const valDir = path.join(root, 'stage2_highdensity_dataset', 'val');
const pattern = /^stage2_\(14\)state_transition_high_density_train_v(\d+)\.source\.jsonl$/;
const files = fs.readdirSync(sourceDir).filter(file => pattern.test(file)).sort();
const controlled = new Set(['is_a', 'subclass_of', 'part_of', 'classification', 'boundary', 'contrast', 'comparison', 'function', 'role', 'process', 'state', 'attribute', 'other']);
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const normalized = value => value.normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim();
const wordTokens = value => value.normalize('NFKC').toLowerCase().match(/[0-9A-Za-z가-힣]+/g) || [];
const expectedKeys = ['primary', 'relations', 'text'];
const warningRulesPath = path.join(root, 'stage2_highdensity_dataset', 'tools', 'primary_naturalness_warning_rules_v1.json');
const warningRulesRaw = fs.readFileSync(warningRulesPath);
const warningRules = JSON.parse(warningRulesRaw.toString('utf8'));

const errors = {
  missing_or_extra_versions: 0,
  utf8_bom_or_replacement: 0,
  blank_lines: 0,
  json_parse: 0,
  source_schema: 0,
  rows_not_150: 0,
  empty_primary_or_text: 0,
  primary_literal: 0,
  uncontrolled_relations: 0,
  relation_cardinality: 0,
  relation_internal_duplicates: 0,
  unicode_control: 0,
  exact_primary_duplicates: 0,
  exact_text_duplicates: 0,
  normalized_text_duplicates: 0,
  adjacent_duplicate_words: 0,
  stage2_existing_corpus_primary_overlap: 0,
  stage2_existing_corpus_text_overlap: 0,
  reserved_validation_unseen_relation_set_collisions: 0
};
const examples = Object.fromEntries(Object.keys(errors).map(key => [key, []]));
const rows = [];
const warningNormalize = value => String(value || '').normalize('NFKC').replace(/\s+/gu, ' ').trim();
const qualifierAfterDash = primary => {
  const match = warningNormalize(primary).match(/\s+[—–-]\s+(.+)$/u);
  return match ? match[1] : null;
};
function collectNaturalnessWarnings(sourceRows) {
  const assignments = [];
  const add = (row, code, rule, extra = {}) => assignments.push({
    owner: row.owner, primary: row.primary, text: row.text, code,
    expression: rule.term || rule.prefix || rule.phrase || null,
    category: rule.category || null, reason: rule.reason || null, ...extra
  });
  for (const row of sourceRows) {
    const qualifier = qualifierAfterDash(row.primary);
    if (qualifier) {
      add(row, 'primary_dash_qualifier', {}, { qualifier });
      const exact = warningRules.qualifier_exact_terms.find(rule => qualifier === warningNormalize(rule.term));
      if (exact) add(row, 'primary_warning_expression_exact', exact);
      else {
        const prefix = warningRules.qualifier_prefix_terms.find(rule => qualifier === warningNormalize(rule.prefix) || qualifier.startsWith(`${warningNormalize(rule.prefix)} `));
        if (prefix) add(row, 'primary_warning_expression_prefix', prefix, { qualifier });
      }
    }
    const primary = warningNormalize(row.primary);
    const text = warningNormalize(row.text);
    for (const rule of warningRules.primary_contains_terms) if (primary.includes(warningNormalize(rule.term))) add(row, 'primary_warning_constructed_term', rule);
    for (const rule of warningRules.text_opaque_phrases) if (text.includes(warningNormalize(rule.phrase))) add(row, 'text_warning_opaque_record_keeping', rule);
  }
  const summarize = selector => {
    const buckets = new Map();
    for (const item of assignments) {
      const key = selector(item);
      if (!buckets.has(key)) buckets.set(key, { value: key, assignments: 0, owners: new Set(), examples: [] });
      const bucket = buckets.get(key);
      bucket.assignments += 1;
      bucket.owners.add(item.owner);
      if (bucket.examples.length < 5) bucket.examples.push({ owner: item.owner, primary: item.primary, text: item.text });
    }
    return [...buckets.values()].map(bucket => ({ value: bucket.value, assignments: bucket.assignments, records: bucket.owners.size, examples: bucket.examples }))
      .sort((left, right) => right.records - left.records || left.value.localeCompare(right.value));
  };
  const dashRows = sourceRows.filter(row => qualifierAfterDash(row.primary));
  const dashOwners = new Set(dashRows.map(row => row.owner));
  const dashStyle = warningRules.dash_style_review || {};
  const copiedParticles = Array.isArray(dashStyle.copied_subject_particles)
    ? dashStyle.copied_subject_particles : ['은', '는', '이', '가', '에서', '으로'];
  const coreReuseThreshold = Number.isInteger(dashStyle.core_reuse_min_records)
    ? dashStyle.core_reuse_min_records : 2;
  const coreGroups = new Map();
  for (const row of dashRows) {
    const core = warningNormalize(row.primary).split(/\s+[—–-]\s+/u, 1)[0];
    if (!coreGroups.has(core)) coreGroups.set(core, []);
    coreGroups.get(core).push(row);
  }
  const reusedCore = [...coreGroups.entries()].map(([core, members]) => ({
    core,
    records: members.length,
    distinct_qualifiers: new Set(members.map(member => qualifierAfterDash(member.primary))).size,
    examples: members.slice(0, 3).map(member => ({ owner: member.owner, primary: member.primary, text: member.text }))
  })).filter(group => group.records >= coreReuseThreshold)
    .sort((left, right) => right.records - left.records || right.distinct_qualifiers - left.distinct_qualifiers || left.core.localeCompare(right.core));
  const copiedIntoText = dashRows.filter(row => {
    const primary = warningNormalize(row.primary);
    const text = warningNormalize(row.text);
    if (!text.startsWith(primary)) return false;
    const rest = text.slice(primary.length);
    return copiedParticles.some(particle => rest.startsWith(particle));
  });
  return {
    mode: 'ADVISORY_WARNING_ONLY',
    rules_path: path.relative(root, warningRulesPath).split(path.sep).join('/'),
    rules_sha256: sha256(warningRulesRaw),
    warning_records: new Set(assignments.map(item => item.owner)).size,
    warning_assignments: assignments.length,
    primary_dash_records: dashOwners.size,
    primary_dash_ratio: sourceRows.length ? dashOwners.size / sourceRows.length : 0,
    dash_style_review: {
      core_reuse_min_records: coreReuseThreshold,
      copied_subject_particles: copiedParticles,
      text_begins_exact_dash_primary_plus_particle_records: copiedIntoText.length,
      text_begins_exact_dash_primary_plus_particle_ratio: sourceRows.length ? copiedIntoText.length / sourceRows.length : 0,
      repeated_core_groups: reusedCore.length,
      records_in_repeated_core_groups: reusedCore.reduce((total, group) => total + group.records, 0),
      top_repeated_core_groups: reusedCore.slice(0, 20),
      interpretation: 'This is an advisory style signal only; it does not make the structural verdict fail.'
    },
    by_code: summarize(item => item.code),
    by_expression: summarize(item => item.expression || item.code),
    examples: assignments.slice(0, 20).map(item => ({ owner: item.owner, primary: item.primary, code: item.code, expression: item.expression, category: item.category, text: item.text })),
    note: 'Warnings collect evidence only; they do not change source or alter this independent structure verdict.'
  };
}
const versions = files.map(file => Number(file.match(pattern)[1]));
const expectedVersions = Array.from({ length: 69 }, (_, index) => index + 1);
if (JSON.stringify(versions) !== JSON.stringify(expectedVersions)) {
  errors.missing_or_extra_versions++;
  examples.missing_or_extra_versions.push({ expected: expectedVersions, actual: versions });
}

for (const file of files) {
  const buffer = fs.readFileSync(path.join(sourceDir, file));
  const content = buffer.toString('utf8');
  if (buffer.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf])) || content.includes('\ufffd')) {
    errors.utf8_bom_or_replacement++;
    examples.utf8_bom_or_replacement.push(file);
  }
  const lines = content.split(/\r?\n/);
  if (lines.at(-1) === '') lines.pop();
  const blanks = lines.filter(line => line.trim() === '').length;
  errors.blank_lines += blanks;
  if (blanks && examples.blank_lines.length < 20) examples.blank_lines.push({ file, blanks });
  if (lines.length !== 150) {
    errors.rows_not_150++;
    examples.rows_not_150.push({ file, rows: lines.length });
  }
  lines.forEach((line, offset) => {
    const owner = `${file}:${offset + 1}`;
    let row;
    try { row = JSON.parse(line); }
    catch (error) {
      errors.json_parse++;
      if (examples.json_parse.length < 20) examples.json_parse.push({ owner, error: error.message });
      return;
    }
    const keys = Object.keys(row).sort();
    if (JSON.stringify(keys) !== JSON.stringify(expectedKeys) || typeof row.primary !== 'string' || typeof row.text !== 'string' || !Array.isArray(row.relations)) {
      errors.source_schema++;
      if (examples.source_schema.length < 20) examples.source_schema.push({ owner, keys });
    }
    if (!row.primary || !row.text) {
      errors.empty_primary_or_text++;
      if (examples.empty_primary_or_text.length < 20) examples.empty_primary_or_text.push(owner);
    }
    if (!row.text.includes(row.primary)) {
      errors.primary_literal++;
      if (examples.primary_literal.length < 20) examples.primary_literal.push(owner);
    }
    const outside = row.relations.filter(value => !controlled.has(value));
    errors.uncontrolled_relations += outside.length;
    if (outside.length && examples.uncontrolled_relations.length < 20) examples.uncontrolled_relations.push({ owner, outside });
    if (row.relations.length < 2 || row.relations.length > 5) {
      errors.relation_cardinality++;
      if (examples.relation_cardinality.length < 20) examples.relation_cardinality.push({ owner, count: row.relations.length });
    }
    if (new Set(row.relations).size !== row.relations.length) {
      errors.relation_internal_duplicates++;
      if (examples.relation_internal_duplicates.length < 20) examples.relation_internal_duplicates.push(owner);
    }
    for (const character of row.text) {
      const point = character.codePointAt(0);
      if ((point < 0x20 && character !== '\t' && character !== '\n' && character !== '\r') || point === 0x7f) {
        errors.unicode_control++;
        if (examples.unicode_control.length < 20) examples.unicode_control.push({ owner, codepoint: `U+${point.toString(16).toUpperCase().padStart(4, '0')}` });
      }
    }
    const tokens = wordTokens(row.text);
    for (let index = 1; index < tokens.length; index++) {
      if (tokens[index] === tokens[index - 1]) {
        errors.adjacent_duplicate_words++;
        if (examples.adjacent_duplicate_words.length < 20) examples.adjacent_duplicate_words.push({ owner, token: tokens[index] });
      }
    }
    rows.push({ owner, ...row });
  });
}

function duplicateSummary(values, errorName) {
  const counts = new Map();
  for (const [owner, value] of values) {
    if (!counts.has(value)) counts.set(value, []);
    counts.get(value).push(owner);
  }
  const duplicates = [...counts].filter(([, owners]) => owners.length > 1);
  errors[errorName] = duplicates.length;
  examples[errorName] = duplicates.slice(0, 20).map(([value, owners]) => ({ value, owners }));
}
duplicateSummary(rows.map(row => [row.owner, row.primary]), 'exact_primary_duplicates');
duplicateSummary(rows.map(row => [row.owner, row.text]), 'exact_text_duplicates');
duplicateSummary(rows.map(row => [row.owner, normalized(row.text)]), 'normalized_text_duplicates');

const existingPrimary = new Set();
const existingText = new Set();
for (const file of fs.readdirSync(trainDir).filter(file => file.endsWith('.json') && !file.startsWith('stage2_(14)'))) {
  let data;
  try { data = JSON.parse(fs.readFileSync(path.join(trainDir, file), 'utf8')); } catch { continue; }
  for (const record of data.records || []) {
    for (const concept of record.concepts || []) existingPrimary.add(concept);
    if (typeof record.text === 'string') existingText.add(record.text);
  }
}
for (const row of rows) {
  if (existingPrimary.has(row.primary)) {
    errors.stage2_existing_corpus_primary_overlap++;
    if (examples.stage2_existing_corpus_primary_overlap.length < 20) examples.stage2_existing_corpus_primary_overlap.push(row.owner);
  }
  if (existingText.has(row.text)) {
    errors.stage2_existing_corpus_text_overlap++;
    if (examples.stage2_existing_corpus_text_overlap.length < 20) examples.stage2_existing_corpus_text_overlap.push(row.owner);
  }
}

const unseenSets = new Set();
if (fs.existsSync(valDir)) {
  for (const file of fs.readdirSync(valDir).filter(file => file.endsWith('.json'))) {
    let data;
    try { data = JSON.parse(fs.readFileSync(path.join(valDir, file), 'utf8')); } catch { continue; }
    for (const record of data.records || []) {
      if (record.unseen_relation === true && Array.isArray(record.relations)) unseenSets.add([...record.relations].sort().join('\0'));
    }
  }
}
const trainSets = new Set(rows.map(row => [...row.relations].sort().join('\0')));
const collisions = [...trainSets].filter(value => unseenSets.has(value));
errors.reserved_validation_unseen_relation_set_collisions = collisions.length;
examples.reserved_validation_unseen_relation_set_collisions = collisions.slice(0, 20).map(value => value.split('\0'));

const nonTextProjection = rows.map(row => JSON.stringify({ primary: row.primary, relations: row.relations })).join('\n') + '\n';
const sourceSet = sha256(files.map(file => sha256(fs.readFileSync(path.join(sourceDir, file)))).join(''));
const naturalnessWarnings = collectNaturalnessWarnings(rows);
const report = {
  audit: 'A04 independent structure and integrity review',
  source_files: files.length,
  source_records: rows.length,
  source_set_sha256: sourceSet,
  non_text_projection_sha256: sha256(nonTextProjection),
  errors,
  examples,
  naturalness_warnings: naturalnessWarnings,
  verdict: Object.values(errors).every(value => value === 0) ? 'PASS' : 'FAIL'
};
const serialized = JSON.stringify(report, null, 2) + '\n';
const outIndex = process.argv.indexOf('--out');
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
if (outIndex >= 0 && (!outPath || outPath.startsWith('--'))) throw new Error('--out requires a path');
if (outPath) {
  fs.writeFileSync(path.resolve(outPath), serialized, 'utf8');
} else if (process.argv.includes('--write-report')) {
  const reportPath = path.join(
    root,
    'stage2_highdensity_dataset',
    'audit_reports',
    'machine',
    'TinyLM_Stage2_A04_Independent_Structure_Review_2026-09-10.json'
  );
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, serialized, 'utf8');
}
if (!outPath) process.stdout.write(serialized);
