#!/usr/bin/env python3
"""P066 — **wandb 동기화. 기존 로그를 건드리지 않고 사후에 올린다.**

★설계 원칙 셋 (2026-08-20 사용자 지시)
   1. **기존 로그는 그대로 보존한다.** `runs/logs/*.json` 과 `test_result/*.txt` 는
      지금까지처럼 정본이다. wandb 는 **읽기 전용 사본**이다.
   2. ★★**학습 경로를 건드리지 않는다.** `trainer.py` 에 훅을 넣지 않았다 —
      넣으면 **비트 동일성이 깨질 수 있고**, 네트워크 실패가 5시간짜리 런을 죽인다.
      이 도구는 **런이 끝난 뒤** json 을 읽어 올린다. 실패해도 잃는 것이 없다.
   3. ★**API 키를 코드·로그·인쇄 어디에도 남기지 않는다.** **경로만** 읽는다.
      기본 경로 `Z:/TinyLM_private/weave_apikey_only.txt`, 환경변수 `TL_WANDB_KEY_FILE` 로 변경.

★무엇을 올리는가
   config   arch·preset·steps·seed·mlp_group·attn_group·kd·kd_alpha·pool_tokens …
   summary  final·best_val·grad_max·vram_reserved_gb·deploy_mb·runtime_mb·ms_step_median …
   history  json 의 `history`(스텝별 val) 를 스텝 곡선으로
   tables   `experiments.tsv`(실험 메타) · `checkpoints.tsv`(체크포인트 판정)

★기본이 dry-run 이다
   `--push` 를 주지 않으면 **네트워크를 쓰지 않고** 무엇이 올라갈지만 인쇄한다.
   준비 상태 점검은 이걸로 한다.

사용법
   python scripts/wandb_sync.py                       # dry-run, 전체
   python scripts/wandb_sync.py --tag mC_d36_ag4      # dry-run, 하나만
   python scripts/wandb_sync.py --push --project tinylm
   python scripts/wandb_sync.py --check               # 키 파일·패키지만 점검
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "runs" / "logs"
DEFAULT_KEY_FILE = r"Z:/TinyLM_private/weave_apikey_only.txt"

# ★config 로 올릴 필드 — "런을 재현하는 데 필요한 것" 만.
CONFIG_KEYS = [
    "arch", "preset", "data", "tokens", "steps", "seed", "lr", "seq",
    "micro_bs", "accum", "eff_batch", "pool_tokens", "exact_cache",
    "sched", "anneal_end", "decay_frac", "grad_ckpt", "compile",
    "mlp_group", "micro_group", "attn_group", "mlp_split", "n_layers",
    "emb_rank", "sparse34", "bpw", "depth_init", "train_repeat", "repeat_mode",
    "kd", "kd_every", "kd_alpha", "kd_temp", "kd_teacher", "kd_chunk",
    "init_from", "init_from_src", "opt_dtype", "sdpa_gqa", "params",
]
# ★summary 로 올릴 필드 — "판정에 쓰는 것" 만.
SUMMARY_KEYS = [
    "final", "best_val", "best_step", "grad_max", "grad_peak_warmup", "n_skip",
    "deploy_mb", "packed_mb", "runtime_mb", "mem_params", "opt_state_mb",
    "vram_alloc_gb", "vram_reserved_gb", "ms_step_median", "ms_step_spread",
    "wall_sec", "tokens_per_microbatch", "bytes_per_token",
]


def key_file_path():
    return Path(os.environ.get("TL_WANDB_KEY_FILE", DEFAULT_KEY_FILE))


def read_key():
    """★키를 **돌려주기만** 한다. 인쇄·로그·예외 메시지에 절대 싣지 않는다."""
    p = key_file_path()
    if not p.exists():
        raise FileNotFoundError(
            f"wandb 키 파일이 없다: {p}  "
            f"(경로만 확인한다. 파일 내용은 이 도구가 인쇄하지 않는다)")
    k = p.read_text(encoding="utf-8").strip()
    if not k:
        raise ValueError(f"키 파일이 비어 있다: {p}")
    return k


def mask(k):
    """★인쇄용. 길이와 앞뒤 2자만 — 그마저도 `--check` 에서만 쓴다."""
    return f"<{len(k)}자, {k[:2]}…{k[-2:]}>" if len(k) > 6 else "<너무 짧다>"


def banner(s, ch="="):
    print("\n" + ch * 92)
    print(f"  {s}")
    print(ch * 92)


def collect(tag=None):
    """`runs/logs/*.json` 을 읽어 (이름, dict) 목록으로. **tiny_ 스모크는 제외**한다."""
    out = []
    for p in sorted(LOGS.glob("*.json")):
        if p.name.startswith(("tiny_", "lrfind_")):
            continue
        if tag and tag not in p.stem:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:                                  # noqa: BLE001
            print(f"  [건너뜀] {p.name}: 읽기 실패 ({type(e).__name__})")
            continue
        if not isinstance(d, dict) or "steps" not in d:
            continue
        out.append((p.stem, d))
    return out


def payload(name, d):
    cfg = {k: d.get(k) for k in CONFIG_KEYS if k in d}
    summ = {k: d.get(k) for k in SUMMARY_KEYS if d.get(k) is not None}
    hist = d.get("history") or []
    return cfg, summ, hist


def do_check():
    banner("wandb 준비 점검 — 네트워크를 쓰지 않는다", "#")
    p = key_file_path()
    print(f"  키 파일 경로 : {p}")
    print(f"  존재 여부    : {'있다' if p.exists() else '★없다'}")
    if p.exists():
        try:
            k = read_key()
            print(f"  키 형태      : {mask(k)}   ★값은 인쇄하지 않는다")
        except Exception as e:                                  # noqa: BLE001
            print(f"  ★키 읽기 실패: {type(e).__name__}")
    try:
        import wandb                                            # noqa: F401
        print(f"  wandb 패키지 : 설치됨 (v{wandb.__version__})")
    except ImportError:
        print("  wandb 패키지 : ★없다 → `pip install wandb`")
    runs = collect()
    print(f"  올릴 런 수   : {len(runs)}  (tiny_·lrfind_ 제외)")
    for f in ("experiments.tsv", "checkpoints.tsv"):
        print(f"  {f:<16}: {'있다' if (ROOT / f).exists() else '없다'}")
    print("\n  ⚠️ 이 점검은 **파일과 패키지**만 본다. 실제 업로드 권한은 `--push` 로만 확인된다.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="wandb 사후 동기화 (기존 로그 불변)")
    ap.add_argument("--check", action="store_true", help="키 파일·패키지만 점검하고 끝")
    ap.add_argument("--push", action="store_true", help="실제로 올린다(기본은 dry-run)")
    ap.add_argument("--project", default="tinylm")
    ap.add_argument("--entity", default=None)
    ap.add_argument("--tag", default=None, help="런 이름 부분 일치 필터")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    if a.check:
        return do_check()

    runs = collect(a.tag)
    if a.limit:
        runs = runs[:a.limit]
    banner(f"wandb 동기화 — {'PUSH' if a.push else 'DRY-RUN(네트워크 없음)'} · {len(runs)}런", "#")
    if not a.push:
        print("  ★`--push` 가 없으므로 **아무것도 올리지 않는다.** 무엇이 올라갈지만 보여준다.")
    print("  ★기존 `runs/logs/*.json` 과 `test_result/*.txt` 는 **읽기만** 한다. 수정하지 않는다.")

    run_ctx = None
    if a.push:
        try:
            import wandb
        except ImportError:
            print("\n  🚫 wandb 가 설치돼 있지 않다 — `pip install wandb`")
            return 2
        wandb.login(key=read_key())          # ★키는 여기서만 쓰이고 어디에도 안 남는다
        run_ctx = wandb

    for name, d in runs:
        cfg, summ, hist = payload(name, d)
        print(f"\n  --- {name}")
        print(f"      config {len(cfg)}개 · summary {len(summ)}개 · history {len(hist)}점")
        print(f"      final={d.get('final')}  grad_max={d.get('grad_max')}  "
              f"vram={d.get('vram_reserved_gb')}  ms/step={d.get('ms_step_median')}")
        if not a.push:
            continue
        r = run_ctx.init(project=a.project, entity=a.entity, id=name, name=name,
                         config=cfg, resume="allow", reinit=True)
        for i, h in enumerate(hist):
            if isinstance(h, dict):
                run_ctx.log(h, step=h.get("step", i))
        for k, v in summ.items():
            r.summary[k] = v
        r.finish()

    if a.push:
        for f in ("experiments.tsv", "checkpoints.tsv"):
            p = ROOT / f
            if not p.exists():
                continue
            r = run_ctx.init(project=a.project, entity=a.entity,
                             id=f"meta_{p.stem}", name=f"meta_{p.stem}",
                             resume="allow", reinit=True)
            art = run_ctx.Artifact(p.stem, type="metadata")
            art.add_file(str(p))
            r.log_artifact(art)
            r.finish()
            print(f"  [artifact] {f} 업로드")

    print("\n  ⚠️★**wandb 는 정본이 아니다.** 판정 근거는 `test_result/` 문서이고,")
    print("     wandb 는 **찾아보기 편하라고 있는 사본**이다. 둘이 다르면 문서가 옳다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
