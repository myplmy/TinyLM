# 044 — P057 단계0: **측정 0건. `build_attention` 미import 로 3팔 전부 죽었다**

- **계획**: [P057](../test_plan/P057_어텐션-타잉-남은-최대축.md) 단계0
- **로그**: [`044_log_20260814_P057_stage0_attn-error.txt`](044_log_20260814_P057_stage0_attn-error.txt)
- **배치**: `run_P057_stage0_attn_gate.bat` (2026-08-14, GPU 진단, 3팔 각 0.1분, **종료코드 1 / 1 / 1**)
- **도구**: `scripts/diag_depth_init.py --attn-group {2,4,8} --modes prop`

---

## 0. 한 줄

> 🚫**어텐션 타잉 게이트는 아직 아무것도 재지 않았다.** `attn_group` 2·4·8 세 팔이
> **모델을 짓는 첫 줄에서** 똑같이 죽었다:
>
> ```
> File "Z:\TinyLM\tinylm\model\transformer.py", line 53, in __init__
>     self.mid_attns = nn.ModuleList([build_attention(cfg, True)
> NameError: name 'build_attention' is not defined
> ```
>
> ★**`build_attention` 은 `modules.py` 에 **존재한다**(L21). `transformer.py` 의 **import 목록에만
> 없었다.** 한 줄짜리 결함이고, 아키텍처·이식 로직과는 무관하다.
>
> ★★**그런데 이 결함은 스모크를 통과했다.** 같은 밤 `run_smoke_check.bat` 이 **총 에러 0건**을 찍었다.

---

## 1. 무엇이 죽었나 — 3팔 전부, 같은 자리

| 팔 | 명령 | 결과 |
|---|---|---|
| `attn_group 2` | `--preset m100R1c --teacher-preset m100 --attn-group 2 --modes prop` | 🚫 `NameError` (0.1분) |
| `attn_group 4` | 〃 `--attn-group 4` | 🚫 `NameError` (0.1분) |
| `attn_group 8` | 〃 `--attn-group 8` | 🚫 `NameError` (0.1분) |

★**죽은 지점은 난수 대조군 팔**이다 — 로그의 `모드 (난수 대조군)` 헤더 직후.
즉 **이식(`init_from_dense`)에는 도달조차 못 했다.** `attn_group` 관련 코드 중
**실행된 것은 `TiedMLPTransformer.__init__` 의 `ag > 1` 분기 한 줄뿐**이다.

⚠️**따라서 다음은 전부 미검증이다** — 이번 로그로 판정하지 않는다:

- 그룹평균 어텐션 이식(`init_utils.py` L219~251)이 옳게 도는가
- 공유 어텐션이 CLA 소유층/재사용층 양쪽에 서는 것이 성립하는가
- `attn_group` 별 step0 CE, 난수 대조군과의 GAP
- g 가 커질 때 값어치가 어디서 무너지는가

## 2. ★원인 — **정의는 있는데 import 가 없었다**

```python
# tinylm/model/modules.py L21  — 정의는 여기 있다
def build_attention(cfg, owns_kv): ...

# tinylm/model/transformer.py L16 (수정 전)  — 이 목록에 없었다
from .modules import RMSNorm, Attention, MLP, Layer, build_rope, apply_rope
```

`Layer.__init__`(L154)은 **같은 파일(`modules.py`) 안**이라 정상 동작했다.
`transformer.py` 에서 부르는 곳은 **`attn_group > 1` 일 때 만드는 공유 풀**(L53) **하나뿐**이다.

> ★**그래서 기본 경로는 완전히 멀쩡했다.** `attn_group = 1`(=종전 전부)에서는
> `if ag > 1:` 이 거짓이라 그 줄이 **아예 실행되지 않는다.**
> 학습·평가·추론 어디에도 영향이 없었고, **P057 을 켠 순간에만** 죽는다.

## 3. ★★왜 스모크가 못 잡았나 — **필드가 기록되는 것 ≠ 코드 경로가 실행되는 것**

같은 밤 `smoketest_logs/202608140030_smoke_0837c15.txt` 는 **총 에러 0건**이다.
`check_smoke.py` 의 필수 필드 목록에는 **`attn_group` 이 이미 들어 있었다**(L39).

| 스모크가 한 것 | 스모크가 **안 한 것** |
|---|---|
| json 에 `attn_group` **키가 실렸는지** 확인 (6팔 전부 값 1) | `attn_group` 을 **1 이 아닌 값으로 모델을 지어 본 것** |
| `mlp_split` 키 확인 (전부 `[]`) | `mlp_split` 을 **실제로 준 것** |

★**이것이 함정 10 의 새로운 얼굴이다.** 지금까지의 계열은
*"미구현 플래그로 배치 작성"*(함정 10) → *"파서에 있는데 전달이 안 된다"*(함정 21·31) 였고,
이번은 **"플래그도 있고 전달도 되는데 그 분기가 한 번도 실행된 적이 없다"** 이다.
`check_batch_flags.py` 는 이름만 보고, `check_smoke.py` 는 **기록된 값만** 본다.
**둘 사이에 "그 값으로 실제로 돌려 본다" 가 비어 있었다.**

> ⚠️**`CLAUDE.md` 의 지침은 이미 옳았다** — *"파서에 있는 것과 실제로 전달되는 것은 다르므로
> 코드 경로를 눈으로 확인한다"*, *"코드를 고쳤으면 `run_smoke_check.bat`"*.
> **둘 다 했다.** 눈으로 따라간 것은 `--attn-group` 이 `cfg.attn_group` 에 닿는 경로였고
> (그건 맞았다), 스모크는 **그 분기를 타지 않는 6팔**이었다.
> → **규칙이 아니라 스모크의 커버리지가 문제였다.**

## 4. 조치 (전부 diff 확인)

| # | 파일 | 무엇 |
|---|---|---|
| 1 | `tinylm/model/transformer.py` | **`build_attention` 을 import 에 추가.** 왜 기본 경로가 멀쩡했는지 주석으로 남김 |
| 2 | `scripts/batch/tool_smoke.bat` | ★**스모크 팔 2개 신설** — `[7] --attn-group 2 --init-from`(sm_ag) / `[8] --mlp-split 1 --init-from`(sm_split). **`--init-from` 을 붙여 이식 경로까지 탄다** |
| 3 | `scripts/check_smoke.py` | `EXPECT` 에 `sm_ag`(attn_group 2)·`sm_split`(mlp_split [1]) 추가 |
| 4 | `ai_dev_tool/01` | **계측함정 37** 등재 |

### 4.1 ★전수 확인 — **같은 종류가 더 있는가**

`pyflakes` 로 `tinylm/`·`scripts/`·`run100m.py`·`train_eval.py`·`util/` 전체를 정적 검사:

```
undefined name : 0건
```

→ **`build_attention` 이 이 계열의 유일한 결함**이었다. `compileall` 도 0에러.
(이 검사는 저장소 도구가 아니라 이번 1회 확인이다. 상시 그물은 조치 2·3 이다.)

## 5. 판정

| 게이트 | 상태 |
|---|---|
| **G0-a**(죽지 않는다) | 🚫 **실패** — 모델 생성에서 즉사 |
| **G0-b**(알린다) | ⏸ 도달 못 함 |
| **G0-c**(이식이 돕는다) | ⏸ 도달 못 함 |

> **P057 단계0 은 미실행으로 취급한다.** 재실행이 필요하고, 배치를 `-done` 에서 되돌렸다.

## 6. 재현 명령 (수정 후 그대로 재실행)

```
python scripts\runlog.py --name P057_stage0_attn --note "[P057 stage 0] attn_group 2 - 8 shared attentions over 16 middle layers."
python scripts\runlog.py --name P057_stage0_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 2 --modes prop
python scripts\runlog.py --name P057_stage0_attn --note "[P057 stage 0] attn_group 4 - 4 shared attentions. Harder average, larger saving."
python scripts\runlog.py --name P057_stage0_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 4 --modes prop
python scripts\runlog.py --name P057_stage0_attn --note "[P057 stage 0] attn_group 8 - 2 shared attentions. This is the aggressive end."
python scripts\runlog.py --name P057_stage0_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 8 --modes prop
```

⚠️**재실행 전 `run_smoke_check.bat` 을 먼저 돌린다** — 신설 팔 [7][8] 이 이 수정을
검증하는 것이고, 스모크가 통과하면 게이트가 **의미 있는 값을 낼 상태**라는 뜻이다.

## 7. 읽을 때 주의 (재실행 로그를 받으면)

1. **난수 대조군이 `ln V = 10.3972` 근처**인지 먼저 본다 — 아니면 계측이 아픈 것이다.
2. `attn_group` 별 step0 CE 를 **대역 5.0~9.3972 · 앵커 7.7742** 에 대고 읽는다.
3. ★**난수와 이식의 GAP 이 그룹평균이 산 것**이다. 절대 CE 가 아니라 GAP 을 본다.
4. **g 가 커질수록 GAP 이 무너지는 지점**이 쓸 수 있는 g 다.
5. ⚠️크롭 2×512 **단일 표본** — 다른 스크립트의 CE 와 비교하지 않는다.
6. ⚠️배치 주석이 정직하게 적어 둔 것: *"AVERAGING IS NOT KNOWN TO WORK HERE."*
   MLP 에서는 살았지만(결과 030 §2) **어텐션은 위치별 패턴이 층마다 달라 평균이
   아무 층도 안 닮을 수 있다.** 그게 이 게이트가 재는 것이다.
