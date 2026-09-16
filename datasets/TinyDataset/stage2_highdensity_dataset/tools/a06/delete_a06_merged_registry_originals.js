'use strict';

/*
 * Delete only registry originals that are explicitly listed in the completed
 * A06 consolidated manifests.  This is intentionally separate from the
 * consolidation tool: it refuses to delete an unlisted file, a file whose
 * bytes/SHA changed, or anything outside machine/a06.  Run without arguments
 * to create a READY_FOR_DELETE manifest; run with --delete-verified only after
 * reviewing that manifest.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = process.cwd();
const MACHINE = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06');
const OUT = path.join(MACHINE, 'consolidated');
const GENERATED_AT = '2026-09-16';
const DELETION_MANIFEST = 'A06_Merged_Registry_Originals_Deletion_Manifest_2026-09-16.json';
const MANIFEST_FILES = [
  'A06_registry_before_semantic_rewrite_v02_v15_Consolidated_2026-09-16_Part01.jsonl',
  'A06_registry_backups_all_Consolidated_2026-09-16_Part01.jsonl',
  'A06_registry_candidates_Consolidated_2026-09-16_Part01.jsonl',
  'A06_registry_primary_changes_all_Consolidated_2026-09-16_Part01.jsonl',
];
const CANONICAL_GUARDS = [
  path.join(ROOT, 'stage2_highdensity_dataset', 'sources', 'train', 'stage2_(16)relational_composition_high_density_train_v16.source.psv'),
  path.join(ROOT, 'stage2_highdensity_dataset', 'sources', 'term_registry', 'stage2_(16)relational_composition_train_registry_v01_v52.jsonl'),
  path.join(MACHINE, 'fixtures', 'stage2_(16)relational_composition_train_registry_v01_v52.jsonl'),
];

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex').toUpperCase();
}

function fileGuard(file) {
  const buffer = fs.readFileSync(file);
  return { bytes: buffer.length, sha256: sha256(buffer) };
}

function topLevelFiles() {
  return fs.readdirSync(MACHINE)
    .filter((name) => fs.statSync(path.join(MACHINE, name)).isFile())
    .sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
}

function isRegistryOriginal(name) {
  return /^A06_registry_before_v\d+_semantic_rewrite_.+\.jsonl$/i.test(name)
    || /^A06_v\d+_.+_registry_backup(?:_r\d+)?_2026-.+\.jsonl$/i.test(name)
    || /^A06_registry_candidate_v\d+_.+\.jsonl$/i.test(name)
    || /^A06_v\d+_.+_registry_primary_changes_2026-.+\.json$/i.test(name);
}

function category(name) {
  if (/^A06_registry_before/i.test(name)) return 'before_semantic_rewrite';
  if (/registry_backup/i.test(name)) return 'backup';
  if (/registry_candidate/i.test(name)) return 'candidate';
  return 'primary_changes';
}

function readManifest(name) {
  const file = path.join(OUT, name);
  if (!fs.existsSync(file)) throw new Error(`consolidated registry manifest missing: ${name}`);
  const buffer = fs.readFileSync(file);
  if (buffer.length >= 3 && buffer[0] === 0xEF && buffer[1] === 0xBB && buffer[2] === 0xBF) throw new Error(`manifest BOM: ${name}`);
  const first = buffer.toString('utf8').split('\n')[0];
  const manifest = JSON.parse(first);
  if (!Array.isArray(manifest.original_files)) throw new Error(`manifest has no original_files: ${name}`);
  return { name, bytes: buffer.length, sha256: sha256(buffer), manifest };
}

function loadTargets() {
  const manifests = MANIFEST_FILES.map(readManifest);
  const listed = new Map();
  for (const item of manifests) {
    for (const original of item.manifest.original_files) {
      if (listed.has(original.name)) throw new Error(`duplicate manifest target: ${original.name}`);
      listed.set(original.name, { ...original, source_manifest: item.name, source_category: item.manifest.category });
    }
  }
  const currentRegistry = topLevelFiles().filter(isRegistryOriginal);
  const unlisted = currentRegistry.filter((name) => !listed.has(name));
  const absent = currentRegistry.filter((name) => !fs.existsSync(path.join(MACHINE, name)));
  if (unlisted.length) throw new Error(`current registry originals not listed in manifests: ${unlisted.join(', ')}`);
  if (absent.length) throw new Error(`current registry originals unexpectedly absent: ${absent.join(', ')}`);
  const targets = currentRegistry.map((name) => ({ name, ...listed.get(name), category: category(name) }));
  const mismatches = [];
  for (const target of targets) {
    const current = fileGuard(path.join(MACHINE, target.name));
    if (current.bytes !== target.bytes || current.sha256 !== target.sha256) mismatches.push({ name: target.name, expected: { bytes: target.bytes, sha256: target.sha256 }, current });
  }
  if (mismatches.length) throw new Error(`registry original precondition mismatch: ${JSON.stringify(mismatches.slice(0, 3))}`);
  return { manifests, currentRegistry, targets };
}

function guardsSnapshot() {
  return CANONICAL_GUARDS.map((file) => {
    if (!fs.existsSync(file)) throw new Error(`guard file missing: ${file}`);
    return { path: path.relative(ROOT, file).replace(/\\/g, '/'), ...fileGuard(file) };
  });
}

function writeReadyManifest() {
  const loaded = loadTargets();
  const outputGuards = MANIFEST_FILES.map((name) => {
    const file = path.join(OUT, name);
    return { name, ...fileGuard(file) };
  });
  const result = {
    schema_version: 1,
    status: 'READY_FOR_DELETE',
    generated_at: GENERATED_AT,
    scope: 'stage2_highdensity_dataset/audit_reports/machine/a06 top-level registry originals only',
    manifest_inputs: outputGuards,
    target_count: loaded.targets.length,
    target_total_bytes: loaded.targets.reduce((sum, item) => sum + item.bytes, 0),
    target_counts: loaded.targets.reduce((counts, item) => { counts[item.category] = (counts[item.category] || 0) + 1; return counts; }, {}),
    targets: loaded.targets,
    canonical_guards_before: guardsSnapshot(),
    excluded: [
      'A06 consolidated outputs and deletion manifests',
      'machine/a06/fixtures/**',
      'stage2_highdensity_dataset/sources/** (canonical source and registry)',
      'human audit folder (registry originals there were deleted in the preceding verified operation)',
      'all files not listed in the four manifest inputs',
    ],
    guard: 'Delete only when current registry-original set equals targets and every target SHA/byte precondition and guard hash is unchanged. No recursive deletion.',
  };
  const file = path.join(OUT, DELETION_MANIFEST);
  if (fs.existsSync(file)) throw new Error(`refusing to overwrite deletion manifest: ${file}`);
  fs.writeFileSync(file, `${JSON.stringify(result, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
  return result;
}

function deleteVerified() {
  const file = path.join(OUT, DELETION_MANIFEST);
  if (!fs.existsSync(file)) throw new Error(`deletion manifest missing: ${file}`);
  const plan = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (plan.status !== 'READY_FOR_DELETE') throw new Error(`unexpected deletion manifest status: ${plan.status}`);
  const loaded = loadTargets();
  const plannedNames = plan.targets.map((item) => item.name).sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
  const currentNames = loaded.currentRegistry.slice().sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
  if (JSON.stringify(plannedNames) !== JSON.stringify(currentNames)) throw new Error('registry-original file set changed; deletion aborted');
  const beforeGuards = guardsSnapshot();
  if (JSON.stringify(beforeGuards) !== JSON.stringify(plan.canonical_guards_before)) throw new Error('canonical/source guard changed; deletion aborted');
  for (const target of loaded.targets) {
    if (path.basename(target.name) !== target.name) throw new Error(`unsafe target: ${target.name}`);
    fs.unlinkSync(path.join(MACHINE, target.name));
  }
  const remaining = topLevelFiles().filter(isRegistryOriginal);
  if (remaining.length) throw new Error(`registry originals remain after deletion: ${remaining.join(', ')}`);
  const afterGuards = guardsSnapshot();
  if (JSON.stringify(afterGuards) !== JSON.stringify(beforeGuards)) throw new Error('canonical/source guard changed during deletion');
  plan.status = 'DELETE_PASS';
  plan.deleted_at = new Date().toISOString();
  plan.deleted_count = loaded.targets.length;
  plan.remaining_registry_originals = remaining;
  plan.canonical_guards_after = afterGuards;
  fs.writeFileSync(file, `${JSON.stringify(plan, null, 2)}\n`, { encoding: 'utf8' });
  return { status: plan.status, deleted_count: plan.deleted_count, target_total_bytes: plan.target_total_bytes, remaining_registry_originals: remaining, deletion_manifest: DELETION_MANIFEST };
}

if (process.argv.includes('--delete-verified')) console.log(JSON.stringify(deleteVerified(), null, 2));
else console.log(JSON.stringify(writeReadyManifest(), null, 2));

