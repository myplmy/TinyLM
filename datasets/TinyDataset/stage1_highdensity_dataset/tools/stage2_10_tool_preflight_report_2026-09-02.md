# Stage 2-10 tool preflight — 2026-09-02

Scope: tool development and read-only/draft validation only.  No corpus,
canonical source, central ledger, manifest, or checkpoint was written.

- Central ledger: schema 2.0, 4,370 reservations, SHA-256
  `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`.
- Inventory: 36 existing pilots and 4,334 missing reservations.
- AST: all Stage 2-10 tool modules parsed successfully.
- Nine-file draft sample: 1,350 rows; every Stage exact tokenizer mean passed
  the approved ledger mean at `±10%`; known grammar signatures 0; primary
  concepts 150/150 unique in every file.

| Stage | sample mean | approved target | gate |
|---:|---:|---:|:---:|
| 2 | 40.053333 | 41.625000 | PASS |
| 3 | 40.600000 | 42.883333 | PASS |
| 4 | 45.540000 | 45.316667 | PASS |
| 5 | 36.026667 | 33.183333 | PASS |
| 6 | 48.466667 | 48.551675 | PASS |
| 7 | 39.020000 | 42.600000 | PASS |
| 8 | 40.660000 | 39.616667 | PASS |
| 9 | 41.680000 | 39.548327 | PASS |
| 10 | 44.266667 | 41.060000 | PASS |

The sample reports 132-146 provenance template fingerprints per Stage, maximum
single-fingerprint share 2.0%, and 1,350 rows of manual-review debt.  Therefore
its automatic structural verdict is `PASS`, while direct-authoring compliance
is `FAIL_GENERATED_ROWS_REQUIRE_MANUAL_SEMANTIC_REVIEW`.

Canonical write-block reproduction: a one-file `--write` request exited 1 with
`CANONICAL_WRITE_BLOCKED_DIRECT_AUTHORING_FAIL`; the isolated temp workspace
contained zero files afterward.

The read-only materialized-pilot auditor exited 0 over 36 source/corpus pairs
and 5,400 rows.  It found zero exact duplicate/leakage keys, zero hard grammar
findings, zero manual-review debt, and zero repeated cross-record five-word
n-grams among 98,453 record assignments.  It also emitted 155 non-blocking
particle warnings; sampled warnings such as substrings `결과와` and `차이가`
show why these are review candidates rather than automatic errors.  Coverage
was correctly reported as partial with 4,334 reservations missing.

A complete Stage 2 virtual expansion (480 files / 72,000 rows) also passed:
mean 41.495514 versus target 41.625, known grammar findings 0, while retaining
71,400 generated rows as direct-authoring debt.  The later all-Stage virtual
run was deliberately interrupted on the parent time boundary and is not
reported as passed.

Blocker: Guide §10 permits automation for packaging/audit, not corpus prose
authoring.  Actual 650,100-row composition cannot begin through this generator
unless the user approves an explicit Guide §10 exception, or a separate human
authoring/review process changes every draft row to
`manual_semantic_review: true` after substantive review.
