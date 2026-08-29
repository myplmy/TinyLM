#!/usr/bin/env python3
"""P030 추론 속도 벤치 — **CPU/GPU tok/s 와 TTFT**. 프로젝트 타깃(저사양 CPU)의 첫 측정.

★왜: 지금까지 측정한 것은 전부 **GPU 학습 속도**(결과 007·P021B·010)다.
   `CLAUDE.md` 첫 줄이 "저사양 CPU·엣지" 인데 **CPU 추론은 0회 측정**했다.
   즉 30.9MB → 11.7MB 로 줄인 것이 실제로 무슨 이득인지 아직 모른다.

★2026-07-31 갱신 (P030 단계1 반영) — 결과 014 는 이 두 결함으로 **무효**였다
   (1) `load_model` 이 삼진화를 고정하지 않아 **매 forward 재양자화**했다(CPU 시간의 ~79%).
       → `freeze_quant()` 로 1회만 계산. sparse34 가 dense 보다 느려 보인 원인이 이것이다.
   (2) **KV 캐시가 없어** 매 토큰 전체 시퀀스를 재계산했다(O(T²)).
       → `use_cache=True` 가 기본. `--no-cache` 로 옛 경로와 대조할 수 있다.
   여전히 남는 한계: 삼진 가중치는 추론 시 **dequant 후 fp/bf16 GEMM** 이라
   저장 MB 는 "저장" 크기다. **실행시 메모리는 P034 가 따로 잰다.**

★2026-07-31 2차 수정 — **표의 MB 가 하드코딩이었다**
   `DEFAULT_MODELS` 에 30.9 / 14.9 / 11.7 이 **리터럴로 박혀** 있었다. 그래서
     · 같은 배치 안에서 이 스크립트는 30.9/14.9/11.7 을, `mem_runtime.py` 는
       27.1/13.1/12.4 를 찍어 **한 로그에 두 개의 진실**이 남았고
     · `--models` 를 주면 mb=0.0 이 되어 비율 절이 통째로 사라졌으며
     · 그 값들이 **2026-07-31 이전 구 규약**이라 회계 통일(안 B)과 어긋났다.
   → 이제 **로드한 모델의 `mem_report_all()` 에서 계산**한다(`CLAUDE.md` 파라미터
     단일 소스 규약). 저장(packed)·상주(runtime)를 **둘 다** 찍는다 — 결과 016 이
     "속도는 저장이 아니라 상주를 따라갈 것"이라고 예측했으므로 둘 다 있어야 읽힌다.

사용법
  python scripts/bench_infer.py                                   # 기본 3모델, CPU+GPU
  python scripts/bench_infer.py --device cpu --threads 1 2 4 8     # 스레드 스윕
  python scripts/bench_infer.py --models mA_g4s34_k4 --max-new 32
"""
from __future__ import annotations
import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ★MB 를 여기 적지 않는다 — 모델을 로드한 뒤 mem_report_all() 로 계산한다.
DEFAULT_MODELS = [
    ("p6d", "dense"),
    ("mC_g8_k4", "tied"),
    ("mA_g4s34_k4", "tied"),
]
PROMPT = "대한민국의 수도 서울은"          # 학습 분포 안. 길이는 --prompt-tokens 로 패딩


# ★★2026-08-29 (사용자 지적) — **CPU 측정이 다른 프로세스에 오염됐을 수 있다.**
#
#   결과 014 §12 의 배포경로 수(12.50 tok/s 등)는 **Windows 데스크톱에서 잰 것**이고,
#   그 사이에 다른 프로그램이 코어를 쓰고 있었는지 **우리는 모른다.** 재현 불가능한 측정이
#   결과문서에 들어가면 그 뒤 모든 판단이 그 위에 쌓인다.
#
#   → **측정 창(window) 동안의 시스템 CPU 사용률과 우리 프로세스 사용률을 함께 기록**한다.
#     `외부 부하 = 시스템 - 우리` 가 임계를 넘으면 **그 반복을 버리고 다시 잰다**(최대 재시도).
#     ⚠️`psutil` 이 없으면 **조용히 통과시키지 않고 경고를 인쇄**한다 — 계측함정 4.
def _cpu_probe():
    """(psutil, 프로세스핸들) 또는 (None, None)."""
    try:
        import psutil
        return psutil, psutil.Process()
    except Exception:                                        # noqa: BLE001
        return None, None


# ★★2026-08-29 정정 (사용자 지적) — **한계치의 단위가 지표의 단위와 달랐다**(계측함정 1 계열).
#
#   초판은 `ext` 를 **"코어 1개 기준 백분율의 합"**(16 논리코어 만재 = 1600)으로 냈는데
#   배치는 `--cpu-ext-limit 25` 를 **"머신의 25%"** 라는 뜻으로 줬다.
#   그 눈금에서 25 는 **머신의 1.6%** 이고, 유휴 Windows 데스크톱도 그 아래로 안 내려간다.
#   → 사용자 실측: 작업관리자 **6~12%** 인데 도구는 **ext 150~250%** 를 찍고 매 반복을 재측정했다.
#
#   ★조치 셋
#     1. **눈금을 작업관리자와 같은 시스템 전체 %(0~100)** 로 통일한다.
#     2. ★**한계를 넘어도 런을 막지 않는다** — 기본 재측정 0회. `ext` 를 **평균/중위/최대로 기록**하고
#        한계 초과는 **행에 표시만** 한다. 재측정은 `--cpu-ext-retry N` 으로 **명시적으로** 켠다.
#     3. **코어 고정(affinity)을 하지 않는다** — OS 스케줄러가 배정하는 대로 둔다(사용자 지시).
#        대신 **논리/물리 코어 수와 부하 분포**를 인쇄해 무엇을 쟀는지 남긴다.
class _CpuWatch:
    """측정 창 동안의 시스템/자기 CPU 사용률. `psutil` 이 없으면 전부 None 이다.

    ★**모든 값의 눈금 = 시스템 전체 %(0~100)** — 작업관리자와 같은 눈금이다."""

    def __init__(self):
        self.ps, self.proc = _cpu_probe()
        self.n_cpu = (self.ps.cpu_count() if self.ps else None)            # 논리
        self.n_phys = (self.ps.cpu_count(logical=False) if self.ps else None)
        self.busy_cores = 0.0        # 마지막 창에서 50% 넘게 쓴 논리코어 수

    def start(self):
        if not self.ps:
            return
        self.ps.cpu_percent(None, percpu=True)               # 기준점 리셋
        self.proc.cpu_percent(None)

    def stop(self):
        """(시스템%, 우리%, 외부%) — 전부 **시스템 전체 기준 %(0~100)**."""
        if not self.ps:
            return None, None, None
        per = self.ps.cpu_percent(None, percpu=True) or [0.0]
        self.busy_cores = sum(1 for c in per if c >= 50.0)
        sysp = sum(per) / len(per)                           # 0~100
        selfp = self.proc.cpu_percent(None) / (self.n_cpu or 1)   # 0~100 으로 환산
        return sysp, selfp, max(0.0, sysp - selfp)


def bench_one(model, cfg, tok, prompt, max_new, device, reps, use_cache=True,
              watch=None, ext_limit=None, max_retry=0):
    """(tok/s, TTFT_ms, 부하정보) 를 reps 회 재서 중위값. 첫 회는 warmup 으로 버린다.

    `watch` 가 있으면 반복마다 외부 CPU 부하를 **시스템 전체 %(0~100)** 로 재서 기록한다.
    ★**기본은 기록만 한다**(`max_retry=0`) — 🚫**한계를 넘어도 런을 막지 않는다**(2026-08-29 사용자 지시).
    `max_retry ^> 0` 이면 한계 초과 반복을 그만큼 다시 재고, 그래도 넘으면 **오염 표시와 함께 채택**한다
    — 🚫조용히 버리면 측정이 0건이 되고 그건 결과 031·059 가 지불한 실패 양식이다.
    """
    import torch
    from tinylm.infer.generate import sample
    rates, ttfts = [], []
    ext_seen, sys_seen, busy_seen, dirty = [], [], [], 0
    r, tries = 0, 0
    while r <= reps:
        if watch:
            watch.start()
        # TTFT: 프롬프트 1회 forward
        ids = tok.encode(prompt).ids
        x = torch.tensor([ids], dtype=torch.long, device=device)
        if device == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        with torch.no_grad():
            dev_t = device if isinstance(device, str) else device.type
            with torch.autocast(dev_t, dtype=torch.bfloat16, enabled=(dev_t == "cuda")):
                _ = model(x[:, -cfg.max_seq_len:])
        if device == "cuda":
            torch.cuda.synchronize()
        ttft = (time.perf_counter() - t0) * 1000

        if device == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        _ = sample(model, cfg, tok, prompt, max_new=max_new, temperature=0.7,
                   top_k=40, device=device, use_cache=use_cache,
                   stop_at_eos=False)      # ★속도 측정은 항상 max_new 토큰을 다 생성해야 공정
        if device == "cuda":
            torch.cuda.synchronize()
        el = time.perf_counter() - t0

        _sys, _self, _ext = (watch.stop() if watch else (None, None, None))
        if r > 0 and _ext is not None:
            ext_seen.append(_ext)
            sys_seen.append(_sys)
            busy_seen.append(getattr(watch, "busy_cores", 0.0))
            if ext_limit is not None and _ext > ext_limit and tries < max_retry:
                tries += 1
                print(f"      [cpu-watch] 외부 부하 {_ext:.1f}% ^> 한계 {ext_limit:.1f}% "
                      f"(시스템 전체 기준) — 이 반복을 버리고 다시 잰다({tries}/{max_retry})")
                time.sleep(2.0)
                ext_seen.pop(); sys_seen.pop(); busy_seen.pop()
                continue                   # r 을 안 올린다 = 같은 반복 재측정
            if ext_limit is not None and _ext > ext_limit:
                dirty += 1

        if r == 0:
            r += 1
            continue                       # warmup 버림
        rates.append(max_new / el)
        ttfts.append(ttft)
        r += 1
        tries = 0
    info = {}
    if ext_seen:
        info = {"ext_med": statistics.median(ext_seen),
                "ext_mean": statistics.fmean(ext_seen),
                "ext_max": max(ext_seen),
                "sys_mean": statistics.fmean(sys_seen) if sys_seen else None,
                "busy_max": max(busy_seen) if busy_seen else None,
                "n_win": len(ext_seen), "dirty": dirty}
    return statistics.median(rates), statistics.median(ttfts), info


def main():
    ap = argparse.ArgumentParser(description="P030 추론 속도 벤치")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--device", nargs="*", default=["cuda", "cpu"])
    ap.add_argument("--threads", nargs="*", type=int, default=[0],
                    help="CPU 스레드 수(0=torch 기본). 엣지는 코어가 적으니 1 이 가장 현실적")
    ap.add_argument("--max-new", type=int, default=128,
                    help="KV 캐시 구현 후 기본 128(캐시 이득은 길수록 커진다)")
    ap.add_argument("--no-cache", action="store_true",
                    help="KV 캐시 off. 결과 014 조건 재현용 대조군")
    ap.add_argument("--both-cache", action="store_true",
                    help="캐시 on/off 를 같은 표에 나란히 측정(캐시 이득 배수를 직접 본다)")
    ap.add_argument("--check-cache", action="store_true",
                    help="먼저 캐시 유/무 그리디 출력 일치를 검증한다(불일치면 중단)")
    ap.add_argument("--reps", type=int, default=3, help="반복(중위값). Windows 는 노이즈가 크다")
    ap.add_argument("--cpu-watch", action="store_true",
                    help="★측정 창의 시스템/자기 CPU 사용률을 함께 기록한다(psutil 필요)")
    ap.add_argument("--cpu-ext-limit", type=float, default=None,
                    help="★외부 CPU 부하 한계 — **시스템 전체 %%(0~100, 작업관리자와 같은 눈금)**. "
                         "🚫**넘어도 런을 막지 않는다**(2026-08-29 정정). 그 행에 표시만 한다. "
                         "예: 15 (--cpu-watch 와 함께 쓴다)")
    ap.add_argument("--cpu-ext-retry", type=int, default=0,
                    help="★한계 초과 반복을 몇 번까지 다시 잴지(기본 **0 = 재측정 안 함**). "
                         "🚫1 이상을 주면 런이 최대 (1+N)배 길어진다")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--preset", default="m100")
    ap.add_argument("--drop-latent", action="store_true",
                    help="P034 단계2 — latent 해제 상태로 잰다. 상주가 절반이면 속도가 따라오는가")
    ap.add_argument("--int8-store", action="store_true",
                    help="P034 단계3 — int8 저장. **느려질 것으로 예상**(forward 마다 되돌린다)")
    ap.add_argument("--unpack-cache", action="store_true",
                    help="P034 단계3C — int8 언팩을 **유니크 모듈당 1회**로. 타잉 모델만 이득이고 "
                         "**dense 는 안 변해야 한다(대조군)**. --int8-store 와 함께 쓴다")
    ap.add_argument("--infer-repeat", type=float, default=1.0,
                    help="(P030 단계4) middle 통과 배수. **층 수만 바꾸고 파라미터는 고정**한다 — "
                         "결과 016 §10.4 의 '속도는 파라미터가 아니라 층 수를 따라간다' 가설 검정용")
    ap.add_argument("--repeat-where", choices=["front", "back", "even"], default="front")
    a = ap.parse_args()

    import torch
    from tinylm import paths
    from tinylm.infer.generate import load_model
    from tinylm.data import tokenizer_path
    from tokenizers import Tokenizer

    models = ([(t, "dense" if t.startswith(("p6d", "dense", "p12d")) else "tied")
               for t in a.models] if a.models else DEFAULT_MODELS)
    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))
    base = f"{a.preset}_{a.data}_{a.tokens}"

    modes = [True, False] if a.both_cache else [not a.no_cache]
    print("=" * 92)
    print("  P030 추론 속도 벤치 (단계1: KV 캐시 + eos + 삼진 1회계산 반영)")
    print(f"  max_new={a.max_new}  reps={a.reps}(중위값)  프롬프트={PROMPT!r}")
    _watch = _CpuWatch() if (a.cpu_watch or a.cpu_ext_limit is not None) else None
    dirty_rows = 0
    if _watch is not None:
        if _watch.ps is None:
            print("  ⚠️★**`psutil` 이 없어 CPU 감시를 못 한다.** `pip install psutil` 후 다시 재세요 — "
                  "🚫감시 없이 잰 수는 **다른 프로세스에 오염됐는지 알 수 없다**")
        else:
            print(f"  ★CPU 감시 켬 — 논리 {_watch.n_cpu}개 / 물리 {_watch.n_phys}개. "
                  f"`ext` 열 = **우리 프로세스를 뺀 외부 부하**, 눈금은 "
                  f"★**시스템 전체 %(0~100, 작업관리자와 같다)**.")
            print(f"    한계 {a.cpu_ext_limit if a.cpu_ext_limit is not None else '없음'} · "
                  f"재측정 {a.cpu_ext_retry}회 — 🚫**한계를 넘어도 런을 막지 않는다**(표시만).")
            print("    ★**코어 고정(affinity)을 하지 않는다** — OS 스케줄러가 배정하는 대로 둔다. "
                  "`busy` 열은 그 창에서 50% 넘게 쓴 논리코어 수다.")
    print(f"  캐시 모드={['on' if m else 'off' for m in modes]}   (off = 결과 014 조건)")
    print("=" * 92)
    print("  ★MB 는 하드코딩이 아니라 로드한 모델에서 계산한다(회계 = 안 B, 2026-07-31 통일).")
    print("    저장 = packed_mb(아직 없는 패킹 포맷의 이론값) / 상주 = runtime_mb(결과 016 실측식).")
    print("=" * 92)
    print(f"\n{'device':>8} {'threads':>8} {'model':>16} {'저장MB':>7} {'상주MB':>8} {'캐시':>5} "
          f"{'tok/s':>9} {'TTFT ms':>9}")
    print("-" * 92)

    rows = []
    for dev in a.device:
        if dev == "cuda" and not torch.cuda.is_available():
            print("  (cuda 없음 — 건너뜀)")
            continue
        thread_list = a.threads if dev == "cpu" else [0]
        for nt in thread_list:
            if dev == "cpu" and nt > 0:
                torch.set_num_threads(nt)
            for tag, arch in models:
                ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, tag)
                if not ck.exists():
                    print(f"{dev:>8} {nt:>8} {tag:>16}  체크포인트 없음 — 건너뜀")
                    continue
                try:
                    model, cfg, _ = load_model(arch=arch, ckpt_path=str(ck), device=dev,
                                               drop_latent=a.drop_latent,
                                               int8_store=a.int8_store,
                                               unpack_cache=a.unpack_cache)
                except Exception as e:
                    print(f"{dev:>8} {nt:>8} {tag:>16}  로드 실패: {type(e).__name__}: {e}")
                    continue
                # ★P030 단계4: 층 수만 바꾼다(파라미터·메모리 고정). 1.0 이면 종전 경로.
                if a.infer_repeat != 1.0:
                    cfg.infer_repeat = a.infer_repeat
                    cfg.repeat_where = a.repeat_where
                    _n = len(model.visit_schedule())
                    print(f"  [P030-4] {tag}: 층 통과 {_n}회(기준 {cfg.n_layers}회) "
                          f"— 파라미터·메모리는 그대로다")
                # ★단일 소스: 표에 찍는 MB 는 여기서 계산된다(리터럴 금지).
                _mr = model.mem_report_all()
                mb, rt = _mr["packed_mb"], _mr["runtime_mb"]
                if a.check_cache:
                    from tinylm.infer.generate import check_cache_equivalence
                    if not check_cache_equivalence(model, cfg, tok, PROMPT, 16, dev):
                        print("  [중단] 캐시 출력이 불일치한다 — 속도를 재는 의미가 없다.")
                        return 2
                for use_c in modes:
                    try:
                        r, t, _ci = bench_one(model, cfg, tok, PROMPT, a.max_new, dev,
                                              a.reps, use_c, watch=_watch,
                                              ext_limit=a.cpu_ext_limit,
                                              max_retry=a.cpu_ext_retry)
                    except Exception as e:
                        print(f"{dev:>8} {nt:>8} {tag:>16}  실패: {type(e).__name__}: {e}")
                        continue
                    _cs = ""
                    if _ci:
                        _cs = (f"  ext {_ci['ext_mean']:>4.1f}/{_ci['ext_max']:>4.1f}%"
                               f"  sys {_ci['sys_mean']:>4.1f}%  busy {_ci['busy_max']:>2.0f}"
                               + ("  ⚠️한계초과" if _ci.get("dirty") else ""))
                        if _ci.get("dirty"):
                            dirty_rows += 1
                    print(f"{dev:>8} {nt if nt else '기본':>8} {tag:>16} {mb:>7.1f} {rt:>8.1f} "
                          f"{'on' if use_c else 'off':>5} {r:>9.2f} {t:>9.1f}{_cs}")
                    rows.append((dev, nt, tag, mb, r, t, use_c, rt))
                del model
                if dev == "cuda":
                    torch.cuda.empty_cache()

    print("-" * 92)
    if _watch is not None and _watch.ps is not None:
        print("  ★`ext` = 외부 부하 평균/최대(시스템 전체 %) · `sys` = 창 전체 평균 · "
              "`busy` = 50% 넘게 쓴 논리코어 수")
        if dirty_rows:
            print(f"  ⚠️★**한계 초과 {dirty_rows}행** — 🚫**이것은 '무효' 표시가 아니라 '조건 기록'이다.**")
            print("     **같은 표 안의 행끼리 ext 가 비슷하면 비교는 여전히 유효**하고, "
                  "행마다 크게 다르면 **그 차이를 속도 차이로 귀속하지 않는다**.")
        elif a.cpu_ext_limit is not None:
            print("  ✅외부 CPU 부하가 전 행에서 한계 안이었다")
    if rows:
        print("\n★핵심 질문: 메모리를 줄이면 CPU 추론이 빨라지는가?")
        print("  ★결과 016 의 예측: 속도가 메모리를 따라간다면 **저장이 아니라 상주**를 따라간다.")
        print("    저장 순위(mA<mC<p6d)와 상주 순위(mC<mA<p6d)가 역전돼 있으므로 둘을 갈라 읽는다.")
        for dev in sorted({r[0] for r in rows}):
            for nt in sorted({r[1] for r in rows if r[0] == dev}):
                sub = [r for r in rows if r[0] == dev and r[1] == nt and r[3] > 0 and r[6]]
                if len(sub) < 2:
                    continue
                sub.sort(key=lambda r: -r[3])      # 저장 큰 것부터 = 기준선이 dense
                base_rate, base_pk, base_rt = sub[0][4], sub[0][3], sub[0][7]
                print(f"\n  [{dev} t{nt if nt else '기본'}] 기준 = {sub[0][2]}"
                      f"(저장 {base_pk:.1f}MB / 상주 {base_rt:.1f}MB) {base_rate:.2f} tok/s")
                print(f"    {'모델':16} {'저장비':>7} {'상주비':>7} {'속도비':>7}   판정")
                for _, _nt, tag, mb, r, _t, _c, rt in sub[1:]:
                    sp, st, rr = base_pk / mb, base_rt / rt, r / base_rate
                    # 어느 축을 따라가는지 기계적으로 판정한다(눈대중 금지)
                    d_pk, d_rt, d_1 = abs(rr - sp), abs(rr - st), abs(rr - 1.0)
                    verdict = ("전이 없음(속도비~1.0)" if d_1 <= min(d_pk, d_rt)
                               else "상주를 따라감" if d_rt < d_pk else "저장을 따라감")
                    print(f"    {tag:16} {sp:6.2f}x {st:6.2f}x {rr:6.2f}x   {verdict}")
        print("\n  읽는 법: 속도비가 1.0 근처면 **전이 없음** — 가중치가 GEMM 직전에 fp32 로")
        print("           dequant 되기 때문이다. 그것이 P034 단계2~4 가 존재하는 이유이고,")
        print("           음성 결과이지 실패가 아니다.")
        if a.both_cache:
            print("\n★캐시 이득(같은 모델, on/off):")
            for dev, nt, tag, mb, r, _t, c, _rt in rows:
                if not c:
                    on = [q for q in rows if q[:4] == (dev, nt, tag, mb) and q[6]]
                    if on:
                        print(f"    [{dev} t{nt}] {tag:16} off {r:6.2f} -> on {on[0][4]:6.2f} "
                              f"tok/s = {on[0][4]/r:5.2f}x")
    print("\n★한계: 삼진은 dequant 후 GEMM(저장≠실행 크기 — 상주는 같은 표의 상주MB 열) /")
    print("        Windows CPU 측정은 노이즈 큼(중위값 사용, 1~2% 차이는 읽지 않는다) /")
    print("        batch 1 단일요청. 서버 처리량은 다른 주제다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
