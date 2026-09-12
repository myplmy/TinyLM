# 00 — CODEX WORKING RULES (operational, English)

> **Last updated**: 2026-09-12 · **Rule counts**: `[gate]` 8 · `[human]` 46 · `[fact]` 3

**Read this one every session.** It is the short list. Rationale, evidence and war
stories live in the Codex-owned ledgers (01–08) and shared project evidence; this file only says
*what to do*. Korean mirror for user review: [`00_작업규약_한글판.md`](00_작업규약_한글판.md)
— same IDs. P2 compared both ID sets read-only. The Codex-only P7 environment aggregate
later passed 20/20; the shared project-wide `scripts/check_static_all.py` remained outside
that environment-only run because it includes protected-data checks.

> **Environment boundary:** [`README.md`](README.md). Codex does not use `.claude/**`,
> `CLAUDE.md`, or root `ai_dev_tool/00–08` as runtime instructions. Root 09 is referenced,
> never copied.

- **`[gate]`** = a script enforces this. You do not have to remember it; you have to
  run `python scripts/check_static_all.py`.
- **`[human]`** = only a person can catch it. These are the ones worth memorising.
- **`[fact]`** = a number you keep re-deriving. Look it up, do not recall it.
- The 2026-08-27 audit of the source rule corpus found **1,397 substantive lines across 9 files**.
  That is a historical diagnostic, not the current file count. ★**Volume, not duplication, was the problem.**
  The fix is this file plus moving checkable rules into gates.

---

## A. Hard boundaries (never negotiable)

- **R01** `[human]` **Never delete a file. Never request delete permission.** Not `rm`,
  not a permission tool. Write what should go in the handoff's *"사용자에게 부탁하는 것"*
  section and stop. `mv` (rename) is fine and the AI does it itself. Rename is
  reversible; deletion is not. (Violated once, 2026-08-14 → D11.)
- **R02** `[human]` **The AI never runs training or GPU code.** It writes batches and
  scripts; the user runs them and returns logs.
- **R03** `[human]` **git is the user's.** The AI proposes a Korean commit title+body.
- **R04** `[human]` **Never write "조치 완료" without a file diff.** And a diff is not
  proof either — declaring bf16 fixed twice on the strength of a diff is confession A4.
  Proof is a gate that failed before the fix and passes after.

## B. Comparison validity — this is where numbers go wrong

- **R05** `[human]` **Resident ≠ storage.** `resident = unique ternary params × 4B × 2
  copies + everything else as fp32`. **bpw is not in that formula.** The json already
  separates them: **`packed_mb` = storage, `runtime_mb` = resident.** ⚠️`deploy_mb` is a
  legacy **alias for `packed_mb`** — the name says deploy, the value is storage. Read
  `runtime_mb`; do not recompute. (Corrected 2026-08-28 — the previous wording told you
  to recompute, which was wrong.)
- **R06** `[human]` **Resolution is FAMILY-dependent and all of it is measured.**
  tied **0.0006** / dense **0.0021** / recursion **0.0018** (2σ, 3 seeds where the
  condition is clean). bpb **0.008**. Outside the measured conditions (KD mixed in, no
  parent init) fall back to **0.024**. ★The single source is **`scripts/_rulers.py`** —
  `paired_eval` and `paired_join` both read it and print which ruler they used.
  🚫The old wording (0.0034 for no-KD + parent-init) is retired: it was one condition,
  not one family, and it was drawn from a single seed pair.
  ★A two-seed estimate is not biased, it is **high-variance** (relative sd ~52% at n=2,
  ~36% at n=3). It came out 2x too big for tied and 2x too small for recursion.
- **R07** `[human]` When writing "동급", write **"실무상 동급, 통계적으로는 유의"** if `|t| > 2`.
- **R08** `[human]` **Compare only across matched pool / tokenizer / steps / grad_ckpt.**
  grad-ckpt drift is measured: **−0.0014** (051), below the 0.0034 ruler but not below
  the 0.008 bpb ruler.
- **R09** `[human]` **Different tokenizers ⇒ only `common_bpb` is valid.** Token-level
  loss and perplexity always favour the larger vocabulary.
- **R10** `[human]` **Judge with `paired_eval`, not the training log's val.** Training val
  is a random-crop sample and flips sign. Read json `grad_max`, not the printed `|g|`.
- **R11** `[human]` **step0 CE is a binary gate only** — "did the transplant land, is it in
  band". Never a size, ranking, or axis-opening predictor (D13).
- **R12** `[human]` **Check `val − train_ce` before judging.** Baselines sit near 0. Over
  **0.3** means training and eval ran different schedules (trap 39) — suspect the
  instrument first. A `--train-repeat` checkpoint must be evaluated with
  `--match-train-repeat`, otherwise you evaluate a function that was never trained.
- **R13** `[human]` **250-step runs measure speed and VRAM only.** Never quality.

## C. Code changes

- **R14** `[gate]` **One concept, one definition.** Every set-membership answer comes from a
  single function, and that function must honour every flag the model honours.
  `check_group_map.py` enumerates preset × arch and catches disagreement.
  (P074 lost four training arms to `mlp_group_index` ignoring `tie_mlp`.)
- **R15** `[gate]` **A new axis needs a smoke arm that turns it ON**, plus an `EXPECT` entry
  in `check_smoke.py` so a dead arm is an error. A recorded json field is not a
  running code path (trap 37). `check_smoke_coverage.py` lists axes batches use that
  smoke never runs.
- **R16** `[human]` **Failures come from new *combinations*, not new features.** Every recent
  code error was two old things meeting for the first time (dense × init-from,
  tying × bf16 storage, existing tool × vocab 151,936). Rules cannot catch these —
  only enumeration can. When you add anything, ask *what has this never been run with*.
- **R17** `[human]` **Count every consumption site before changing a tensor's dtype or shape.**
  Weight tying means one tensor is read at four places (input lookup, input up-proj,
  head up-proj, head logits). Route them through one accessor.
- **R18** `[human]` **A judgement tool has a different shape from the training loop.** A lesson
  written for training must be re-applied to eval by hand (A3: 21.5 h of runs judged
  three times into OOM). Do not build the gate at a size where the defect cannot appear.
- **R19** `[human]` **"Measured 0, exit 0" is the worst failure mode.** Any tool that can
  produce zero measurements must exit non-zero. Paid for twice: `runlog` (031),
  `mem_runtime` (059).
- **R20** `[human]` **Printed value ≠ canonical value** (trap 4). A tool must not print a
  table, map, or number it did not use. `diag_depth_init` printed the role map and
  measured the zip map for a whole session.
- **R21** `[gate]` After editing code or docs, Codex runs `python scripts/check_static_all.py`
  itself. The script output owns the gate count and must use no torch or GPU. Then ask the user for
  `run_smoke_check.bat` if code changed. **Static never replaces dynamic.**
  In PowerShell set `$env:PYTHONIOENCODING='utf-8'`; in `cmd.exe` use `set PYTHONIOENCODING=utf-8`.

## D. Batches and the queue

- **R22** `[human]` **Build an experiment batch only when it can run today.** If
  implementation is a prerequisite, the design stays in the plan document.
- **R23** `[gate]` Right after writing a batch: `check_batch_flags.py` + `lint_bat.py --fix`
  + ★**`dryrun_batch.py <batch>`**. The first only checks that a flag **exists in the
  parser**; the last prints the **effective** condition with preset defaults filled in,
  which is where a missing `--cla-group` cost 3.6 GPU-hours. Still follow parser →
  function → behaviour with your eyes.
  ★**2026-09-02: none of those three catches a wrong flag *contract*.** `--tokenizer-hf`
  exists in both `run100m.py train` (bare folder) and `common_bpb.py` (**TAG=folder**),
  and `dryrun_batch` only reads *training* calls — the one that died was a *judging* call.
  Copying a training command into a judging command cost **9.2 hours of headline result**.
  `lint_bat` rule 24 is the net for that. It found the same defect in a batch that had
  not run yet. **When a flag name is shared across tools, read the target tool's parser.**
- **R24** `[human]` `.bat` files: pure ASCII, CRLF, no `%VAR%` immediate expansion, no `chcp`,
  escape `<`, `>`, `|`. `--tag` on every variant run or it overwrites the canonical one.
- **R25** `[human]` Sweeps use `if errorlevel 1 echo [WARN] ... - continuing`. `goto ERROR`
  only for genuine prerequisites (prepare, teacher training). This has saved a whole
  night's queue twice.
- **R26** `[gate]` New batch ⇒ **one row in `experiments.tsv`**, then `queue_menu.py --audit`.
- **R27** `[human]` **Queue instructions go by name, never by id** (trap 36) — ids shift when
  the table gains a row. If an id is needed, let `queue_menu.py --ids <batch>` compute it.
- **R28** `[human]` Experiments must be independent: separate tags, separate cache dirs,
  new flags default **off and bit-identical**. Reason: one failure must not take the
  others down, and the user must be able to run the queue alone.

## E. Documents

- **R29** `[gate]` **Before writing a result document run `python scripts/new_result.py <log>`.**
  Exit 3 = a document already exists for that number → append a section, do not create
  a file. **The number is the experiment-group number, and the log filename's first
  three digits declare it.** Duplicates are now an error (031 was split for 20 days).
- **R30** `[human]` **log-to-result is a chain**: result doc → plan document body →
  `실험목록.md` → `실험계획목록.md` → `EXPERIMENT_BASELINES` → the live review.
- **R31** `[human]` **Cite only what you actually opened** (arXiv id / DOI). Abstract-only
  goes in an explicit 미확인 list and is not summarised.
- **R32** `[human]` **Do not copy a claim into other documents before it is verified** (A11:
  the P072 U2 number reached three documents before it was checked).
- **R33** `[gate]` A derived copy of canonical numbers must be machine-checked against the
  source (`plot_results.py --verify`). A comment saying "this is a copy" is not a fix (A7).
- **R34** `[human]` Write a handoff at ~70 % context and at the end of every work unit.
  Handoff §3 is **canonical** for user requests; the chat report is its summary and may
  neither add nor drop items (`ai_dev_tool/Codex/02` §9). Handoff §1 carries **only what is new
  since the previous edition**.
- **R35** `[human]` **The "사용자에게 부탁하는 것" section is always present**, even if it says
  "요청할 것이 없다", and always includes the `-done` batch deletion verdict.
- **R36** `[human]` **Deferring anything requires prerequisites written as numbers** — what
  must be true first, what it costs, and why not now (D1). A bare ⏸ is not a decision.

## F. Standing facts you keep re-deriving

- **R37** `[fact]` Training tokens = `steps × micro_bs × accum × seq`. `--tokens` is cache size.
  300M baseline = `--micro-bs 8 --accum 16` (effective batch 131 K).
- **R38** `[fact]` `M = micro_bs × seq` drives speed and VRAM together. Knee **M = 8,192** —
  **and that is a vocab-32,768 number, not a constant** (A3).
- **R39** `[fact]` Data pool ≥ 2× training tokens (`--pool-tokens 600M --exact-cache`).
- ★**R41** `[human]` **Answer every numbered item the user gave — all of them, in full.**
  Never silently drop, merge, shorten, or defer one. If an item cannot be done, say so
  **as its own item**, with the reason and what would unblock it (R36 applies: numbers, not
  adjectives). ★Evidence it was needed: on 2026-09-03 the repeat-exposure axis was **read**
  in the source doc, carried into a proposal's alternatives, and then **dropped** from both
  the REVIEW4 draft and `03_knowledge_quality.md` — the user had to ask why.
  ⚠️This also governs the WIP ledger: **copy the instruction verbatim, do not summarize it.**

- **R40** `[gate]` In `scripts/`, `import tinylm` **before** `datasets`/`transformers`, or the HF
  cache redirect does not apply and downloads land outside the work folder. `[gate]`

- ★**R42** `[human]` **A rule written in more places does not get followed more.** In the
  historical Claude environment, the "use a dedicated edit tool, not a shell heredoc" rule lived in three places and the
  session-start prompt) and the accident still happened **15 times**. When a rule keeps
  being broken, the fix is a **mechanism outside the agent's choice** (a gate, a hook),
  never a fourth copy of the text.
- ★**R43** `[human]` **Say what a metric measures before ranking with it.** full-val and
  정답CE are **pass/fail gates**; likelihood accuracy is the **ranking** metric, and only
  on a task with the power to resolve the comparison. Three tasks gave three different
  CE orderings, and the full-val winner was at chance on our intelligence task.
- ★**R44** `[human]` **A benchmark that is not yet validated is quoted with that caveat.**
  Our held-out is the only high-sensitivity instrument we have and we do not yet know why
  depth reverses on it. Never pick a deployment model on it alone.
- ★★**R45** `[human]` **Never judge an architecture from a single seed's McNemar z.**
  The instrument's own seed noise crosses the significance threshold: two checkpoints of
  the SAME architecture differed by +6.67pp, z +2.21. Say how many seeds a held-out
  number rests on, every time.
- ★★**R46** `[human]` **Never mix training-log val and deterministic full-val in one table.**
  The same checkpoint reads 3.5139 and 3.5389 — a bias of +0.025, which is 10.4x the
  norecur ruler. If both must appear, put the scale in the column name.
- ★**R47** `[human]` **Rank with `gold_margin`, gate with `gold_ce`.** Measured over six
  checkpoints: Spearman rho against accuracy is **+0.943** for the margin and **−0.371**
  for gold CE — the accuracy leader had the worst CE.
- ★**R48** `[human]` **Say whether a residency number is a formula or a measurement.**
  Only the six shapes in baselines B.26.1 are measured; everything else is still the formula.
- ★★**R49** `[human]` **A quality gate must not delete a Pareto candidate.** The objective
  is (residency, intelligence, speed). Label each tier pass/fail and let Pareto decide.
  Only two things stay mandatory — contamination and degeneracy — because they make the
  measurement invalid, not merely worse.
- ★★**R50** `[human]` **Write down which sections of a paper you read before claiming you
  implemented it.** mlp-lrm measured the scalar triple of equation 2 while the paper's
  contribution is the vector multiplier of equation 3, and two of our three duplicated
  existing parameters. Log every paper-referenced implementation in [root 09](../09_구현검증_필요목록.md).

- ★★**R51** `[human]` Attach the **fixed axis** to every statement that A beats B. Residency-
  fixed and speed-fixed comparisons can reverse recursion versus depth; a ranking without its fixed task,
  budget, or latency axis is not a decision.
- ★**R52** `[human]` Never mix training-log val values with deterministic full-val values.
  A ranking may be reused only where order preservation was measured; never turn the observed offset into
  a correction constant.
- ★**R53** `[human]` Never declare a deployment winner from formula-only (`⚙`) residency or
  speed. The candidate shape needs user-authorized `mem_runtime` and `bench_infer` measurements; otherwise
  label it a candidate and keep the dynamic evidence `NOT_RUN`.
- ★★**R54** `[human]` Hyperparameter optima depend on run length. A short probe says whether
  an axis opens; the full-run scale must measure at least the two neighbouring settings before fixing a value.
- ★★**R55** `[human]` Never write "matches the paper" without the paper copy. If only an
  equation was checked, say "equation only" and link the required implementation audit in root 09.
- ★★**R56** `[human]` For held-out v2.8 and later, pairwise model judgement uses relation-family
  resampling confidence intervals. Item-independent z and exact McNemar may be printed but do not decide the pair.
- ★★**R57** `[human]` Every threshold carries the instrument conditions that established it,
  including checkpoint count, dataset version, and resampling unit. If conditions differ, the tool and report defer judgement.
