# CLAUDE.md

이 파일은 Claude가 이 저장소에서 작업할 때 매 프롬프트 참조하는 지침이다. **간결 유지**가 원칙 —
상세는 아래 정본/참고 문서로 뺀다.

## 이 리포는 무엇인가

**TinyLM** = 저사양 CPU·엣지·모바일용 **초경량 LLM 아키텍처**. 핵심 목표는 **연산이 아니라
메모리 최적화**(연산 증가는 감수). 지향점: dense 대비 절반 이하 메모리로 유사 품질.

> **현재 상태:** 아키텍처 v5(QK-norm 등 안정화), 코드 v6(`tinylm/` 패키지). 100M급에서 dense vs
> tied 손실 격차 측정·축소 실험 중. P016 **3:4 희소 삼진(`--sparse34`, 1.25bpw) 구현 완료**.
> P017(skip-forward/dynamic KD) 300M `--accum 16` 재측정 진행 중.

## 정본 / 참고 문서

- **코드가 정본이다.** 현재 아키텍처·구조는 `tinylm/` 패키지가 진실의 원천.
- **확정 스펙·설계 근거·안정화 이력**: `handoff/` 의 최신 메모(참고용 스냅샷).
- **실행 방법·실험 계획**: `test_plan/{계획번호}_{요약}.md` + `test_plan/실험계획목록.md`.
- **방법론 원장**(기법별 상태·트레이드오프): `docs/METHODS.md` + `docs/methods/`.
- **실험 결과**: `test_result/{번호}_{시간}_{요약}.md` + `test_result/실험목록.md`.

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
  `--kd-every K [--kd-dynamic]`(교사 forward 1/K, skip-forward), `--kd-teacher-tag`(압축 교사),
  `--sparse34`(3:4 희소 삼진 1.25bpw, 표준 경로 전용), `--no-ckpt`(grad ckpt off, 속도).
- **데이터 풀 제어(토큰스윕)**: `--pool-tokens N`(데이터 풀을 학습길이·이름과 분리 — Loader가 캐시
  전체에서 랜덤 샘플하므로 모든 예산을 같은 풀에서 뽑아야 공정), `--exact-cache`(상위호환 무시, 정확한
  크기 캐시), `--init-from-tag TAG`(정본 dense 대신 태그된 dense에서 초기화).
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

## `.claude/skills/` — 워크플로우 스킬

범용 스킬 13종. 특히 유용: `session-handoff`(인수인계), `grill-with-docs`(설계 반론),
`impact-analysis`(변경 영향). `.claude/project.json` 존재(프로젝트 메타·실행규약).

## 폴더 정리

`architecture/`(단일파일 v5 이력), `spec/`(spec_v4), `util/`(rank_spectrum_v3), `handoff/`(스펙·
설계 스냅샷), `article/`(참고 논문), `docs/`(방법론 원장), `test_plan/`(실험 계획),
`test_result/`(실험 기록). 신규 코드 작업은 `tinylm/` 에서만 한다.
