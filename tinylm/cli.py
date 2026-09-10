#!/usr/bin/env python3
"""TinyLM 단일 진입점.

  python -m tinylm all --data ko-en --tokens 300M --steps 2289 --lr 1e-3 --compile
  python -m tinylm lrfind --method both
  python -m tinylm generate --arch tied --prompt "안녕하세요"

(호환) 저장소 루트의 run100m.py 도 이 main() 을 호출한다.
"""
from __future__ import annotations

import argparse

from . import paths  # noqa: F401  (HF 리다이렉트 먼저)
from .data import DATASETS
from .config import PRESETS
from .config import REPEAT_MODES


def _tok(s):
    s = str(s)
    return int(float(s.rstrip("MmBb")) * (1e9 if s[-1] in "Bb" else 1e6))


def _preset(a):
    return "tiny" if a.tiny else a.preset


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["prepare", "train", "eval", "compare", "all",
                                   "lrfind", "generate", "kdcache"])
    p.add_argument("--arch", choices=["dense", "tied"], default="tied")
    # choices 를 PRESETS 에서 자동 유도 — 종전 하드코딩은 `m100d` 를 빠뜨리고 있었다.
    p.add_argument("--preset", choices=list(PRESETS), default="m100",
                   help="m100R1a/m100R1c = REVIEW1 잠정 보존 후보(2026-07-31 승격). "
                        "아키텍처만 고정하고 KD 등 학습 조합은 명령줄이 정한다")
    p.add_argument("--data", default="ko-en", choices=list(DATASETS) + ["synthetic"])
    p.add_argument("--tokens", default="300M")
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--micro-bs", type=int, default=8)
    p.add_argument("--seq", type=int, default=1024)
    p.add_argument("--accum", type=int, default=8)
    p.add_argument("--lr", type=float, default=6e-4)
    p.add_argument("--eval-every", type=int, default=250)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--tiny", action="store_true", help="tiny 프리셋(파이프라인 확인용)")
    p.add_argument("--no-ckpt", action="store_true", help="gradient checkpointing 끄기")
    p.add_argument("--compile", action="store_true", help="torch.compile 사용")
    p.add_argument("--compile-mode", choices=["default", "reduce-overhead", "max-autotune"],
                   default="default", help="reduce-overhead=CUDA그래프(런치 오버헤드↓)")
    # --- v6: 효율/실험 ---
    p.add_argument("--sched", choices=["cosine", "wsd", "stable", "decay"], default="cosine",
                   help="stable=plateau 생성(감쇠X), decay=plateau에서 cooldown 분기")
    p.add_argument("--decay-from", default=None, help="decay 분기 시 불러올 plateau 체크포인트 경로")
    p.add_argument("--anneal-end", type=float, default=0.60,
                   help="(P026) 삼진 어닐 완료 지점(진행률 0~1). 기본 0.60=종전 동작. "
                        "cooldown-QAT 정렬은 wsd 의 1-decay_frac 과 같은 값으로 준다(예: 0.80)")
    p.add_argument("--decay-frac", type=float, default=0.2,
                   help="(P026) wsd 스케줄에서 마지막 LR 감쇠 구간 비율(기본 0.2)")
    p.add_argument("--anneal-shape", choices=["linear", "step"], default="linear",
                   help="(P035) 삼진 어닐의 형태. linear=종전 램프(기본, 무변). "
                        "step=--anneal-start 까지 FP(anneal 0), 그 지점에서 1.0 으로 급전이. "
                        "논문이 상정한 'FP 학습 후 별도 QAT' 를 인위적으로 재현해 기전 유무를 본다")
    p.add_argument("--anneal-start", type=float, default=None,
                   help="(P035) 어닐 시작(step 이면 전이) 지점(진행률 0~1). "
                        "미지정이면 종전대로 warm/steps+0.05 를 쓴다(무변)")
    # ── P036 : Arenas(annealing residual synapse). 학습 플래그, 기본 off ──
    p.add_argument("--arenas", action="store_true",
                   help="(P036) Y=X*Ta + lambda_t*X*W. latent W 를 입력 gradient 경로에 넣는다")
    p.add_argument("--arena-lambda", type=float, default=0.1,
                   help="(P036) lambda_0. 학습 시작 시점의 residual 계수")
    p.add_argument("--arena-end", type=float, default=0.9,
                   help="(P036) 이 진행률에서 lambda_t=0 (이후 순수 삼진 → 추론 오버헤드 0)")
    # ── P031 : 추론 시 middle 반복(깊이 외삽). eval/generate 전용, 학습 무영향 ──
    p.add_argument("--infer-repeat", type=float, default=1.0,
                   help="(P031) middle 블록 통과 배수. 1.0=학습된 그대로 / 0.5=축소 / 1.5=확장")
    p.add_argument("--repeat-where", choices=["front", "back", "even"], default="front",
                   help="(P031) 분수 R 에서 어디를 더/덜 돌지. 결과가 이것에 의존한다")
    p.add_argument("--kv-dtype", choices=["fp32", "bf16", "fp16"], default="fp32",
                   help="★KV 캐시 **저장** 정밀도(P077 단계1). bf16 이면 KV 가 절반이 된다. "
                        "계산은 fp32 로 되올리므로 산술은 안 바뀐다. 기본 fp32 = 비트 동일")
    p.add_argument("--repeat-kv-reuse", action="store_true",
                   help="(P031) 반복 통과에서 KV 를 재계산하지 않고 첫 통과 것을 재사용(대조 조건)")
    # ★★P067(2026-08-22 사용자 지시) — **외부 토크나이저·외부 교사.**
    #   목적: (1) 더 나은 교사로 학습 효율이 오르는가 (2) ★**KD 가 무익했던 것이
    #   "우리 dense 가 무능해서" 였는지** — 결과 038 은 그 둘을 구분하지 못했다.
    #   ⚠️**세 플래그 전부 기본 None = 종전 = 비트 동일.**
    # ★★P073(2026-08-23) — **`cla_group` 을 명령줄에서 바꾼다.**
    #   감사에서 나온 것: `cla_group=2` 는 **기본으로 켜져 있는데 품질 대가가 단독 귀속된
    #   적이 없다.** 결과 033 은 VRAM(-35.3%)만 쟀고, 결과 044 가 이미
    #   *"대가를 귀속하려면 cla_group=1 대조가 필요"* 라고 적어 뒀다.
    #   ⚠️미지정(None)이면 **프리셋 값 그대로 = 비트 동일**.
    p.add_argument("--cla-group", type=int, default=None,
                   help="★(P073) K/V 를 몇 층이 공유하는가. 미지정=프리셋(보통 2). "
                        "1 이면 층마다 자기 KV(파라미터·VRAM 이 는다)")
    p.add_argument("--ce-chunk", type=int, default=0,
                   help="★★(결과 054) 평균 CE 를 행 청크로. 0=끄기=비트 동일. "
                        "**P065 두 팔이 정확히 CE 에서 OOM 났다** — --kd-chunk 는 KD 만 나눈다. "
                        "무KD + --no-ckpt 조합에서 이 항이 노출된다. 권장 2048")
    p.add_argument("--tokenizer-hf", default=None, metavar="HF폴더",
                   help="★(P067) 외부 HF 모델의 tokenizer.json 으로 토큰화한다. "
                        "**데이터 캐시가 분리되고 vocab_size 가 그 어휘로 바뀐다**")
    p.add_argument("--kd-teacher-hf", default=None, metavar="HF폴더",
                   help="★(P067) KD 교사를 외부 HF CausalLM 으로. "
                        "⚠️**어휘가 학생과 같아야 한다** — 보통 --tokenizer-hf 와 같은 폴더")
    p.add_argument("--teacher-dtype", choices=["bf16", "fp16", "fp32"], default="bf16",
                   help="(P067) 외부 교사 실행 dtype. 기본 bf16(원본 dtype). "
                        "★로짓은 어느 경우든 fp32 로 올려서 KD 에 넘긴다")
    p.add_argument("--reuse-attn-on-dup", action="store_true",
                   help="★P049 §17.3 — 재귀 **두 번째 이후 통과에서 어텐션 출력을 재사용**"
                        "(041 §17 복제층 cos 0.9882). 학습·추론 **양쪽에 같은 값**을 준다(함정 39)")
    p.add_argument("--seed", type=int, default=1337,
                   help="시드(기본 1337=종전 동작). 가중치 초기화 + train 크롭 순서에 반영. "
                        "val 크롭은 항상 고정(99)이라 런 간 비교가 유지된다. 재현 노이즈 측정용")
    p.add_argument("--snapshot-at", default=None, help="토큰 마크에서 명명 스냅샷 저장(콤마, 예: 100M,300M,600M)")
    p.add_argument("--ema", type=float, default=0.0, help="EMA decay(0=끔, 예: 0.999)")
    p.add_argument("--early-stop", type=int, default=0, help="val 개선 없이 N회 eval시 종료(0=끔)")
    p.add_argument("--init-from", action="store_true", help="tied를 dense.pt로 부모초기화")
    p.add_argument("--ckpt-tokens", default=None, metavar="300M",
                   help="★★2026-09-07 신설(함정 28 여섯째) — **이 명령이 읽는** 체크포인트 "
                        "파일명의 토큰 칸. `--init-from` 부모 · `--init-from-tag` · KD 교사 셋에 "
                        "걸린다. 🚫**쓰는 체크포인트는 언제나 `--tokens`** 를 따른다(네임스페이스 유지). "
                        "생략하면 `--tokens` 와 같다 = 종전과 비트 동일. "
                        "부모를 300M 로 학습해 두고 600M 로 학습할 때 "
                        "`--tokens 600M --ckpt-tokens 300M` 이 된다. "
                        "★`paired_eval --ckpt-tokens` 와 **같은 개념·같은 이름**이다(R14)")
    p.add_argument("--init-from-tag", default=None,
                   help="부모초기화를 base_dense.pt 대신 base_{TAG}.pt 로(태그된 dense에서 초기화). "
                        "토큰스윕 클린판처럼 정본 dense 를 덮지 않고 별도 태그 dense 를 쓸 때.")
    p.add_argument("--kd", action="store_true", help="dense.pt를 교사로 KD")
    p.add_argument("--kd-best", action="store_true", help="KD 교사를 dense_best.pt로(더 강한 교사)")
    p.add_argument("--kd-cache", action="store_true", help="오프라인 KD(캐시 top-k, 교사 forward 없음)")
    p.add_argument("--kd-topk", type=int, default=16, help="오프라인 KD top-k")
    p.add_argument("--kd-every", type=int, default=1,
                   help="온라인 KD skip-forward: K스텝마다 교사 forward 1회(교사 연산 1/K). 1=매 스텝")
    p.add_argument("--kd-dynamic", action="store_true",
                   help="동적 KD: 교사 forward 간격을 1→kd-every 로 선형 증가(초반 촘촘·후반 성김)")
    p.add_argument("--kd-teacher-tag", default=None,
                   help="KD 교사를 dense 대신 임의 태그 체크포인트로(압축 교사 distill, P018)")
    p.add_argument("--ema-start", type=float, default=0.0, help="EMA를 steps의 이 비율 이후부터 누적(0=처음부터)")
    p.add_argument("--kd-alpha", type=float, default=0.5)
    p.add_argument("--kd-temp", type=float, default=2.0)
    p.add_argument("--lora-rank", type=int, default=0, help="공유 MLP 층별 LoRA rank(0=끔)")
    p.add_argument("--lora-bits", type=int, default=2, choices=[2, 16])
    p.add_argument("--lora-decay", type=float, default=0.0,
                   help="(P008) LoRA 출력 스케일 s(t) 를 1->0 으로 어닐. 진행률 이 지점에서 0. "
                        "0=끔(고정 LoRA, 종전 동작). 0 이 되면 배포 메모리 대가가 사라진다")
    p.add_argument("--tag", default=None, help="체크포인트/로그 파일명(실험 조건 구분용)")
    p.add_argument("--vs", default=None, help="compare에서 tied vs tied 비교할 상대 태그")
    p.add_argument("--mlp-group", type=int, default=None, help="MLP 타잉 g 오버라이드(프리셋값 대체, g-스윕용)")
    # ★P061(2026-08-13) — 불균등 타잉. 경계 목록. 미지정=균등=비트 동일.
    #   예: `--mlp-split 12` -^> [0..11][12..15] / `--mlp-split 4` -^> [0..3][4..15]
    p.add_argument("--mlp-split", type=int, nargs="*", default=None,
                    help="중간 MLP 타잉 경계(불균등). 미지정이면 --mlp-group 균등")
    # ★★P005(2026-09-03) — Muon. 🚫기본 `adamw` = 비트 동일.
    p.add_argument("--optimizer", choices=["adamw", "muon"], default="adamw",
                   help="★(P005) `muon` 이면 **행렬만** Muon(Newton-Schulz 5), "
                        "임베딩·norm·bias 는 AdamW. ⚠️이점은 대배치 집중 — 우리 131K 는 작다. "
                        "⚠️삼진 STE 상호작용 미검증")
    p.add_argument("--muon-lr-mult", type=float, default=1.0,
                   help="★(P005, 2026-09-05) Muon 그룹의 lr 배수. Muon 의 관용 lr 은 "
                        "AdamW 보다 한 자릿수 크다(원 구현 2e-2 vs 우리 1e-3). "
                        "🚫기본 1.0 = 종전 동작 그대로. `--optimizer muon` 일 때만 쓴다")
    # ★★P005b b-1(2026-09-10, 사용자 지시 2E 허가) — **업데이트 스케일 규약.**
    #   `ai_dev_tool/09` V1 검증이 참조 구현 둘을 확인했다. 🚫기본 `jordan` = **비트 동일**.
    p.add_argument("--muon-scale", choices=["jordan", "rms"], default="jordan",
                   help="★(P005b b-1) Muon 업데이트 스케일 규약. "
                        "`jordan` = max(1, out/in)**0.5 (원 구현, **기본·비트 동일**) · "
                        "`rms` = 0.2*sqrt(max(out,in)) (AdamW 업데이트 RMS 에 맞춘다 — "
                        "arXiv:2505.02222 각주 2 · Kimi K2 Algorithm 1). "
                        "★두 규약의 비는 형상마다 다르므로 `--muon-lr-mult` 로는 못 바꾼다")
    # ★★P086(2026-09-04) — 층별 스칼라 승수(Learnable Multipliers). 🚫기본 off = 비트 동일.
    p.add_argument("--mlp-lrm", action="store_true",
                   help="★(P086) 타잉된 중간층마다 **gate·up·down 스칼라 승수**를 준다. "
                        "W 는 공유한 채 **스케일만 층별로** 푼다. ★추론 상주 증가 0(per-row α 에 흡수). "
                        "⚠️승수에는 약한 WD(0.01)가 걸린다 — 대칭성 표류 방지")
    # ★★P086 단계3(2026-09-08(3차), 사용자 지시 2F) — 논문의 **벡터 승수**. 🚫기본 scalar = 비트 동일.
    p.add_argument("--mlp-lrm-mode", choices=["scalar", "vector"], default="scalar",
                   help="★(P086 단계3) 승수의 모양. `scalar` = 종전 3개(**비트 동일**) · "
                        "`vector` = gate/up 에 ffn_dim, down 에 dim 벡터(논문 arXiv:2601.04890 식 3 의 행 승수). "
                        "🚫열 승수는 안 붙인다 — `m_scale` 이 이미 그 자리다(논문의 중복 경고). "
                        "⚠️`--mlp-lrm` 과 **함께** 줘야 한다")
    p.add_argument("--mlp-lrm-wd", type=float, default=0.01,
                   help="★(P086 단계3) 승수 그룹의 weight decay. 기본 **0.01 = 종전**(대칭성 표류 완화, 논문 §4.1). "
                        "논문 §1 은 승수에 WD 를 안 건다 → **0 을 주면 그 조건**이다(팔 B)")
    # ★★P084(2026-09-03) — prelude·coda 에 CLA 를 적용하지 않는다. 🚫기본 = 비트 동일.
    p.add_argument("--no-cla-edges", action="store_true",
                   help="★(P084) 머리(prelude)·꼬리(coda)는 **자기 K/V 를 갖는다**. "
                        "그룹은 middle 안에서만 묶인다. ⚠️**KV 엔트리가 늘어 상주가 커진다**")
    p.add_argument("--opt-dtype", choices=["fp32", "fp32c", "bf16"], default="fp32",
                   help="(P022B 단계2) AdamW **상태**(exp_avg/exp_avg_sq) 정밀도. "
                        "fp32=종전 torch fused AdamW(기본, 비트 동일) / "
                        "fp32c=우리 구현·fp32 상태(자기검증) / bf16=상태만 bf16(약 254MB 절감). "
                        "master weight·gradient·산술은 어느 모드에서도 fp32 다")
    p.add_argument("--wq-dtype", choices=["fp32", "bf16"], default=None,
                   help="(P068 A1) `_wq` 저장 dtype. 계산은 항상 fp32. "
                        "기본 fp32=비트 동일. bf16 은 F.linear 진입 캐스팅을 없앤다")
    p.add_argument("--emb-chunk", type=int, default=None,
                   help="(P034 단계5) 출력 헤드를 어휘 축으로 자르는 크기. 0=끄기. "
                        "양자화 임베딩에서만 의미가 있다(배포 전용)")
    p.add_argument("--micro-group", type=int, default=None,
                   help="(P051) 삼진 alpha 그룹 크기 오버라이드(프리셋 기본 128). 저장 bpw 의 "
                        "scale 항이 16/g 이므로 g 를 키우면 packed 가 준다. 미지정=프리셋값=비트동일")
    p.add_argument("--attn-group", type=int, default=None,
                   help="(P057) 어텐션 타잉 g — 중간층 g 개가 어텐션 하나를 공유. "
                        "미지정=프리셋(1)=층마다 독립=비트동일. 삼진의 48.4%% 가 어텐션이다")
    p.add_argument("--train-repeat", type=float, default=None,
                   help="(P049B) 학습 시 중간 블록 통과 배수(1.0=종전=비트동일). "
                        "--infer-repeat 와 동시 사용 금지")
    # ★목록은 `config.REPEAT_MODES` 가 정본이다(함정 18, 2026-08-22 실사고)
    p.add_argument("--repeat-mode", choices=list(REPEAT_MODES), default="uniform",
                   help="(P049B) uniform=중간 전체 / block=--repeat-block 그룹만 / progressive=깊을수록 증가")
    p.add_argument("--repeat-block", type=int, default=0, help="(P049B) block 모드의 MLP 그룹 인덱스")
    p.add_argument("--save-every", type=int, default=0,
                   help="(P058) 체크포인트 저장 주기(스텝). 0=매 eval 마다(종전). "
                        "eval 은 자주 하되 저장은 드물게 하려는 것 — model+optimizer 직렬화가 비싸다")
    p.add_argument("--sdpa-gqa", action="store_true",
                   help="(F-1) GQA K/V 물리복제 대신 SDPA enable_gqa 사용. 기본 off=비트동일. "
                        "게이트: scripts/diag_gqa_equiv.py")
    p.add_argument("--kd-chunk", type=int, default=0,
                   help="(T-2/P053) KD KL 을 이 행수씩 나눠 계산(0=off=비트동일). "
                        "동시 임시텐서를 줄인다 — backward 저장분은 안 줄어든다")
    p.add_argument("--depth-init", choices=["prop", "gate_scale", "identity", "role"],
                   default="prop",
                   help="(P049) 부모초기화 층 대응. prop=기본 / gate_scale=복제횟수로 gate 나눔 / "
                        "★identity=복제층 gate 를 0 으로(=교사와 동일 함수에서 출발. 결과 041 권장) / "
                        "role=얕을 때도 역할정렬 강제(⚠️결과 032 와 조건이 달라진다)")
# ★`--fused-int8` 을 여기 두지 않는다(2026-08-14). `cfg.fused_int8` 은 **추론 경로 옵션**이고
#   `--int8-store`·`--unpack-cache`·`--drop-latent` 와 같은 계열이라 **CLI 가 아니라 진단
#   스크립트가 켠다**(`scripts/bench_fused_int8.py`). 여기 두면 학습 명령이 받아들이는데
#   train() 은 쓰지 않는 **조용한 무동작 플래그**가 된다 — 결과 031 계열.
    p.add_argument("--kd-teacher-infer", action="store_true",
                   help="(P042) KD 교사에 freeze_quant()+drop_latent() 를 적용한다. 교사는 "
                        "가중치가 고정인데 매 스텝 refresh_quant 를 돌고 fp32 latent 도 든다. "
                        "**기본 off = 종전 동작(비트 동일)**")
    p.add_argument("--emb-rank", type=int, default=None,
                   help="(P046) factorized embedding 병목 E 오버라이드(프리셋 256). "
                        "E 를 줄이면 임베딩이 선형으로 줄지만 **로짓 랭크가 E 로 제한**된다")
    p.add_argument("--mlp-film", action="store_true", help="공유 MLP에 층별 FiLM(거의 공짜 조건화)")
    p.add_argument("--center-weights", action="store_true", help="(실험) g128 그룹 latent weight centering")
    p.add_argument("--ternary-kernel", action="store_true", help="(실험) 커스텀 삼진 커널 경로(레퍼런스)")
    p.add_argument("--ternary-kernel-triton", action="store_true", help="커널 Triton forward(검증 후에만)")
    p.add_argument("--sparse34", action="store_true", help="(P016) 3:4 희소 삼진 1.25bpw(각 4-블록 |w|최소 1개 0강제)")
    p.add_argument("--pool-tokens", default=None,
                   help="데이터 풀(캐시) 크기를 학습길이·이름과 분리 지정(예: 600M). "
                        "미지정이면 --tokens 사용. 토큰스윕 클린판: 모든 예산을 같은 풀에서 샘플.")
    p.add_argument("--doc-filter", action="store_true",
                   help="(P037 단계2) SEO 스팸 문서를 제외하고 캐시를 만든다. 서명 = 대형 AND "
                        "줄바꿈 ~0%% AND 줄 고유율 100%% (결과 018). **별도 디렉터리에 쓴다**")
    p.add_argument("--doc-min-chars", type=int, default=50_000,
                   help="(P037) 스팸 판정 최소 길이(자). 이보다 짧으면 절대 버리지 않는다")
    p.add_argument("--exact-cache", action="store_true",
                   help="상위호환 캐시를 고르지 않고 정확히 {data}_{요청토큰} 캐시만 사용/생성.")
    p.add_argument("--force-dense", action="store_true", help="all 실행 시 dense 재학습 강제(기본은 재사용)")
    # lrfind
    p.add_argument("--method", choices=["range", "grid", "both"], default="range")
    p.add_argument("--lrs", default="3e-4,6e-4,1e-3,2e-3", help="grid 스윕 LR 목록(콤마)")
    p.add_argument("--lr-min", type=float, default=1e-5)
    p.add_argument("--lr-max", type=float, default=1e-1)
    p.add_argument("--lrfind-steps", type=int, default=150)
    # generate
    p.add_argument("--prompt", default="")
    p.add_argument("--max-new", type=int, default=100)
    p.add_argument("--temp", type=float, default=0.8)
    p.add_argument("--top-k", type=int, default=40)
    p.add_argument("--ckpt-path", default=None)
    # P030 단계1: 캐시/eos. 기본은 켜짐 — 끄는 쪽이 대조군이다.
    p.add_argument("--no-cache", action="store_true",
                   help="KV 캐시 off(정확성 대조용). 느리다 — 속도 측정에 쓰지 말 것")
    p.add_argument("--no-eos-stop", action="store_true",
                   help="<eos> 에서 멈추지 않는다(문서 경계를 넘어 생성)")
    p.add_argument("--check-cache", action="store_true",
                   help="캐시 유/무 그리디 출력 일치 검증만 하고 종료")
    a = p.parse_args()

    import sys as _sys                           # 실행 인자 로그(배치파일에서 어떤 조건인지 추적)
    print("[cmd] python " + " ".join(_sys.argv))

    n_tok = _tok(a.tokens)
    preset, ckpt = _preset(a), not a.no_ckpt
    tokstr = f"{n_tok//1_000_000}M" if n_tok >= 10**6 else str(n_tok)
    base = f"{preset}_{a.data}_{tokstr}"        # 스케일별 이름 프리픽스
    # ★부모 dense 는 프리셋을 넘어 찾는다(2026-08-01). `m100R1a/c` 는 `m100` 에서 한 필드만
    #   바꾼 파생이라 **부모가 하나뿐**인데, 종전에는 `m100R1a_..._dense.pt` 를 찾다 즉사했다
    #   (P038·P036 단계2 실패). 쓰기 경로는 그대로 `{preset}_...` 라 네임스페이스는 유지된다.
    # ★★2026-09-07 (함정 28 여섯째) — **읽는 이름과 쓰는 이름을 가른다.**
    #   🚫사고: `--tokens 600M` 이 데이터 캐시 크기이자 **부모 체크포인트 파일명**이라
    #   `m100s8_ko-en_600M_dense.pt` 를 찾다 즉사했다. 부모는 300M 로만 학습돼 있다.
    #   **4팔이 죽었다**(P062 단계9 3팔 + P005 단계2 4번째 팔, 2026-09-07).
    #   ⚠️`src_tok` 은 **읽기 전용**이다 — `base`/`tokstr` 은 그대로 두어야
    #   쓰는 체크포인트·로그 이름의 네임스페이스가 유지된다.
    src_tok = getattr(a, "ckpt_tokens", None) or tokstr
    if src_tok != tokstr:
        print(f"  ★읽는 체크포인트의 토큰 칸 = {src_tok} (쓰는 것은 {tokstr}) — "
              "부모·교사 파일명과 학습 길이를 갈라 쓴다")
    dense_ck = paths.resolve_ckpt(preset, a.data, src_tok, "dense")
    dense_best_ck = paths.resolve_ckpt(preset, a.data, src_tok, "dense_best")

    pool_tok = _tok(a.pool_tokens) if a.pool_tokens else None

    if a.cmd == "prepare":
        from .data import prepare
        prepare(a.data, pool_tok if pool_tok else n_tok, exact=a.exact_cache, hf_tok=a.tokenizer_hf,
                doc_filter=a.doc_filter, doc_min_chars=a.doc_min_chars)

    elif a.cmd == "kdcache":
        from .train.kd_cache import build_kd_cache
        teacher = str(dense_best_ck if a.kd_best else dense_ck)
        build_kd_cache(base, teacher, a.data, n_tok, a.steps, a.micro_bs, a.seq, a.accum, a.kd_topk, a.kd_temp)

    elif a.cmd == "train":
        from .train import train
        # KD 교사 경로: 압축 교사(--kd-teacher-tag) > dense_best > dense
        if a.kd_teacher_tag:
            kd_teacher = str(paths.resolve_ckpt(preset, a.data, src_tok, a.kd_teacher_tag))
        else:
            kd_teacher = str(dense_best_ck if a.kd_best else dense_ck)
        # 부모초기화 소스: --init-from-tag 주면 base_{TAG}.pt, 아니면 base_dense.pt
        # ★`src_tok`(= `--ckpt-tokens` 또는 `--tokens`) 을 쓴다 — **읽는 이름**이기 때문이다.
        init_src = (str(paths.resolve_ckpt(preset, a.data, src_tok, a.init_from_tag)) if a.init_from_tag
                    else (str(dense_ck) if a.init_from else None))
        # ★★2026-09-07 — **원인을 말하고 즉시 거절한다.** 종전에는 `torch.load` 가
        #   raw `FileNotFoundError` 를 던져 *"왜 600M 을 찾지?"* 를 사람이 풀어야 했다.
        #   4팔이 그렇게 죽었고 넷 다 원인이 같았다.
        import os as _os
        _src_tag = a.init_from_tag or "dense"
        _kd_tag = a.kd_teacher_tag or ("dense_best" if a.kd_best else "dense")
        for _what, _p, _t in (("부모초기화", init_src, _src_tag),
                              ("KD 교사", kd_teacher if a.kd else None, _kd_tag)):
            if _p and not _os.path.exists(_p):
                _alt = sorted(q.name for q in (paths.RUNS / "ckpt").glob(
                    f"*_{a.data}_*_{_t}.pt"))
                print(f"\n  🚫**{_what} 체크포인트가 없다**: {_os.path.basename(_p)}")
                if _alt:
                    print("     ★같은 태그가 **다른 토큰 칸**에 있다: " + ", ".join(_alt[:4]))
                print(f"     ★`--tokens`({tokstr}) 는 **데이터 캐시 크기이자 쓰는 이름**이고, "
                      "읽는 이름은 `--ckpt-tokens` 가 정한다(함정 28 여섯째).")
                print("     부모를 300M 로 학습해 두고 600M 를 돌리려면 "
                      "`--tokens 600M --ckpt-tokens 300M` 이다.")
                # 🚫★`return 2` 로는 안 된다 — `run100m.py` 가 반환값을 버려서
                #   **exit 0** 이 된다(R19: 계측 0 에 exit 0 이 최악의 실패 모드).
                #   453줄의 기존 규약과 같이 `SystemExit` 로 던진다.
                raise SystemExit(2)
        train(preset, a.arch, a.data, n_tok, a.steps, a.micro_bs, a.seq, a.accum,
              a.lr, a.eval_every, a.resume, ckpt, a.compile,
              sched=a.sched, ema=a.ema, early_stop=a.early_stop,
              init_from=init_src,
              kd=(kd_teacher if a.kd else False),
              kd_alpha=a.kd_alpha, kd_temp=a.kd_temp,
              lora_rank=a.lora_rank, lora_bits=a.lora_bits, mlp_film=a.mlp_film,
              tag=a.tag, tokstr=tokstr, compile_mode=a.compile_mode, mlp_group=a.mlp_group,
              mlp_split=a.mlp_split,
              micro_group=a.micro_group, opt_dtype=a.opt_dtype,
              optimizer=a.optimizer, muon_lr_mult=a.muon_lr_mult,
              muon_scale=a.muon_scale,
              wq_dtype=a.wq_dtype, emb_chunk=a.emb_chunk,
              ema_start=a.ema_start, center_weights=a.center_weights, decay_from=a.decay_from,
              snapshots=([_tok(x) for x in a.snapshot_at.split(',')] if a.snapshot_at else None),
              use_ternary_kernel=a.ternary_kernel, ternary_kernel_triton=a.ternary_kernel_triton,
              kd_cache=a.kd_cache, kd_topk=a.kd_topk,
              kd_every=a.kd_every, kd_dynamic=a.kd_dynamic, sparse34=a.sparse34,
              pool_tokens=pool_tok, exact_cache=a.exact_cache,
              anneal_end=a.anneal_end, decay_frac=a.decay_frac, seed=a.seed,
              anneal_shape=a.anneal_shape, anneal_start=a.anneal_start,
              arenas=a.arenas, arena_lambda=a.arena_lambda, arena_end=a.arena_end,
              doc_filter=a.doc_filter, doc_min_chars=a.doc_min_chars,
              lora_decay=a.lora_decay, emb_rank=a.emb_rank,
              kd_teacher_infer=a.kd_teacher_infer,
              sdpa_gqa=a.sdpa_gqa, kd_chunk=a.kd_chunk, depth_init=a.depth_init,
              attn_group=a.attn_group, train_repeat=a.train_repeat,
              repeat_mode=a.repeat_mode, repeat_block=a.repeat_block,
              reuse_attn_on_dup=a.reuse_attn_on_dup,
              ce_chunk=a.ce_chunk, cla_group=a.cla_group,
              cla_edges=(not a.no_cla_edges), mlp_lrm=a.mlp_lrm,
              mlp_lrm_mode=a.mlp_lrm_mode, mlp_lrm_wd=a.mlp_lrm_wd,
              tokenizer_hf=a.tokenizer_hf, kd_teacher_hf=a.kd_teacher_hf,
              teacher_dtype=a.teacher_dtype,
              save_every=a.save_every)

    elif a.cmd == "all":
        from .train import train
        from .eval import compare
        import json as _json
        dlog = paths.RUNS / "logs" / f"{base}_dense.json"
        # dense 재사용: 같은 (preset,data,steps) 의 dense 로그·체크포인트가 있으면 재학습 생략.
        # (seq·lr 은 로그에 있으면 함께 대조. --force-dense 로 강제 재학습.)
        reuse = False
        if not a.force_dense and dense_ck.exists() and dlog.exists():
            try:
                dj = _json.loads(dlog.read_text())
                reuse = (dj.get("preset") == preset and dj.get("data") == a.data
                         and dj.get("steps") == a.steps
                         and dj.get("seq", a.seq) == a.seq
                         and abs(dj.get("lr", a.lr) - a.lr) < 1e-12)
            except Exception:
                reuse = False
        for arch in ("dense", "tied"):
            if arch == "dense" and reuse:
                dj = _json.loads(dlog.read_text())
                print("\n" + "#" * 68 + "\n#  dense (재사용)\n" + "#" * 68)
                print(f"[dense] 기존 학습 재사용: val {dj['final']['val_loss']:.4f} "
                      f"(preset={dj.get('preset')} data={dj.get('data')} steps={dj.get('steps')}). "
                      f"재학습하려면 --force-dense")
                continue
            print("\n" + "#" * 68 + f"\n#  {arch}\n" + "#" * 68)
            is_tied = arch == "tied"
            train(preset, arch, a.data, n_tok, a.steps, a.micro_bs, a.seq, a.accum,
                  a.lr, a.eval_every, a.resume, ckpt, a.compile,
                  sched=a.sched, ema=a.ema, early_stop=a.early_stop,
                  init_from=(str(dense_ck) if (is_tied and a.init_from) else None),
                  kd=((str(dense_best_ck) if a.kd_best else str(dense_ck)) if (is_tied and a.kd) else False),
                  kd_alpha=a.kd_alpha, kd_temp=a.kd_temp,
                  lora_rank=(a.lora_rank if is_tied else 0), lora_bits=a.lora_bits,
                  mlp_film=(a.mlp_film if is_tied else False), tokstr=tokstr,
                  compile_mode=a.compile_mode, mlp_group=(a.mlp_group if is_tied else None),
                  ema_start=a.ema_start, center_weights=(a.center_weights if is_tied else False),
                  decay_from=a.decay_from, pool_tokens=pool_tok, exact_cache=a.exact_cache)
        print(); compare(base)

    elif a.cmd == "eval":
        import torch
        from .data import prepare, Loader
        from .eval import evaluate
        from .infer import load_model
        meta = prepare(a.data, n_tok, hf_tok=getattr(a, 'tokenizer_hf', None))
        ckp = a.ckpt_path or str(paths.resolve_ckpt(preset, a.data, tokstr,
                                                    a.tag if a.tag else a.arch))
        model, cfg, device = load_model(a.arch, ckp)
        # ★P031 — 체크포인트의 cfg 위에 **추론 전용** 설정만 덮어쓴다. 가중치는 그대로다.
        if a.kv_dtype != "fp32":
            cfg.kv_dtype = a.kv_dtype
            print(f"[P077] ★KV 저장 dtype = {a.kv_dtype} (계산은 fp32로 되올린다). "
                  f"KV 상주가 절반이 된다 — 예: seq 1024 에서 15.0 -> 7.5 MiB. "
                  f"⚠️품질 대가는 diag_kvcache.py 가 잰다")
        if a.infer_repeat != 1.0 or a.repeat_kv_reuse or a.reuse_attn_on_dup:
            cfg.infer_repeat = a.infer_repeat
            cfg.repeat_where = a.repeat_where
            cfg.repeat_kv_reuse = a.repeat_kv_reuse
            cfg.reuse_attn_on_dup = a.reuse_attn_on_dup
            sch = model.visit_schedule()
            print(f"[P031] infer_repeat={a.infer_repeat} where={a.repeat_where} "
                  f"kv_reuse={a.repeat_kv_reuse} reuse_attn={a.reuse_attn_on_dup} -> 층 통과 {len(sch)}회"
                  f"(기준 {cfg.n_layers}회), middle {len(sch) - cfg.n_prelude - cfg.n_coda}회")
            print("[P031] 메모리는 R 과 무관하게 동일하다 — 늘어나는 것은 연산과 지연뿐이다.")
        print(model.report())
        va = Loader("val", a.micro_bs, a.seq, device, meta["dir"], seed=99)
        print(evaluate(model, va, 100, device))

    elif a.cmd == "compare":
        from .eval import compare
        compare(base, a.tag, a.vs)

    elif a.cmd == "lrfind":
        from .train import lr_find
        grid_lrs = tuple(float(x) for x in a.lrs.split(","))
        lr_find(method=a.method, preset=preset, arch=a.arch, data=a.data,
                n_tokens=a.tokens, micro_bs=a.micro_bs, seq=a.seq, accum=a.accum,
                ckpt=ckpt, range_steps=a.lrfind_steps, lr_min=a.lr_min, lr_max=a.lr_max,
                grid_lrs=grid_lrs)

    elif a.cmd == "generate":
        from .infer import generate
        if not a.prompt:
            p.error("generate 에는 --prompt 가 필요합니다")
        gckp = a.ckpt_path or str(paths.RUNS / "ckpt" / (f"{base}_{a.tag}.pt" if a.tag else f"{base}_{a.arch}.pt"))
        if a.check_cache:
            from tokenizers import Tokenizer
            from .data import tokenizer_path
            from .infer import load_model, check_cache_equivalence
            m, cfg_, dev = load_model(a.arch, gckp)
            tk = Tokenizer.from_file(str(tokenizer_path(a.data)))
            ok = check_cache_equivalence(m, cfg_, tk, a.prompt, max_new=a.max_new, device=dev)
            raise SystemExit(0 if ok else 1)
        generate(a.prompt, arch=a.arch, data=a.data, max_new=a.max_new,
                 temperature=a.temp, top_k=a.top_k, ckpt_path=gckp,
                 use_cache=not a.no_cache, stop_at_eos=not a.no_eos_stop)


if __name__ == "__main__":
    main()
