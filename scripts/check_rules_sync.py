"""정적 게이트 17 — 작업규약 **영문 정본**과 **한글 대조본**의 규칙 번호가 같은가.

★왜 필요한가 (2026-08-27)
    규약을 두 언어로 두면 그 자체가 **계측함정 18**(한 개념을 두 곳에서 정의)이다.
    한쪽만 고치면 사용자가 검토한 것과 AI 가 따르는 것이 갈라진다.
    내용까지 기계가 대조할 수는 없으므로 **규칙 번호 집합**과 **[gate]/[게이트] 표시**를 맞춘다.

    python scripts/check_rules_sync.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "ai_dev_tool" / "00_WORKING_RULES.md"
KO = ROOT / "ai_dev_tool" / "00_작업규약_한글판.md"

RULE = re.compile(r"\*\*(R\d\d)\*\*\s*`([^`]+)`")


def load(p: Path) -> dict[str, str]:
    if not p.exists():
        print(f"🚫 없다: {p}")
        sys.exit(1)
    return {m.group(1): m.group(2) for m in RULE.finditer(p.read_text(encoding="utf-8"))}


en, ko = load(EN), load(KO)
GATE = {"[gate]", "[게이트]"}
HUMAN = {"[human]", "[사람]"}

print("=" * 92)
print("  정적 게이트 17 — 작업규약 영문 정본 ↔ 한글 대조본")
print("=" * 92)
print(f"  영문 {len(en)}개 · 한글 {len(ko)}개")

err = []
for k in sorted(set(en) - set(ko)):
    err.append(f"{k} 이 영문에만 있다")
for k in sorted(set(ko) - set(en)):
    err.append(f"{k} 이 한글에만 있다")
for k in sorted(set(en) & set(ko)):
    a, b = en[k], ko[k]
    if (a in GATE) != (b in GATE):
        err.append(f"{k} 의 강제 주체가 다르다 — 영문 {a} vs 한글 {b}")

if err:
    print(f"\n  🚫 {len(err)}건\n")
    for e in err:
        print(f"    - {e}")
    print("\n  ★한쪽만 고치면 사용자가 검토한 것과 AI 가 따르는 것이 갈라진다.")
    sys.exit(1)
print("\n  ✅ 규칙 번호와 강제 주체가 일치")
sys.exit(0)
