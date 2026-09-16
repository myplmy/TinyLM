'use strict';

/* Derive the line-addressed registry primary change set from the rewrite plan. */
const fs = require('node:fs');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..', '..', '..');
const planPath = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06', 'A06_Semantic_Rewrite_Plan_v16_v52_2026-09-16.json');
const outPath = path.join(ROOT, 'stage2_highdensity_dataset', 'audit_reports', 'machine', 'a06', 'A06_registry_primary_changes_v16_v52_2026-09-16.json');
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const seen = new Set();
const allRows = plan.rows;
const changes = allRows.filter((row) => row.old_primary !== row.new_primary).map((row) => {
  const key = `${row.source_file}\u0000${row.source_line}`;
  if (seen.has(key)) throw new Error(`duplicate locator ${row.source_file}:${row.source_line}`);
  seen.add(key);
  if (!row.new_primary || row.new_primary.includes(' — ') || /[\r\n|]/u.test(row.new_primary)) throw new Error(`unsafe new primary at ${key}`);
  if (row.old_primary === row.new_primary) throw new Error(`unchanged primary at ${key}`);
  return {
    source_file: row.source_file,
    source_line: row.source_line,
    old_primary: row.old_primary,
    new_primary: row.new_primary,
  };
});
if (changes.length === 0) throw new Error('no primary changes found');
const document = {
  schema_version: 1,
  area: 'A06',
  generated_at: new Date().toISOString(),
  plan_id: plan.plan_id,
  source_rewrite_count: allRows.length,
  primary_change_count: changes.length,
  text_only_count: allRows.length - changes.length,
  changes,
};
if (fs.existsSync(outPath)) throw new Error(`output already exists: ${outPath}`);
fs.writeFileSync(outPath, `${JSON.stringify(document, null, 2)}\n`, { flag: 'wx' });
process.stdout.write(JSON.stringify({ output: outPath, source_rewrite_count: allRows.length, primary_change_count: changes.length, text_only_count: allRows.length - changes.length }) + '\n');
