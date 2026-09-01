# Stage 2-10 corpus engine and auditor

These tools read the schema-2.0 central reservation ledger and preserve the
existing 36 pilot sources/corpora.  They do not use `relation_focus` as a
generation whitelist.

## Files

- `stage2_10_corpus_common.py`: ledger, source, corpus, Korean-particle, exact
  tokenizer, and validation relation-set contracts.
- `stage2_10_semantic_banks.py`: curated Stage/area semantic atoms for all 13
  controlled relations.
- `stage2_10_semantic_generator.py`: deterministic draft composer with
  `semantic_composition_generator` provenance and per-relation literal spans.
- `stage2_10_corpus_engine.py`: checkpoint/resume source-first builder and
  exact structural/token preflight.
- `stage2_10_corpus_audit.py`: read-only scalable audit of materialized source
  and corpus files.

## Safety boundary

The composer is not Guide §10 direct authoring.  Every composed row has
`manual_semantic_review: false`, and the engine reports those rows as manual
review debt.  `--write` hard-fails before creating a source, corpus, or
checkpoint whenever such debt is present.  Draft composition is therefore
limited to `--dry-run`/`--check-only` in memory unless the project owner first
approves a Guide §10 exception or every row is manually reviewed through a
separate authoring workflow.

Structural `PASS` never implies direct-authoring compliance.  The two verdicts
are printed separately.

## Read-only examples

```powershell
python -X utf8 stage1_highdensity_dataset/tools/stage2_10_corpus_engine.py plan --json

python -X utf8 stage1_highdensity_dataset/tools/stage2_10_corpus_engine.py source `
  --reservation-id S2-A01-T-002 --dry-run --json

python -X utf8 stage1_highdensity_dataset/tools/stage2_10_corpus_audit.py `
  --check-only --json
```

The source/run preflight uses the repository ByteLevel BPE tokenizer and gates
each represented Stage at its central-ledger approved mean, with a default
`±10%` tolerance.  It also requires zero known grammar signatures, validates
150 unique primary concepts per file, and reports provenance-template
frequency.  Validation rows require exactly 18 `unseen_relation: true` rows;
true relation labels must all have appeared in Stage train while their sorted
set did not, and every false set must have appeared in Stage train.

## Packaging and resume behavior

The intended authorized workflow is canonical source JSONL first, then corpus
JSON projection.  Existing PSV/JSONL pilot sources are read and preserved.
Creates are atomic and never replace a non-identical source/corpus.  A
checkpoint binds the central-ledger SHA-256, semantic-bank version, generator
version, artifact hashes, and manual-review debt.

The checkpoint-level `generator` fields identify the draft capability bundled
with the engine; they do not assert that every completed source was generated.
Each completed entry carries the authoritative `source_authoring_method`.
Unprovenanced canonical `*.source.jsonl` files produced through the approved
record-by-record path are recorded as `direct_model_authoring`, while legacy
pilot sources remain `legacy_direct_source`.

Do not run a full `--write` while generated manual-review debt exists.  Tool
development itself wrote no canonical artifact.  The later authorized direct
authoring run used this engine only to package and checkpoint the already
written `S2-A01-T-002` source.
