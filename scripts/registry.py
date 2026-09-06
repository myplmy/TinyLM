#!/usr/bin/env python3
"""★★실험 파라미터 기록 보존·검색 — **안 C**(TSV 정본 + MD 뷰 + DB 캐시).

승인: 2026-09-05 사용자 지시 (2)A — *"권장안 승인. DB캐시 포함하여 질의/탐색 효율화할 것."*
제안서: [`proposal/done/20260904_실험파라미터-기록보존과-검색-approved.md`]

## 세 층

| 층 | 파일 | 성격 |
|---|---|---|
| 보존 | `runs/logs/*.json` | 🚫**손대지 않는다.** 이미 정본이다 |
| ★**색인** | **`runs/registry.tsv`** (git 추적) | 한 런 = 한 줄. **diff 가 된다** |
| 읽기 | `docs/RUN_REGISTRY.md` | TSV 에서 **생성**한다. 손으로 안 고친다 |
| ★**질의** | `runs/registry.db` (gitignore) | TSV 에서 **재생성**. 없어도 된다 |

🚫**TSV 가 정본인 이유**: MD 표는 **셀 안의 파이프**에서 깨진다(2026-08-31 실사고, 728자 → 455자).
DB 가 정본이 아닌 이유는 **바이너리라 게이트 30종의 diff 검토 밖**이기 때문이다.

## 스키마 (사용자 지정 — 제안서 §3)

| 열 | 뜻 |
|---|---|
| `tag` | 체크포인트 태그(런의 열쇠) |
| `preset` `data` `tokens_dir` | json 파일명을 이루는 셋 |
| `plan_stages` | ★`P084/stage2` 형식, **여러 개면 `;` 로** |
| `log_files` | ★`plan_stage` 와 **쌍**을 이룬다. 같은 순서·같은 개수 |
| `date` | 실험일자(ISO) |
| `steps` `tokens` | 학습 길이 |
| `loss` `bpb` | ★**`steps < 500` 이면 빈칸**(250스텝 프로브·30스텝 스모크) |
| `params` | ★**기본값과 다른 것만** `k=v` 를 `;` 로 |
| `note` | 개명 이력 등 |

★**`steps < 500` 문턱의 근거**: 실측 분포가 {20,30,40,250} vs {763,2289,4578,9156} 로 갈리고
사이에 값이 없다. 🚫**1000 으로 두면 `763` 3런이 빠진다.**

## 사용법

    python scripts/registry.py --backfill        # json 전수 -> TSV (기존 행 보존)
    python scripts/registry.py --render          # TSV -> docs/RUN_REGISTRY.md
    python scripts/registry.py --db              # TSV -> runs/registry.db (질의용)
    python scripts/registry.py --scan            # json 중 TSV 에 없는 것 (게이트)
    python scripts/registry.py --find "cla_group=2 depth=12"      # 질의
    python scripts/registry.py --sql "select tag,loss from runs where loss<3.5"
    python scripts/registry.py --record --tag X --plan-stage P088/stage1 --log f.txt
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "runs" / "logs"
RESULTS = ROOT / "test_result"
TSV = ROOT / "runs" / "registry.tsv"
MD = ROOT / "docs" / "RUN_REGISTRY.md"
DB = ROOT / "runs" / "registry.db"
TAB = chr(9)
NL = chr(10)

FULL_MIN_STEPS = 500      # ★이 아래는 loss·bpb 를 안 적는다(제안서 §3)

COLS = ["tag", "preset", "data", "tokens_dir", "plan_stages", "log_files",
        "date", "steps", "tokens", "loss", "bpb", "params", "note"]

# ★"기본값과 다른 것만" 을 판정하기 위한 기준. 🚫113키를 다 적으면 표를 아무도 안 읽는다.
#   값은 `tinylm/config.py` 의 프리셋 기본과 `cli.py` 의 인자 기본에서 온다.
DEFAULTS = {
    "arch": "tied", "kd": False, "kd_alpha": 0.5, "kd_every": 1, "kd_dynamic": False,
    "kd_temp": 2.0, "kd_teacher": None, "kd_teacher_hf": None, "kd_teacher_infer": False,
    "kd_chunk": 0, "ce_chunk": 0, "lora_rank": 0, "lora_decay": 0.0, "mlp_film": False,
    "mlp_lrm": False, "emb_rank": 0, "micro_group": None, "sparse34": False,
    "opt_dtype": "fp32", "ema": 0.0, "arenas": False, "arena_lambda": 0.0,
    "anneal_shape": "linear", "anneal_end": 0.60, "decay_frac": 0.2, "seed": 1337,
    "sched": "cosine", "grad_ckpt": True, "exact_cache": False, "init_from": False,
    "depth_init": "zip", "cla_group": 1, "cla_edges": True, "attn_group": 1,
    "mlp_group": 1, "train_repeat": 1.0, "repeat_mode": "uniform", "emb_init": None,
    "tokenizer_hf": None, "doc_filter": False, "micro_bs": 8, "accum": 8, "seq": 1024,
    "lr": 1e-3, "optimizer": "adamw", "repeat_kv_reuse": False, "reuse_attn_on_dup": False,
}
# 표에 넣을 값이 아닌 것(측정 결과·환경). params 열에서 뺀다.
NOT_PARAM = {
    "final", "history", "grad_max", "grad_peak_warmup", "n_skip", "best_val", "best_step",
    "minutes", "ms_step", "ms_step_spread", "params", "runtime_mb", "packed_mb", "deploy_mb",
    "bpw", "bpw_ternary", "bpw_convention", "kv_mb", "kv_dim", "kv_entries", "kv_visits",
    "kv_kb_per_token", "kv_dtype_bytes", "kv_seq_len", "bytes_per_token",
    "bytes_per_token_val", "mix_token_frac", "eff_batch", "tokens_per_microbatch",
    "vram_reserved_gb", "vram_alloc_gb", "kd_fwd_steps", "kd_step_ce_mean",
    "kd_step_loss_mean", "kd_step_n", "commit", "dirty", "tag", "preset", "steps",
    "tokens", "data", "pool_tokens", "init_from_src",
}


# ────────────────────────────────────────────────────────────────── TSV I/O
def read_tsv():
    if not TSV.is_file():
        return []
    rows = []
    for i, ln in enumerate(io.open(TSV, encoding="utf-8").read().split(NL)):
        if not ln.strip() or ln.startswith("#"):
            continue
        c = ln.split(TAB)
        if i == 0 and c[0] == "tag":
            continue
        c += [""] * (len(COLS) - len(c))
        rows.append(dict(zip(COLS, c[:len(COLS)])))
    return rows


def write_tsv(rows):
    body = [TAB.join(COLS)]
    for r in sorted(rows, key=lambda r: (r.get("date", ""), r.get("tag", ""))):
        body.append(TAB.join(str(r.get(k, "") or "").replace(TAB, " ") for k in COLS))
    b = (NL.join(body) + NL).encode("utf-8")
    TSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = TSV.with_suffix(".tsv.tmp")
    io.open(tmp, "wb").write(b)
    assert os.path.getsize(tmp) == len(b)          # ★함정 35 — 0바이트 방지
    os.replace(tmp, TSV)
    return len(rows)


# ────────────────────────────────────────────────────────── json -> 한 줄
def stem_parts(stem):
    """`m100s8_ko-en_300M_d12_cla2_r20` -> (preset, data, tokens_dir, tag)"""
    p = stem.split("_")
    if len(p) < 4:
        return stem, "", "", stem
    return p[0], p[1], p[2], "_".join(p[3:])


def row_from_json(path: Path):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    # ★★PM moonshot 런은 `moonshot_result/registry.tsv` 가 정본이다. 일반 레지스트리의
    # scan/backfill/record 에 섞으면 사용자가 요구한 branch 실험 경계가 사라진다.
    if re.search(r"(?:^|_)pm\d{3,}__", str(d.get("tag", "")), re.I):
        return None
    steps = d.get("steps")
    if not steps:
        return None                                  # 학습 런이 아니다
    preset, data, tokens_dir, tag = stem_parts(path.stem)
    full = int(steps) >= FULL_MIN_STEPS
    fin = d.get("final") or {}
    par = []
    for k in sorted(d):
        if k in NOT_PARAM or k.startswith("_"):
            continue
        v = d[k]
        if isinstance(v, (list, dict)):
            continue
        if k in DEFAULTS and v == DEFAULTS[k]:
            continue
        if v in (None, False, "", 0) and k not in DEFAULTS:
            continue
        par.append(f"{k}={v}")
    dt = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    return {
        "tag": tag, "preset": preset, "data": data, "tokens_dir": tokens_dir,
        "plan_stages": "", "log_files": "", "date": dt,
        "steps": steps, "tokens": d.get("tokens", ""),
        "loss": (f"{fin.get('val_loss'):.7f}" if full and fin.get("val_loss") is not None else ""),
        "bpb": (f"{fin.get('bpb'):.6f}" if full and fin.get("bpb") is not None else ""),
        "params": ";".join(par), "note": "",
    }


# ───────────────────────────────────────────── 로그에서 계획번호-단계 붙이기
RUNLOG_NAME = re.compile(r"^\[runlog\].*\bname=(\S+)")
RUNLOG_CMD = re.compile(r"^\[runlog\] cmd=(.*)$")


def harvest_plan_stages():
    """`test_result/*.txt` 안에서 `name=` 과 그 **다음** `cmd=… --tag X` 를 짝짓는다.

    ★한 로그 파일에 여러 팔이 있으므로 **파일 전체가 아니라 블록 단위**로 본다.
    🚫mtime 으로 추측하지 않는다(같은 시각에 두 런이 끝날 수 있다).
    """
    out = {}                                     # tag -> {(plan_stage, logfile)}
    for f in sorted(RESULTS.glob("*.txt")):
        cur = None
        for ln in io.open(f, encoding="utf-8", errors="replace"):
            m = RUNLOG_NAME.match(ln)
            if m:
                cur = m.group(1)
                continue
            m = RUNLOG_CMD.match(ln)
            if m and cur:
                mt = re.search(r"--tag\s+(\S+)", m.group(1))
                if mt and " train " in m.group(1):
                    out.setdefault(mt.group(1), set()).add((_norm_stage(cur), f.name))
    return out


def _norm_stage(name):
    """`P088_stage1_tokens600m` -> `P088/stage1`"""
    m = re.match(r"^(P\d{3,}[A-Za-z]*)_([A-Za-z0-9]+)", name)
    return f"{m.group(1)}/{m.group(2).lower()}" if m else name


# ──────────────────────────────────────────────────────────────── 동작들
MANUAL = ROOT / "runs" / "registry_manual.tsv"


def read_manual():
    """★소급 매핑(제안서 §8 단계3). `runlog` 이전 런은 로그에 `name=` 이 없다.

    `how` 열이 **어떻게 정했는지**를 적는다 — `derived-first-mention` 은
    *"그 태그를 처음 언급한 결과문서"* 라는 뜻이고 🚫**runlog 기록과 같은 급이 아니다.**
    """
    out = {}
    if not MANUAL.is_file():
        return out
    for i, ln in enumerate(io.open(MANUAL, encoding="utf-8").read().split(NL)):
        if not ln.strip() or ln.startswith("#"):
            continue
        c = ln.split(TAB)
        if i == 0 and c[0] == "tag":
            continue
        if len(c) >= 3 and c[2]:
            out[c[0]] = (c[2], c[1], c[3] if len(c) > 3 else "")
    return out


def backfill():
    have = {r["tag"]: r for r in read_tsv()}
    plans = harvest_plan_stages()
    manual = read_manual()
    n_new = n_upd = 0
    for p in sorted(LOGS.glob("*.json")):
        r = row_from_json(p)
        if r is None:
            continue
        pairs = sorted(plans.get(r["tag"], []))
        if pairs:
            r["plan_stages"] = ";".join(a for a, _ in pairs)
            r["log_files"] = ";".join(b for _, b in pairs)
        if not r["plan_stages"] and r["tag"] in manual:
            pl, no, how = manual[r["tag"]]
            r["plan_stages"] = pl
            r["note"] = (f"⚙소급({how}) 결과{no}").strip()
        old = have.get(r["tag"])
        if old is None:
            have[r["tag"]] = r
            n_new += 1
        else:
            # ★손으로 적은 열(plan_stages·log_files·note)은 **비어 있을 때만** 채운다
            for k, v in r.items():
                if k in ("plan_stages", "log_files", "note") and old.get(k):
                    continue
                if str(old.get(k, "")) != str(v):
                    old[k] = v
                    n_upd += 1
    n = write_tsv(list(have.values()))
    unmatched = [r["tag"] for r in have.values() if not r["plan_stages"]]
    print(f"  ✅ 소급 반영 — 총 {n}행 (신규 {n_new} · 갱신 {n_upd})")
    print(f"  ★계획번호가 붙은 런 {n - len(unmatched)}/{n} = {(n-len(unmatched))/max(n,1):.0%}")
    if unmatched:
        print(f"  ⚠️계획번호 미상 {len(unmatched)}개 — `note` 에 손으로 적는다: "
              f"{', '.join(sorted(unmatched)[:8])}{' …' if len(unmatched) > 8 else ''}")
    return 0


def render():
    rows = read_tsv()
    full = [r for r in rows if r["loss"]]
    probe = [r for r in rows if not r["loss"]]
    L = []
    L.append("# 런 레지스트리 — **생성물이다. 손으로 고치지 않는다**")
    L.append("")
    L.append(f"> 🚫**정본은 [`runs/registry.tsv`](../runs/registry.tsv)** 이고 이 문서는 "
             f"`python scripts/registry.py --render` 가 만든다.")
    L.append(f"> 갱신 {datetime.now():%Y-%m-%d %H:%M} · 총 **{len(rows)}행** "
             f"(full-train **{len(full)}** · 프로브/스모크 {len(probe)})")
    L.append("> ★질의는 `python scripts/registry.py --find \"cla_group=2\"` 또는 `--sql`.")
    L.append("")
    L.append("## full-train (steps >= 500) — loss 오름차순")
    L.append("")
    L.append("| tag | preset | steps | tokens | loss | bpb | 계획-단계 | 파라미터(기본값과 다른 것) |")
    L.append("|---|---|---:|---:|---:|---:|---|---|")
    for r in sorted(full, key=lambda r: float(r["loss"])):
        par = r["params"].replace(";", " · ").replace("|", "\\|")
        L.append(f"| `{r['tag']}` | {r['preset']} | {r['steps']} | {r['tokens']} | "
                 f"**{r['loss']}** | {r['bpb']} | {r['plan_stages'].replace(';', ' ')} | {par} |")
    L.append("")
    L.append("## 프로브·스모크 (steps < 500) — ★loss·bpb 는 **일부러 비운다**")
    L.append("")
    L.append("| tag | preset | steps | 계획-단계 |")
    L.append("|---|---|---:|---|")
    for r in sorted(probe, key=lambda r: r["tag"]):
        L.append(f"| `{r['tag']}` | {r['preset']} | {r['steps']} | {r['plan_stages'].replace(';', ' ')} |")
    L.append("")
    b = (NL.join(L) + NL).encode("utf-8")
    tmp = MD.with_suffix(".md.tmp")
    io.open(tmp, "wb").write(b)
    assert os.path.getsize(tmp) == len(b)
    os.replace(tmp, MD)
    print(f"  ✅ 렌더 — {MD.relative_to(ROOT)} ({len(rows)}행 · full {len(full)})")
    return 0


def build_db():
    import sqlite3
    rows = read_tsv()
    if DB.exists():
        DB.unlink()                        # ★캐시다 — 항상 새로 만든다(정본은 TSV)
    con = sqlite3.connect(DB)
    con.execute("create table runs (" + ", ".join(
        f"{c} {'real' if c in ('loss', 'bpb') else 'integer' if c in ('steps', 'tokens') else 'text'}"
        for c in COLS) + ")")
    con.execute("create table params (tag text, key text, value text)")
    for r in rows:
        con.execute(f"insert into runs values ({','.join('?' * len(COLS))})",
                    [(float(r[c]) if r[c] else None) if c in ("loss", "bpb")
                     else (int(r[c]) if r[c] else None) if c in ("steps", "tokens")
                     else r[c] for c in COLS])
        for kv in r["params"].split(";"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                con.execute("insert into params values (?,?,?)", (r["tag"], k, v))
    con.execute("create index i_params on params(key, value)")
    con.execute("create index i_loss on runs(loss)")
    con.commit()
    n = con.execute("select count(*) from runs").fetchone()[0]
    m = con.execute("select count(*) from params").fetchone()[0]
    con.close()
    print(f"  ✅ DB 캐시 — {DB.relative_to(ROOT)} (runs {n}행 · params {m}행 · 인덱스 2개)")
    print("  🚫**정본이 아니다** — gitignore. TSV 가 바뀌면 `--db` 로 다시 만든다.")
    return 0


def scan():
    """json 중 TSV 에 없는 것 (게이트용)."""
    have = {r["tag"] for r in read_tsv()}
    missing = []
    for p in sorted(LOGS.glob("*.json")):
        r = row_from_json(p)
        if r and r["tag"] not in have:
            missing.append(r["tag"])
    if missing:
        print(f"  🚫 TSV 에 없는 런 **{len(missing)}개** — `--backfill` 을 돌린다: "
              f"{', '.join(missing[:10])}{' …' if len(missing) > 10 else ''}")
        return 1
    print(f"  ✅ `runs/logs/*.json` 의 모든 학습 런이 레지스트리에 있다 ({len(have)}행)")
    return 0


def find(expr):
    """`cla_group=2 steps>=4578 loss<3.5` 같은 자유 질의."""
    import sqlite3
    if not DB.exists():
        build_db()
    con = sqlite3.connect(DB)
    where, args = [], []
    for tok in expr.split():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|!=|=|>|<)\s*(.+)$", tok)
        if not m:
            where.append("(tag like ? or params like ?)")
            args += [f"%{tok}%", f"%{tok}%"]
            continue
        k, op, v = m.group(1), m.group(2), m.group(3)
        op = "=" if op == "=" else op
        if k in COLS:
            where.append(f"{k} {op} ?")
            args.append(float(v) if k in ("loss", "bpb") else
                        int(v) if k in ("steps", "tokens") else v)
        else:
            where.append("tag in (select tag from params where key=? and value" + op + "?)")
            args += [k, v]
    q = "select tag, preset, steps, loss, bpb, plan_stages from runs"
    if where:
        q += " where " + " and ".join(where)
    q += " order by loss is null, loss"
    rows = con.execute(q, args).fetchall()
    print(f"  질의: {expr}")
    print(f"  {'tag':<34}{'preset':<10}{'steps':>7}{'loss':>12}{'bpb':>10}  계획-단계")
    print("  " + "-" * 96)
    for t, pr, st, ls, bp, ps in rows:
        print(f"  {t:<34}{pr:<10}{st or 0:>7}"
              f"{(f'{ls:.7f}' if ls else '—'):>12}{(f'{bp:.4f}' if bp else '—'):>10}  {ps}")
    print(f"\n  {len(rows)}행")
    con.close()
    return 0 if rows else 1                 # ★R19 — 0건이면 조용히 성공하지 않는다


def sql(q):
    import sqlite3
    if not DB.exists():
        build_db()
    con = sqlite3.connect(DB)
    cur = con.execute(q)
    names = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchall()
    if names:
        print("  " + " | ".join(names))
        print("  " + "-" * 90)
    for r in rows:
        print("  " + " | ".join("—" if x is None else str(x) for x in r))
    print(f"\n  {len(rows)}행")
    con.close()
    return 0 if rows else 1


def record(tag, plan_stage, log_file, note=""):
    """★`runlog` 가 종료코드 0 일 때 부른다. json 이 아직 없으면 조용히 넘어간다."""
    hits = [p for p in LOGS.glob(f"*_{tag}.json")]
    if not hits:
        return 2
    r = row_from_json(sorted(hits)[-1])
    if r is None:
        return 2
    rows = {x["tag"]: x for x in read_tsv()}
    old = rows.get(tag)
    if old:
        for k, v in r.items():
            if k in ("plan_stages", "log_files", "note"):
                continue
            old[k] = v
        r = old
    ps = [x for x in (r.get("plan_stages") or "").split(";") if x]
    lf = [x for x in (r.get("log_files") or "").split(";") if x]
    if plan_stage and (plan_stage, log_file) not in list(zip(ps, lf)):
        ps.append(plan_stage)
        lf.append(log_file)
    r["plan_stages"] = ";".join(ps)
    r["log_files"] = ";".join(lf)
    if note:
        r["note"] = ((r.get("note") or "") + " " + note).strip()
    rows[tag] = r
    write_tsv(list(rows.values()))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--db", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--find", default=None)
    ap.add_argument("--sql", default=None)
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--plan-stage", default=None)
    ap.add_argument("--log", default=None)
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    if a.record:
        if not a.tag:
            print("  🚫 --record 에는 --tag 가 필요하다.", file=sys.stderr)
            return 2
        return record(a.tag, a.plan_stage or "", a.log or "", a.note)
    if a.backfill:
        rc = backfill()
        render()
        build_db()
        return rc
    if a.render:
        return render()
    if a.db:
        return build_db()
    if a.scan:
        return scan()
    if a.find is not None:
        return find(a.find)
    if a.sql is not None:
        return sql(a.sql)
    return scan()


if __name__ == "__main__":
    sys.exit(main())
