/*
 * Read-only diagnosis for residual repeated 5-word sequences in Stage2 A04.
 *
 * The canonical audit reports aggregate counts. This companion report adds
 * row/file coverage and a deterministic greedy rewrite set: for every
 * repeated five-word sequence it retains one occurrence and selects rows
 * whose rewording would remove the remaining occurrences. It never writes
 * source data.
 */
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const sourceFiles = fs.readdirSync(sourceDir)
  .filter(file => /^stage2_\(14\)state_transition_high_density_train_v\d+\.source\.jsonl$/.test(file))
  .sort();

const rows = [];
for (const file of sourceFiles) {
  const lines = fs.readFileSync(path.join(sourceDir, file), 'utf8').trimEnd().split(/\r?\n/);
  lines.forEach((line, offset) => {
    const record = JSON.parse(line);
    rows.push({
      file,
      version: Number(file.match(/_v(\d+)\.source/)[1]),
      line: offset + 1,
      primary: record.primary,
      text: record.text
    });
  });
}

const words = text => text.normalize('NFKC').toLowerCase().match(/[0-9A-Za-z가-힣]+/g) || [];
const occurrences = new Map();
const rowNgrams = rows.map(() => []);

rows.forEach((row, rowIndex) => {
  const tokens = words(row.text);
  const unique = new Set();
  for (let index = 0; index <= tokens.length - 5; index++) {
    unique.add(tokens.slice(index, index + 5).join(' '));
  }
  for (const ngram of unique) {
    if (!occurrences.has(ngram)) occurrences.set(ngram, []);
    occurrences.get(ngram).push(rowIndex);
  }
});

const repeated = [...occurrences.entries()].filter(([, indices]) => indices.length > 1);
for (const [ngram, indices] of repeated) {
  for (const rowIndex of indices) rowNgrams[rowIndex].push(ngram);
}

const activeCounts = new Map(repeated.map(([ngram, indices]) => [ngram, indices.length]));
const scores = Int32Array.from(rowNgrams, ngrams => ngrams.length);
const selected = new Uint8Array(rows.length);

class MaxHeap {
  constructor() { this.items = []; }
  push(item) {
    const values = this.items;
    values.push(item);
    let index = values.length - 1;
    while (index > 0) {
      const parent = (index - 1) >> 1;
      if (values[parent][0] > item[0] || (values[parent][0] === item[0] && values[parent][1] < item[1])) break;
      values[index] = values[parent];
      index = parent;
    }
    values[index] = item;
  }
  pop() {
    const values = this.items;
    if (!values.length) return null;
    const top = values[0];
    const last = values.pop();
    if (values.length) {
      let index = 0;
      while (true) {
        let child = index * 2 + 1;
        if (child >= values.length) break;
        if (child + 1 < values.length &&
            (values[child + 1][0] > values[child][0] ||
             (values[child + 1][0] === values[child][0] && values[child + 1][1] > values[child][1]))) child++;
        if (values[child][0] < last[0] || (values[child][0] === last[0] && values[child][1] < last[1])) break;
        values[index] = values[child];
        index = child;
      }
      values[index] = last;
    }
    return top;
  }
}

const heap = new MaxHeap();
for (let rowIndex = 0; rowIndex < rows.length; rowIndex++) {
  if (scores[rowIndex]) heap.push([scores[rowIndex], rowIndex]);
}

const chosen = [];
let residualAssignments = repeated.reduce((sum, [, indices]) => sum + indices.length, 0);
let residualTypes = repeated.length;
while (residualTypes > 0) {
  let item;
  do {
    item = heap.pop();
    if (!item) throw new Error('greedy selection exhausted before all repeats were covered');
  } while (selected[item[1]] || item[0] !== scores[item[1]]);

  const [, rowIndex] = item;
  selected[rowIndex] = 1;
  chosen.push({ rowIndex, scoreAtSelection: scores[rowIndex] });

  for (const ngram of rowNgrams[rowIndex]) {
    const count = activeCounts.get(ngram);
    if (count <= 1) continue;
    activeCounts.set(ngram, count - 1);
    residualAssignments--;
    if (count - 1 === 1) {
      residualTypes--;
      for (const other of occurrences.get(ngram)) {
        if (!selected[other]) {
          scores[other]--;
          if (scores[other] > 0) heap.push([scores[other], other]);
        }
      }
    }
  }
  scores[rowIndex] = 0;
}

function describeRow(rowIndex, extra = {}) {
  return { row_index: rowIndex, ...rows[rowIndex], repeated_5grams: rowNgrams[rowIndex].length, ...extra };
}

const participating = rowNgrams.reduce((count, ngrams) => count + Number(ngrams.length > 0), 0);
const byFile = new Map();
rows.forEach((row, rowIndex) => {
  if (!rowNgrams[rowIndex].length) return;
  const item = byFile.get(row.file) || { file: row.file, participating_rows: 0, repeated_assignments: 0, greedy_rows: 0 };
  item.participating_rows++;
  item.repeated_assignments += rowNgrams[rowIndex].length;
  byFile.set(row.file, item);
});
for (const item of chosen) byFile.get(rows[item.rowIndex].file).greedy_rows++;

const result = {
  audit: 'A04 repeated five-word target diagnosis',
  source_files: sourceFiles.length,
  source_records: rows.length,
  repeated_5gram_types: repeated.length,
  repeated_5gram_assignments: repeated.reduce((sum, [, indices]) => sum + indices.length, 0),
  participating_rows: participating,
  greedy_rewrite_rows_to_leave_one_occurrence_each: chosen.length,
  top_repeated_5grams: repeated
    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], 'ko'))
    .slice(0, 100)
    .map(([ngram, indices]) => ({
      ngram,
      occurrences: indices.length,
      rows: indices.map(index => ({ file: rows[index].file, line: rows[index].line, primary: rows[index].primary }))
    })),
  top_rows_by_initial_coverage: rowNgrams
    .map((ngrams, rowIndex) => ({ rowIndex, count: ngrams.length }))
    .filter(item => item.count)
    .sort((a, b) => b.count - a.count || a.rowIndex - b.rowIndex)
    .slice(0, 200)
    .map(item => describeRow(item.rowIndex, { initial_coverage: item.count })),
  greedy_rewrite_set: chosen.map(item => describeRow(item.rowIndex, { score_at_selection: item.scoreAtSelection })),
  file_coverage: [...byFile.values()].sort((a, b) => a.file.localeCompare(b.file))
};

const similarityArg = process.argv.indexOf('--similarity-json');
if (similarityArg >= 0) {
  const similarityPath = process.argv[similarityArg + 1];
  if (!similarityPath) throw new Error('--similarity-json requires a path');
  const similarity = JSON.parse(fs.readFileSync(path.resolve(similarityPath), 'utf8'));
  const edges = [];
  for (const [metric, pairs] of [
    ['tfidf', similarity.similarity.char_3_5_tfidf.all_threshold_pairs || []],
    ['jaccard', similarity.similarity.word_set_jaccard.all_threshold_pairs || []]
  ]) {
    for (const pair of pairs) {
      const key = endpoint => `${endpoint.file}:${endpoint.line}`;
      edges.push({ metric, left: key(pair.left), right: key(pair.right), score: pair.score });
    }
  }

  const remaining = edges.slice();
  const similarityRows = new Set();
  while (remaining.length) {
    const degree = new Map();
    for (const edge of remaining) {
      degree.set(edge.left, (degree.get(edge.left) || 0) + 1);
      degree.set(edge.right, (degree.get(edge.right) || 0) + 1);
    }
    const chosenKey = [...degree]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0][0];
    similarityRows.add(chosenKey);
    for (let index = remaining.length - 1; index >= 0; index--) {
      if (remaining[index].left === chosenKey || remaining[index].right === chosenKey) remaining.splice(index, 1);
    }
  }

  const topRepeatArg = process.argv.indexOf('--top-repeat-groups');
  const topRepeatGroups = topRepeatArg >= 0 ? Number(process.argv[topRepeatArg + 1]) : 0;
  const repeatRows = new Set();
  const repeatReasons = new Map();
  for (const [ngram, indices] of repeated
    .slice()
    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], 'ko'))
    .slice(0, topRepeatGroups)) {
    // Keep the first occurrence as the semantic reference and reword the rest.
    for (const rowIndex of indices.slice(1)) {
      const key = `${rows[rowIndex].file}:${rows[rowIndex].line}`;
      repeatRows.add(key);
      if (!repeatReasons.has(key)) repeatReasons.set(key, []);
      repeatReasons.get(key).push(ngram);
    }
  }

  const combined = new Set([...similarityRows, ...repeatRows]);
  const keyToIndex = new Map(rows.map((row, index) => [`${row.file}:${row.line}`, index]));
  result.similarity_target_plan = {
    threshold_edges: edges.length,
    greedy_vertex_cover_rows: similarityRows.size,
    top_repeat_groups: topRepeatGroups,
    repeated_group_rewrite_rows: repeatRows.size,
    combined_rewrite_rows: combined.size,
    rows: [...combined]
      .map(key => {
        const rowIndex = keyToIndex.get(key);
        return describeRow(rowIndex, {
          selected_for_similarity: similarityRows.has(key),
          selected_for_top_repeat: repeatRows.has(key),
          repeat_reasons: repeatReasons.get(key) || []
        });
      })
      .sort((a, b) => a.version - b.version || a.line - b.line)
  };
}

const serialized = JSON.stringify(result, null, 2) + '\n';
if (process.argv.includes('--write-report')) {
  const outputArg = process.argv.indexOf('--output');
  const reportPath = outputArg >= 0
    ? path.resolve(process.argv[outputArg + 1] || (() => { throw new Error('--output requires a path'); })())
    : path.join(
      root,
      'stage2_highdensity_dataset',
      'audit_reports',
      'machine',
      'TinyLM_Stage2_A04_Residual_Repeat5_Targets_2026-09-10.json'
    );
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, serialized, 'utf8');
}
process.stdout.write(serialized);
