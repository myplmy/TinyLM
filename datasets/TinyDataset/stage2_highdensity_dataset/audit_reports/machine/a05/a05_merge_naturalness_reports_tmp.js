'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const dir = __dirname;
const consolidatedName = 'TinyLM_Stage2_A05_ModalityPossibility_Reaudit_Naturalness_Consolidated_2026-09-16.json';
const consolidatedPath = path.join(dir, consolidatedName);
const tempPath = consolidatedPath + '.merge_tmp';
const writeTemp = process.argv.includes('--write-temp');

function sha256Buffer(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function sha256File(file) {
  return sha256Buffer(fs.readFileSync(file));
}

function clone(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function numericRevision(file) {
  const m = file.match(/_r(\d+)_/);
  return m ? Number(m[1]) : Number.MAX_SAFE_INTEGER;
}

function summarySimilarity(groups) {
  const metricNames = [
    'raw_text_word_set_jaccard',
    'raw_text_char_3_5_tfidf_cosine',
    'masked_primary_word_set_jaccard',
    'masked_primary_char_3_5_tfidf_cosine',
  ];
  return (groups || []).map((g) => {
    const out = {
      relation_set: g.relation_set,
      records: g.records,
      possible_pairs: g.possible_pairs,
      candidate_search: {
        mode: g.candidate_search && g.candidate_search.mode,
        candidate_pairs_examined: g.candidate_search && g.candidate_search.candidate_pairs_examined,
        capped: g.candidate_search && g.candidate_search.capped,
        oversized_buckets_count: g.candidate_search && g.candidate_search.oversized_buckets,
      },
    };
    for (const name of metricNames) {
      const m = g[name] || {};
      const maximumScore = m.maximum_score !== undefined
        ? m.maximum_score
        : (m.maximum && m.maximum.score !== undefined ? m.maximum.score : null);
      const topPairsCount = Array.isArray(m.top_pairs)
        ? m.top_pairs.length
        : (m.top_pairs_count === undefined ? 0 : m.top_pairs_count);
      out[name] = {
        threshold: m.threshold,
        pairs_ge_threshold: m.pairs_ge_threshold,
        maximum_score: maximumScore,
        top_pairs_count: topPairsCount,
      };
    }
    return out;
  });
}

function reportSummary(report, file, bytes, sha) {
  const registry = report.registry || {};
  const parseProblems = registry.parse_problems;
  const parseProblemsCount = Array.isArray(parseProblems)
    ? parseProblems.length
    : (typeof parseProblems === 'number' ? parseProblems : (parseProblems ? 1 : 0));
  const naturalness = report.naturalness_warnings || {};
  const queueIndex = (items) => (items || []).map((q) => ({
    review_key: q.review_key,
    kind: q.kind,
    severity: q.severity,
    code: q.code,
  }));
  const stale = report.stale_or_invalid_decisions;
  const stat = fs.statSync(path.join(dir, file));
  return {
    file,
    mtime_utc: new Date(stat.mtimeMs).toISOString(),
    bytes,
    sha256: sha.toUpperCase(),
    source_set_sha256: report.source_set_sha256,
    source_files: report.source_files,
    source_records: report.source_records,
    registry: {
      supplied: registry.supplied,
      require_registry: registry.require_registry,
      sha256: registry.sha256,
      parse_problems_count: parseProblemsCount,
      records: registry.records,
      coverage: registry.coverage,
    },
    primary_eunneun_opening: clone(report.primary_eunneun_opening),
    x1_x2_composite: clone(report.x1_x2_composite),
    similarity_summary: summarySimilarity(report.same_relation_set_masked_similarity),
    naturalness_warnings: {
      mode: naturalness.mode,
      warning_records: naturalness.warning_records,
      warning_assignments: naturalness.warning_assignments,
      primary_dash_records: naturalness.primary_dash_records,
      primary_dash_ratio: naturalness.primary_dash_ratio,
      by_code: clone(naturalness.by_code),
      by_expression: clone(naturalness.by_expression),
    },
    hard_source_errors: report.hard_source_errors,
    review_queue_counts: clone(report.review_queue_counts),
    chatgpt_review_index: queueIndex(report.chatgpt_review_queue),
    user_review_index: queueIndex(report.user_review_queue),
    stale_or_invalid_decisions_count: Array.isArray(stale) ? stale.length : (stale || 0),
  };
}

function sourceSnapshot(report, file, sha) {
  return {
    source_set_sha256: report.source_set_sha256,
    source_files: report.source_files,
    source_records: report.source_records,
    source_file_sha256: clone(report.source_file_sha256),
    report_files: [file],
    report_sha256: [sha.toUpperCase()],
  };
}

function loadRawReports() {
  const files = fs.readdirSync(dir)
    .filter((file) => file.includes('ModalityPossibility_Reaudit_Naturalness_r') && file.endsWith('.json'))
    .sort((a, b) => numericRevision(a) - numericRevision(b) || a.localeCompare(b));
  if (files.length === 0) throw new Error('No current rNN naturalness reports found');
  return files.map((file) => {
    const buf = fs.readFileSync(path.join(dir, file));
    const report = JSON.parse(buf.toString('utf8'));
    if (!report.source_set_sha256 || !report.source_file_sha256) {
      throw new Error(`missing source hashes: ${file}`);
    }
    return {
      file,
      report,
      bytes: buf.length,
      sha: sha256Buffer(buf),
    };
  });
}

function merge() {
  const baseBuf = fs.readFileSync(consolidatedPath);
  const baseSha = sha256Buffer(baseBuf).toUpperCase();
  const base = JSON.parse(baseBuf.toString('utf8'));
  const rawReports = loadRawReports();
  const history = clone(base.report_history || []);
  const historyFiles = new Set(history.map((entry) => entry.file));
  const historyShas = new Set(history.map((entry) => String(entry.sha256).toUpperCase()));
  const duplicateCurrent = [];
  const currentShaToFiles = new Map();
  for (const item of rawReports) {
    const list = currentShaToFiles.get(item.sha.toUpperCase()) || [];
    list.push(item.file);
    currentShaToFiles.set(item.sha.toUpperCase(), list);
  }
  for (const [sha, files] of currentShaToFiles) {
    if (files.length > 1) duplicateCurrent.push({ sha256: sha, files });
  }
  for (const item of rawReports) {
    if (historyFiles.has(item.file)) throw new Error(`history already contains current file: ${item.file}`);
    if (historyShas.has(item.sha.toUpperCase())) {
      throw new Error(`current report SHA already in history: ${item.file}`);
    }
    history.push(reportSummary(item.report, item.file, item.bytes, item.sha));
  }

  const snapshotMap = new Map();
  for (const snapshot of (base.source_snapshots || [])) {
    snapshotMap.set(snapshot.source_set_sha256, clone(snapshot));
  }
  for (const item of rawReports) {
    const incoming = sourceSnapshot(item.report, item.file, item.sha);
    const existing = snapshotMap.get(incoming.source_set_sha256);
    if (!existing) {
      snapshotMap.set(incoming.source_set_sha256, incoming);
      continue;
    }
    existing.report_files = [...new Set([...(existing.report_files || []), ...incoming.report_files])];
    existing.report_sha256 = [...new Set([...(existing.report_sha256 || []), ...incoming.report_sha256])];
  }

  const reviewMap = new Map();
  for (const entry of (base.review_queue_union_index || [])) {
    reviewMap.set(entry.review_key, clone(entry));
  }
  for (const item of rawReports) {
    for (const q of [...(item.report.chatgpt_review_queue || []), ...(item.report.user_review_queue || [])]) {
      const existing = reviewMap.get(q.review_key);
      if (!existing) {
        reviewMap.set(q.review_key, {
          review_key: q.review_key,
          kind: q.kind,
          severity: q.severity,
          code: q.code,
          first_seen_report: item.file,
          last_seen_report: item.file,
        });
      } else {
        existing.last_seen_report = item.file;
        existing.kind = q.kind;
        existing.severity = q.severity;
        existing.code = q.code;
      }
    }
  }

  const appended = rawReports.map((item) => ({
    file: item.file,
    sha256: item.sha.toUpperCase(),
    bytes: item.bytes,
  }));
  const oldAppended = (base.scope && base.scope.deduplication && base.scope.deduplication.appended_reports) || [];
  const allAppended = [...oldAppended, ...appended];
  const reportHistoryBytes = history.reduce((sum, entry) => sum + Number(entry.bytes || 0), 0);
  const exactGroups = clone((base.scope && base.scope.deduplication && base.scope.deduplication.exact_duplicate_groups) || []);
  exactGroups.push(...duplicateCurrent);

  const out = clone(base);
  out.generated_at_utc = new Date().toISOString();
  out.scope.input_report_count = history.length;
  out.scope.input_total_bytes = reportHistoryBytes;
  out.scope.deduplication = {
    ...(out.scope.deduplication || {}),
    exact_duplicate_group_count: exactGroups.length,
    exact_duplicate_groups: exactGroups,
    source_snapshot_count: snapshotMap.size,
    appended_reports: allAppended,
    deleted_original_report_count: rawReports.length,
    deleted_original_reports: rawReports.map((item) => item.file),
    input_files_exclude_retained_consolidated: true,
    policy: '전문은 최신 보고서 하나만 보존하고, 과거·중간 보고서는 해시·시각·핵심 지표·소스 스냅샷·검토 인덱스로 통합한다. 동일 바이트 보고서는 중복 그룹으로 묶고 전문을 반복 저장하지 않는다.',
  };
  out.report_history = history;
  out.source_snapshots = [...snapshotMap.values()];
  out.review_queue_union_index = [...reviewMap.values()];
  const latest = rawReports[rawReports.length - 1];
  out.latest_report_file = null;
  out.latest_report_sha256 = latest.sha.toUpperCase();
  out.latest_report = latest.report;
  out.latest_report_source_file = latest.file;
  out.latest_report_storage = 'embedded_in_consolidated';
  out.consolidation = {
    operation: 'append_deduplicate_delete_a05_naturalness_reports',
    performed_at_utc: out.generated_at_utc,
    retained_file: consolidatedName,
    input_report_pattern: '*ModalityPossibility_Reaudit_Naturalness*.json (consolidated file excluded)',
    appended_report_count: rawReports.length,
    appended_reports: appended,
    deleted_original_reports: rawReports.map((item) => item.file),
    exact_duplicate_groups_total: exactGroups.length,
    deduplicated_fields: {
      report_history: 'one compact summary per report file; exact-byte duplicates retain provenance without repeated full payloads',
      source_snapshots: 'one entry per source_set_sha256; report file and SHA lists unioned',
      review_queue_union_index: 'one entry per review_key; first/last observed report retained',
      latest_report: `only ${latest.file} full report embedded`,
    },
    size_limit_bytes: 20000000,
    previous_consolidated_sha256: baseSha,
  };
  const serialized = JSON.stringify(out, null, 2) + '\n';
  const outputBytes = Buffer.byteLength(serialized, 'utf8');
  if (outputBytes >= 20000000) throw new Error(`projected output is over limit: ${outputBytes}`);
  if (history.length !== out.scope.input_report_count) throw new Error('history count mismatch');
  if (reportHistoryBytes !== out.scope.input_total_bytes) throw new Error('history byte sum mismatch');
  if (new Set(out.report_history.map((entry) => entry.file)).size !== out.report_history.length) throw new Error('history file duplicate');
  if (new Set(out.source_snapshots.map((entry) => entry.source_set_sha256)).size !== out.source_snapshots.length) throw new Error('snapshot duplicate');
  if (new Set(out.review_queue_union_index.map((entry) => entry.review_key)).size !== out.review_queue_union_index.length) throw new Error('review key duplicate');
  if (out.latest_report_source_file !== latest.file || out.latest_report_sha256 !== latest.sha.toUpperCase()) throw new Error('latest report mismatch');
  const result = {
    base_sha256: baseSha,
    raw_report_count: rawReports.length,
    raw_report_bytes: rawReports.reduce((sum, item) => sum + item.bytes, 0),
    raw_report_files: rawReports.map((item) => item.file),
    output_bytes: outputBytes,
    output_sha256: sha256Buffer(Buffer.from(serialized, 'utf8')).toUpperCase(),
    report_history_count: out.report_history.length,
    source_snapshot_count: out.source_snapshots.length,
    review_union_count: out.review_queue_union_index.length,
    latest_report_source_file: latest.file,
    latest_report_sha256: latest.sha.toUpperCase(),
    exact_duplicate_group_count: exactGroups.length,
    temp_path: tempPath,
  };
  if (writeTemp) {
    fs.writeFileSync(tempPath, serialized, { encoding: 'utf8', flag: 'w' });
    const written = fs.readFileSync(tempPath);
    if (written.length !== outputBytes) throw new Error('written temp byte mismatch');
    if (sha256Buffer(written).toUpperCase() !== result.output_sha256) throw new Error('written temp SHA mismatch');
    JSON.parse(written.toString('utf8'));
  }
  console.log(JSON.stringify(result, null, 2));
}

merge();
