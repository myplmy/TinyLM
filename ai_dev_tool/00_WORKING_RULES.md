# 00 — WORKING RULES (operational, English)

**Read this one every session.** It is the short list. Rationale, evidence and war
stories live in the Korean ledgers (01–08) and `CLAUDE.md`; this file only says
*what to do*. Korean mirror for user review: [`00_작업규약_한글판.md`](00_작업규약_한글판.md)
— same IDs, checked by `scripts/check_rules_sync.py`.

- **`[gate]`** = a script enforces this. You do not have to remember it; you have to
  run `python scripts/check_static_all.py`.
- **`[human]`** = only a person can catch it. These are the ones worth memorising.
- **`[fact]`** = a number you keep re-deriving. Look it up, do not recall it.
- Measured 2026-08-27: the rule corpus is **1,397 substantive lines across 9 files**
  with **1 duplicated line**. ★**Duplication is not the problem — volume is.**
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
  copies + everything else as fp32`. **bpw is not in that formula.** ⚠️The json field
  named `deploy_mb` holds **packed storage**, not resident — the name lies.
- **R06** `[human]` **Resolution is condition-dependent.** no-KD + parent-init 2σ =
  **0.0034**; dense / no-parent = **0.024**; bpb = **0.008**. Always name the ruler used.
  `paired_eval` prints which one it picked.
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
- **R21** `[gate]` After editing code or docs, run `python scripts/check_static_all.py`
  yourself — **16 gates, no torch, no GPU**. Then ask the user for
  `run_smoke_check.bat` if code changed. **Static never replaces dynamic.**
  On Windows prefix with `set PYTHONIOENCODING=utf-8`.

## D. Batches and the queue

- **R22** `[human]` **Build an experiment batch only when it can run today.** If
  implementation is a prerequisite, the design stays in the plan document.
- **R23** `[gate]` Right after writing a batch: `check_batch_flags.py` + `lint_bat.py --fix`.
  The former only checks that a flag **exists in the parser** — follow parser → function
  → behaviour with your eyes.
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
  neither add nor drop items (`ai_dev_tool/02` §9). Handoff §1 carries **only what is new
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
- **R40** `[gate]` In `scripts/`, `import tinylm` **before** `datasets`/`transformers`, or the HF
  cache redirect does not apply and downloads land outside the work folder. `[gate]`
