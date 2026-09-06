#!/usr/bin/env python3
"""★W&B Stage0 — **여러 런의 벤치 Table 을 한 Custom Chart 가 합쳐 읽는가**(학습 0 · GPU 0).

## 왜 이 도구가 있나 (2026-09-05 사용자 지시 (5))

W&B 시각화 제안서가 Stage0 에 *"아무 두 런에 손으로 `bench/table` 을 하나씩 올린다(3행짜리 더미)"*
라고만 적고 🚫**어떻게 올리는지를 안 적었다.** 사용자가 실행할 수단이 없었다. 이 스크립트가 그것이다.

## ★2026-09-06 — **wide format 이 붙었다**(사용자 지시 (2))

✅사용자가 화면에서 **long format 차트 생성을 확인**했다(제안서 §4.2). 🚫**그런데 반쪽이다** —
Vega `params` 로 만든 **`metric_choice` 셀렉터가 W&B 화면에서 안 먹는다.** 지표를 바꾸려면
**Vega spec 을 직접 고쳐야** 하고, 그것은 *"하나의 차트 정의로 세 지표를 돌려 쓴다"*(검토서 §10)가 아니다.

W&B workspace AI 의 안내(제안서 §4.2.1): **지표를 열로 펴면**(wide) W&B **공식** 열 선택 문법
**`${field:y_metric}`** 이 쓸 수 있게 되고, **패널 편집 화면의 Chart fields** 에 셀렉터가 생긴다.

    long                                    wide
    model | task | metric   | value         model | task | acc  | acc_norm | gold_ce
    A     | piqa | acc      | 0.21          A     | piqa | 0.21 | 0.22     | 10.1
    A     | piqa | acc_norm | 0.22

★**그래서 이 프로브가 두 형식을 다 올린다.** 화면에서 나란히 보고 정한다.

| | long | wide |
|---|---|---|
| 행 수(런당) | 과제 × 지표 = **9** | 과제 = **3** |
| 지표 바꾸기 | 🚫Vega `filter` 를 손으로 고친다 | ✅**Chart fields 드롭다운** |
| 지표 추가 | ✅스키마 불변(행만 는다) | 🚫**열이 는다 = 스키마 변경** |
| 지표 두 개를 한 차트에 | ✅`color` 로 편다 | 🚫**못 한다**(열이 둘) |
| 축 척도 | ⚠️acc(0~1)와 gold_ce(3.5~6.8)가 **한 열에 섞인다** | ✅**열이 다르니 안 섞인다** |

⚠️★**이 표는 예측이고 판정은 화면이 한다.** 그래서 프로브다.

## 🚫**기본 프로젝트는 `tinylm` 이 아니다**

`tinylm-probe` 로 간다. 이유: 검증하려는 것은 **W&B 의 동작**이지 우리 프로젝트의 상태가 아니고,
**더미 런이 실험 워크스페이스에 섞이면 지운다는 보장이 없다**(우리는 파일을 안 지운다).
같은 자리에서 보고 싶으면 `--project tinylm`.

## ★두 형식은 **다른 `tableKey`** 로 간다

`bench/table`(long) 과 **`bench/table_wide`**(wide). 🚫**같은 키에 두 스키마를 올리면**
한 run set 에 섞였을 때 Vega 가 **열이 없는 행**을 만난다. 키가 다르면 차트도 둘이고 비교가 깨끗하다.

## 문서 근거 (2026-09-05 조회)

`docs.wandb.ai/guides/app/features/custom-charts/walkthrough/` — Custom Chart 의 질의는
**`runSets`** 로 **여러 런을 한 번에** 읽고, 표는 **`summaryTable`** + **`tableKey`** 로 고른다.
권고 상한은 **키당 10,000점**(우리는 모델당 3~9행이라 문제없다).
⚠️★**문서가 그렇다는 것이지 우리 화면이 그렇다는 것이 아니다** — 그래서 이 프로브가 있다.

사용:

    python scripts/wandb_table_probe.py --format both     # ★권장 — 두 형식을 한 번에
    python scripts/wandb_table_probe.py --format wide
    python scripts/wandb_table_probe.py --format long --project tinylm --prefix zz_
    python scripts/wandb_table_probe.py --format both --dry-run    # 올리지 않고 표만 인쇄
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import tinylm                                   # noqa: E402  ★R40 — HF 캐시 리다이렉트 먼저

_ = tinylm

META = ["n", "n_asked", "skipped", "seed", "pmi"]
COLS_LONG = ["model", "task", "metric", "value"] + META
COLS_WIDE = ["model", "task", "acc", "acc_norm", "gold_ce"] + META

KEY_LONG = "bench/table"
KEY_WIDE = "bench/table_wide"

TASKS = ["hellaswag", "arc_easy", "piqa"]
METRICS = ["acc", "acc_norm", "gold_ce"]
N_ASKED = {"hellaswag": 5000, "arc_easy": 2376, "piqa": 1838}
BUMP = {"hellaswag": 0.00, "arc_easy": 0.05, "piqa": 0.10}

# ★명백한 더미다 — 실측과 헷갈릴 수 없는 값만 쓴다.
#   acc·acc_norm 은 0.11/0.22/0.33 계열, gold_ce 는 9.x 계열(우리 실측은 3.5~6.8).
DUMMY = {
    "modelA": {"acc": 0.11, "acc_norm": 0.12, "gold_ce": 9.1},
    "modelB": {"acc": 0.22, "acc_norm": 0.23, "gold_ce": 9.2},
    "modelC": {"acc": 0.33, "acc_norm": 0.34, "gold_ce": 9.3},
}


def value(model, task, metric):
    """과제마다 조금씩 다르게 — 막대 높이가 달라야 x축 그룹이 보인다."""
    b = BUMP[task]
    return round(DUMMY[model][metric] + (b * 10 if metric == "gold_ce" else b), 4)


def rows_long(model, run_name):
    out = []
    for t in TASKS:
        for m in METRICS:
            out.append([run_name, t, m, value(model, t, m), 5000, N_ASKED[t], 0, 99, True])
    return out


def rows_wide(model, run_name):
    out = []
    for t in TASKS:
        out.append([run_name, t] + [value(model, t, m) for m in METRICS]
                   + [5000, N_ASKED[t], 0, 99, True])
    return out


SPEC_WIDE = """{
  "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
  "title": "Benchmark metric by task and model",
  "data": {"name": "wandb"},
  "mark": "bar",
  "encoding": {
    "x":       {"field": "task",  "type": "nominal", "title": "Task"},
    "xOffset": {"field": "model", "type": "nominal"},
    "y":       {"field": "${field:y_metric}", "type": "quantitative", "title": "Value"},
    "color":   {"field": "model", "type": "nominal", "title": "Model"},
    "tooltip": [
      {"field": "model", "type": "nominal"},
      {"field": "task",  "type": "nominal"},
      {"field": "${field:y_metric}", "type": "quantitative"},
      {"field": "n",     "type": "quantitative"}
    ]
  }
}"""


def guide_long(project, names, key):
    print()
    print("=" * 96)
    print("  ★[LONG] 사용자가 화면에서 할 것 — ✅**2026-09-05 에 이미 확인된 경로**")
    print("=" * 96)
    print(f"  1. https://wandb.ai/<entity>/{project} 를 연다.")
    print(f"     런 {len(names)}개가 보여야 한다: {', '.join(names)}")
    print("  2. 왼쪽 런 목록에서 **셋을 전부 선택**한다(체크박스). <- ★이것이 run set 이다")
    print("  3. 패널 추가 -> **Custom Chart**.")
    print("  4. 오른쪽 **Query** 에서 `summary` 를 **`summaryTable`** 로 바꾸고")
    print(f"     **`tableKey`** 에 **`{key}`** 를 넣는다.")
    print("  5. **Chart fields**: x -> `task` · y -> `value` · color -> `model`")
    print("  6. Vega spec 에 필터를 넣는다(acc 만 보기):")
    print("       \"transform\": [{\"filter\": \"datum.metric === 'acc'\"}]")
    print()
    print("  🚫★**여기가 막힌 곳이다** — 지표를 바꾸려면 이 필터 문자열을 **손으로 고쳐야** 한다.")
    print("     Vega `params` 로 만든 셀렉터(`metric_choice`)는 W&B 화면에서 **안 먹었다**(제안서 §4.2).")
    print("     -> 그래서 아래 WIDE 를 함께 올렸다.")


def guide_wide(project, names, key):
    print()
    print("=" * 96)
    print("  ★★[WIDE] 사용자가 화면에서 할 것 — **이번에 확인할 것**")
    print("=" * 96)
    print(f"  1. https://wandb.ai/<entity>/{project} 를 연다.")
    print(f"     런 {len(names)}개: {', '.join(names)}")
    print("  2. 왼쪽에서 **셋을 전부 선택**한다.")
    print("  3. 패널 추가 -> **Custom Chart** -> Query 를 **`summaryTable`** 로.")
    print(f"  4. **`tableKey`** 에 **`{key}`** 를 넣는다. 🚫long 과 **다른 키**다.")
    print("  5. 프리셋 아무거나 고르고 **Edit** -> Vega 편집기에 아래를 통째로 붙인다:")
    print()
    for ln in SPEC_WIDE.split(chr(10)):
        print("       " + ln)
    print()
    print("  ★★**판정 — 이 하나만 보면 된다**")
    print("     패널 편집 화면의 **Chart fields** 에 **`y_metric`** 이라는 칸이 생기고,")
    print("     거기 드롭다운에 **acc / acc_norm / gold_ce** 가 뜨는가?")
    print("       ✅뜨면  -> **wide 채택.** Vega 를 안 고치고 지표를 바꾼다")
    print("       🚫안 뜨면 -> **long 유지.** 지표마다 차트를 따로 만든다(3개)")
    print()
    print("  ⚠️함께 봐 줄 것 셋")
    print("     · `y_metric` 을 `gold_ce` 로 바꾸면 y축 눈금이 **9~10 대역**으로 따라 바뀌는가")
    print("       (long 에서는 acc 와 gold_ce 가 **한 열에 섞여** 축이 뭉갠다)")
    print("     · 런을 하나 더 선택/해제하면 막대가 따라 늘고 주는가")
    print("       (그래야 **모델을 추가할 때 차트를 안 고친다**)")
    print("     · x축에 **hellaswag / arc_easy / piqa 세 칸**이 서고 칸마다 막대 3개인가")


def verdict(project):
    print()
    print("=" * 96)
    print("  ★결정 — **둘 중 하나를 고른다**(제안서 §6 이 이 답을 기다린다)")
    print("=" * 96)
    print("  wide 가 되면 얻는 것: **하나의 차트로 세 지표**, 축 척도가 안 섞인다")
    print("  wide 로 잃는 것:   **지표를 추가하면 열이 는다**(스키마 변경) ·")
    print("                     **두 지표를 한 차트에 못 겹친다**")
    print("  🚫**정본은 어느 쪽이든 `test_result/bench_results.tsv` 다**(제안서 §5.2)")
    print("     — 표는 매번 전량 재구성하므로 **형식 전환 비용은 0.3h** 다.")
    print()
    print("  🚫**더미 런은 지워도 된다** — W&B 화면에서 사용자가 지운다.")
    print("     우리 저장소 규칙(R01)은 **디스크 파일**에 대한 것이고 W&B 는 사용자 계정이다.")
    print("=" * 96)


def build(fmt, prefix):
    """(런이름, 열, 행, 키, 라벨) 목록을 만든다. **한 곳에서 정한다**(R14)."""
    out = []
    if fmt in ("long", "both"):
        for m in DUMMY:
            nm = prefix + "probe_" + m
            out.append((nm, COLS_LONG, rows_long(m, nm), KEY_LONG, "long"))
    if fmt in ("wide", "both"):
        for m in DUMMY:
            nm = prefix + "probe_wide_" + m
            out.append((nm, COLS_WIDE, rows_wide(m, nm), KEY_WIDE, "wide"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="tinylm-probe")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--format", default="both", choices=["long", "wide", "both"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    plan = build(a.format, a.prefix)
    print("=" * 96)
    print("  W&B Stage0 프로브 — 여러 런의 Table 을 한 Custom Chart 가 합쳐 읽는가")
    print("=" * 96)
    print(f"  프로젝트 {a.project}  ·  형식 **{a.format}**  ·  런 {len(plan)}개")
    if a.format in ("long", "both"):
        print(f"  long  키 `{KEY_LONG}`       스키마: {' | '.join(COLS_LONG)}")
        print(f"        런당 {len(TASKS)} 과제 x {len(METRICS)} 지표 = **{len(TASKS)*len(METRICS)}행**")
    if a.format in ("wide", "both"):
        print(f"  wide  키 `{KEY_WIDE}`  스키마: {' | '.join(COLS_WIDE)}")
        print(f"        런당 {len(TASKS)} 과제 = **{len(TASKS)}행** (지표가 열이다)")
    print("  ★값은 전부 더미다 — acc 0.11~0.43 · gold_ce 9.1~10.3 (실측 대역 3.5~6.8 밖)")
    print()
    for nm, cols, rows, key, lab in plan:
        print(f"  [{lab}] {nm}  {len(rows)}행  예: {rows[0]}")

    long_names = [p[0] for p in plan if p[4] == "long"]
    wide_names = [p[0] for p in plan if p[4] == "wide"]

    def show():
        if long_names:
            guide_long(a.project, long_names, KEY_LONG)
        if wide_names:
            guide_wide(a.project, wide_names, KEY_WIDE)
        verdict(a.project)

    if a.dry_run:
        print()
        print("  ⚠️--dry-run — 아무것도 올리지 않았다.")
        show()
        return 0

    try:
        import wandb
    except ImportError:
        print("  🚫 wandb 가 없다 — `pip install wandb`", file=sys.stderr)
        return 2
    from wandb_sync import read_key                    # noqa: PLC0415
    wandb.login(key=read_key())                        # ★키는 여기서만 쓰인다

    n_ok = 0
    for nm, cols, rows, key, lab in plan:
        run = wandb.init(project=a.project, id=nm, name=nm, resume="allow", reinit=True)
        # ★`log` 로 올리면 **history 와 summary 양쪽**에 들어가고, summary 쪽을
        #   `summaryTable(tableKey=...)` 이 읽는다. 🚫같은 키를 나중에 다시 log 하면
        #   **summary 의 표가 통째로 교체된다** — 그래서 실제 도구는 **누적 표**를 올려야 한다.
        run.log({key: wandb.Table(columns=cols, data=rows)})
        run.finish()
        n_ok += 1
        print(f"  ✅ 올림 [{lab}] {nm}")

    if n_ok == 0:                                       # ★R19 — 0 을 조용히 통과시키지 않는다
        print("  🚫 올린 런이 0개다.", file=sys.stderr)
        return 1
    show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
