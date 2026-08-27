#!/usr/bin/env python3
"""스모크 결과 검증 — 신규 계측 필드가 실제로 기록됐는지 json 으로 확인한다.

왜: 필드를 추가해놓고 "기록되겠지" 하고 긴 런을 돌린 뒤에야 비어 있는 걸 발견하면
    그 GPU 시간이 통째로 낭비된다. 스모크(수 분)로 먼저 계약을 검증한다.
    (P021B 에서 nvidia-smi VRAM 을 사람이 적기로 했다가 통째로 빠뜨린 것이 계기)

검사
  1. 필수 필드 존재 — seed·micro_bs·accum·pool_tokens·mlp_group·grad_ckpt·deploy_mb·
     vram_reserved_gb·tokens_per_microbatch ...
  2. 값 정합 — eff_batch == micro_bs*accum*seq, tokens == steps*eff_batch,
     tokens_per_microbatch == micro_bs*seq, deploy_mb == parts 합
  3. 플래그 반영 — --seed/--sparse34/--anneal-end 가 실제로 json 에 반영됐는지
  4. VRAM 이 0 이 아닌지(cuda 런일 때)

사용법
  python scripts/check_smoke.py                 # tiny_synthetic_* 전부
  python scripts/check_smoke.py --tag sm_seed
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "runs" / "logs"

REQUIRED = ["seed", "micro_bs", "accum", "eff_batch", "pool_tokens", "exact_cache",
            "mlp_group", "grad_ckpt", "kd_teacher", "init_from_src", "anneal_end",
            "decay_frac", "deploy_mb", "mem_parts_mb", "mem_params",
            "vram_alloc_gb", "vram_reserved_gb", "tokens_per_microbatch",
            "sparse34", "bpw", "grad_max", "grad_peak_warmup",
            # ★2026-08-13 추가 — 신규 축이 json 에 안 실리면 결과문서를 쓸 수 없다.
            #   계약을 늦게 갱신하면 **긴 런을 돌리고 나서** 필드가 없는 것을 안다.
            "ms_step_median", "ms_step_spread",        # T-1 계측
            "sdpa_gqa", "kd_chunk",                    # F-1 / T-2
            "depth_init", "n_layers",                  # P049
            "attn_group", "train_repeat", "mlp_split", "repeat_mode",  # P057 / P049B
            "kd_alpha", "kd_temp",                     # ★P055(2026-08-20) — 한 번도 안 실렸다
            "wq_dtype", "emb_chunk",
            "reuse_attn_on_dup",                       # ★P049 §17.3(2026-08-22)
            # ★★2026-08-23 (함정 37) — 이 둘은 **공통 경로에 들어간 신규 축**인데
            #   계약에도 팔에도 없었다. `--cla-group` 은 P073(1.8h)이 통째로 걸려 있고
            #   `--ce-chunk` 는 무KD + `--no-ckpt` 조합에서 실제로 쓰인다.
            "cla_group", "ce_chunk",
            "emb_init",                                # ★자백 A13(2026-08-27) — 임베딩 초기화 갈래
            "tokenizer_hf", "kd_teacher_hf", "teacher_dtype", "vocab_size",  # ★P067
                             # ★P068 A1 / P034 단계5 (2026-08-22)
            "save_every"]                              # P058


def check(name, d, expect=None):
    errs, warns, oks = [], [], []

    # 1. 필드 존재 (None 허용 필드는 키 존재만 확인)
    # ★2026-08-22 — `kd_alpha`·`kd_temp` 는 **무KD 런에서 정당하게 None** 이다.
    #   지난 세션에 REQUIRED 에만 넣고 nullable 에 안 넣어서 **무KD 팔 7개가 전부 에러**였다.
    #   ⚠️필드를 필수로 만들 때는 **"언제 None 이 정상인가" 를 같이 정한다**(함정 34 계열).
    nullable = {"pool_tokens", "kd_teacher", "init_from_src", "kd_alpha", "kd_temp", "tokenizer_hf", "kd_teacher_hf"}
    for k in REQUIRED:
        if k not in d:
            errs.append(f"필드 누락: {k}")
        elif d[k] is None and k not in nullable:
            errs.append(f"필드가 None: {k}")
    if not errs:
        oks.append(f"필수 필드 {len(REQUIRED)}개 모두 존재")

    # 2. 정합성
    if all(k in d for k in ("micro_bs", "accum", "seq", "eff_batch")):
        want = d["micro_bs"] * d["accum"] * d["seq"]
        (oks if d["eff_batch"] == want else errs).append(
            f"eff_batch {d['eff_batch']} == mb*accum*seq {want}")
    if all(k in d for k in ("steps", "eff_batch", "tokens")):
        want = d["steps"] * d["eff_batch"]
        (oks if d["tokens"] == want else errs).append(
            f"tokens {d['tokens']} == steps*eff_batch {want}")
    if all(k in d for k in ("micro_bs", "seq", "tokens_per_microbatch")):
        want = d["micro_bs"] * d["seq"]
        (oks if d["tokens_per_microbatch"] == want else errs).append(
            f"M(tokens_per_microbatch) {d.get('tokens_per_microbatch')} == mb*seq {want}")
    if "mem_parts_mb" in d and d.get("deploy_mb"):
        tot = sum(d["mem_parts_mb"].values())
        (oks if abs(tot - d["deploy_mb"]) < 1e-6 else errs).append(
            f"deploy_mb {d['deploy_mb']:.4f} == parts 합 {tot:.4f}")

    # 3. VRAM
    if d.get("vram_reserved_gb") is not None:
        v = d["vram_reserved_gb"]
        if v <= 0:
            errs.append(f"vram_reserved_gb 가 {v} (0 이하)")
        else:
            oks.append(f"VRAM peak reserved {v:.3f}GB (alloc {d.get('vram_alloc_gb', 0):.3f}GB)")
    else:
        warns.append("VRAM 미기록 — CPU 런이면 정상, CUDA 런이면 버그")

    # 4. 기대값(플래그가 반영됐는지)
    for k, want in (expect or {}).items():
        got = d.get(k)
        (oks if got == want else errs).append(f"{k} = {got!r} (기대 {want!r})")

    mark = "FAIL" if errs else ("WARN" if warns else "OK")
    print(f"\n=== {name}  [{mark}]")
    for m in errs:
        print(f"  [E] {m}")
    for m in warns:
        print(f"  [W] {m}")
    for m in oks:
        print(f"  [ok] {m}")
    return len(errs)


EXPECT = {   # 태그 접미사 -> 그 런이 반드시 만족해야 하는 값
    "sm_base":   {"seed": 1337, "sparse34": False, "anneal_end": 0.60, "grad_ckpt": True},
    "sm_seed":   {"seed": 4242},
    "sm_s34":    {"sparse34": True, "bpw": 1.25},
    "sm_sched":  {"anneal_end": 0.80, "sched": "wsd", "decay_frac": 0.2},
    "sm_nockpt": {"grad_ckpt": False},
    "sm_kd":     {"kd": True, "init_from": True, "kd_every": 4, "kd_alpha": 0.5},
    # ★2026-08-14 추가 (계측함정 37) — P057·P061 은 **구성 경로 자체가 한 번도 안 돌았다.**
    #   `attn_group=1`·`mlp_split=()` 만 스모크에 있었기 때문에 `transformer.py` 의
    #   `build_attention` 미import 가 **스모크 0에러를 통과**하고 실험 로그(044)에서 죽었다.
    #   이 두 줄은 "필드가 실렸는가" 뿐 아니라 **그 경로로 모델이 지어지는가**를 산다.
    "sm_ag":     {"attn_group": 2, "init_from": True},
    "sm_split":  {"mlp_split": [1], "init_from": True},
    # ★2026-08-22 (함정 37) — `_wq` bf16 저장은 **새 코드 경로**다. 필드만 넣으면 안 돈다.
    "sm_wqbf16": {"wq_dtype": "bf16", "init_from": True},
    # ★★2026-08-22 (함정 37) — 아래 둘은 **학습 경로를 바꾸는 축**이다.
    #   `reuse_attn_on_dup` 은 `train_repeat != 1.0` 일 때만 살아 있으므로 **둘을 함께 켠 팔**이어야
    #   한다. 하나만 켜면 코드가 안 돌고 필드만 실린다 — 044 가 정확히 그 사고였다.
    "sm_reuseattn": {"train_repeat": 2.0, "reuse_attn_on_dup": True, "init_from": True},
    "sm_inplace":   {"train_repeat": 2.0, "repeat_mode": "inplace", "init_from": True},
    # ★★2026-08-23 (함정 37, 재발 조건 차단) — `--cla-group` 은 2026-08-22 에 만든 축인데
    #   스모크 팔이 없어 **단 한 번도 실행되지 않은 채** 0에러를 찍고 있었다.
    #   `cla_group` 은 **모델 생성 전에** 개입하므로 기본값 팔로는 그 경로가 안 돈다.
    "sm_cla1":      {"cla_group": 1, "init_from": True},
    "sm_cechunk":   {"ce_chunk": 256},
    # ★★2026-08-27 (함정 37 · 함정 18) — **dense 학생 + 부모초기화.**
    #   `--arch dense --init-from` 조합이 이 저장소에 한 번도 없었다 — dense 는 늘
    #   scratch 부모였다. 그래서 `mlp_group_index` 가 `tie_mlp` 를 안 보는 버그가
    #   **모든 dense 프리셋에서** 잠자다가 P074 단계1 의 학습 팔 네 개를 전부 죽였다.
    #   정적 게이트 14(`check_group_map.py`)가 프리셋 전수로 같은 것을 보지만,
    #   **정적은 동적을 대체하지 않는다** — 이 팔은 그 경로가 실제로 도는지를 산다.
    "sm_denseinit": {"arch": "dense", "init_from": True, "depth_init": "role",
                     "mlp_group": 1, "grad_ckpt": False, "ce_chunk": 256},
    # ★2026-08-27 — dense x 재귀. P074 단계2 의 E3 팔이 쓰는 조합이고,
    #   재귀는 여태 tied 에서만 돌았다. 게이트 15 가 배치 작성 당일 지적했다.
    "sm_denserep": {"arch": "dense", "train_repeat": 2.0, "init_from": True},
}


def main():
    ap = argparse.ArgumentParser(description="스모크 결과 계측필드 검증")
    ap.add_argument("--tag")
    a = ap.parse_args()
    files = sorted(LOGS.glob(f"*{a.tag}.json")) if a.tag else sorted(LOGS.glob("tiny_*sm_*.json"))
    if not files:
        print(f"[!] 검사할 스모크 로그가 없습니다({LOGS}). 먼저 run_smoke.bat 을 돌리세요.")
        return 1
    total = 0
    seen_tags = set()
    for p in files:
        d = json.loads(p.read_text())
        exp = next((v for k, v in EXPECT.items() if p.stem.endswith(k)), None)
        seen_tags.update(k for k in EXPECT if p.stem.endswith(k))
        total += check(p.stem, d, exp)
    # ★2026-08-14 (계측함정 37) — **팔이 죽으면 json 이 아예 안 생긴다.**
    #   종전 로직은 `glob` 한 것만 돌았으므로 **죽은 팔이 조용히 사라졌다** — 결과 044 가
    #   지불한 "조용한 무동작" 과 정확히 같은 형태다. 기대 태그가 통째로 없으면 **에러**로 센다.
    if not a.tag:
        for k in EXPECT:
            if k not in seen_tags:
                print(f"\n=== {k}  [FAIL]\n  [E] 이 태그의 json 이 **없다** — 그 팔이 죽었거나 "
                      f"tool_smoke.bat 에서 빠졌다. 로그의 `[WARN] {k} failed` 줄을 볼 것")
                total += 1
    print(f"\n{'='*60}\n총 에러 {total}건 — 0 이면 계측 계약이 지켜지고 있습니다.")
    print("주의: 이 검사는 '필드가 기록되는가'만 본다. 값이 물리적으로 옳은지(예: VRAM 절대값)는")
    print("      실제 장기 런과 nvidia-smi 로 1회 대조해야 한다.")
    return total


if __name__ == "__main__":
    sys.exit(main())
