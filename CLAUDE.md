# CLAUDE.md

이 파일은 Claude가 이 저장소에서 작업할 때 매 프롬프트 참조하는 지침이다. **간결 유지**가 원칙 —
상세는 아래 정본/참고 문서로 뺀다.

## 이 리포는 무엇인가

**TinyLM** = 저사양 CPU·엣지·모바일용 **초경량 LLM 아키텍처**. 핵심 목표는 **연산이 아니라
메모리 최적화**(연산 증가는 감수). 지향점: dense 대비 절반 이하 메모리로 유사 품질.

> **현재 상태(2026-07-30, 1차 리뷰 시점):** 아키텍처 v5(QK-norm 등 안정화), 코드 v6(`tinylm/`).
> 최적 조합 = **삼진 + MLP 타잉(g8) + 부모초기화 + KD 정적 k4**, 여기에 **3:4 희소(1.25bpw)** 로
> **10.3MB(3.00×) / +0.061** 까지 확인(결과 008). 다음 = `run100m_REVIEW1.bat`(최적안 3개 공정풀 검증),
> P026(구현완료·실측대기), P022(0단계 게이트 **통과** — 결과 010, 1단계는 σ·REVIEW1 후).
> **1차 리뷰 정본: [`docs/review/202607301200_1차리뷰_실험종합및최적모델3안.md`](docs/review/202607301200_1차리뷰_실험종합및최적모델3안.md)** —
> 기법별 채택/보류/폐기 판정과 최적 모델안 3개가 여기에 있다. 새 실험 제안 전 반드시 읽는다.

## 정본 / 참고 문서

- **코드가 정본이다.** 현재 아키텍처·구조는 `tinylm/` 패키지가 진실의 원천.
- **확정 스펙·설계 근거·안정화 이력**: `handoff/` 의 최신 메모(참고용 스냅샷).
- **실행 방법·실험 계획**: `test_plan/{계획번호}_{요약}.md` + `test_plan/실험계획목록.md`.
- **방법론 원장**(기법별 상태·트레이드오프): `docs/METHODS.md` + `docs/methods/`.
- **실험 결과**: `test_result/{번호}_{시간}_{요약}.md` + `test_result/실험목록.md`.
- **종합 리뷰**(누적 판정·기법 채택 수준·모델안): `docs/review/`. 개별 결과보다 **상위 판단**이 여기 있다.
- **실험 조건 기준표**: `docs/EXPERIMENT_BASELINES.md` — 표준조건·런 레지스트리·비교유효성 규칙·
  태그 네임스페이스·VRAM 예산·확정된 사실. **새 실험 설계 시 여기와 대조**(`exp-preflight` 스킬).

## 코드 구조 — `tinylm/` 패키지 (정본)

버전마다 전체 파일을 복사하지 않는다. 아키텍처 실험은 `config.py` 프리셋만 바꾼다.

```
tinylm/
  paths.py            작업폴더 기준 경로 + HF 캐시 리다이렉트(import 부작용)
  config.py           TMTConfig + PRESETS(tiny/m100/m100d) + build_config + dense_baseline
  model/              ternary.py · modules.py(RMSNorm/RoPE/Attention[QK-norm]/MLP/Layer) · transformer.py
  data/               prepare.py(토큰화+크기별 캐시) · loader.py
  train/              trainer.py(어닐·NaN가드·EMA·WSD·베스트ckpt·KD) · lr_finder.py · init_utils.py
  eval/               evaluate.py · compare.py
  infer/              generate.py(체크포인트 로드+샘플링)
  cli.py              단일 진입점(prepare/train/eval/compare/all/lrfind/generate)
run100m.py            호환 래퍼 → tinylm.cli.main
```

작업폴더에 자동 생성(모두 gitignore): `HF/`(모델·데이터셋 캐시), `data_cache/`(토큰 바이너리,
크기별 재사용), `runs/`(ckpt·logs). `paths.py` 가 외부 `HF_HOME` 을 무시하고 HF 캐시를 **강제로
`HF/`** 로 돌린다(허브 캐시 = `HF/hub`). 다른 위치는 실행 전 `TINYLM_HF=<경로>`.

## 작업 규약

- **한글 본문 · 영문 식별자.** 서술은 한글, 변수·파일명·수식 기호는 영문/수학 기호.
- **파라미터 단일 소스.** 기본값은 `config.py` 의 `TMTConfig`/`PRESETS` 한 곳 — 하드코딩 산재 금지.
- **기준 학습토큰 = steps × micro_bs × accum × seq**(= 유효배치×steps). `--tokens` 는 데이터 캐시
  크기일 뿐 학습 길이가 아니다. **300M 기준선 = `--micro-bs 8 --accum 16`(유효배치 131K)**.
  이를 빠뜨리면(기본 accum8) 150M만 학습된다(005 혼입 사례). ms/step 은 accum 에 ~선형이라
  "accum 조정으로 step 반감"은 **총 벽시계 이득이 아니다**(연산 바운드).
- **주요 실험 플래그**: `--mlp-group`(타잉 g), `--init-from`(부모초기화), `--kd`(온라인 KD),
  `--kd-every K [--kd-dynamic]`(교사 forward 1/K, skip-forward — **기본 권장 = 정적 k4**),
  `--kd-teacher-tag`(압축 교사), `--sparse34`(3:4 희소 삼진 1.25bpw, 표준 경로 전용),
  `--no-ckpt`(grad ckpt off, **-17.3%**), `--anneal-end F`·`--decay-frac F`(P026 cooldown-QAT 정렬,
  기본값 0.60/0.2 = 종전 동작), `--seed N`(기본 1337=종전 동작. 초기화+train 크롭 순서에 반영,
  **val 크롭은 99 고정** — 흔들면 런 비교가 깨진다. σ 측정용).
- **★데이터 풀은 학습토큰의 2배 이상**(결과 006). Loader가 캐시 전체에서 랜덤 샘플하므로 풀이
  작으면 반복 노출로 손해 — **같은 300M 학습에서 풀 300M→600M 만으로 dense가 0.12 개선됐다.**
  신규 기준선은 `--pool-tokens 600M --exact-cache` 로. 풀이 다른 런끼리는 **직접 비교 금지.**
  `--init-from-tag TAG`(정본 dense 대신 태그된 dense에서 초기화·증류 → 정본 미오염).
- **VRAM 한계(16GB, 스필벽 13~14GB)**: dense+`--no-ckpt` = 13.5GB(안전). micro_bs↑는 **이득 0**이고
  스필만 유발 → 폐기. **tied+KD+dense교사에는 `--no-ckpt` 금지**(15.7GB 이상, OOM 위험).
- **속도 비교는 정상상태로**: 로그 `ms/step` 은 누적 평균이라 compile 첫 스텝이 섞인다.
  `(누적평균×N − step0)/(N−1)` 로 환산하고, 유효배치가 다르면 토큰당으로 정규화한다.
- **스윕·벤치 배치파일은 한 런 실패로 중단되지 않게** — `if errorlevel 1 echo [WARN] ... - continuing`.
  `goto ERROR` 는 선행 의존 단계(prepare, 교사 학습)에만.
- **AI는 사용자 환경에서 코드를 직접 실행하지 않는다.** 수정만 하고, 실행이 필요하면
  명령어·순서를 제시해 대리 수행을 요청한다(GPU 사용량·시간 보호).
- **git 은 사용자가 Windows 셸에서 수행한다.** Cowork 마운트에서 rename/unlink가 차단되어
  샌드박스 git 쓰기 불가(파일 생성·수정은 가능). `.claude/` 도 파일툴 차단 → 셸 마운트로 기록.

## 산출물·기록 규칙 (문서/실험)

- **방법론**: 기법을 제안·적용할 때마다 `docs/methods/0N_*.md` 해당 표에 행을 추가·갱신
  (상태·버전·작동원리·트레이드오프·특기). living document.
- **실험 계획**: 어떤 아키텍처·명령줄로 무슨 목적을 검증하는지 `test_plan/{계획번호}_{요약}.md` 에
  기록하고 `test_plan/실험계획목록.md` 갱신.
- **실험 결과**: `test_result/{실험번호}_{YYYYMMDDHHMMSS}_{요약}.md` 로 기록(어느 계획 P번호
  기반인지 명시)하고 `test_result/실험목록.md` 갱신. 같은 실험군은 한 파일에 이어 쓰고, 성격이
  다르면 새 번호로 분리(파편화 여부로 판단).
- **체크포인트·로그는 스케일별로 분리**: `runs/ckpt/{preset}_{data}_{tokens}_{arch 또는 tag}.pt`.
  다른 토큰/프리셋/태그가 서로 덮어쓰지 않는다(재측정 시 재학습·오염 방지).
- **외부 근거 표기.** 논문·기법·데이터셋을 인용·도입할 때 계획/결과/방법론 문서에 근거 링크를
  함께 남긴다: 논문은 arXiv id, 데이터셋·모델은 HF id, 그 외는 URL(재현·검증 추적용).

## 판정 기준

`compare` 손실 격차: `≤ +0.07` 성립 / `+0.07~+0.15` prelude·coda↑ 또는 g↓ /
`> +0.15` 는 `|g|max` 먼저 확인(10 이상이면 학습 문제).

> **★단서(미해결)**: 이 임계값은 **재현 노이즈 σ 실측 없이** 쓰이고 있다. 따라서 **`≤0.05` 급 차이를
> "차이 있음"으로 단정하지 말 것.** 실측(P021 추가검증 A)이 나오면 임계를 `max(0.07, 2σ)` 로 갱신한다.
> 결과 007의 "동일 런 0.11 nats 발산"은 `grad_max` 10.8~35.4 의 **불안정 구간** 값이라 **σ 의
> 추정치로 인용 금지**(2289스텝 런은 `grad_max` 0.5~1.2 로 안정).
> **짧은 런(250스텝급)의 val 은 품질 비교에 쓰지 않는다** — 속도만 읽는다.
> **안정성 판정은 인쇄된 `|g|`(10스텝 샘플) 가 아니라 json `grad_max`**(warmup 이후 전 스텝 최대)로
> 한다. sp_base 인쇄 최대 4.51 vs 실제 10.79.

## 알려진 함정 (측정·문서 신뢰도)

- **배포메모리**: ✅ 수정됨 — `transformer.mem_breakdown()` 단일 소스 + json `deploy_mb` 기록.
  **단 구 로그(2026-07-30 이전)에는 `deploy_mb` 가 없어** compare 가 `~` 근사로 표시하고,
  sparse34 구 로그는 여전히 과소다. 그 경우 **정확값은 학습 로그 상단 `report()` 블록**.
- **`docs/METHODS.md` 핵심 측정치 절이 낡았다**(tied 기준선 3.9452/+0.1178 → 로그는 3.95578/+0.132).
  수치를 인용할 땐 `runs/logs/*.json` 을 정본으로.
- **교차데이터셋 bpb 비교는 무효** — 토크나이저·val셋이 다르면 성립하지 않는다(결과 009).
  공통 원문 eval 셋이 필요하다(P028).
- **σ(재현 노이즈) 미측정** — `--seed` 는 구현됐고(기본 1337=무변) 측정은 `run100m_REVIEW1.bat` [1]
  (`p6d_s2`) 대기. 그때까지 `≤0.05` 급 차이를 단정하지 않는다.
- **구 로그(2026-07-30 이전)에는 `pool_tokens`·`mlp_group`·`micro_bs`·`accum`·`deploy_mb`·`seed` 가
  없다** → 로그만으로 조건 복원 불가. 과거 조건은 `docs/EXPERIMENT_BASELINES.md` §2 레지스트리로 본다.

## `.claude/skills/` — 워크플로우 스킬

**이 프로젝트 전용 3종(실험 루프)** — 해당 맥락이면 반드시 적용:

| 스킬 | 언제 | 무엇을 막는가 |
|---|---|---|
| **`exp-preflight`** | 새 학습 명령·배치·계획서를 만들기 **전** | 조건 중복·토큰 환산 오류·태그 충돌·무효 비교. 기준 정본 = `docs/EXPERIMENT_BASELINES.md` |
| **`log-to-result`** | 학습 로그를 받았을 때 | 로그 인쇄값 오인용(누적평균 ms/step, 10스텝 샘플 `\|g\|`, sparse34 메모리), 연쇄 갱신 누락 |
| **`run-batch`** | `.bat` 작성·수정 | 비ASCII·`<>\|%`·chcp, `--tag` 누락, 한 런 실패로 배치 전체 중단 |

보조 스크립트: `scripts/check_run_registry.py`(레지스트리 조회·중복·태그 점검),
`scripts/lint_bat.py`(배치 린터). 둘 다 **문법·중복만** 본다 — 실험이 옳은지는 보증하지 않는다.

범용 스킬 12종도 있다. 특히 유용: `session-handoff`(인수인계), `grill-with-docs`(설계 반론),
`impact-analysis`(변경 영향), `check-and-verify`(산출물 검증). `.claude/project.json` 존재
(프로젝트 메타·실행규약).

## 폴더 정리

`architecture/`(단일파일 v5 이력), `spec/`(spec_v4), `util/`(rank_spectrum_v3), `handoff/`(스펙·
설계 스냅샷), `article/`(참고 논문), `docs/`(방법론 원장 + `docs/review/` 종합 리뷰),
`scripts/`(벤치·진단 스크립트), `test_plan/`(실험 계획), `test_result/`(실험 기록),
루트 실행 배치: `run100m_REVIEW1.bat`(최적안 3안 + σ) · `run100m_P026.bat` · `run100m_P007B.bat`
(풀 포화점) · `run100m_P021B.bat`(mb 재스윕) · `run_P022_bench.bat` · `run_P028_diag.bat`(캐시 진단) ·
완료분 `run100m_P007.bat`·`run100m_P021.bat`(템플릿 재활용 가치가 있어 보존).
P012·P016·P017(=`run100m_test.bat`) 배치는 **삭제됨** — 명령은 각 결과문서 §재현 명령과
P017 계획서에 보존되어 있다(삭제 전 기계 대조 완료).
신규 코드 작업은 `tinylm/` 에서만 한다.
