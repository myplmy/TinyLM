#!/usr/bin/env python3
"""진단 도구의 **계측 건강** 정적 검사 — 함정 31·32 의 기계 그물. GPU 0 · 1초.

## 왜 이 검사가 생겼나

**2026-08-13 하루에 같은 형태의 사고가 두 번 났다.**

| 도구 | 무엇이 틀렸나 | 결과 |
|---|---|---|
| `diag_depth_init.py` | 입력과 **정답을 둘 다 난수 토큰**으로 줬다 | ★**이식이 성공할수록 지표가 나빠졌다**(결과 041 §11) |
| `diag_kd_loss.py` | 교사·학생 로짓이 **같은 `base` 를 공유**해 두 분포가 거의 같았다 | KL≈0 → *"실효 α = 0.000"* 이 **데이터의 성질**이었다(결과 042 §3) |

둘 다 **코드가 아니라 테스트 데이터**가 틀렸고, **대조군은 정확했다.**
`diag_depth_init` 의 난수 대조군은 `ln(32768)` 을 소수 셋째 자리까지 재현했고,
결과문서가 그걸 근거로 *"계측은 건강하다"* 라고 적었다. **대조군만 건강했다.**

## 규칙 — **차이 지표와 절대 지표를 가른다**

| 지표 종류 | 난수 입력 | 왜 |
|---|---|---|
| **차이(difference)** — 같은 입력에 두 경로를 태우고 뺀다 | ✅ **허용** | 입력이 무엇이든 **차이는 유효**하다(예: `diag_gqa_equiv`) |
| ★**절대(absolute)** — CE·loss·bpb·ppl 처럼 **품질을 직접 읽는다** | 🚫 **금지** | 난수 정답 대비 CE 는 **학습된 모델일수록 나쁘다** = 부호가 뒤집힌다 |

그리고 절대 지표에는 **성공 기준값**이 있어야 한다:

> ★**"성공했을 때 나와야 하는 값" 을 대조군과 **함께** 정한다.**
> 실패 쪽 기준선(난수 ≈ `ln V`)만 있으면 **부호가 뒤집힌 지표를 못 알아본다.**

★★**그런데 기준값을 *적는* 것과 *옳은* 것을 적는 것은 다르다** (2026-08-13, 함정 34).
P049B 게이트가 이 검사를 **통과했는데도 틀렸다** — 교사 full-val **3.8080** 을 적었지만,
`init_from_dense` 는 중간 MLP 를 타잉 그룹별로 **평균**하므로 **부모초기화 타잉 학생은
교사가 될 수 없다.** 옳은 앵커는 결과 030 §2 의 **7.7742** 였고, 그 값은 **이미 있었다.**

| 조건 | 옳은 앵커 | 근거 |
|---|---|---|
| dense 학생(구조 동일) | **3.8080** | 결과 040 §2 |
| ★**타잉 학생 + 부모초기화** | **7.7742** | ★결과 030 §2 |
| 초기화 없음(난수) | `ln V` = **10.3972** | 결과 030 §2 |

> **이 도구는 "상수가 있는가" 만 본다. "그 상수가 이 조건에 맞는가" 는 사람이 본다.**

## 무엇을 보는가 (정적 · torch 불필요)

1. 절대 지표(`cross_entropy`·`nll_loss`·`bpb`·`perplexity`)를 계산하는가
2. 그렇다면 **정답 텐서를 난수로 만들지 않는가**(`randint` 로 만든 것을 target 으로)
3. 그렇다면 **성공 기준값이 파일 안에 있는가**(실측 상수 또는 실데이터 로딩)

⚠️ **정적 검사의 한계**: 변수 이름과 호출 패턴만 본다. **의미는 모른다.**
통과가 "계측이 옳다" 는 증명이 아니라 **두 번 문 함정을 다시 물지 않았다**는 뜻이다.

사용:
    python scripts/check_diag_data.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

ABS_METRIC = re.compile(r"cross_entropy|nll_loss|\bbpb\b|perplexity|\bppl\b")
REAL_DATA = re.compile(r"Loader\(|prepare\(|load_squad|SQUAD|resolve_ckpt|load_model")
# 성공 기준값: 우리가 실측한 상수들. 하나라도 있으면 "기준을 적어 뒀다" 로 본다.
SUCCESS_REF = re.compile(r"3\.80|3\.69|3\.7[0-9]|TEACHER_|기준값|참고값|성공했을 때|reference")
RAND_TENSOR = re.compile(r"(\w+)\s*=\s*torch\.randint")


def audit(p: Path):
    """(치명, 경고, 정보) 목록."""
    txt = p.read_text(encoding="utf-8", errors="replace")
    err, warn, info = [], [], []

    if not ABS_METRIC.search(txt):
        return err, warn, ["절대 지표 없음 — 이 검사의 대상이 아니다(차이 지표 도구)"]

    # 난수로 만든 텐서 이름을 모은다
    rand_names = set(RAND_TENSOR.findall(txt))
    # 그 이름이 CE 의 **정답 인자**로 들어가는가
    for m in re.finditer(r"cross_entropy\([^)]*\)", txt):
        call = m.group(0)
        args = call[call.index("(") + 1:]
        parts = [a.strip() for a in args.split(",")]
        if len(parts) >= 2:
            tgt = re.sub(r"\..*$", "", parts[1]).strip()
            if tgt in rand_names:
                err.append(f"★`cross_entropy(..., {tgt})` 의 정답이 **난수**다 "
                           f"(`{tgt} = torch.randint(...)`). 학습된 모델일수록 CE 가 "
                           f"나빠진다 = **부호가 뒤집힌 계측**(함정 31, 결과 041 §11)")

    # 합성 데이터라도 **퇴화 감지 장치가 있으면** 통과로 본다(함정 32 의 규칙을 지킨 것).
    has_guard = re.search(r"총변동거리|degenerate|퇴화", txt)
    if not REAL_DATA.search(txt) and not has_guard:
        warn.append("절대 지표를 계산하는데 **실데이터도 안 읽고 퇴화 감지도 없다** — "
                    "합성 데이터는 조용히 퇴화한다(함정 32, 결과 042 §3)")
    if not SUCCESS_REF.search(txt):
        warn.append("★**성공 기준값이 안 보인다** — 실패 쪽(난수 ≈ ln V)만 있으면 "
                    "부호가 뒤집힌 지표를 못 알아본다. **'성공했을 때 나와야 하는 값'** 을 "
                    "인쇄할 것(함정 31). dense=3.8080 / **타잉+부모초기화=7.7742** / 난수=10.3972 — "
                    "★**조건에 맞는 것**을 고를 것(함정 34)")
    return err, warn, info


def main():
    targets = sorted(list(SCRIPTS.glob("diag_*.py")) + list(SCRIPTS.glob("bench_*.py")))
    W = 96
    print("=" * W)
    print("  진단 도구 계측 건강 정적 검사 (함정 31·32)")
    print("=" * W)
    ne = nw = 0
    for p in targets:
        err, warn, info = audit(p)
        if not err and not warn:
            tag = "OK" if not info else "N/A"
            print(f"  [{tag:3s}] {p.name}")
            continue
        print(f"\n  === {p.name} ===")
        for e in err:
            print(f"    [E] {e}")
        for w in warn:
            print(f"    [W] {w}")
        ne += len(err)
        nw += len(warn)
    print()
    print(f"  총 에러 {ne}건 / 경고 {nw}건")
    print("  ⚠️ 정적 검사다. **통과가 '계측이 옳다' 는 증명이 아니다** — "
          "두 번 문 함정을 다시 물지 않았다는 뜻이다.")
    print("=" * W)
    return ne


if __name__ == "__main__":
    sys.exit(main())
