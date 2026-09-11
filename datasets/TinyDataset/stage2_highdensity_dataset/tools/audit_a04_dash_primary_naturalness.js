#!/usr/bin/env node
'use strict';

/*
 * Read-only A04 primary-dash naturalness review.
 *
 * A dash in a primary is not by itself a structural error.  This tool keeps
 * that distinction explicit: it counts and groups the labels, exposes known
 * fragment/opaque-text warnings, and makes no source edits or PASS/FAIL claim.
 */

const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const rulesPath = path.join(root, 'stage2_highdensity_dataset', 'tools', 'primary_naturalness_warning_rules_v1.json');
const filePattern = /^stage2_\(14\)state_transition_high_density_train_v\d+\.source\.jsonl$/;
const normalize = value => String(value || '').normalize('NFKC').replace(/\s+/gu, ' ').trim();
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');

function qualifierParts(primary) {
  const match = normalize(primary).match(/^(.*?)\s+[—–-]\s+(.+)$/u);
  return match ? { core: match[1], qualifier: match[2] } : null;
}

function loadRules() {
  const raw = fs.readFileSync(rulesPath);
  const parsed = JSON.parse(raw.toString('utf8'));
  for (const field of ['qualifier_exact_terms', 'qualifier_prefix_terms', 'text_opaque_phrases']) {
    if (!Array.isArray(parsed[field])) throw new Error(`warning-rule field ${field} must be an array`);
  }
  return { raw, parsed };
}

function classify(row, rules) {
  const primary = qualifierParts(row.primary);
  if (!primary) return null;
  const exact = rules.qualifier_exact_terms.find(rule => primary.qualifier === normalize(rule.term));
  const prefix = exact ? null : rules.qualifier_prefix_terms.find(rule =>
    primary.qualifier === normalize(rule.prefix) || primary.qualifier.startsWith(`${normalize(rule.prefix)} `)
  );
  const opaque = rules.text_opaque_phrases.filter(rule => normalize(row.text).includes(normalize(rule.phrase)));
  const tokenCount = primary.qualifier.match(/[0-9A-Za-z가-힣]+/gu)?.length || 0;
  let preliminary = 'DASH_DELIMITER_REVIEW';
  if (exact || prefix) preliminary = 'DIRECT_REWRITE_CANDIDATE';
  else if (opaque.length) preliminary = 'SEMANTIC_TEXT_REVIEW';
  return {
    ...row,
    core: primary.core,
    qualifier: primary.qualifier,
    qualifier_shape: tokenCount <= 1 ? 'single_token' : tokenCount === 2 ? 'two_tokens' : 'three_or_more_tokens',
    exact_warning: exact ? exact.term : null,
    prefix_warning: prefix ? prefix.prefix : null,
    opaque_text_warnings: opaque.map(rule => rule.phrase),
    preliminary
  };
}

function summarize(rows, rulesMeta) {
  const countBy = (values, selector, exampleSelector) => {
    const map = new Map();
    for (const value of values) {
      const key = selector(value);
      if (!map.has(key)) map.set(key, { value: key, records: 0, examples: [] });
      const bucket = map.get(key);
      bucket.records += 1;
      if (bucket.examples.length < 5) bucket.examples.push(exampleSelector(value));
    }
    return [...map.values()].sort((left, right) => right.records - left.records || left.value.localeCompare(right.value));
  };
  const byCore = new Map();
  for (const row of rows) {
    if (!byCore.has(row.core)) byCore.set(row.core, []);
    byCore.get(row.core).push(row);
  }
  const reusedCore = [...byCore.entries()].map(([core, members]) => ({
    core,
    records: members.length,
    distinct_qualifiers: new Set(members.map(member => member.qualifier)).size,
    qualifiers: [...new Set(members.map(member => member.qualifier))].sort().slice(0, 12),
    examples: members.slice(0, 5).map(member => ({ locator: member.locator, primary: member.primary, text: member.text }))
  })).filter(group => group.distinct_qualifiers > 1)
    .sort((left, right) => right.records - left.records || right.distinct_qualifiers - left.distinct_qualifiers || left.core.localeCompare(right.core));

  const firstToken = row => row.qualifier.split(' ')[0];
  const dashStyle = rulesMeta.parsed.dash_style_review || {};
  const copiedParticles = Array.isArray(dashStyle.copied_subject_particles)
    ? dashStyle.copied_subject_particles : ['은', '는', '이', '가', '에서', '으로'];
  const copiedIntoText = rows.filter(row => {
    const primary = normalize(row.primary);
    const text = normalize(row.text);
    if (!text.startsWith(primary)) return false;
    const rest = text.slice(primary.length);
    return copiedParticles.some(particle => rest.startsWith(particle));
  });
  return {
    audit: 'A04 primary dash naturalness review',
    mode: 'READ_ONLY_ADVISORY',
    warning_rules: { path: path.relative(root, rulesPath).split(path.sep).join('/'), sha256: sha256(rulesMeta.raw), schema_version: rulesMeta.parsed.schema_version },
    source_files: new Set(rows.map(row => row.file)).size,
    dash_primary_records: rows.length,
    preliminary_classification: countBy(rows, row => row.preliminary, row => ({ locator: row.locator, primary: row.primary, text: row.text })),
    qualifier_shape: countBy(rows, row => row.qualifier_shape, row => ({ locator: row.locator, primary: row.primary })),
    qualifier_first_token_top: countBy(rows, firstToken, row => ({ locator: row.locator, primary: row.primary, qualifier: row.qualifier })).slice(0, 40),
    dash_style_review: {
      core_reuse_min_records: Number.isInteger(dashStyle.core_reuse_min_records) ? dashStyle.core_reuse_min_records : 2,
      copied_subject_particles: copiedParticles,
      text_begins_exact_dash_primary_plus_particle_records: copiedIntoText.length,
      text_begins_exact_dash_primary_plus_particle_ratio: rows.length ? copiedIntoText.length / rows.length : 0,
      total_core_groups: byCore.size,
      repeated_core_groups: reusedCore.length,
      records_in_repeated_core_groups: reusedCore.reduce((total, group) => total + group.records, 0),
      unique_core_records: rows.length - reusedCore.reduce((total, group) => total + group.records, 0),
      interpretation: 'A dash label copied into a sentence and a highly reused core can indicate a generated title pattern. These are review signals, not structural errors or automatic rewrite instructions.'
    },
    repeated_core_groups: {
      group_count: reusedCore.length,
      records: reusedCore.reduce((total, group) => total + group.records, 0),
      top_groups: reusedCore.slice(0, 40)
    },
    direct_rewrite_candidates: rows.filter(row => row.preliminary === 'DIRECT_REWRITE_CANDIDATE').map(row => ({ locator: row.locator, primary: row.primary, qualifier: row.qualifier, exact_warning: row.exact_warning, prefix_warning: row.prefix_warning, text: row.text })),
    semantic_text_review_candidates: rows.filter(row => row.preliminary === 'SEMANTIC_TEXT_REVIEW').map(row => ({ locator: row.locator, primary: row.primary, qualifier: row.qualifier, opaque_text_warnings: row.opaque_text_warnings, text: row.text })),
    interpretation: 'DASH_DELIMITER_REVIEW means that a human-readable separator remains in a primary that is copied into text. It is a naturalness review target, not proof that the underlying concept is invalid. No source mutation is performed by this tool.'
  };
}

function loadRows() {
  const files = fs.readdirSync(sourceDir).filter(file => filePattern.test(file)).sort();
  const rows = [];
  for (const file of files) {
    const lines = fs.readFileSync(path.join(sourceDir, file), 'utf8').trimEnd().split(/\r?\n/);
    lines.forEach((line, index) => {
      const raw = JSON.parse(line);
      const row = classify({ file, line: index + 1, locator: `${file}:${index + 1}`, primary: raw.primary, text: raw.text, relations: raw.relations }, loadRows.rules);
      if (row) rows.push(row);
    });
  }
  return rows;
}

function selfTest() {
  const rules = {
    qualifier_exact_terms: [{ term: '또 상태' }],
    qualifier_prefix_terms: [{ prefix: '처리에서' }],
    text_opaque_phrases: [{ phrase: '변경순서를 정한다' }]
  };
  const exact = classify({ locator: 'fixture:1', primary: '설비 점검 — 또 상태', text: '설비 점검 — 또 상태를 확인한다.' }, rules);
  const opaque = classify({ locator: 'fixture:2', primary: '설비 점검 — 온도 확인', text: '설비 점검 — 온도 확인은 변경순서를 정한다.' }, rules);
  assert.equal(exact.preliminary, 'DIRECT_REWRITE_CANDIDATE');
  assert.equal(opaque.preliminary, 'SEMANTIC_TEXT_REVIEW');
  assert.deepEqual(qualifierParts('설비 점검 — 온도 확인'), { core: '설비 점검', qualifier: '온도 확인' });
  console.log(JSON.stringify({ self_test: 'PASS' }));
}

function main() {
  if (process.argv.includes('--self-test')) return selfTest();
  const outIndex = process.argv.indexOf('--out');
  const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
  if (outIndex >= 0 && (!outPath || outPath.startsWith('--'))) throw new Error('--out requires a path');
  const rulesMeta = loadRules();
  loadRows.rules = rulesMeta.parsed;
  const rendered = `${JSON.stringify(summarize(loadRows(), rulesMeta), null, 2)}\n`;
  if (outPath) fs.writeFileSync(path.resolve(outPath), rendered, 'utf8');
  else process.stdout.write(rendered);
}

try { main(); }
catch (error) { console.error(`ERROR: ${error.message}`); process.exitCode = 1; }
