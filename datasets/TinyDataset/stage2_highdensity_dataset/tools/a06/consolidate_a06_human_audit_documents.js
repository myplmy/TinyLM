'use strict';

/*
 * Consolidate and (only after explicit --delete-verified) remove the original
 * A06 human-folder audit documents.  This helper deliberately does not touch
 * machine/a06 originals, canonical source/registry, package data, manifests,
 * checkpoints, or the central ledger.
 *
 * The protected consolidated log remains in audit_reports/a06.  Every other
 * top-level file in that directory is captured in a provenance manifest and a
 * JSONL document record before deletion.  Run without arguments first; the
 * second invocation with --delete-verified performs guarded deletion only if
 * the planned file list, bytes, and SHA-256 values are unchanged.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = process.cwd();
const HUMAN = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'a06');
const MACHINE = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06');
const OUT = path.join(MACHINE, 'consolidated');
const CAP_BYTES = 19_500_000;
const GENERATED_AT = '2026-09-16';
const PROTECTED_LOG = 'A06_Semantic_Rewrite_Consolidated_Log_2026-09-16.md';
const OUTPUT_BASE = 'A06_Human_Audit_Documents_Consolidated_2026-09-16';
const DELETION_MANIFEST = 'A06_Human_Audit_Documents_Deletion_Manifest_2026-09-16.json';

fs.mkdirSync(OUT, { recursive: true });

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex').toUpperCase();
}

function textOf(value) {
  return JSON.stringify(value);
}

function hasBom(buffer) {
  return buffer.length >= 3 && buffer[0] === 0xEF && buffer[1] === 0xBB && buffer[2] === 0xBF;
}

function classify(name) {
  if (/registry_(?:prechange|primary_changes)/i.test(name)) return 'registry_reference_already_consolidated';
  if (/Semantic_Text_Repair_Prechange_Plan|Text_Repair_Prechange_Plan/i.test(name)) return 'text_repair_prechange_plan';
  if (/Semantic_Rewrite_Prechange_Plan/i.test(name)) return 'semantic_rewrite_prechange_plan';
  if (/Transaction_Audit/i.test(name)) return 'transaction_audit';
  return 'other_audit';
}

function markdownBlockStats(body) {
  const normalized = body.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = normalized.endsWith('\n') ? normalized.slice(0, -1).split('\n') : normalized.split('\n');
  const blocks = [];
  let current = [];
  const push = () => {
    if (!current.length) return;
    const block = current.join('\n').replace(/[ \t]+$/gm, '').trimEnd();
    if (block) blocks.push(block);
    current = [];
  };
  for (const line of lines) {
    if (line.trim() === '') push();
    else current.push(line);
  }
  push();
  const seen = new Set();
  let duplicate = 0;
  for (const block of blocks) {
    if (seen.has(block)) duplicate += 1;
    else seen.add(block);
  }
  return { original_blocks: blocks.length, duplicate_blocks_removed: duplicate };
}

function listHumanFiles() {
  return fs.readdirSync(HUMAN)
    .filter((name) => fs.statSync(path.join(HUMAN, name)).isFile())
    .sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
}

function lineRecord(record) {
  const line = textOf(record) + '\n';
  const bytes = Buffer.byteLength(line, 'utf8');
  if (bytes > CAP_BYTES) throw new Error(`single record exceeds cap: ${bytes}`);
  return { line, bytes };
}

function writeParts(records) {
  const outputs = [];
  let part = 1;
  let lines = [];
  let size = 0;
  const flush = () => {
    if (!lines.length) return;
    const name = `${OUTPUT_BASE}_Part${String(part).padStart(2, '0')}.jsonl`;
    const target = path.join(OUT, name);
    if (fs.existsSync(target)) throw new Error(`refusing to overwrite derived output: ${target}`);
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

function readRegistryManifest(name) {
  const file = path.join(MACHINE, 'consolidated', name);
  if (!fs.existsSync(file)) throw new Error(`required registry consolidated output missing: ${name}`);
  const buffer = fs.readFileSync(file);
  const lines = buffer.toString('utf8').split('\n');
  if (lines[lines.length - 1] === '') lines.pop();
  if (!lines.length || !lines[0].trim()) throw new Error(`empty registry consolidated output: ${name}`);
  return JSON.parse(lines[0]);
}

function registryCoverage(registryNames) {
  const backupManifest = readRegistryManifest('A06_registry_backups_all_Consolidated_2026-09-16_Part01.jsonl');
  const primaryManifest = readRegistryManifest('A06_registry_primary_changes_all_Consolidated_2026-09-16_Part01.jsonl');
  const listed = new Set([
    ...(backupManifest.original_files || []).map((item) => item.name),
    ...(primaryManifest.original_files || []).map((item) => item.name),
  ]);
  const missing = registryNames.filter((name) => !listed.has(name));
  if (missing.length) throw new Error(`human registry inputs missing from all manifests: ${missing.join(', ')}`);
  return {
    required_files: registryNames,
    listed_count: registryNames.length - missing.length,
    missing,
    backup_manifest: backupManifest.category,
    primary_manifest: primaryManifest.category,
  };
}

function buildConsolidation() {
  const allNames = listHumanFiles();
  if (!allNames.includes(PROTECTED_LOG)) throw new Error(`protected consolidated log is missing: ${PROTECTED_LOG}`);
  const targetNames = allNames.filter((name) => name !== PROTECTED_LOG);
  if (!targetNames.length) throw new Error('no unmerged human-folder files remain');

  const artifacts = [];
  const documents = new Map();
  const categoryCounts = {};
  let totalBytes = 0;
  for (const name of targetNames) {
    const file = path.join(HUMAN, name);
    const buffer = fs.readFileSync(file);
    const body = buffer.toString('utf8');
    const bodyKey = body;
    if (!documents.has(bodyKey)) {
      const stats = markdownBlockStats(body);
      documents.set(bodyKey, {
        document_id: `D${String(documents.size + 1).padStart(4, '0')}`,
        format: /\.jsonl?$/i.test(name) ? (name.toLowerCase().endsWith('.jsonl') ? 'jsonl' : 'json') : 'markdown',
        body,
        artifact_indices: [],
        ...stats,
      });
    }
    const document = documents.get(bodyKey);
    const category = classify(name);
    categoryCounts[category] = (categoryCounts[category] || 0) + 1;
    const index = artifacts.length;
    document.artifact_indices.push(index);
    artifacts.push({
      artifact_index: index,
      name,
      category,
      bytes: buffer.length,
      sha256: sha256(buffer),
      has_bom: hasBom(buffer),
      document_id: document.document_id,
      ...markdownBlockStats(body),
    });
    totalBytes += buffer.length;
  }

  const registryNames = targetNames.filter((name) => /registry_(?:prechange|primary_changes)/i.test(name));
  const coverage = registryCoverage(registryNames);
  const protectedBuffer = fs.readFileSync(path.join(HUMAN, PROTECTED_LOG));
  const records = [{
    record_type: 'manifest',
    schema_version: 1,
    category: 'A06 human audit documents',
    generated_at: GENERATED_AT,
    source_directory: 'stage2_highdensity_dataset/audit_reports/a06',
    cap_bytes: CAP_BYTES,
    protected_file: { name: PROTECTED_LOG, bytes: protectedBuffer.length, sha256: sha256(protectedBuffer) },
    original_file_count: artifacts.length,
    original_total_bytes: totalBytes,
    original_files: artifacts.map((item) => ({ ...item })),
    unique_document_count: documents.size,
    deduplication: 'Exact raw document bodies are stored once and linked by document_id. Duplicate blank-separated blocks are counted for review metadata; original body text remains byte-faithful after UTF-8 decoding.',
    registry_coverage: coverage,
    deletion_scope: 'Only the listed top-level files are eligible. The protected consolidated log remains. Deletion requires --delete-verified and exact precondition hashes.',
  }];
  artifacts.forEach((item) => records.push({ record_type: 'artifact', ...item }));
  for (const document of documents.values()) records.push({ record_type: 'document', ...document });

  const outputs = writeParts(records);
  const outputBuffers = outputs.map((item) => ({ ...item, buffer: fs.readFileSync(path.join(OUT, item.name)) }));
  for (const item of outputBuffers) {
    if (item.buffer.length >= 20_000_000) throw new Error(`output exceeds 20MB: ${item.name}`);
    if (hasBom(item.buffer)) throw new Error(`output has BOM: ${item.name}`);
  }

  // Re-read every source and ensure the manifest/document references still
  // recover the exact decoded body and raw bytes before deletion is enabled.
  const docById = new Map(Array.from(documents.values()).map((doc) => [doc.document_id, doc]));
  for (const item of artifacts) {
    const buffer = fs.readFileSync(path.join(HUMAN, item.name));
    const doc = docById.get(item.document_id);
    if (!doc || doc.body !== buffer.toString('utf8') || buffer.length !== item.bytes || sha256(buffer) !== item.sha256) {
      throw new Error(`pre-delete document reconstruction failed: ${item.name}`);
    }
  }

  const deletion = {
    schema_version: 1,
    status: 'READY_FOR_DELETE',
    generated_at: GENERATED_AT,
    source_directory: 'stage2_highdensity_dataset/audit_reports/a06',
    protected_file: { name: PROTECTED_LOG, bytes: protectedBuffer.length, sha256: sha256(protectedBuffer) },
    target_count: artifacts.length,
    target_total_bytes: totalBytes,
    targets: artifacts.map((item) => ({ name: item.name, category: item.category, bytes: item.bytes, sha256: item.sha256, document_id: item.document_id })),
    consolidated_outputs: outputs,
    registry_coverage: coverage,
    guard: 'Delete only when current top-level file set equals protected_file plus targets and every target precondition matches. No recursive delete.',
  };
  const deletionPath = path.join(OUT, DELETION_MANIFEST);
  if (fs.existsSync(deletionPath)) throw new Error(`refusing to overwrite deletion manifest: ${deletionPath}`);
  fs.writeFileSync(deletionPath, `${JSON.stringify(deletion, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
  return { all_files: allNames.length, target_files: artifacts.length, target_bytes: totalBytes, unique_documents: documents.size, category_counts: categoryCounts, outputs, deletion_manifest: DELETION_MANIFEST, registry_coverage: coverage };
}

function deleteVerified() {
  const deletionPath = path.join(OUT, DELETION_MANIFEST);
  if (!fs.existsSync(deletionPath)) throw new Error(`deletion manifest missing: ${deletionPath}`);
  const deletion = JSON.parse(fs.readFileSync(deletionPath, 'utf8'));
  if (deletion.status !== 'READY_FOR_DELETE') throw new Error(`deletion manifest status is not READY_FOR_DELETE: ${deletion.status}`);
  const current = listHumanFiles();
  const targetNames = deletion.targets.map((item) => item.name).sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
  const expected = [deletion.protected_file.name, ...targetNames].sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
  if (textOf(current) !== textOf(expected)) throw new Error('human-folder file set changed since consolidation; deletion aborted');
  for (const item of deletion.targets) {
    if (item.name === PROTECTED_LOG || path.basename(item.name) !== item.name) throw new Error(`unsafe deletion target: ${item.name}`);
    const file = path.join(HUMAN, item.name);
    const buffer = fs.readFileSync(file);
    if (buffer.length !== item.bytes || sha256(buffer) !== item.sha256) throw new Error(`delete precondition mismatch: ${item.name}`);
  }
  const protectedPath = path.join(HUMAN, deletion.protected_file.name);
  if (!fs.existsSync(protectedPath)) throw new Error('protected log disappeared before deletion');
  for (const item of deletion.targets) fs.unlinkSync(path.join(HUMAN, item.name));
  const remaining = listHumanFiles();
  if (remaining.length !== 1 || remaining[0] !== deletion.protected_file.name) throw new Error(`deletion verification failed; remaining: ${remaining.join(', ')}`);
  const protectedBuffer = fs.readFileSync(protectedPath);
  deletion.status = 'DELETE_PASS';
  deletion.deleted_at = new Date().toISOString();
  deletion.deleted_count = deletion.targets.length;
  deletion.remaining_files = remaining;
  deletion.protected_file_after = { bytes: protectedBuffer.length, sha256: sha256(protectedBuffer) };
  fs.writeFileSync(deletionPath, `${JSON.stringify(deletion, null, 2)}\n`, { encoding: 'utf8' });
  return { status: deletion.status, deleted_count: deletion.deleted_count, target_total_bytes: deletion.target_total_bytes, remaining_files: remaining, deletion_manifest: DELETION_MANIFEST };
}

function main() {
  if (process.argv.includes('--delete-verified')) {
    console.log(JSON.stringify(deleteVerified(), null, 2));
    return;
  }
  console.log(JSON.stringify(buildConsolidation(), null, 2));
}

main();

