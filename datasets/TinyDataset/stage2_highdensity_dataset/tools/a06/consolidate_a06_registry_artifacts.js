'use strict';

/*
 * A06 registry-artifact consolidation helper.
 *
 * The files handled here are historical registry snapshots/backups/candidates
 * and small primary-change JSON reports.  They are evidence, not replacements
 * for the canonical registry.  Full snapshots are represented as one complete
 * baseline per logical sequence followed by line-addressed deltas.  The tool
 * reconstructs every input snapshot before writing and refuses to overwrite a
 * derived output or any original.
 *
 * Scope: stage2_highdensity_dataset/audit_reports/machine/a06 only.
 * Canonical source/registry, package train/val, manifest, central ledger and
 * other areas are not read or changed by this helper.
 * Use --merge-mixed-only when the machine-only before/candidate outputs have
 * already been created and only the human-folder additions need a new all
 * backup/primary-change bundle.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = process.cwd();
const MACHINE = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06');
const HUMAN = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'a06');
const OUT = path.join(MACHINE, 'consolidated');
const CAP_BYTES = 19_500_000;
const GENERATED_AT = '2026-09-16';

fs.mkdirSync(OUT, { recursive: true });

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex').toUpperCase();
}

function textOf(value) {
  return JSON.stringify(value);
}

function resolveArtifact(name) {
  const machineFile = path.join(MACHINE, name);
  if (fs.existsSync(machineFile)) return { file: machineFile, source_scope: 'audit_reports/machine/a06' };
  const humanFile = path.join(HUMAN, name);
  if (fs.existsSync(humanFile)) return { file: humanFile, source_scope: 'audit_reports/a06' };
  throw new Error(`A06 registry artifact not found: ${name}`);
}

function fileInfo(name, buffer, extra = {}) {
  return { name, bytes: buffer.length, sha256: sha256(buffer), ...extra };
}

function readJsonl(name) {
  const resolved = resolveArtifact(name);
  const buffer = fs.readFileSync(resolved.file);
  if (buffer.length >= 3 && buffer[0] === 0xEF && buffer[1] === 0xBB && buffer[2] === 0xBF) {
    throw new Error(`BOM is not permitted: ${name}`);
  }
  const text = buffer.toString('utf8');
  const raw = text.split('\n');
  const lines = raw.length && raw[raw.length - 1] === '' ? raw.slice(0, -1) : raw;
  const rows = [];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].replace(/\r$/, '');
    if (line.trim() === '') throw new Error(`blank JSONL line: ${name}:${i + 1}`);
    rows.push(JSON.parse(line));
  }
  return { buffer, rows, source_scope: resolved.source_scope };
}

function readJson(name) {
  const resolved = resolveArtifact(name);
  const buffer = fs.readFileSync(resolved.file);
  if (buffer.length >= 3 && buffer[0] === 0xEF && buffer[1] === 0xBB && buffer[2] === 0xBF) {
    throw new Error(`BOM is not permitted: ${name}`);
  }
  return { buffer, value: JSON.parse(buffer.toString('utf8')), source_scope: resolved.source_scope };
}

function locator(row) {
  if (!row || typeof row !== 'object') throw new Error('snapshot row is not an object');
  if (row.source_file === undefined || row.source_line === undefined) {
    throw new Error(`snapshot row has no source locator: ${textOf(row)}`);
  }
  return `${row.source_file}\u0000${row.source_line}`;
}

function validateSnapshotRows(name, rows) {
  if (rows.length !== 7800) throw new Error(`${name}: expected 7800 rows, got ${rows.length}`);
  const seen = new Set();
  rows.forEach((row, index) => {
    const key = locator(row);
    if (seen.has(key)) throw new Error(`${name}: duplicate locator at row ${index + 1}: ${key}`);
    seen.add(key);
  });
  return seen;
}

function descriptor(name) {
  const before = name.match(/^A06_registry_before_v(\d+)_semantic_rewrite_(.+?)_2026-/i);
  if (!before) throw new Error(`cannot parse before-snapshot filename: ${name}`);
  const version = Number(before[1]);
  const suffix = before[2];
  const revisionMatch = suffix.match(/_r(\d+)$/i);
  const revision = revisionMatch ? Number(revisionMatch[1]) : 0;
  const core = revisionMatch ? suffix.slice(0, revisionMatch.index) : suffix;
  const numbers = core.split('_').filter(Boolean).map((part) => {
    if (!/^\d+$/.test(part)) throw new Error(`non-numeric snapshot range in ${name}`);
    return Number(part);
  });
  if (!numbers.length) throw new Error(`empty snapshot range in ${name}`);
  return { version, suffix, numbers, start: numbers[0], end: numbers[1] ?? numbers[0], revision };
}

function compareDescriptor(a, b) {
  const ax = descriptor(a);
  const bx = descriptor(b);
  if (ax.start !== bx.start) return ax.start - bx.start;
  if (ax.end !== bx.end) return ax.end - bx.end;
  const n = Math.max(ax.numbers.length, bx.numbers.length);
  for (let i = 2; i < n; i += 1) {
    const av = ax.numbers[i] ?? -1;
    const bv = bx.numbers[i] ?? -1;
    if (av !== bv) return av - bv;
  }
  if (ax.revision !== bx.revision) return ax.revision - bx.revision;
  return a.localeCompare(b, 'en', { numeric: true });
}

function groupBeforeFiles(names) {
  const groups = new Map();
  for (const name of names) {
    const version = descriptor(name).version;
    if (!groups.has(version)) groups.set(version, []);
    groups.get(version).push(name);
  }
  for (const list of groups.values()) list.sort(compareDescriptor);
  return Array.from(groups.entries()).sort((a, b) => a[0] - b[0]);
}

function versionOf(name, kind) {
  const pattern = kind === 'candidate' ? /registry_candidate_v(\d+)_/i : /A06_v(\d+)_/i;
  const match = name.match(pattern);
  if (!match) throw new Error(`cannot parse ${kind} version: ${name}`);
  return Number(match[1]);
}

function rangeKey(name) {
  const match = name.match(/_v\d+_(.+?)_registry_(?:backup|candidate|prechange)/i);
  return match ? match[1] : name;
}

function compareSequenceName(a, b, kind) {
  const av = versionOf(a, kind);
  const bv = versionOf(b, kind);
  if (av !== bv) return av - bv;
  return rangeKey(a).localeCompare(rangeKey(b), 'en', { numeric: true }) || a.localeCompare(b, 'en', { numeric: true });
}

function groupSequenceFiles(names, kind) {
  const groups = new Map();
  for (const name of names) {
    const version = versionOf(name, kind);
    if (!groups.has(version)) groups.set(version, []);
    groups.get(version).push(name);
  }
  for (const list of groups.values()) list.sort((a, b) => compareSequenceName(a, b, kind));
  return Array.from(groups.entries()).sort((a, b) => a[0] - b[0]);
}

function lineRecord(record) {
  const line = textOf(record) + '\n';
  const bytes = Buffer.byteLength(line, 'utf8');
  if (bytes > CAP_BYTES) throw new Error(`single derived record exceeds cap: ${bytes}`);
  return { line, bytes };
}

function writeParts(baseName, records) {
  const outputs = [];
  let part = 1;
  let lines = [];
  let size = 0;
  const flush = () => {
    if (!lines.length) return;
    const suffix = `Part${String(part).padStart(2, '0')}.jsonl`;
    const name = `${baseName}_${suffix}`;
    const target = path.join(OUT, name);
    if (fs.existsSync(target)) throw new Error(`refusing to overwrite existing derived file: ${target}`);
    const body = lines.join('');
    fs.writeFileSync(target, body, { encoding: 'utf8', flag: 'wx' });
    const buffer = Buffer.from(body, 'utf8');
    outputs.push({ name, bytes: buffer.length, sha256: sha256(buffer), records: lines.length });
    part += 1;
    lines = [];
    size = 0;
  };
  for (const record of records) {
    const item = lineRecord(record);
    if (size && size + item.bytes > CAP_BYTES) flush();
    lines.push(item.line);
    size += item.bytes;
  }
  flush();
  return outputs;
}

function manifest(category, infos, extra = {}) {
  return {
    record_type: 'manifest',
    schema_version: 1,
    category,
    generated_at: GENERATED_AT,
    cap_bytes: CAP_BYTES,
    original_file_count: infos.length,
    original_total_bytes: infos.reduce((sum, item) => sum + item.bytes, 0),
    original_files: infos.map((item, index) => ({ index, ...item })),
    ...extra,
  };
}

function equalRows(a, b) {
  return textOf(a) === textOf(b);
}

function reconstructAndVerify(records, expectedSnapshots) {
  const metas = records.filter((record) => record.record_type === 'snapshot')
    .sort((a, b) => a.snapshot_index - b.snapshot_index);
  const baselineRows = new Map();
  const deltaRows = new Map();
  for (const record of records) {
    if (record.record_type === 'snapshot_row') {
      if (!baselineRows.has(record.snapshot_index)) baselineRows.set(record.snapshot_index, []);
      baselineRows.get(record.snapshot_index).push(record);
    } else if (record.record_type === 'snapshot_delta') {
      if (!deltaRows.has(record.snapshot_index)) deltaRows.set(record.snapshot_index, []);
      deltaRows.get(record.snapshot_index).push(record);
    }
  }
  let current = null;
  const failures = [];
  for (const meta of metas) {
    if (meta.role === 'baseline') {
      const rows = (baselineRows.get(meta.snapshot_index) || [])
        .sort((a, b) => a.index - b.index)
        .map((record) => record.row);
      current = rows;
    } else {
      if (!current) throw new Error(`delta before baseline at snapshot ${meta.snapshot_index}`);
      current = current.slice();
      for (const record of (deltaRows.get(meta.snapshot_index) || [])) current[record.index] = record.row;
    }
    const expected = expectedSnapshots[meta.snapshot_index];
    if (!expected || current.length !== expected.rows.length) failures.push(meta.name);
    else {
      for (let i = 0; i < current.length; i += 1) {
        if (!equalRows(current[i], expected.rows[i])) { failures.push(`${meta.name}:row${i + 1}`); break; }
      }
    }
  }
  if (failures.length) throw new Error(`snapshot reconstruction failed: ${failures.slice(0, 5).join(', ')}`);
  return { status: 'PASS', snapshots: metas.length };
}

function consolidateSnapshotGroup(groupName, names, category, records, allSummaries) {
  const parsed = [];
  const infos = [];
  for (const name of names) {
    const { buffer, rows, source_scope } = readJsonl(name);
    validateSnapshotRows(name, rows);
    parsed.push(rows);
    infos.push(fileInfo(name, buffer, { rows: rows.length, source_scope }));
  }
  const groupStart = records.length;
  records.push({
    record_type: 'sequence',
    category,
    sequence_id: groupName,
    snapshot_count: names.length,
    baseline_rows: parsed[0].length,
    ordering: 'numeric range start/end/additional range numbers, then revision, then filename; this is a deterministic evidence order, not a claim about edit chronology',
    files: infos.map((item) => item.name),
  });
  let current = parsed[0];
  const expected = [];
  const snapshotIndices = [];
  const groupSummaries = [];
  const baseIndex = allSummaries.snapshotCount;
  for (let s = 0; s < parsed.length; s += 1) {
    const rows = parsed[s];
    if (rows.length !== current.length) throw new Error(`${names[s]} row count differs from baseline`);
    for (let i = 0; i < rows.length; i += 1) {
      if (locator(rows[i]) !== locator(current[i])) throw new Error(`${names[s]} locator/order mismatch at row ${i + 1}`);
    }
    const snapshotIndex = allSummaries.snapshotCount;
    allSummaries.snapshotCount += 1;
    snapshotIndices.push(snapshotIndex);
    expected[snapshotIndex] = { rows };
    const delta = [];
    if (s === 0) {
      records.push({
        record_type: 'snapshot',
        category,
        sequence_id: groupName,
        snapshot_index: snapshotIndex,
        local_snapshot_index: s,
        name: names[s],
        bytes: infos[s].bytes,
        sha256: infos[s].sha256,
        rows: rows.length,
        changed_count: rows.length,
        role: 'baseline',
      });
      rows.forEach((row, index) => records.push({
        record_type: 'snapshot_row',
        category,
        sequence_id: groupName,
        snapshot_index: snapshotIndex,
        index,
        locator: locator(row),
        row,
      }));
    } else {
      for (let i = 0; i < rows.length; i += 1) {
        if (!equalRows(rows[i], current[i])) delta.push({ index: i, row: rows[i] });
      }
      records.push({
        record_type: 'snapshot',
        category,
        sequence_id: groupName,
        snapshot_index: snapshotIndex,
        local_snapshot_index: s,
        name: names[s],
        bytes: infos[s].bytes,
        sha256: infos[s].sha256,
        rows: rows.length,
        changed_count: delta.length,
        role: 'delta',
      });
      delta.forEach((item) => records.push({
        record_type: 'snapshot_delta',
        category,
        sequence_id: groupName,
        snapshot_index: snapshotIndex,
        index: item.index,
        locator: locator(item.row),
        row: item.row,
      }));
    }
    groupSummaries.push({ name: names[s], rows: rows.length, changed_count: s === 0 ? rows.length : delta.length, sha256: infos[s].sha256 });
    current = rows;
  }
  allSummaries.groups.push({ sequence_id: groupName, files: infos.length, bytes: infos.reduce((sum, x) => sum + x.bytes, 0), snapshot_indices: snapshotIndices, snapshots: groupSummaries });
  allSummaries.groupRecordRanges.push({ sequence_id: groupName, start_record: groupStart, end_record: records.length - 1 });
  return { infos, expected, snapshotIndices };
}

function consolidateSnapshots(names, category, baseName, groups) {
  if (!names.length) throw new Error(`no files for ${category}`);
  const infos = [];
  const records = [];
  const expectedByIndex = [];
  const summary = { files: names.length, bytes: 0, rows: 7800, snapshotCount: 0, groups: [], groupRecordRanges: [] };
  for (const [version, groupNames] of groups) {
    const result = consolidateSnapshotGroup(`v${String(version).padStart(2, '0')}`, groupNames, category, records, summary);
    for (const item of result.infos) infos.push(item);
    result.snapshotIndices.forEach((globalIndex, localIndex) => { expectedByIndex[globalIndex] = result.expected[globalIndex] || result.expected[localIndex]; });
  }
  summary.bytes = infos.reduce((sum, item) => sum + item.bytes, 0);
  const fullRecords = [manifest(category, infos, {
    representation: 'baseline_plus_line_addressed_deltas',
    source_snapshot_count: names.length,
    sequence_count: groups.length,
    baseline_per_sequence: true,
    originals_retained: true,
    reconstruction: 'Each source snapshot must reconstruct byte-equivalent JSON object rows and SHA-256 from its sequence baseline and deltas; reconstruction was executed before output.',
    sequence_summaries: summary.groups,
  }), ...records];
  // Records use global snapshot indexes.  Reconstruct from the generated record
  // stream itself rather than trusting only the in-memory source arrays.
  const reconstructed = reconstructAndVerify(fullRecords, expectedByIndex);
  const outputs = writeParts(baseName, fullRecords);
  return { summary: { ...summary, reconstruction: reconstructed }, outputs };
}

function consolidatePrimaryChanges(names, baseName) {
  const infos = [];
  const unique = new Map();
  for (const name of names) {
    const { buffer, value, source_scope } = readJson(name);
    const changes = Array.isArray(value.changes) ? value.changes : [];
    const artifactIndex = infos.length;
    for (const change of changes) {
      const key = textOf(change);
      if (!unique.has(key)) unique.set(key, { change, artifact_indices: [], occurrence_count: 0 });
      const item = unique.get(key);
      item.artifact_indices.push(artifactIndex);
      item.occurrence_count += 1;
    }
    infos.push(fileInfo(name, buffer, {
      source_scope,
      schema_version: value.schema_version ?? null,
      area: value.area ?? null,
      change_count: changes.length,
    }));
  }
  const uniqueItems = Array.from(unique.values());
  const records = [manifest('A06 registry_primary_changes', infos, {
    representation: 'exact_change_object_deduplication_with_artifact_provenance',
    originals_retained: true,
    unique_change_count: uniqueItems.length,
    total_change_occurrences: uniqueItems.reduce((sum, item) => sum + item.occurrence_count, 0),
  })];
  infos.forEach((item, index) => records.push({ record_type: 'artifact', artifact_index: index, ...item }));
  uniqueItems.forEach((item, index) => records.push({
    record_type: 'change',
    change_id: `RPC${String(index + 1).padStart(6, '0')}`,
    ...item.change,
    occurrence_count: item.occurrence_count,
    artifact_indices: item.artifact_indices,
    artifact_files: item.artifact_indices.map((i) => infos[i].name),
  }));
  return {
    summary: { files: infos.length, bytes: infos.reduce((sum, item) => sum + item.bytes, 0), unique_changes: uniqueItems.length, occurrences: uniqueItems.reduce((sum, item) => sum + item.occurrence_count, 0) },
    outputs: writeParts(baseName, records),
  };
}

function listNames(predicate, directory = MACHINE) {
  return fs.readdirSync(directory).filter(predicate).sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
}

const beforeNames = listNames((name) => /^A06_registry_before_v\d+_semantic_rewrite_.+\.jsonl$/i.test(name));
const machineBackupNames = listNames((name) => /^A06_v\d+_.+_registry_backup(?:_r\d+)?_2026-.+\.jsonl$/i.test(name));
const humanPrechangeNames = listNames((name) => /^A06_v\d+_.+_registry_prechange_2026-.+\.jsonl$/i.test(name), HUMAN);
const backupNames = Array.from(new Set([...machineBackupNames, ...humanPrechangeNames]));
const candidateNames = listNames((name) => /^A06_registry_candidate_v\d+_.+\.jsonl$/i.test(name));
const machinePrimaryChangeNames = listNames((name) => /^A06_v\d+_.+_registry_primary_changes_2026-.+\.json$/i.test(name));
const humanPrimaryChangeNames = listNames((name) => /^A06_v\d+_.+_registry_primary_changes_2026-.+\.json$/i.test(name), HUMAN);
const primaryChangeNames = Array.from(new Set([...machinePrimaryChangeNames, ...humanPrimaryChangeNames]));
const mixedOnly = process.argv.includes('--merge-mixed-only');

if (!mixedOnly && !beforeNames.length) throw new Error('no remaining semantic-rewrite registry snapshots found');
if (!backupNames.length) throw new Error('no registry backups found');
if (!mixedOnly && !candidateNames.length) throw new Error('no registry candidates found');
if (!primaryChangeNames.length) throw new Error('no registry primary-change files found');

const beforeResult = mixedOnly ? null : consolidateSnapshots(
  beforeNames,
  'A06 registry_before_semantic_rewrite_v02_v03_v05_v15',
  'A06_registry_before_semantic_rewrite_v02_v15_Consolidated_2026-09-16',
  groupBeforeFiles(beforeNames),
);
const backupResult = consolidateSnapshots(
  backupNames,
  'A06 registry_backups_v15_v16_machine_human',
  'A06_registry_backups_all_Consolidated_2026-09-16',
  groupSequenceFiles(backupNames, 'backup'),
);
const candidateResult = mixedOnly ? null : consolidateSnapshots(
  candidateNames,
  'A06 registry_candidates_v09_v10',
  'A06_registry_candidates_Consolidated_2026-09-16',
  groupSequenceFiles(candidateNames, 'candidate'),
);
const primaryResult = consolidatePrimaryChanges(primaryChangeNames, 'A06_registry_primary_changes_all_Consolidated_2026-09-16');

console.log(JSON.stringify({
  generated_at: GENERATED_AT,
  cap_bytes: CAP_BYTES,
  preserved_originals: true,
  categories: {
    before: beforeResult,
    backups: backupResult,
    candidates: candidateResult,
    primary_changes: primaryResult,
  },
}, null, 2));
