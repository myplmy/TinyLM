# CLAUDE.md

이 파일은 Claude가 이 저장소에서 작업할 때 따르는 지침이다.

## 이 리포는 무엇인가

**TinyLM** 은 저사양 CPU·엣지·모바일 환경용 **초경량 LLM 아키텍처**를 설계·검증하는
프로젝트다. 핵심 목표는 **연산량이 아니라 메모리 최적화**다(연산 증가는 감수).
최종 지향점은 dense 대비 절반 이하 메모리로 유사 품질 — 성공 시 8B급을 1.7B급
메모리로, 27B급을 8B급 메모리로 구동하는 것.

> **현재 상태:** 아키텍처 v5. 100M급에서 학습 발산(NaN) 문제를 해결하고
> dense vs tied 손실 격차 측정 단계에 있다. 진행 로그·설계 근거·미결 항목은
> [`handoff/`](handoff/) 의 최신 세션 인수인계 문서가 정본이다.

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

**검증용 100M급 설정** (`d=768 ffn=2048 heads=12/3 vocab=32768 E=256`)

| | tied | dense 기준선 |
|---|---|---|
| 파라미터 | 72.9M | 132.5M |
| 배포 메모리 (1.95bpw) | 17.1 MB | 30.9 MB |
| KV 캐시 | 7.5 KB/token | 15.0 KB/token |
| 토큰당 FLOPs | 0.248 GFLOP | 0.248 GFLOP (동일) |

메모리 감축 **1.82배**. FLOPs가 같은 건 의도된 것 — 타잉은 메모리를 줄이지 연산을 줄이지 않는다.
이 실험이 재는 것은 **그 감축의 대가(손실 격차)가 얼마인가** 하나다.

### 유지 중인 설계 요소
- g128 삼진 양자화 (llama.cpp Q2_0_g128 / T-MAC 호환 레이아웃)
- TWN 임계(0.7·E|w|) + L2 최적 alpha, weight 기반 AMP-안전 STE
- 삼진 어닐링 (배포 시점 = 학습 종료 시점, train/test 불일치 없음)
- 공유 MLP LR 1/√g, weight decay 미보정
- prelude/coda 분리 (단일 최대 이득), 어텐션 층별 독립·MLP만 타잉
- factorized embedding (V×E + E×d)

### v5에서 추가한 학습 안정화 (메모리·파라미터·FLOPs 중립)
- **QK-norm** — q·k 내적 전에 파라미터 없는 RMSNorm. v4의 300M 학습에서
  dense·tied 모두 완전 FP 구간(anneal 0.00)에서 |g| 폭주로 NaN 발산한 문제의 주원인.
- **NaN 가드** — clip_grad_norm_이 non-finite면 그 스텝을 건너뛴다(가중치 오염 방지).
- **torch.compile 안전 어닐** — quant_anneal을 버퍼 + `set_anneal()`로. dynamo 재컴파일 제거.
- **기본 LR 2e-3 → 6e-4** — d=768·유효배치 131K에는 2e-3이 과다(발산 원인).

## 파일 구성

| 경로 | 역할 |
|---|---|
| `architecture_v5/tied_mlp_transformer.py` | v5 아키텍처 정의. `TMTConfig`, `TiedMLPTransformer`, `dense_baseline()` |
| `architecture_v5/run100m.py` | 데이터 준비 / 학습 / 평가 / 비교 파이프라인 (단일 진입점) |
| `architecture_v5/spec_v5.py` | 파라미터·메모리·KV·CPU/GPU 회계 계산기 |
| `train_eval.py` | 스모크 테스트 + 간이 학습 스캐폴드 |
| `rank_spectrum_v3.py` | 널 대조군 있는 랭크 스펙트럼 측정 (HF 모델 대상, depth-delta 폐기 근거) |
| `handoff/` | 세션 인수인계 문서 (정본 진행 상태) |
| `article/` | 참고 논문 PDF (Tying the Loop, RMoE, SISA 등) |
| `architecture_v4/` | 직전 버전 보존 (v4, NaN 발산본) |

## 빌드 · 실행

학습은 **CUDA GPU(RTX 4070 Ti)** 에서 사용자가 직접 실행한다. `torch`, `datasets`,
`tokenizers` 필요.

```bash
cd architecture_v5

# 파이프라인 동작 확인(합성, 컴파일 포함) — 수 분
python run100m.py all --tiny --data synthetic --tokens 2M --steps 40 \
    --micro-bs 4 --seq 128 --accum 2 --eval-every 20 --compile

# 데이터 준비(캐시 있으면 생략)
python run100m.py prepare --data ko-en --tokens 300M

# 학습(dense·tied 자동) + 비교
python run100m.py all --data ko-en --tokens 300M --steps 2289 \
    --micro-bs 8 --seq 1024 --accum 16 --lr 6e-4 --eval-every 100 --compile
```

**판정 기준** (`compare` 출력의 손실 격차):
- `≤ +0.07` → 아키텍처 성립. g를 6, 8로 올리며 한계 탐색
- `+0.07 ~ +0.15` → prelude/coda를 3+3으로 늘리거나 g=2로 후퇴
- `> +0.15` → `|g|max` 먼저 확인. 10 이상이면 학습 문제지 아키텍처 문제 아님

## 작업 규약

- **한글 본문 · 영문 식별자.** 설계 문서·주석의 서술은 한글, 변수·파일명·수식 기호는 영문/수학 기호.
- **파라미터 단일 소스.** 기본값은 `make_config()`/`TMTConfig` 한 곳에서 정의한다 — 하드코딩 산재 금지.
- **AI는 사용자 환경에서 코드를 직접 실행하지 않는다.** 수정만 하고, 실행이 필요하면
  실행할 명령어와 순서를 사용자에게 제시해 대리 수행을 요청한다(GPU 사용량·시간 보호).
- **git 은 사용자가 Windows 셸에서 수행한다.** 이 리포는 Cowork 마운트에서 rename/unlink가
  차단되어 샌드박스에서 git 쓰기가 불가하다. 파일 생성·수정은 가능.

## `.claude/skills/` — 워크플로우 스킬

`.claude/skills/` 에 범용 작업 스킬 13종이 있다: `plan-doc`, `pr-workflow`, `impact-analysis`,
`session-handoff`, `check-and-verify`, `to-prd`, `to-issues`, `triage`, `grill-me`,
`grill-with-docs`, `zoom-out`, `setup-matt-pocock-skills`. 일부(plan-doc/pr-workflow/
impact-analysis/session-handoff)는 `.claude/project.json` 에서 프로젝트 상수를 읽도록
범용화돼 있으나, 현재 이 리포에는 `project.json` 이 없어 기본값으로 동작한다.
