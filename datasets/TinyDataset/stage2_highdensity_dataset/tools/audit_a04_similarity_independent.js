/* Independent A04 similarity and particle review.
 * This tool intentionally does not import or call the canonical structural auditor.
 * It mirrors the documented sparse TF-IDF/Jaccard definitions with a separate Node implementation.
 */
const fs = require('fs');
const path = require('path');

const root = process.cwd();
const includeAllThresholdPairs = process.argv.includes('--all-threshold-pairs');
const sourceDir = path.join(root, 'stage2_highdensity_dataset', 'sources', 'train');
const sourceFiles = fs.readdirSync(sourceDir)
  .filter(f => /^stage2_\(14\)state_transition_high_density_train_v\d+\.source\.jsonl$/.test(f))
  .sort();

const rows = [];
for (const file of sourceFiles) {
  const lines = fs.readFileSync(path.join(sourceDir, file), 'utf8').trimEnd().split(/\r?\n/);
  lines.forEach((line, index) => {
    const row = JSON.parse(line);
    rows.push({ file, line: index + 1, primary: row.primary, text: row.text });
  });
}

const texts = rows.map(r => r.text);
const n = rows.length;
const wordTokens = text => text.normalize('NFKC').toLowerCase().match(/[0-9A-Za-z가-힣]+/g) || [];

function characterCounts(text) {
  const value = text.normalize('NFKC').toLowerCase();
  const counts = new Map();
  for (let size = 3; size <= 5; size++) {
    for (let i = 0; i <= value.length - size; i++) {
      const feature = value.slice(i, i + size);
      counts.set(feature, (counts.get(feature) || 0) + 1);
    }
  }
  return counts;
}

function buildCharIndex() {
  const perDoc = [];
  const df = new Map();
  for (const text of texts) {
    const counts = characterCounts(text);
    perDoc.push(counts);
    for (const feature of counts.keys()) df.set(feature, (df.get(feature) || 0) + 1);
  }
  const idf = new Map();
  const postings = new Map();
  for (const [feature, count] of df) {
    idf.set(feature, Math.log((1 + n) / (1 + count)) + 1);
    if (count >= 2) postings.set(feature, []);
  }
  const norms = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    let sum = 0;
    for (const [feature, count] of perDoc[i]) {
      const weight = count * idf.get(feature);
      sum += weight * weight;
      if (postings.has(feature)) postings.get(feature).push([i, count]);
    }
    norms[i] = Math.sqrt(sum);
  }
  return { perDoc, idf, postings, norms };
}

function describePair(pair, score) {
  if (!pair) return null;
  const left = rows[pair[0]], right = rows[pair[1]];
  return {
    score: Number(score.toFixed(9)),
    left: { file: left.file, line: left.line, primary: left.primary, text: left.text },
    right: { file: right.file, line: right.line, primary: right.primary, text: right.text }
  };
}

function retainTopPair(entries, pair, score, limit = 24) {
  entries.push({ pair, score });
  if (entries.length > limit * 2) {
    entries.sort((a, b) => b.score - a.score);
    entries.length = limit;
  }
}

function describeTopPairs(entries, limit = 24) {
  return entries
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(entry => describePair(entry.pair, entry.score));
}

function charSimilarity() {
  const { perDoc, idf, postings, norms } = buildCharIndex();
  const dots = new Float64Array(n);
  const marks = new Int32Array(n);
  let stamp = 0;
  let thresholdPairs = 0;
  let maximum = 0;
  let maximumPair = null;
  let pairCountWithSharedFeature = 0;
  const topPairs = [];
  const allThresholdPairs = [];
  for (let i = 0; i < n; i++) {
    stamp++;
    const touched = [];
    const leftNorm = norms[i];
    for (const [feature, leftCount] of perDoc[i]) {
      const list = postings.get(feature);
      if (!list) continue;
      const leftWeight = (leftCount * idf.get(feature)) / leftNorm;
      for (const [j, rightCount] of list) {
        if (j <= i) continue;
        if (marks[j] !== stamp) { marks[j] = stamp; dots[j] = 0; touched.push(j); }
        dots[j] += leftWeight * ((rightCount * idf.get(feature)) / norms[j]);
      }
    }
    pairCountWithSharedFeature += touched.length;
    for (const j of touched) {
      const score = dots[j];
      if (score >= 0.72) {
        thresholdPairs++;
        retainTopPair(topPairs, [i, j], score);
        if (includeAllThresholdPairs) allThresholdPairs.push(describePair([i, j], score));
      }
      if (score > maximum) { maximum = score; maximumPair = [i, j]; }
    }
  }
  return {
    method: 'character 3-5-gram TF-IDF cosine; NFKC/lowercase; raw term counts; smooth IDF; L2 normalization; sparse pair accumulation',
    threshold: 0.72,
    records: n,
    pairs_with_shared_feature: pairCountWithSharedFeature,
    pairs_ge_threshold: thresholdPairs,
    max: Number(maximum.toFixed(9)),
    max_pair: describePair(maximumPair, maximum),
    top_threshold_pairs: describeTopPairs(topPairs),
    ...(includeAllThresholdPairs ? { all_threshold_pairs: allThresholdPairs } : {})
  };
}

function buildWordIndex() {
  const sets = [];
  const postings = new Map();
  for (let i = 0; i < n; i++) {
    const set = new Set(wordTokens(texts[i]));
    sets.push(set);
    for (const word of set) {
      if (!postings.has(word)) postings.set(word, []);
      postings.get(word).push(i);
    }
  }
  return { sets, postings };
}

function wordJaccard() {
  const { sets, postings } = buildWordIndex();
  const intersections = new Uint16Array(n);
  const marks = new Int32Array(n);
  let stamp = 0;
  let thresholdPairs = 0;
  let maximum = 0;
  let maximumPair = null;
  let pairCountWithSharedWord = 0;
  const topPairs = [];
  const allThresholdPairs = [];
  for (let i = 0; i < n; i++) {
    stamp++;
    const touched = [];
    for (const word of sets[i]) {
      const list = postings.get(word);
      for (const j of list) {
        if (j <= i) continue;
        if (marks[j] !== stamp) { marks[j] = stamp; intersections[j] = 0; touched.push(j); }
        intersections[j]++;
      }
    }
    pairCountWithSharedWord += touched.length;
    for (const j of touched) {
      const score = intersections[j] / (sets[i].size + sets[j].size - intersections[j]);
      if (score >= 0.60) {
        thresholdPairs++;
        retainTopPair(topPairs, [i, j], score);
        if (includeAllThresholdPairs) allThresholdPairs.push(describePair([i, j], score));
      }
      if (score > maximum) { maximum = score; maximumPair = [i, j]; }
    }
  }
  return {
    method: 'word-set Jaccard; NFKC/lowercase; Korean/ASCII/number lexical tokens; sparse inverted-index pair accumulation',
    threshold: 0.60,
    records: n,
    pairs_with_shared_word: pairCountWithSharedWord,
    pairs_ge_threshold: thresholdPairs,
    max: Number(maximum.toFixed(9)),
    max_pair: describePair(maximumPair, maximum),
    top_threshold_pairs: describeTopPairs(topPairs),
    ...(includeAllThresholdPairs ? { all_threshold_pairs: allThresholdPairs } : {})
  };
}

function particleReview() {
  const hardPatterns = [
    '신호면', '상태를로', '값를', '값가', '기록를', '기록가', '자료를로'
  ];
  const hardFindings = [];
  const adjacentDuplicateWords = [];
  const particleFindings = [];
  let hangulPrimaryRows = 0;
  let numberedPrimaryRows = 0;
  let attachedParticleOccurrences = 0;
  const particleHistogram = new Map();
  function finalType(word) {
    const cp = word.codePointAt(word.length - 1);
    if (!cp || cp < 0xac00 || cp > 0xd7a3) return null;
    const jong = (cp - 0xac00) % 28;
    if (jong === 0) return 'none';
    if (jong === 8) return 'rieul';
    return 'final';
  }
  function allowed(type, particle) {
    if (!type) return true;
    // Genitive, locative and instrumental particles below are not determined
    // by a final consonant in this audit; only the paired particles are gated.
    if (particle === '의' || particle === '에' || particle === '에서') return true;
    if (particle === '으로') return type === 'final' && type !== 'rieul';
    if (particle === '로') return type === 'none' || type === 'rieul';
    if (type === 'final' || type === 'rieul') return new Set(['은', '이', '을', '과']).has(particle);
    return new Set(['는', '가', '를', '와']).has(particle);
  }
  rows.forEach((row, index) => {
    for (const pattern of hardPatterns) if (row.text.includes(pattern)) hardFindings.push({ index, pattern, ...row });
    const words = wordTokens(row.text);
    for (let i = 1; i < words.length; i++) if (words[i] === words[i - 1]) adjacentDuplicateWords.push({ index, word: words[i], ...row });
    // A04 uses trailing decimal digits as record discriminators.  Judge the
    // particle against the preceding Korean concept noun, not the digit name.
    const pronunciationStem = row.primary.replace(/[0-9]+$/, '').trimEnd();
    if (pronunciationStem !== row.primary) numberedPrimaryRows++;
    if (/[가-힣]$/.test(pronunciationStem)) {
      hangulPrimaryRows++;
      let start = 0;
      while ((start = row.text.indexOf(row.primary, start)) >= 0) {
        const rest = row.text.slice(start + row.primary.length);
        const match = rest.match(/^(에서|으로|은|는|이|가|을|를|과|와|로|에|의)/);
        if (match) {
          const particle = match[1];
          attachedParticleOccurrences++;
          particleHistogram.set(particle, (particleHistogram.get(particle) || 0) + 1);
          const type = finalType(pronunciationStem);
          if (!allowed(type, particle)) particleFindings.push({
            index, primary: row.primary, pronunciation_stem: pronunciationStem,
            particle, final_type: type, ...row
          });
        }
        start += row.primary.length;
      }
    }
  });
  return {
    hard_pattern_candidates: hardFindings.length,
    hard_pattern_examples: hardFindings.slice(0, 20),
    adjacent_duplicate_word_candidates: adjacentDuplicateWords.length,
    adjacent_duplicate_examples: adjacentDuplicateWords.slice(0, 20),
    primary_hangul_rows: hangulPrimaryRows,
    numbered_primary_rows: numberedPrimaryRows,
    primary_attached_occurrences: attachedParticleOccurrences,
    particle_histogram: Object.fromEntries([...particleHistogram].sort((a, b) => b[1] - a[1])),
    primary_particle_candidates: particleFindings.length,
    primary_particle_examples: particleFindings.slice(0, 20),
    review_note: '후보는 독립 휴리스틱의 검출값이며, 실제 오류 여부는 사람이 예문을 확인해야 한다. A04의 primary 끝 숫자는 레코드 구분자로 보고 앞선 한글 개념명의 받침을 판정했다.'
  };
}

console.error(`[independent] loaded ${n} records from ${sourceFiles.length} files`);
const result = {
  audit: 'A04 independent similarity and particle review',
  source_files: sourceFiles.length,
  source_records: n,
  similarity: {
    char_3_5_tfidf: charSimilarity(),
    word_set_jaccard: wordJaccard()
  },
  particle_review: particleReview()
};
const serialized = JSON.stringify(result, null, 2) + '\n';
const outIndex = process.argv.indexOf('--out');
const outPath = outIndex >= 0 ? process.argv[outIndex + 1] : null;
if (outIndex >= 0 && (!outPath || outPath.startsWith('--'))) throw new Error('--out requires a path');
if (outPath) {
  fs.writeFileSync(path.resolve(outPath), serialized, 'utf8');
} else if (process.argv.includes('--write-report')) {
  const reportPath = path.join(root, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'TinyLM_Stage2_A04_Independent_Similarity_Review_2026-09-10.json');
  fs.writeFileSync(reportPath, serialized, 'utf8');
  console.error(`[independent] wrote ${reportPath}`);
}
if (!outPath) console.log(serialized);
