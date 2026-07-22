# CLAUDE.md

이 파일은 Claude가 이 저장소에서 작업할 때 따르는 지침이다.

## 이 리포는 무엇인가

**TinyLM** 은 저사양 CPU·엣지·모바일 환경용 **초경량 LLM 아키텍처**를 설계·검증하는
프로젝트다. 핵심 목표는 **연산량이 아니라 메모리 최적화**다(연산 증가는 감수).
최종 지향점은 dense 대비 절반 이하 메모리로 유사 품질 — 성공 시 8B급을 1.7B급
메모리로, 27B급을 8B급 메모리로 구동하는 것.

> **현재 상태:** 아키텍처 v5. 100M급에서 학습 발산(NaN)을 해결했고(QK-norm·NaN 가드),
> 코드를 `tinylm/` 패키지로 모듈화했다. 다음 관문은 **동일 실데이터에서 dense vs tied
> 300M 본 실행**의 손실 격차 측정이다. 진행 로그·설계 근거는 [`handoff/`](handoff/) 가 정본.

## 아키텍처 (v5) — 확정 스펙

```
prelude 2층      어텐션·MLP 전부 독립          (임베딩 직후 조정)
   ↓
중간 16층        어텐션: 층마다 독립 (16세트)
                 MLP:    4층씩 묶어 4그룹만 저장 (mlp_group=4)
                 K/V:    인접 2층이 공유 (CLA2)
                 adaLN:  층별 scale/shift/gate
   ↓
coda 2층         어텐션·MLP 전부 독립          (lm_head 직전 조정)
   ↓
최종 RMSNorm → factorized lm_head (임베딩 전치 공유)
```

**검증용 100M급 프리셋 `m100`** (`d=768 ffn=2048 heads=12/3 vocab=32768 E=256`)

| | tied | dense 기준선 |
|---|---|---|
| 파라미터 | 72.9M | 132.5M |
| 배포 메모리 (1.95bpw) | 17.1 MB | 30.9 MB |
| KV 캐시 | 7.5 KB/token | 15.0 KB/token |
| 토큰당 FLOPs | 0.248 GFLOP | 0.248 GFLOP (동일) |

메모리 감축 **1.82배**. FLOPs가 같은 건 의도된 것 — 타잉은 메모리를 줄이지 연산을 줄이지 않는다.
이 실험이 재는 것은 **그 감축의 대가(손실 격차)가 얼마인가** 하나다.

### 유지 중인 설계 요소
- g128 삼진 양자화 (llama.cpp Q2_0_g128 / T-MAC 호환), TWN 임계 + L2 alpha, AMP-안전 STE
- 삼진 어닐링(배포 시점 = 학습 종료 시점), 공유 MLP LR 1/√g, weight decay 미보정
- prelude/coda 분리, 어텐션 층별 독립·MLP만 타잉, factorized embedding

### v5 학습 안정화 (메모리·파라미터·FLOPs 중립)
- **QK-norm** — q·k 내적 전에 파라미터 없는 RMSNorm. v4 300M 학습의 NaN 발산 주원인 해결.
- **NaN 가드** — clip_grad_norm_이 non-finite면 그 스텝을 건너뛴다(가중치 오염 방지).
- **torch.compile 안전 어닐** — quant_anneal을 버퍼 + `set_anneal()`로. 재컴파일 제거.
- **기본 LR 6e-4** (구 2e-3은 과다). 실측: QK-norm 적용 후 1e-3까지 안정(|g|~0.5).

## 코드 구조 — `tinylm/` 패키지 (정본)

버전마다 전체 파일을 복사하지 않는다. 아키텍처 실험은 `config.py` 프리셋만 바꾼다.

```
tinylm/
  paths.py            작업폴더 기준 경로 + HF 캐시 리다이렉트(import 부작용)
  config.py           TMTConfig + PRESETS(tiny/m100) + build_config + dense_baseline
  model/
    ternary.py        _TernarySTE, ternary, TLinear
    modules.py        RMSNorm, RoPE, Attention(QK-norm), MLP, Layer
    transformer.py    TiedMLPTransformer (set_anneal, report, param_groups)
  data/
    prepare.py        토큰화 + 크기별 재사용 캐시(data_cache/{name}_{tokens}/)
    loader.py         memmap 무작위 크롭
  train/
    trainer.py        학습 루프(어닐·NaN 가드·체크포인트)
    lr_finder.py      자동 LR (range test 기본 / grid sweep 고급)
  eval/
    evaluate.py, compare.py
  infer/
    generate.py       체크포인트 로드 + 샘플링(정성 확인용, KV 캐시 없음)
  cli.py              단일 진입점(prepare/train/eval/compare/all/lrfind/generate)
run100m.py            호환 래퍼 → tinylm.cli.main
```

작업폴더에 자동 생성되는 폴더(모두 gitignore): `HF/`(모델·데이터셋 캐시),
`data_cache/`(토큰 바이너리, 크기별 재사용), `runs/`(ckpt·logs).

## 빌드 · 실행

학습은 **CUDA GPU(RTX 4070 Ti)** 에서 사용자가 직접 실행한다.
필요 패키지: `torch`, `datasets`, `tokenizers`. 저장소 루트에서 실행:

```bash
# 파이프라인 동작 확인(tiny·합성·컴파일) — 수 분
python run100m.py all --tiny --data synthetic --tokens 2M --steps 40 \
    --micro-bs 4 --seq 128 --accum 2 --eval-every 20 --compile

# 자동 LR 탐색(range test 기본 / --method both 로 grid까지)
python run100m.py lrfind --arch tied --data ko-en --tokens 50M --method both

# 본 실행(dense·tied 자동) + 비교
python run100m.py all --data ko-en --tokens 300M --steps 2289 \
    --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile

# 추론 정성 확인
python run100m.py generate --arch tied --prompt "안녕하세요" --max-new 80
```

`python -m tinylm <cmd> ...` 도 동일하게 동작한다.

**판정 기준** (`compare` 손실 격차): `≤ +0.07` 성립 / `+0.07~+0.15` prelude·coda↑ 또는 g↓ /
`> +0.15` 는 `|g|max` 먼저 확인(10 이상이면 학습 문제).

## 작업 규약

- **한글 본문 · 영문 식별자.** 서술은 한글, 변수·파일명·수식 기호는 영문/수학 기호.
- **파라미터 단일 소스.** 기본값은 `config.py` 의 `TMTConfig`/`PRESETS` 한 곳 — 하드코딩 산재 금지.
- **AI는 사용자 환경에서 코드를 직접 실행하지 않는다.** 수정만 하고, 실행이 필요하면
  명령어와 순서를 제시해 대리 수행을 요청한다(GPU 사용량·시간 보호).
- **git 은 사용자가 Windows 셸에서 수행한다.** 이 리포는 Cowork 마운트에서 rename/unlink가
  차단되어 샌드박스 git 쓰기가 불가하다(파일 생성·수정은 가능).

## `.claude/skills/` — 워크플로우 스킬

범용 작업 스킬 13종: `plan-doc`, `pr-workflow`, `impact-analysis`, `session-handoff`,
`check-and-verify`, `to-prd`, `to-issues`, `triage`, `grill-me`, `grill-with-docs`,
`zoom-out`, `setup-matt-pocock-skills`. 우리 작업에 특히 유용: `session-handoff`(세션 인수인계),
`grill-with-docs`(설계 반론 검증), `impact-analysis`(변경 영향). `.claude/project.json` 이
없어 프로젝트 상수는 기본값으로 동작한다.

## 직전 버전 보존

`architecture_v4/`(NaN 발산본), `architecture_v5/`(단일파일 v5)는 이력 보존용이다.
신규 작업은 `tinylm/` 에서만 한다.
