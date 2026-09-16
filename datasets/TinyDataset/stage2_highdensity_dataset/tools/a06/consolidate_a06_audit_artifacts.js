'use strict';

/*
 * A06 audit-artifact consolidation helper.
 *
 * This tool only reads the existing A06 audit artifacts and writes derived,
 * line-delimited JSONL indexes under audit_reports/machine/a06/consolidated.
 * Canonical source, registry, package, manifest, ledger, and original audit
 * files are never replaced or removed.  Parts are deliberately capped below
 * the 20 MB requirement so that a line-boundary shard cannot cross the cap.
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

function bytesOfFile(file) {
  return fs.readFileSync(file);
}

function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex').toUpperCase();
}

function jsonText(value) {
  return JSON.stringify(value);
}

function readJson(file) {
  const buf = bytesOfFile(file);
  return { buf, value: JSON.parse(buf.toString('utf8')) };
}

function readJsonl(file) {
  const buf = bytesOfFile(file);
  const text = buf.toString('utf8');
  const raw = text.split('\n');
  const lines = raw.length && raw[raw.length - 1] === '' ? raw.slice(0, -1) : raw;
  const rows = [];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].replace(/\r$/, '');
    if (line.trim() === '') throw new Error(`blank JSONL line: ${file}:${i + 1}`);
    rows.push(JSON.parse(line));
  }
  return { buf, rows };
}

function fileNames(dir, predicate) {
  return fs.readdirSync(dir)
    .filter(predicate)
    .sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
}

function numericRange(file) {
  const m = file.match(/_([0-9]+)(?:_([0-9]+))?(?:_r([0-9]+))?_2026/);
  return {
    start: m ? Number(m[1]) : Number.MAX_SAFE_INTEGER,
    end: m && m[2] ? Number(m[2]) : (m ? Number(m[1]) : Number.MAX_SAFE_INTEGER),
    revision: m && m[3] ? Number(m[3]) : 0,
  };
}

function rangeSort(a, b) {
  const x = numericRange(a);
  const y = numericRange(b);
  return x.start - y.start || x.end - y.end || x.revision - y.revision || a.localeCompare(b, 'en', { numeric: true });
}

function lineRecord(record) {
  const line = jsonText(record) + '\n';
  const bytes = Buffer.byteLength(line, 'utf8');
  if (bytes > CAP_BYTES) throw new Error(`single output record exceeds cap: ${bytes} bytes`);
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
    const text = lines.join('');
    fs.writeFileSync(target, text, { encoding: 'utf8', flag: 'wx' });
    outputs.push({ name, bytes: Buffer.byteLength(text, 'utf8'), sha256: sha256(Buffer.from(text, 'utf8')), records: lines.length });
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

function manifest(category, files, extra) {
  const total = files.reduce((sum, f) => sum + f.bytes, 0);
  return {
    record_type: 'manifest',
    schema_version: 1,
    category,
    generated_at: GENERATED_AT,
    cap_bytes: CAP_BYTES,
    original_file_count: files.length,
    original_total_bytes: total,
    original_files: files.map((f, index) => ({ index, name: f.name, bytes: f.bytes, sha256: f.sha256 })),
    ...extra,
  };
}

function artifactInfo(name, buf) {
  return { name, bytes: buf.length, sha256: sha256(buf) };
}

function consolidateChangeFiles(files, category, baseName) {
  const infos = [];
  const unique = new Map();
  for (const name of files) {
    const file = path.join(MACHINE, name);
    const { buf, value } = readJson(file);
    const index = infos.length;
    const changes = Array.isArray(value.changes) ? value.changes : [];
    const keys = [];
    for (const change of changes) {
      const key = jsonText(change);
      let item = unique.get(key);
      if (!item) {
        item = { change, artifact_indices: [], occurrence_count: 0 };
        unique.set(key, item);
      }
      item.artifact_indices.push(index);
      item.occurrence_count += 1;
      keys.push(key);
    }
    infos.push({ ...artifactInfo(name, buf), schema_version: value.schema_version ?? null, area: value.area ?? null, change_count: changes.length, change_keys: keys });
  }

  const uniqueItems = Array.from(unique.values());
  const keyToId = new Map();
  uniqueItems.forEach((item, index) => keyToId.set(jsonText(item.change), `C${String(index + 1).padStart(6, '0')}`));
  const records = [manifest(category, infos, {
    deduplication: 'Exact change objects are keyed by source_file, source_line, old_primary, and new_primary; originals remain untouched.',
    unique_change_count: uniqueItems.length,
    total_change_occurrences: uniqueItems.reduce((sum, x) => sum + x.occurrence_count, 0),
  })];
  infos.forEach((item, index) => records.push({
    record_type: 'artifact',
    artifact_index: index,
    name: item.name,
    bytes: item.bytes,
    sha256: item.sha256,
    schema_version: item.schema_version,
    area: item.area,
    change_count: item.change_count,
    unique_change_ids: item.change_keys.map((key) => keyToId.get(key)),
  }));
  uniqueItems.forEach((item, index) => records.push({
    record_type: 'change',
    change_id: `C${String(index + 1).padStart(6, '0')}`,
    ...item.change,
    occurrence_count: item.occurrence_count,
    artifact_indices: item.artifact_indices,
    artifact_files: item.artifact_indices.map((i) => infos[i].name),
  }));
  return { records, outputs: writeParts(baseName, records), summary: { files: infos.length, bytes: infos.reduce((s, x) => s + x.bytes, 0), unique: uniqueItems.length, occurrences: uniqueItems.reduce((s, x) => s + x.occurrence_count, 0) } };
}

function dedupeMarkdown(text) {
  const normalized = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const hadFinalNewline = normalized.endsWith('\n');
  const lines = normalized.split('\n');
  if (hadFinalNewline) lines.pop();
  const blocks = [];
  let current = [];
  const pushBlock = () => {
    if (!current.length) return;
    const block = current.join('\n').replace(/[ \t]+$/gm, '').trimEnd();
    if (block) blocks.push(block);
    current = [];
  };
  for (const line of lines) {
    if (line.trim() === '') pushBlock();
    else current.push(line);
  }
  pushBlock();
  const seen = new Set();
  const kept = [];
  let removed = 0;
  for (const block of blocks) {
    if (seen.has(block)) { removed += 1; continue; }
    seen.add(block);
    kept.push(block);
  }
  const body = kept.join('\n\n') + (hadFinalNewline ? '\n' : '');
  return { body, original_blocks: blocks.length, duplicate_blocks_removed: removed };
}

function consolidateMarkerFiles(machineFiles, humanFiles, baseName) {
  const infos = [];
  const documents = new Map();
  const changes = new Map();
  const all = [
    ...machineFiles.map((name) => ({ name, kind: 'machine', file: path.join(MACHINE, name) })),
    ...humanFiles.map((name) => ({ name, kind: 'human', file: path.join(HUMAN, name) })),
  ].sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true }));

  for (const item of all) {
    const raw = fs.readFileSync(item.file);
    const index = infos.length;
    if (item.name.toLowerCase().endsWith('.json')) {
      const parsed = JSON.parse(raw.toString('utf8'));
      const changeList = Array.isArray(parsed.changes) ? parsed.changes : [];
      const changeIds = [];
      for (const change of changeList) {
        const key = jsonText(change);
        let entry = changes.get(key);
        if (!entry) { entry = { change, artifact_indices: [], occurrence_count: 0 }; changes.set(key, entry); }
        entry.artifact_indices.push(index);
        entry.occurrence_count += 1;
        changeIds.push(key);
      }
      const remainder = { ...parsed };
      delete remainder.changes;
      const docKey = jsonText(remainder);
      if (!documents.has(docKey)) documents.set(docKey, { kind: 'json', body: remainder, artifact_indices: [] });
      documents.get(docKey).artifact_indices.push(index);
      infos.push({ ...artifactInfo(item.name, raw), kind: item.kind, format: 'json', change_count: changeList.length, change_keys: changeIds, document_key: docKey });
    } else {
      const dedup = dedupeMarkdown(raw.toString('utf8'));
      const docKey = dedup.body;
      if (!documents.has(docKey)) documents.set(docKey, { kind: 'markdown', body: dedup.body, artifact_indices: [], original_blocks: dedup.original_blocks, duplicate_blocks_removed: dedup.duplicate_blocks_removed });
      documents.get(docKey).artifact_indices.push(index);
      infos.push({ ...artifactInfo(item.name, raw), kind: item.kind, format: 'markdown', original_blocks: dedup.original_blocks, duplicate_blocks_removed: dedup.duplicate_blocks_removed, document_key: docKey });
    }
  }

  const documentItems = Array.from(documents.values());
  const documentIds = new Map();
  documentItems.forEach((doc, index) => documentIds.set(doc.kind + '\u0000' + (doc.kind === 'markdown' ? doc.body : jsonText(doc.body)), `D${String(index + 1).padStart(5, '0')}`));
  const changeItems = Array.from(changes.values());
  const changeIds = new Map();
  changeItems.forEach((entry, index) => changeIds.set(jsonText(entry.change), `MC${String(index + 1).padStart(6, '0')}`));
  const records = [manifest('A06 Marker_ReWrite', infos, {
    deduplication: 'Exact JSON change objects and identical Markdown blocks are emitted once; each artifact retains provenance references. Registry snapshots are consolidated separately.',
    unique_document_count: documentItems.length,
    unique_change_count: changeItems.length,
    total_change_occurrences: changeItems.reduce((sum, x) => sum + x.occurrence_count, 0),
  })];
  infos.forEach((item, index) => records.push({
    record_type: 'artifact',
    artifact_index: index,
    name: item.name,
    kind: item.kind,
    format: item.format,
    bytes: item.bytes,
    sha256: item.sha256,
    change_count: item.change_count ?? 0,
    unique_change_ids: (item.change_keys || []).map((key) => changeIds.get(jsonText(JSON.parse(key)))),
    document_id: documentIds.get((item.format === 'json' ? 'json' : 'markdown') + '\u0000' + item.document_key),
    duplicate_blocks_removed: item.duplicate_blocks_removed ?? 0,
  }));
  documentItems.forEach((doc, index) => records.push({
    record_type: 'document',
    document_id: `D${String(index + 1).padStart(5, '0')}`,
    format: doc.kind,
    body: doc.body,
    artifact_indices: doc.artifact_indices,
    original_blocks: doc.original_blocks,
    duplicate_blocks_removed: doc.duplicate_blocks_removed,
  }));
  changeItems.forEach((entry, index) => records.push({
    record_type: 'change',
    change_id: `MC${String(index + 1).padStart(6, '0')}`,
    ...entry.change,
    occurrence_count: entry.occurrence_count,
    artifact_indices: entry.artifact_indices,
    artifact_files: entry.artifact_indices.map((i) => infos[i].name),
  }));
  return { records, outputs: writeParts(baseName, records), summary: { files: infos.length, bytes: infos.reduce((s, x) => s + x.bytes, 0), documents: documentItems.length, unique_changes: changeItems.length, change_occurrences: changeItems.reduce((s, x) => s + x.occurrence_count, 0) } };
}

function orderedSnapshotNames(names, marker) {
  if (marker) {
    return names.slice().sort((a, b) => {
      const abase = /pre_marker_rewrite/.test(a) ? 0 : 1;
      const bbase = /pre_marker_rewrite/.test(b) ? 0 : 1;
      if (abase !== bbase) return abase - bbase;
      return rangeSort(a, b);
    });
  }
  return names.slice().sort(rangeSort);
}

function locator(row) {
  return `${row.source_file}\u0000${row.source_line}`;
}

function consolidateSnapshots(names, category, baseName, marker) {
  const ordered = orderedSnapshotNames(names, marker);
  if (!ordered.length) throw new Error(`no snapshot files for ${category}`);
  const infos = [];
  const parsed = [];
  for (const name of ordered) {
    const { buf, rows } = readJsonl(path.join(MACHINE, name));
    parsed.push(rows);
    infos.push({ ...artifactInfo(name, buf), rows: rows.length });
  }
  const base = parsed[0];
  const indexByLocator = new Map();
  base.forEach((row, index) => indexByLocator.set(locator(row), index));
  const records = [manifest(category, infos, {
    deduplication: 'The first snapshot is stored in full. Each later snapshot stores only changed locator rows, applied in chronological filename order. Original snapshots remain untouched.',
    baseline_snapshot: ordered[0],
    snapshot_count: ordered.length,
    baseline_rows: base.length,
  })];
  let current = base.slice();
  records.push({ record_type: 'snapshot', snapshot_index: 0, name: ordered[0], bytes: infos[0].bytes, sha256: infos[0].sha256, rows: base.length, changed_count: base.length, role: 'baseline' });
  base.forEach((row) => records.push({ record_type: 'snapshot_row', snapshot_index: 0, locator: locator(row), row }));
  const snapshotSummaries = [{ name: ordered[0], rows: base.length, changed_count: base.length }];
  for (let s = 1; s < parsed.length; s += 1) {
    const rows = parsed[s];
    if (rows.length !== base.length) throw new Error(`row count mismatch in snapshot ${ordered[s]}`);
    const delta = [];
    for (let i = 0; i < rows.length; i += 1) {
      if (locator(rows[i]) !== locator(current[i])) throw new Error(`locator/order mismatch: ${ordered[s]} row ${i + 1}`);
      if (jsonText(rows[i]) !== jsonText(current[i])) delta.push({ index: i, row: rows[i] });
    }
    records.push({ record_type: 'snapshot', snapshot_index: s, name: ordered[s], bytes: infos[s].bytes, sha256: infos[s].sha256, rows: rows.length, changed_count: delta.length, role: 'delta' });
    delta.forEach((item) => records.push({ record_type: 'snapshot_delta', snapshot_index: s, locator: locator(item.row), row: item.row }));
    current = rows.slice();
    snapshotSummaries.push({ name: ordered[s], rows: rows.length, changed_count: delta.length });
  }
  return { records, outputs: writeParts(baseName, records), summary: { files: infos.length, bytes: infos.reduce((s, x) => s + x.bytes, 0), rows: base.length, snapshot_summaries: snapshotSummaries } };
}

function ranges(indices) {
  const sorted = Array.from(new Set(indices)).sort((a, b) => a - b);
  const result = [];
  let start = null;
  let prev = null;
  for (const n of sorted) {
    if (start === null) { start = n; prev = n; continue; }
    if (n === prev + 1) { prev = n; continue; }
    result.push(start === prev ? [start] : [start, prev]);
    start = n;
    prev = n;
  }
  if (start !== null) result.push(start === prev ? [start] : [start, prev]);
  return result;
}

function consolidateSemanticAudits(names, baseName) {
  const infos = [];
  const inputSets = new Map();
  const queueStates = new Map();
  let totalQueueOccurrences = 0;
  let totalBytes = 0;
  for (let index = 0; index < names.length; index += 1) {
    const name = names[index];
    const file = path.join(MACHINE, name);
    const { buf, value } = readJson(file);
    totalBytes += buf.length;
    const input = value.inputs || {};
    const inputKey = input.source_set_sha256 || `input_${index}`;
    if (!inputSets.has(inputKey)) inputSets.set(inputKey, {
      source_set_sha256: input.source_set_sha256 || null,
      registry_sha256: input.registry_sha256 || null,
      registry_rows: input.registry_rows ?? null,
      files: input.files || [],
    });
    const semanticSummary = value.semantic ? { ...value.semantic } : {};
    delete semanticSummary.rewrite_queue;
    const queue = value.semantic && Array.isArray(value.semantic.rewrite_queue) ? value.semantic.rewrite_queue : [];
    for (const entry of queue) {
      const key = jsonText(entry);
      let state = queueStates.get(key);
      if (!state) {
        state = { entry, audit_indices: [], occurrence_count: 0 };
        queueStates.set(key, state);
      }
      state.audit_indices.push(index);
      state.occurrence_count += 1;
      totalQueueOccurrences += 1;
    }
    infos.push({
      ...artifactInfo(name, buf),
      audit_index: index,
      generated_at: value.generated_at ?? null,
      scope: value.scope ?? null,
      evidence_limit: value.evidence_limit ?? null,
      inputs_ref: inputKey,
      structural: value.structural ?? null,
      semantic_summary: semanticSummary,
      rewrite_queue_count: queue.length,
    });
  }
  const stateItems = Array.from(queueStates.values());
  const stateIds = new Map();
  stateItems.forEach((state, index) => stateIds.set(jsonText(state.entry), `Q${String(index + 1).padStart(7, '0')}`));
  const inputItems = Array.from(inputSets.entries());
  const records = [manifest('A06 Semantic_Quality_Audit_After', infos, {
    deduplication: 'Per-audit summaries retain provenance; identical input sets are emitted once; identical rewrite-queue states are emitted once with audit-index occurrence ranges. Full original JSON files remain available at their recorded SHA-256.',
    unique_input_set_count: inputItems.length,
    unique_queue_state_count: stateItems.length,
    total_queue_occurrences: totalQueueOccurrences,
  })];
  inputItems.forEach(([key, input]) => records.push({ record_type: 'input_set', input_set_id: key, ...input }));
  infos.forEach((item) => records.push({ record_type: 'audit_file', ...item }));
  stateItems.forEach((state, index) => records.push({
    record_type: 'queue_state',
    state_id: `Q${String(index + 1).padStart(7, '0')}`,
    ...state.entry,
    occurrence_count: state.occurrence_count,
    first_audit_index: Math.min(...state.audit_indices),
    last_audit_index: Math.max(...state.audit_indices),
    audit_ranges: ranges(state.audit_indices),
  }));
  const result = { records, outputs: writeParts(baseName, records), summary: { files: infos.length, bytes: totalBytes, input_sets: inputItems.length, queue_states: stateItems.length, queue_occurrences: totalQueueOccurrences } };
  return result;
}

function print(label, result) {
  console.log(JSON.stringify({ label, summary: result.summary, outputs: result.outputs }, null, 2));
}

const semanticChangeFiles = fileNames(MACHINE, (f) => /Semantic_Rewrite_Changes/i.test(f) && !/marker/i.test(f) && f.toLowerCase().endsWith('.json'));
const markerMachineFiles = fileNames(MACHINE, (f) => /marker_rewrite/i.test(f) && f.toLowerCase().endsWith('.json'))
  .filter((f) => !/registry_/.test(f));
const markerHumanFiles = fileNames(HUMAN, (f) => /Marker_Rewrite/.test(f) && f.toLowerCase().endsWith('.md'));
const markerSnapshotFiles = fileNames(MACHINE, (f) => (/registry_before_v02_marker_rewrite/i.test(f) || /registry_pre_marker_rewrite_v02/i.test(f)) && f.toLowerCase().endsWith('.jsonl'));
const v04SnapshotFiles = fileNames(MACHINE, (f) => /registry_before_v04_semantic_rewrite/i.test(f) && f.toLowerCase().endsWith('.jsonl'));
const semanticAuditFiles = fileNames(MACHINE, (f) => /Semantic_Quality_Audit_After/i.test(f) && f.toLowerCase().endsWith('.json'));

if (semanticChangeFiles.length === 0) throw new Error('no Semantic_Rewrite_Changes artifacts found');
if (markerMachineFiles.length === 0 && markerHumanFiles.length === 0) throw new Error('no Marker_Rewrite artifacts found');
if (markerSnapshotFiles.length === 0) throw new Error('no marker registry snapshots found');
if (v04SnapshotFiles.length === 0) throw new Error('no v04 registry snapshots found');
if (semanticAuditFiles.length === 0) throw new Error('no Semantic_Quality_Audit_After artifacts found');

const changeResult = consolidateChangeFiles(semanticChangeFiles, 'A06 Semantic_Rewrite_Changes', 'A06_Semantic_Rewrite_Changes_Consolidated_2026-09-16');
const markerResult = consolidateMarkerFiles(markerMachineFiles, markerHumanFiles, 'A06_Marker_Rewrite_Consolidated_2026-09-16');
const markerSnapshotResult = consolidateSnapshots(markerSnapshotFiles, 'A06 registry_before_v02_marker_rewrite', 'A06_registry_before_v02_marker_rewrite_Consolidated_2026-09-16', true);
const v04Result = consolidateSnapshots(v04SnapshotFiles, 'A06 registry_before_v04_semantic_rewrite', 'A06_registry_before_v04_semantic_rewrite_Consolidated_2026-09-16', false);
const auditResult = consolidateSemanticAudits(semanticAuditFiles, 'A06_Semantic_Quality_Audit_After_Consolidated_2026-09-16');

print('semantic_changes', changeResult);
print('marker_rewrite', markerResult);
print('marker_registry_snapshots', markerSnapshotResult);
print('v04_registry_snapshots', v04Result);
print('semantic_quality_audit_after', auditResult);
