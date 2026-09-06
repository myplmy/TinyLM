# PM000__MOONSHOT__LATIN_GQA — 실행 결과

> 현재 판정: **Stage0/Stage0B 배선 계약 PASS / 최신 전체 smoke RED(수정 전) / sparse34 수정 후 재검증 대기 / 품질 효과 미측정**
> 실행일: 2026-09-06 (사용자 실행)
> 분석일: 2026-09-06
> 계획: [`PM000__MOONSHOT__LATIN_GQA__PLAN.md`](../plan/PM000__MOONSHOT__LATIN_GQA__PLAN.md)

## 1. 결론

PM000의 pass-dependent Latin GQA 구현은 전용 모듈 격리 후에도 사용자가 실행한 최신
공통 smoke의 PM arm과 Stage0B에서 의도한 경로를 실제로 탔다. Stage0B는 원 Stage0와
같은 여섯 배선 계약을 모두 통과했고, PM smoke JSON에 schedule·seed·order·repeat·CLA
값이 전용 tag로 기록됐다.

그러나 이것은 **성능 향상 결과가 아니다**. fixed/latin/random matched 품질 비교는 아직 한 번도
수행되지 않았고, 30-step synthetic loss는 배선 확인용이라 일반지능이나 제품 품질의 근거로
사용할 수 없다.

또한 09:51에 시작한 최신 저장소 전체 smoke는 34개 runlog arm 중 2개가 nonzero라서
PASS가 아니다. PM000 arm과 instrumentation은 통과했지만 `check_links.py` exit 5와
`diag_sparse34_pack.py` exit 1이 남았다. 로그 분석 후 sparse34의 10비트→8비트 손실
원인을 수정했지만, AI는 torch 진단과 `.bat`을 실행하지 않았으므로 최신 관측 판정은
여전히 **전체 smoke RED / 수정 후 재검증 대기**다.

## 2. 증거와 provenance

| 구분 | 정본 | 소스 상태 | 판정 |
|---|---|---|---|
| 최초 저장소 smoke | [`202609060852_smoke_e0330e3.txt`](../smoketest_logs/202609060852_smoke_e0330e3.txt) | `e0330e3 +dirty 27개` | PM arm PASS, 전체 FAIL |
| PM000 Stage0 | [`202609060859_PM000__MOONSHOT__Stage0_contract_e0330e3.txt`](202609060859_PM000__MOONSHOT__Stage0_contract_e0330e3.txt) | `e0330e3 +dirty 28개` | PASS |
| 최신 저장소 smoke | [`202609060951_smoke_e0330e3.txt`](../smoketest_logs/202609060951_smoke_e0330e3.txt) | `e0330e3 +dirty 47개` | 격리 후 PM arm/contract PASS, 전체 FAIL |
| PM000 Stage0B | [`202609061050_PM000__MOONSHOT__Stage0B_postrefactor_e0330e3.txt`](202609061050_PM000__MOONSHOT__Stage0B_postrefactor_e0330e3.txt) | `e0330e3 +dirty 48개` | PASS |
| 최신 PM smoke JSON | [`tinygqa_synthetic_2M_dense_pm000__sm_gqapass.json`](../runs/logs/tinygqa_synthetic_2M_dense_pm000__sm_gqapass.json) | 최신 smoke 실행 산출물 | 계측 계약 PASS |

`+dirty`이므로 이 결과들은 커밋 `e0330e3` 단독이 아니라 **그 커밋과 각 실행 시점
미커밋 변경의 합**을 검증한다. Stage0B는 PM000 격리 리팩터링 후 새 동적 증거이다.
다만 그 뒤 sparse34 포맷 코드를 바꾸었으므로 수정 후 전체 smoke 증거는 아직 없다.

첫 smoke는 tag 격리 보강 전에 `sm_gqapass`로 실행되어 로컬 일반 registry에도 smoke 행이
생겼다. 역사적 실행 기록을 이 작업에서 삭제하지는 않았다. 후속 smoke는
`dense_pm000__sm_gqapass`를 사용하고 `runlog.py`가 그 tag를 일반 registry에서 제외한다.

## 3. Stage0와 Stage0B 계약 결과

사용자 실행 배치:
[`run_PM000__MOONSHOT__Stage0_contract.bat`](../moonshot_batch/run_PM000__MOONSHOT__Stage0_contract.bat)

| 계약 | 관측값 | 판정 | 해석 |
|---|---:|---|---|
| schedule 정의·결정성 | random seed 17 = `[0, 3, 2, 1, 4]` | PASS | pass 0 identity와 완전 순열 확인 |
| parameter/state 불변 | `36,136` params, `47` keys | PASS | 새 학습 파라미터·state key 없음 |
| R1 exact identity | exact equality | PASS | 첫 pass에서 처치가 기존 출력을 바꾸지 않음 |
| R3 treatment-live | `max_abs_delta=6.521e-03` | PASS | latin 회전이 죽은 플래그가 아님 |
| full/cached 일치 | `max_abs=3.539e-08`, `kv_entries=4` | PASS | cache 원본을 오염시키지 않는 범위에서 일치 |
| finite backward | `loss=0.000030`, `grad_tensors=47` | PASS | 검사한 작은 모델에서 gradient가 유한 |

원 Stage0와 격리 리팩터링 후 Stage0B의 수치는 위 표와 같이 일치한다. 두 로그의
종료코드는 모두 0이고 최종 문구는 `PM000 CONTRACT PASS`다. Stage0B가 통과했으므로
리팩터링 후 동적 재검증 공백은 닫혔다. 이는 작은 모델의 correctness 계약만 검사하므로
CE 크기 자체는 품질 지표가 아니다.

## 4. PM000 smoke arm

smoke 안의 PM arm은 다음 명령 조건으로 수행됐다.

```text
preset=tinygqa, arch=dense, data=synthetic, steps=30,
micro_bs=4, seq=128, accum=2, compile=on,
cla_group=2, train_repeat=3.0, gqa_pass_schedule=latin, gqa_pass_seed=0
```

| 항목 | 관측값 |
|---|---:|
| 실제 토큰 | `30,720` |
| parameter | `5,462,284` |
| schedule / order | `latin` / `[0, 1]` |
| final / best val loss | `9.884375` / `9.8825` |
| gradient max / warmup peak | `0.807831` / `0.857166` |
| skipped steps | `0` |
| wall time | `34.8172 s` |
| CUDA reserved / allocated peak | `0.396484375 / 0.308115959 GB` |
| packed / runtime / runtime+KV | `1.124373499 / 33.586959839 / 40.586959839 MiB` |
| KV | `7` entries, `14` visits, `7.0 KiB/token`, `7.0 MiB @ 1024` |

`scripts/check_smoke.py`는 최신 `dense_pm000__sm_gqapass` arm의 필수 필드와
`latin / seed 0 / order [0,1] / R3 / dense / CLA2` 값을 모두 확인했다. 위 loss는 대조군이
없는 30-step synthetic 값이므로 개선·악화 판정에는 사용하지 않는다. compile 경고
`Not enough SMs to use max_autotune_gemm mode`는 이 arm의 종료코드를 바꾸지 않았다.
최초 smoke의 wall `61.3089 s`와 최신의 `34.8172 s`는 compile/cache 상태를 통제한 matched
보고가 아니므로 성능 차이로 해석하지 않는다.

## 5. 전체 smoke의 두 실패

09:51 최신 로그에 대한 `scripts/summarize_smoke.py`의 사후 판독 결과는 runlog arm 34개,
nonzero 2개,
“exit 0인데 error marker” 0개다.

| 실패 | 종료코드 | 관측 | PM000 판정과의 관계 |
|---|---:|---|---|
| `scripts/check_links.py` | 5 | `data_cache/*/meta.json` 로컬 상대링크 5건 결손 | 기존 환경/로컬 캐시 문제; PM 배선 PASS를 뒤집지는 않음 |
| `scripts/diag_sparse34_pack.py` | 1 | `234,505 / 1,000,000` 왕복 mismatch, 실측 `1.000000 bpw` 대 기대 `1.250 bpw` | PM000과 독립인 기존 sparse34 경로 결함 |

따라서 두 층의 판정은 분리한다.

- **PM000 Stage0와 PM smoke arm:** PASS
- **저장소 전체 smoke:** FAIL

sparse34의 직접 원인은 5비트 code 두 개를 `code0 * 32 + code1`로 합친 뒤 `uint8`로
변환한 것이다. 최대 10비트인 값의 상위 2비트가 잘리며 첫 코드의 zero-position이 손실됐고,
`sparse34_bytes()`도 동일한 잘못된 “2 code/byte” 가정으로 1.0 bpw를 반환했다.

확인한 업데이트된 `main` HEAD `486d71d`에서도 `e0330e3` 이후 해당 두 파일의 변경은
없었고 구현이 동일했다. 따라서 main을 합치지 않고 이 branch에서 `8 code = 40 bit =
5 byte` 연속 포맷으로 교체했다. 목표 크기는 `ceil(groups * 5 / 8)`이다. torch를 쓰지
않는 독립 oracle 321건과 `py_compile`, 정적 import 검사는 PASS했다. 실제 tensor 왕복과
smoke는 **수정 후 미실행**이므로 PASS를 선언하지 않는다.

## 6. 주장 가능 범위

현재 증거로 주장할 수 있는 것은 다음뿐이다.

- 실제 nontrivial GQA에서 non-fixed 처치가 활성화된다.
- R1 identity, state/parameter 불변, 작은 full/cached 일치, finite backward를 만족한다.
- 측정된 smoke에서는 NaN, skipped step, PM 계측 필드 누락이 없었다.

현재 증거로 주장할 수 없는 것은 다음이다.

- Latin GQA가 fixed보다 CE·정확도·일반지능을 높인다.
- 추가 KV 저장량 0이 activation scratch·latency·runtime peak 비용 0을 뜻한다.
- 한 seed 또는 synthetic smoke가 실제 ko-en 학습·held-out 품질을 대표한다.
- branch 전체가 회귀 없이 건강하다.

## 7. 다음 단계 판정

계획상 다음 품질 실험은
[`run_PM000__MOONSHOT__Stage1_r2_signal.bat`](../moonshot_batch/run_PM000__MOONSHOT__Stage1_r2_signal.bat)의
fixed/latin/random matched triad다. 다만 현재 즉시 실행 판정은 **HOLD**다.

1. PM000 격리 후 공통 smoke PM arm과 Stage0B는 모두 PASS했다.
2. 그러나 최신 공통 smoke는 sparse34 수정 **전** 증거다. 사용자가 수정 후
   `run_smoke_check.bat`를 재실행해 실제 왕복 0 mismatch·1.250 bpw를 확인해야 한다.
3. `check_links` exit 5는 sparse34와 별개로 남을 가능성이 크다. 새 smoke 로그를 받아 전체
   정책 gate의 처리를 분리 판정하기 전에는 Stage1/Stage1E/Stage2/Stage2E를 실행하지 않는다.

Stage1 정적 preflight 자체는 완료됐다. 세 tag는 모두 미사용이고, 세 팔은 각
`763 × 8 × 16 × 1024 = 100,007,936` tokens, 20 layer visits, CLA2, grad checkpoint on으로
일치한다. `--no-ckpt`를 쓰지 않은 것은 R2/R3 안전 조건을 맞추기 위한 사전등록 선택이다.
이 정적 준비 완료는 위 HOLD를 해제하지 않는다.

## 8. 누적 판정표

| 단계 | 상태 | 품질 결론 |
|---|---|---|
| 최초 공통 smoke (2026-09-06 08:52) | 전체 FAIL, PM arm PASS | 없음 |
| Stage0 contract (2026-09-06) | PASS | 없음 — wiring only |
| post-refactor 공통 smoke (2026-09-06 09:51) | 전체 FAIL, PM arm/contract PASS | 없음 |
| post-refactor Stage0B (2026-09-06 10:50) | PASS | 없음 — wiring only |
| sparse34 포맷 수정 | 정적 PASS / 동적 PENDING | 없음 — PM000 품질과 독립 |
| Stage1 R2 matched triad | HOLD | 미측정 |
| Stage1E paired full-val | NOT STARTED | 미측정 |
| Stage2 R3 matched triad | NOT STARTED | 미측정 |
| Stage2E paired full-val | NOT STARTED | 미측정 |

## 9. 결과 분석 후 구현 상태

Stage0 분석 뒤 향후 선택 이식 충돌을 줄이기 위해 알고리즘을
[`tinylm/moonshot/pm000_latin_gqa.py`](../tinylm/moonshot/pm000_latin_gqa.py)로 분리하고
[`이식 manifest`](../tinylm/moonshot/README.md)를 추가했다. 공통 smoke의 후속 PM tag도
`dense_pm000__sm_gqapass`로 격리했다.

변경 후 torch-free 검증에서는 py_compile, pure-core schedule/validation/pass counter/shift,
import/attribute/call-kwargs, PM namespace, smoke field/coverage, batch name/flag/lint/dry-run이
통과했다. 전체 정적 스위트는 32종 중 29종 PASS이며, 남은 세 실패는 다음과 같다.

- 기존 held-out D6: `E-157`, `E-205`
- 로컬 gitignored 상대링크 결손 5건
- 사용자 smoke가 만든 일반 `tiny_synthetic_2M_dense.json`의 일반 registry 미등재 1건

이 세 건은 PM000 전용 정적 계약의 실패는 아니지만 전체 저장소 green을 뜻하지도 않는다.
사용자의 최신 smoke와 Stage0B가 PM000 격리 후 동적 공백은 닫혔다. 그 뒤 수정한
`tinylm/model/lut.py`의 sparse34 함수는 검색상 PM000 학습·진단 caller에서 사용되지 않지만,
이 수정 자체의 torch 동적 검증과 수정 후 전체 smoke는 사용자 실행 대기다.
