#!/usr/bin/env python3
"""★★**정적 게이트 전수** — torch·GPU 없이 도는 검사만 모아 한 번에 돌린다.

## 왜 이 도구가 생겼나 (2026-08-22 사용자 지시)

> *"smoke_check 를 claude 가 실행 가능한 부분과 사용자가 실행해야 하는 torch 부분으로
>  구분하여, claude 가 통상적인 업데이트 이후 claude 실행부분 확인 수행할 것."*

★**규범(`CLAUDE.md`)은 "AI 는 사용자 환경에서 코드를 직접 실행하지 않는다" 이고 그것은 유효하다.**
그 규범의 목적은 **GPU 사용량·시간 보호**다. 그런데 이 저장소의 그물 중
**torch 를 전혀 안 쓰는 것이 13종**이고, 그것들은 **초 단위에 끝나고 GPU 를 0 쓴다.**
→ ★**그 13종은 AI 가 매 갱신 직후 스스로 돌린다.** 사용자에게 넘길 이유가 없다.

## ★두 층으로 나뉜다

| 층 | 무엇 | 누가 | 비용 |
|---|---|---|---|
| ★**정적**(이 파일) | 문법·형식·정합성. **torch·GPU 0** | ★**AI 가 매 갱신 직후** | 수 초 |
| **동적**(`run_smoke_check.bat`) | 실제 학습 30스텝 + **계측 필드 계약**(`check_smoke.py`) | **사용자** | 수 분, GPU |

🚫★**정적이 동적을 대체하지 않는다.** 정적은 *"이름이 있는가"* 를 보고
동적은 *"그 경로가 실제로 도는가"* 를 본다 — **함정 37 이 정확히 그 틈**이었다
(`check_smoke` 필수 필드에 이름만 넣으면 값이 기본값이라 코드가 안 돈다).

사용법
    python scripts/check_static_all.py            # 전수
    python scripts/check_static_all.py --quiet     # 실패한 것만
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ★★2026-08-28 (사용자 지적) — **보고 전용 게이트는 `--quiet` 에서도 반드시 인쇄한다.**
#
#   `sync_experiments_tsv` 는 설계상 **항상 종료코드 0** 이다(삭제 후보를 "보고" 만 한다).
#   그런데 나는 매번 `check_static_all.py --quiet` 로 돌렸고, `--quiet` 는 **통과한 게이트의
#   출력을 아예 안 찍는다.** 그래서 *"삭제 가능 후보 N건"* 이라는 줄이 **한 번도 내 눈에
#   들어오지 않았다.** 사용자가 `-done` 6건을 붙여 뒀는데 나는 "삭제 후보 없음" 이라고 보고했다.
#
#   ★원인은 게으름이 아니라 **인터페이스**다 — *"통과 = 볼 것 없음"* 이라는 가정이
#   보고 전용 도구에는 성립하지 않는다. 그래서 목록으로 예외를 만든다.
#   ⚠️새 보고 전용 게이트를 만들면 **여기에 이름을 넣는다.**
ALWAYS_SHOW = {"sync_experiments_tsv"}

# (표시이름, 인자, 무엇을 막는가)  — ★목록을 두 곳에 두지 않는다. 여기가 정본이다.
CHECKS = [
    ("check_attrs",         ["check_attrs.py"],
     "`cfg.X` 오타 — torch 없이 정적 검출"),
    ("check_call_kwargs",   ["check_call_kwargs.py"],
     "`cli.py` 가 넘기는 키워드가 대상 함수에 있는가"),
    ("check_batch_flags",   ["check_batch_flags.py"],
     "배치가 쓰는 CLI 플래그가 **파서에 실제로 있는가**(미구현 배치 2회 재발)"),
    ("lint_bat",            ["lint_bat.py"],
     "배치 린터 20규칙 — 비ASCII·`%VAR%`·`--tag` 누락·VERIFY 뒤 학습런"),
    ("check_links",         ["check_links.py"],
     "문서 상대링크 — 결과문서를 개명하면 참조가 깨진다"),
    ("check_handoff",       ["check_handoff.py"],
     "핸드오프 고정 섹션 8개"),
    ("check_plan_numbers",  ["check_plan_numbers.py"],
     "계획번호 ↔ 계획서 ↔ 실험계획목록 3자 정합(D16)"),
    ("check_run_registry",  ["check_run_registry.py"],
     "런 레지스트리·중복·태그 충돌"),
    ("check_result_numbers", ["check_result_numbers.py"],
     "★결과문서 번호 = 실험군 번호. **로그 파일명이 이미 번호를 말한다**(2026-08-22 오배정)"),
    ("check_hf_redirect",   ["check_hf_redirect.py"],
     "★HF 캐시 리다이렉트 — `tinylm` import 없이 datasets 를 쓰면 작업폴더 밖으로 받는다"),
    ("check_diag_data",     ["check_diag_data.py"],
     "진단 도구의 계측 건강 — 절대지표에 난수 정답을 쓰는가"),
    ("queue_menu --audit",  ["queue_menu.py", "--audit"],
     "`experiments.tsv` ↔ 디스크 양방향 대조"),
    ("sync_experiments_tsv", ["sync_experiments_tsv.py"],
     "`-done` 삭제 가능 판정 + TSV 고아 행(보고만)"),
    ("check_group_map",     ["check_group_map.py"],
     "★설정이 파생하는 집합 ↔ 모델이 만드는 개수 (P074 네 팔 전멸, 로그 059)"),
    ("check_smoke_coverage", ["check_smoke_coverage.py"],
     "★배치가 쓰는 축을 스모크가 실제로 돌리는가 — **새 기능이 아니라 새 조합**에서 죽는다"),
    ("plot_results --verify", ["plot_results.py", "--verify"],
     "★그림 도구의 수치 표 ↔ 정본(json) 대조 (자백 A7 — 사본이 정본을 이중화한다)"),
    ("check_rules_sync",    ["check_rules_sync.py"],
     "작업규약 영문 정본 ↔ 한글 대조본의 규칙 번호·강제 주체 일치"),
    ("check_index_sync",    ["check_index_sync.py"],
     "★색인이 산출물을 다 담고 있는가 — **'연쇄 갱신 완료' 라고 적고 안 한 것**(함정 13, 2026-08-29)"),
    ("check_doc_ownership", ["check_doc_ownership.py"],
     "★★문서 본문이 **남의 것인가** — H1 번호·로그 귀속·본문 중복(함정 42, 2026-08-30). "
     "✅파괴 커밋 86d24c9 에서 **29건 검출**을 확인하고 켰다"),
    ("check_smoke_fields",  ["check_smoke_fields.py"],
     "★★스모크가 요구하는 계측 필드를 trainer 가 **정말 찍는가** — `mlp_film` 이 "
     "실런 2개를 돌고도 json 에 없었다(2026-08-30). ✅그 줄을 뺀 사본에서 검출 확인 후 켰다. "
     "게이트 15 는 *플래그* 단위, 이것은 *필드* 단위다"),
    ("check_tag_arch",      ["check_tag_arch.py"],
     "★★★태그가 **주장하는** 아키텍처 ↔ json 이 **기록한 값**(2026-08-31). "
     "`mC_cla1_ag4_r20_s3` 가 `--cla-group 1` 없이 돌아 **cla2 모델이 cla1 이름**으로 "
     "3.6시간을 썼다. 게이트 15·20 은 *존재*를, 이것은 **값**을 본다. "
     "✅실제 오염 1건을 검출한 상태에서 켰다"),
]


def main():
    ap = argparse.ArgumentParser(description="정적 게이트 전수 (torch·GPU 0)")
    ap.add_argument("--quiet", action="store_true", help="실패한 것의 출력만 보인다")
    a = ap.parse_args()

    print("#" * 100)
    print("  ★정적 게이트 전수 — torch·GPU 를 **전혀 쓰지 않는다**. AI 가 매 갱신 직후 돈다")
    print("  ⚠️ 이것은 `run_smoke_check.bat`(사용자·GPU)의 **대체가 아니라 앞단**이다")
    print("#" * 100)

    rows, bad = [], 0
    for name, argv, why in CHECKS:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / argv[0]), *argv[1:]],
                           cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        ok = r.returncode == 0
        rows.append((name, ok, r.returncode, why))
        if not ok:
            bad += 1
        if (not ok) or (not a.quiet) or (name in ALWAYS_SHOW):
            print(f"\n{'=' * 100}\n  [{'OK ' if ok else 'FAIL'}] {name}   (exit {r.returncode})\n{'=' * 100}")
            out = (r.stdout or "") + (r.stderr or "")
            tail = out.strip().splitlines()
            print("\n".join(tail[-40:]) if len(tail) > 40 else "\n".join(tail))

    print("\n" + "#" * 100)
    print("  요약")
    print("#" * 100)
    for name, ok, rc, why in rows:
        print(f"  {'✅' if ok else '🚫'} {name:<22} exit {rc:<3}  {why}")
    print(f"\n  {'✅ 정적 게이트 전부 통과' if bad == 0 else f'🚫 {bad}건 실패'} "
          f"— 검사 {len(rows)}종")
    if ALWAYS_SHOW:
        print(f"  ★보고 전용 게이트({', '.join(sorted(ALWAYS_SHOW))})는 통과해도 출력을 인쇄한다 — "
              f"**통과 = 볼 것 없음 이 아니다**(2026-08-28).")
    # ★2026-08-28 (사용자 지적) — 종전 문구가 *"다음은 사용자 차례"* 로 시작해서
    #   **정적 게이트까지 사용자 몫으로 읽힐 여지**가 있었다. 실제로 나는 매 세션
    #   *"정적검사를 돌려 주세요"* 라고 보고했다. 🚫**정적은 torch·GPU 를 안 쓰므로 AI 가 직접 돈다.**
    print("  ★**이 스위트는 AI 가 직접 돌린다** — torch·GPU 를 쓰지 않으므로 위임할 이유가 없다.")
    print("  ⚠️★**사용자에게 요청할 것은 `run_smoke_check.bat`(torch·GPU) 하나뿐**이다.")
    print("     정적은 *'이름이 있는가'*, 동적은 *'그 경로가 실제로 도는가'* 를 본다(함정 37).")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
