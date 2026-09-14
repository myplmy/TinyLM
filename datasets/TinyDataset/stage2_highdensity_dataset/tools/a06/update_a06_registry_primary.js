#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const AREA_SOURCE_PREFIX = 'stage2_(16)relational_composition_high_density_train_v';
const REGISTRY_BASENAME = 'stage2_(16)relational_composition_train_registry_v01_v52.jsonl';
const UTF8 = new TextDecoder('utf-8', { fatal: true });

function fail(message) {
  throw new Error(message);
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex').toUpperCase();
}

function decodeUtf8(buffer, label) {
  if (buffer.length >= 3 && buffer[0] === 0xef && buffer[1] === 0xbb && buffer[2] === 0xbf) {
    fail(`${label}: UTF-8 BOM is not allowed`);
  }
  try {
    return UTF8.decode(buffer);
  } catch (error) {
    fail(`${label}: invalid UTF-8 (${error.message})`);
  }
}

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) {
      fail(`unexpected positional argument: ${token}`);
    }
    const name = token.slice(2);
    if (name === 'help') {
      args.help = true;
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(args, name)) {
      fail(`duplicate option: --${name}`);
    }
    const value = argv[index + 1];
    if (value === undefined || value.startsWith('--')) {
      fail(`missing value for --${name}`);
    }
    args[name] = value;
    index += 1;
  }
  return args;
}

function requireOptions(args, names) {
  for (const name of names) {
    if (typeof args[name] !== 'string' || args[name].length === 0) {
      fail(`required option missing: --${name}`);
    }
  }
}

function printUsage() {
  process.stdout.write([
    'A06 registry primary updater',
    'build: node update_a06_registry_primary.js --input <registry.jsonl> --changes <changes.json> --output <candidate.jsonl>',
    'apply: node update_a06_registry_primary.js --target <registry.jsonl> --changes <changes.json> --candidate <candidate.jsonl> --expected-target-sha <SHA256> --backup <verified-backup.jsonl>',
    '',
    'The updater changes only an exact JSON token for primary on approved A06 locators.',
  ].join('\n'));
}

function splitJsonl(buffer) {
  const lines = [];
  let start = 0;
  for (let index = 0; index < buffer.length; index += 1) {
    if (buffer[index] !== 0x0a) {
      continue;
    }
    const bodyEnd = index > start && buffer[index - 1] === 0x0d ? index - 1 : index;
    lines.push({ body: buffer.subarray(start, bodyEnd), terminator: buffer.subarray(bodyEnd, index + 1) });
    start = index + 1;
  }
  if (start < buffer.length) {
    lines.push({ body: buffer.subarray(start), terminator: Buffer.alloc(0) });
  }
  return lines;
}

function locatorKey(sourceFile, sourceLine) {
  return `${sourceFile}\u0000${sourceLine}`;
}

function countOccurrences(haystack, needle) {
  let count = 0;
  let from = 0;
  while (from <= haystack.length - needle.length) {
    const at = haystack.indexOf(needle, from);
    if (at < 0) {
      break;
    }
    count += 1;
    from = at + needle.length;
  }
  return count;
}

function assertSafePrimary(value, label) {
  if (typeof value !== 'string' || value.length === 0) {
    fail(`${label}: primary must be a non-empty string`);
  }
  if (/[\r\n|]/u.test(value)) {
    fail(`${label}: primary contains a record delimiter`);
  }
}

function readChanges(changesPath) {
  const raw = fs.readFileSync(changesPath);
  const document = JSON.parse(decodeUtf8(raw, changesPath));
  if (document.schema_version !== 1 || document.area !== 'A06' || !Array.isArray(document.changes)) {
    fail(`${changesPath}: expected { schema_version: 1, area: "A06", changes: [...] }`);
  }

  const changes = new Map();
  for (const change of document.changes) {
    if (!change || typeof change !== 'object') {
      fail(`${changesPath}: each change must be an object`);
    }
    const { source_file: sourceFile, source_line: sourceLine, old_primary: oldPrimary, new_primary: newPrimary } = change;
    if (typeof sourceFile !== 'string' || !sourceFile.startsWith(AREA_SOURCE_PREFIX) || !sourceFile.endsWith('.source.psv')) {
      fail(`${changesPath}: out-of-area source_file: ${String(sourceFile)}`);
    }
    if (!Number.isInteger(sourceLine) || sourceLine < 2) {
      fail(`${changesPath}: invalid source_line for ${sourceFile}`);
    }
    assertSafePrimary(oldPrimary, `${changesPath}:${sourceFile}:${sourceLine}:old`);
    assertSafePrimary(newPrimary, `${changesPath}:${sourceFile}:${sourceLine}:new`);
    if (newPrimary.includes(' — ')) {
      fail(`${changesPath}:${sourceFile}:${sourceLine}: new primary still contains a dash marker`);
    }
    if (oldPrimary === newPrimary) {
      fail(`${changesPath}:${sourceFile}:${sourceLine}: old and new primary are identical`);
    }
    const key = locatorKey(sourceFile, sourceLine);
    if (changes.has(key)) {
      fail(`${changesPath}: duplicate change locator ${sourceFile}:${sourceLine}`);
    }
    changes.set(key, { sourceFile, sourceLine, oldPrimary, newPrimary });
  }
  if (changes.size === 0) {
    fail(`${changesPath}: changes must not be empty`);
  }
  return changes;
}

function sameNonPrimaryFields(before, after, label) {
  const beforeKeys = Object.keys(before);
  const afterKeys = Object.keys(after);
  if (beforeKeys.length !== afterKeys.length) {
    fail(`${label}: JSON key count changed`);
  }
  for (const key of beforeKeys) {
    if (!Object.prototype.hasOwnProperty.call(after, key)) {
      fail(`${label}: JSON key removed: ${key}`);
    }
    if (key !== 'primary' && JSON.stringify(before[key]) !== JSON.stringify(after[key])) {
      fail(`${label}: non-primary field changed: ${key}`);
    }
  }
}

function buildCandidate(inputPath, changes) {
  const input = fs.readFileSync(inputPath);
  decodeUtf8(input, inputPath);
  const inputLines = splitJsonl(input);
  if (inputLines.length === 0) {
    fail(`${inputPath}: empty registry`);
  }

  const seenLocators = new Set();
  const applied = new Set();
  const targetLineIndexes = new Set();
  const outputLines = [];

  for (let index = 0; index < inputLines.length; index += 1) {
    const line = inputLines[index];
    if (line.body.length === 0) {
      fail(`${inputPath}: blank JSONL row at physical line ${index + 1}`);
    }
    let record;
    try {
      record = JSON.parse(decodeUtf8(line.body, `${inputPath}:${index + 1}`));
    } catch (error) {
      fail(`${inputPath}:${index + 1}: invalid JSON (${error.message})`);
    }
    if (!record || typeof record.source_file !== 'string' || !Number.isInteger(record.source_line)) {
      fail(`${inputPath}:${index + 1}: missing source locator`);
    }
    assertSafePrimary(record.primary, `${inputPath}:${index + 1}`);
    const key = locatorKey(record.source_file, record.source_line);
    if (seenLocators.has(key)) {
      fail(`${inputPath}:${index + 1}: duplicate registry locator ${record.source_file}:${record.source_line}`);
    }
    seenLocators.add(key);

    const change = changes.get(key);
    if (!change) {
      outputLines.push(line);
      continue;
    }
    if (record.primary !== change.oldPrimary) {
      fail(`${inputPath}:${index + 1}: expected old primary mismatch for ${record.source_file}:${record.source_line}`);
    }

    const oldToken = Buffer.from(`"primary":${JSON.stringify(change.oldPrimary)}`, 'utf8');
    const newToken = Buffer.from(`"primary":${JSON.stringify(change.newPrimary)}`, 'utf8');
    if (countOccurrences(line.body, oldToken) !== 1) {
      fail(`${inputPath}:${index + 1}: expected exactly one raw primary token`);
    }
    const at = line.body.indexOf(oldToken);
    const rewrittenBody = Buffer.concat([line.body.subarray(0, at), newToken, line.body.subarray(at + oldToken.length)]);

    let rewrittenRecord;
    try {
      rewrittenRecord = JSON.parse(decodeUtf8(rewrittenBody, `${inputPath}:${index + 1}:rewritten`));
    } catch (error) {
      fail(`${inputPath}:${index + 1}: rewritten JSON is invalid (${error.message})`);
    }
    if (rewrittenRecord.primary !== change.newPrimary) {
      fail(`${inputPath}:${index + 1}: rewritten primary mismatch`);
    }
    sameNonPrimaryFields(record, rewrittenRecord, `${inputPath}:${index + 1}`);
    outputLines.push({ body: rewrittenBody, terminator: line.terminator });
    applied.add(key);
    targetLineIndexes.add(index);
  }

  if (applied.size !== changes.size) {
    const missing = [...changes.entries()].filter(([key]) => !applied.has(key)).map(([, change]) => `${change.sourceFile}:${change.sourceLine}`);
    fail(`${inputPath}: target locator missing: ${missing.join(', ')}`);
  }

  const output = Buffer.concat(outputLines.flatMap((line) => [line.body, line.terminator]));
  const outputLinesCheck = splitJsonl(output);
  if (outputLinesCheck.length !== inputLines.length) {
    fail(`${inputPath}: line count changed during rewrite`);
  }
  let nonTargetByteMismatches = 0;
  for (let index = 0; index < inputLines.length; index += 1) {
    if (!inputLines[index].terminator.equals(outputLinesCheck[index].terminator)) {
      fail(`${inputPath}: line terminator changed at physical line ${index + 1}`);
    }
    if (!targetLineIndexes.has(index) && !inputLines[index].body.equals(outputLinesCheck[index].body)) {
      nonTargetByteMismatches += 1;
    }
  }
  if (nonTargetByteMismatches !== 0) {
    fail(`${inputPath}: non-target byte mismatch count ${nonTargetByteMismatches}`);
  }

  return {
    input,
    output,
    recordCount: inputLines.length,
    targetCount: targetLineIndexes.size,
    nonTargetByteMismatches,
  };
}

function requireCanonicalRegistry(targetPath) {
  if (path.basename(targetPath) !== REGISTRY_BASENAME) {
    fail(`target must be ${REGISTRY_BASENAME}`);
  }
}

function buildMode(args) {
  requireOptions(args, ['input', 'changes', 'output']);
  if (fs.existsSync(args.output)) {
    fail(`output already exists: ${args.output}`);
  }
  const changes = readChanges(args.changes);
  const result = buildCandidate(args.input, changes);
  fs.writeFileSync(args.output, result.output, { flag: 'wx' });
  const written = fs.readFileSync(args.output);
  if (!written.equals(result.output)) {
    fail(`output verification failed: ${args.output}`);
  }
  process.stdout.write(`${JSON.stringify({
    mode: 'build',
    input_sha256: sha256(result.input),
    output_sha256: sha256(result.output),
    record_count: result.recordCount,
    target_count: result.targetCount,
    non_target_byte_mismatches: result.nonTargetByteMismatches,
    output: args.output,
  })}\n`);
}

function applyMode(args) {
  requireOptions(args, ['target', 'changes', 'candidate', 'expected-target-sha', 'backup']);
  requireCanonicalRegistry(args.target);
  const changes = readChanges(args.changes);
  const targetBefore = fs.readFileSync(args.target);
  const targetSha = sha256(targetBefore);
  if (targetSha !== args['expected-target-sha'].toUpperCase()) {
    fail(`target SHA mismatch: expected ${args['expected-target-sha'].toUpperCase()}, got ${targetSha}`);
  }
  const expected = buildCandidate(args.target, changes);
  const candidate = fs.readFileSync(args.candidate);
  if (!candidate.equals(expected.output)) {
    fail('candidate does not equal the line-preserving expected output for the current target');
  }
  if (fs.existsSync(args.backup)) {
    const backup = fs.readFileSync(args.backup);
    if (!backup.equals(targetBefore)) {
      fail(`existing backup does not match target: ${args.backup}`);
    }
  } else {
    fs.copyFileSync(args.target, args.backup, fs.constants.COPYFILE_EXCL);
    if (!fs.readFileSync(args.backup).equals(targetBefore)) {
      fail(`backup verification failed: ${args.backup}`);
    }
  }

  fs.renameSync(args.candidate, args.target);
  const targetAfter = fs.readFileSync(args.target);
  if (!targetAfter.equals(expected.output)) {
    fail('post-rename target verification failed');
  }
  process.stdout.write(`${JSON.stringify({
    mode: 'apply',
    before_sha256: targetSha,
    after_sha256: sha256(targetAfter),
    record_count: expected.recordCount,
    target_count: expected.targetCount,
    non_target_byte_mismatches: expected.nonTargetByteMismatches,
    backup: args.backup,
  })}\n`);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printUsage();
    return;
  }
  if (args.input) {
    buildMode(args);
    return;
  }
  if (args.target) {
    applyMode(args);
    return;
  }
  printUsage();
  fail('choose build mode (--input) or apply mode (--target)');
}

try {
  main();
} catch (error) {
  process.stderr.write(`ERROR: ${error.message}\n`);
  process.exitCode = 1;
}
