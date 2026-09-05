#!/usr/bin/env python3
"""★W&B Stage0 — **여러 런의 `bench/table` 을 한 Custom Chart 가 합쳐 읽는가**(학습 0 · GPU 0).

## 왜 이 도구가 있나 (2026-09-05 사용자 지시 (5))

W&B 시각화 제안서가 Stage0 에 *"아무 두 런에 손으로 `bench/table` 을 하나씩 올린다(3행짜리 더미)"*
라고만 적고 🚫**어떻게 올리는지를 안 적었다.** 사용자가 실행할 수단이 없었다. 이 스크립트가 그것이다.

## 무엇을 하나

**세 개의 더미 런**(`probe_modelA/B/C`)에 **같은 스키마의 long-format `bench/table`** 을 올린다.
각 런의 표는 **3과제 × 3지표 = 9행**이고, 값은 실제 측정과 무관한 **명백한 더미**다
(🚫`0.11`~`0.99` 대역의 라운드 값 — 실측과 헷갈릴 수 없다).

그 다음 **Workspace 에서 사람이 확인할 것**을 인쇄한다.

## 🚫**기본 프로젝트는 `tinylm` 이 아니다**

`tinylm-probe` 로 간다. 이유: 검증하려는 것은 **W&B 의 동작**이지 우리 프로젝트의 상태가 아니고,
**더미 3런이 실험 워크스페이스에 섞이면 지운다는 보장이 없다**(우리는 파일을 안 지운다).
같은 자리에서 보고 싶으면 `--project tinylm`.

## 문서 근거 (2026-09-05 조회)

`docs.wandb.ai/guides/app/features/custom-charts/walkthrough/` — Custom Chart 의 질의는
**`runSets`** 로 **여러 런을 한 번에** 읽고, 표는 **`summaryTable`** + **`tableKey`** 로 고른다.
Vega 필드 이름은 `runSets_summaryTable_<열>` 꼴로 나온다. 권고 상한은 **키당 10,000점**
(우리는 모델당 9행이라 문제없다).
⚠️★**문서가 그렇다는 것이지 우리 화면이 그렇다는 것이 아니다** — 그래서 이 프로브가 있다.

사용:

    python scripts/wandb_table_probe.py                 # tinylm-probe 에 3런
    python scripts/wandb_table_probe.py --project tinylm --prefix zz_probe_
    python scripts/wandb_table_probe.py --dry-run       # 올리지 않고 표만 인쇄
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

COLS = ["model", "task", "metric", "value", "n", "n_asked", "skipped", "seed", "pmi"]
TASKS = ["hellaswag", "arc_easy", "piqa"]
METRICS = ["acc", "acc_norm", "gold_ce"]
N_ASKED = {"hellaswag": 5000, "arc_easy": 2376, "piqa": 1838}

# ★명백한 더미다 — 실측과 헷갈릴 수 없는 값만 쓴다.
#   acc·acc_norm 은 0.11/0.22/0.33 계열, gold_ce 는 9.x 계열(우리 실측은 3.5~6.8).
DUMMY = {
    "probe_modelA": {"acc": 0.11, "acc_norm": 0.12, "gold_ce": 9.1},
    "probe_modelB": {"acc": 0.22, "acc_norm": 0.23, "gold_ce": 9.2},
    "probe_modelC": {"acc": 0.33, "acc_norm": 0.34, "gold_ce": 9.3},
}


def rows_for(model):
    out = []
    for t in TASKS:
        for m in METRICS:
            # 과제마다 조금씩 다르게 — 차트에서 막대 높이가 달라야 x축 그룹이 보인다
            bump = {"hellaswag": 0.00, "arc_easy": 0.05, "piqa": 0.10}[t]
            v = DUMMY[model][m] + (bump if m != "gold_ce" else bump * 10)
            out.append([model, t, m, round(v, 4), 5000, N_ASKED[t], 0, 99, True])
    return out


def guide(project, names, key):
    print()
    print("=" * 96)
    print("  ★사용자가 화면에서 할 것 — **여기서부터는 사람이 본다**")
    print("=" * 96)
    print(f"  1. https://wandb.ai/<entity>/{project} 를 연다.")
    print(f"     런 {len(names)}개가 보여야 한다: {', '.join(names)}")
    print("  2. 왼쪽 런 목록에서 **셋을 전부 선택**한다(체크박스). ← ★이것이 run set 이다")
    print("  3. 패널 추가 -> **Custom Chart**.")
    print("  4. 오른쪽 **Query** 에서 `summary` 를 **`summaryTable`** 로 바꾸고")
    print(f"     **`tableKey`** 에 **`{key}`** 를 넣는다.")
    print("  5. **Chart fields** 에서:")
    print("       x            -> runSets_summaryTable_task")
    print("       y            -> runSets_summaryTable_value")
    print("       color/legend -> runSets_summaryTable_model")
    print("  6. Vega spec 에 필터를 넣는다(acc 만 보기):")
    print('       "transform": [{"filter": "datum.metric === \'acc\'"}]')
    print()
    print("  ★★**판정 — 이 한 가지만 보면 된다**")
    print("     x 축에 **hellaswag / arc_easy / piqa 세 칸**이 서고,")
    print("     각 칸에 **막대 3개(모델 3개)** 가 서면 -> ✅**된다 = 제안서 안 A**")
    print("     한 런의 9행만 보이거나 모델 구분이 안 되면 -> 🚫**안 된다 = 제안서 안 B**")
    print()
    print("  ⚠️함께 봐 줄 것 둘")
    print("     · 필터를 `acc_norm` / `gold_ce` 로 바꿔도 같은 차트가 그려지는가")
    print("       (하나의 차트 정의로 세 지표를 돌려 쓸 수 있어야 한다 — 검토서 §10)")
    print("     · 런을 하나 더 선택/해제하면 막대가 따라 늘고 주는가")
    print("       (그래야 **모델을 추가할 때 차트를 안 고친다**)")
    print()
    print("  🚫**더미 런은 지워도 된다** — W&B 화면에서 사용자가 지운다.")
    print("     우리 저장소 규칙(R01)은 **디스크 파일**에 대한 것이고 W&B 는 사용자 계정이다.")
    print("=" * 96)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="tinylm-probe")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--key", default="bench/table")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    names = [a.prefix + m for m in DUMMY]
    print("=" * 96)
    print("  W&B Stage0 프로브 — 여러 런의 Table 을 한 Custom Chart 가 합쳐 읽는가")
    print("=" * 96)
    print(f"  프로젝트 {a.project}  ·  런 {len(names)}개  ·  키 `{a.key}`")
    print(f"  표 스키마(long format): {' | '.join(COLS)}")
    print(f"  런당 {len(TASKS)} 과제 × {len(METRICS)} 지표 = **{len(TASKS)*len(METRICS)}행**")
    print("  ★값은 전부 더미다 — acc 0.11~0.43 · gold_ce 9.1~10.3 (실측 대역 밖)")
    print()
    for m in DUMMY:
        r = rows_for(m)
        print(f"  [{a.prefix + m}] {len(r)}행  예: {r[0]}")

    if a.dry_run:
        print()
        print("  ⚠️--dry-run — 아무것도 올리지 않았다.")
        guide(a.project, names, a.key)
        return 0

    try:
        import wandb
    except ImportError:
        print("  🚫 wandb 가 없다 — `pip install wandb`", file=sys.stderr)
        return 2
    from wandb_sync import read_key                    # noqa: PLC0415
    wandb.login(key=read_key())                        # ★키는 여기서만 쓰인다

    n_ok = 0
    for m in DUMMY:
        rid = a.prefix + m
        run = wandb.init(project=a.project, id=rid, name=rid, resume="allow", reinit=True)
        tbl = wandb.Table(columns=COLS, data=rows_for(m))
        # ★`log` 로 올리면 **history 와 summary 양쪽**에 들어가고, summary 쪽을
        #   `summaryTable(tableKey=...)` 이 읽는다. 🚫같은 키를 나중에 다시 log 하면
        #   **summary 의 표가 통째로 교체된다** — 그래서 실제 도구는 **누적 표**를 올려야 한다.
        run.log({a.key: tbl})
        run.finish()
        n_ok += 1
        print(f"  ✅ 올림 {rid}")

    if n_ok == 0:                                       # ★R19 — 0 을 조용히 통과시키지 않는다
        print("  🚫 올린 런이 0개다.", file=sys.stderr)
        return 1
    guide(a.project, names, a.key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
