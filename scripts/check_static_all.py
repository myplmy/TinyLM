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
    ("check_imports",       ["check_imports.py"],
     "★★`from A import B` 의 **B 가 A 에 정말 있는가**(2026-09-03 신설). "
     "`check_return_probs.py` 가 **없는 이름 `TMT`** 를 import 해 신설 이래 한 번도 안 돌았는데 "
     "**정적 22종이 매번 전부 통과**했다 — 아무도 import 문을 안 봤다. "
     "함정 37 의 새 얼굴: *'파일이 있다 ≠ 그 파일이 import 된다'*. ✅실제 결함 주입으로 검출 확인·오탐 0"),
    ("check_batch_name",    ["check_batch_name.py", "--quiet"],
     "★★실험 배치 **파일명**의 계획번호·단계 구분자가 **실재하는가**(2026-09-04 사용자 지시 8). "
     "`run_REVIEW4_expC_bench_n5000.bat` 는 계획번호도 단계도 없어 **어느 계획의 몇 단계인지 파일명이 "
     "말하지 않았다.** 🚫계획서에 Stage3 가 있다고 **Stage3B** 가 되는 것이 아니다 — 단계를 먼저 쓴다. "
     "✅위반 1건 검출 후 P085 를 쓰고 개명"),
    ("check_heldout_defects", ["check_heldout_defects.py"],
     "★★held-out 의 **의미 결함**(2026-09-03). 구조 검사(정답 불변·중복·문자폭)는 다 통과하는데 "
     "**정답으로 표시된 후보가 거짓**인 문항이 있었다. D1=완전 일치(정확) · D2=정답 후보가 answer 의 "
     "서술어를 부정(휴리스틱) · D3=후보에 질문 내용어 0개(정보). ⚠️**오탐 3종을 고쳐 세웠다**"),
    ("check_flag_used",     ["check_flag_used.py"],
     "★★**선언만 하고 아무도 안 읽는 CLI 플래그**(2026-09-03 신설). `common_bpb.py --drop-contaminated` 가 "
     "**파서에만 있고 몸통이 0줄**이라 배치가 그 플래그를 주고 돌렸는데 출력이 **바이트 동일**이었다(결과 053 §12.3). "
     "게이트 3(`check_batch_flags`)은 *'파서에 있는가'* 만 본다 — **함정 37 의 셋째 얼굴**. ✅실검출 2건·오탐 2건은 규칙으로 면제"),
    ("check_batch_flags",   ["check_batch_flags.py"],
     "배치가 쓰는 CLI 플래그가 **파서에 실제로 있는가**(미구현 배치 2회 재발)"),
    ("check_flag_whitelist", ["check_flag_whitelist.py"],
     "★★배치가 써도 되는 플래그인가 — **'존재' 가 아니라 '의도'**(2026-09-04, 승인된 제안서). "
     "게이트 3·5 를 통과해도 `--drop-contaminated`(미구현) · `--repeat-kv-reuse`(기각)는 "
     "**배치에 쓰면 안 된다.** 🚫함정 18 을 피하려고 **목록은 파서가 소유하고 표는 등급만** 소유한다 — "
     "양방향 대조라 **새 플래그를 넣고 등급을 안 적으면 에러**다(사용자 요구). "
     "✅행 제거·가짜 행 주입 둘 다 검출 확인. 등급표 `scripts/flag_whitelist.tsv`"),
    ("check_pending",       ["check_pending.py"],
     "★★**선결이 없는데 미뤄 둔 항목**(2026-09-04, 승인된 제안서). `check_handoff` 규칙 9 가 "
     "*'없는 배치를 있는 것처럼 적지 마라'* 라면 이것은 *'만들 수 있는 배치를 안 만들고 넘기지 마라'* 다 — "
     "**의사결정함정 D1 을 기계로.** ✅재현 검증: 2026-09-03 핸드오프에서 **제안서가 지목한 두 행** "
     "(P084 단계0 · 유니크 토큰 축)을 정확히 잡는다. ⚠️초판이 시간칸 `—` 를 0 으로 읽어 3행을 "
     "오탐했고 고쳤다(제안서 §8 이 미리 적어 둔 위험)"),
    ("check_lr_factor_sync", ["check_lr_factor_sync.py"],
     "★★**`_lr_factor` 가 두 곳에 산다** — 정본은 `trainer.py`, 복제는 `diag_lrm_values.py`"
     "(torch 없이 WD 바닥을 계산해야 해서). 함정 18 을 남기는 대신 **값을 기계로 대조**한다 — "
     "sched 4×steps 4×decay_frac 3×점 40 = 1,992점. ✅결함 주입(0.9→0.8) 검출 확인"),
    ("check_eval_pool",     ["check_eval_pool.py"],
     "★★★**채점지가 답안지였는가**(2026-09-05, 결과 075 §6). `prepare()` 의 val 은 스트림 말미 0.5% 이고 "
     "캐시는 결정적 스트림의 **접두사**라 `ko-en_300M/val.bin` 이 `ko-en_600M/train.bin` 안에 "
     "**1,500,000 토큰 전부 바이트 일치**한다. `paired_eval` 기본값이 `--tokens 300M` 이고 표준 학습이 "
     "`--pool-tokens 600M` 이라 **142개 런의 full-val 이 학습 데이터였다.** "
     "✅실물 배치(`run_P084_Stage4_*`)에서 4건 검출 확인. ⚠️`-done` 은 경고로 낮춘다"),
    ("registry --scan",     ["registry.py", "--scan"],
     "★★**런 레지스트리에 빠진 학습 런이 있는가**(2026-09-05, 승인된 제안서 안 C). "
     "`runs/registry.tsv` 가 정본(git·diff) · `docs/RUN_REGISTRY.md` 가 뷰 · `runs/registry.db` 가 질의 캐시. "
     "🚫`runlog` 를 안 거치면 기록이 안 되므로 **json 쪽에서 역으로 본다** — 제안서 §7.2 가 적어 둔 약점의 그물. "
     "✅소급 반영으로 full-train **142/142 = 100%** 에 계획번호가 붙었다"),
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
    ("check_smoke_diag",    ["check_smoke_diag.py"],
     "★★스모크 **진단런**의 계약(`smoke_diag_contract.tsv`) ↔ 배치 ↔ 로그 — "
     "2026-09-05 에 `diag_sparse34_pack` 이 exit 1 인데 *'총 에러 0건'* 이 찍혔다. "
     "`check_smoke` 는 필드만 보고 종료코드를 안 보며, 종료코드를 보라고 만든 "
     "`summarize_smoke` 는 배치가 `--` 를 빠뜨려 신설 이래 한 번도 안 돌았다. "
     "★이 게이트가 *'그 팔이 무엇을 인쇄했는가'* 를 본다(로그가 코드보다 낡으면 경고)"),
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
    ("dryrun_batch",        ["dryrun_batch.py", "--strict", "--live-only"],
     "★★★배치를 **돌리기 전에** 프리셋 기본값까지 넣은 **유효 조건**을 인쇄한다"
     "(2026-09-02). 게이트 21 은 런이 **끝난 뒤** json 을 보고, 이것은 **돌기 전** 배치를 본다 — "
     "`--cla-group` 누락으로 3.6시간을 태운 자리가 이 사이였다. "
     "✅17개 학습 호출 실사에서 실제 OOM 배치 1건 검출·오탐 0. "
     "⚠️`-done` 은 건너뛴다(끝난 배치의 알려진 실패로 스위트를 빨갛게 두면 새 문제를 가린다)"),
    ("check_compass",       ["check_compass.py"],
     "★★**연구방향 나침반(`handoff/COMPASS.md`)이 낡았는가**(2026-09-08(2차) 신설, 승인된 제안서). "
     "축 12개 각각에 대해 **사람이 적은 인용 번호** vs **그 축을 제목에서 다루는 결과문서의 최대 번호** — "
     "★두 값이 독립이라 함정 43(자기 사본과 대조하는 게이트)을 피한다. "
     "본문이 아니라 **헤딩**만 본다(본문으로 보면 매번 빨개지고 아무도 안 읽는 경고는 미탐과 같다). "
     "✅행 하나를 낡게 만들어 검출 확인. ⚠️키워드 오탐 4건을 실물에 대고 걸렀다(`폭`->`폭발`, `CLA`->`CLAUDE.md`)"),
    ("check_control_chars", ["check_control_chars.py"],
     "★★**저장소 텍스트 파일의 제어문자**(2026-09-08(2차) 신설, 사용자 지시 3). "
     "백슬래시 사고 **누적 15회** — 파이썬 패치나 heredoc 의 `\b`·`\v` 가 **실제 바이트**가 된다. "
     "🚫문법 오류가 아니라 **문법적으로 멀쩡한 쓰레기**라 아무도 못 본다. "
     "`lint_bat` 규칙 1b 가 같은 것을 보지만 **`.bat` 만** 본다 — 이 게이트가 `.py`·`.md`·`.tsv` 를 맡는다. "
     "⚠️탭은 안 본다(`.tsv` 구분자·`.py` 들여쓰기로 합법). ✅스크래치패드 사본에 실사고 바이트를 심어 검출 확인(1->0)"),
    ("check_smoke_tokenizer", ["check_smoke_tokenizer.py"],
     "★★**`--data synthetic` 을 받는 도구가 토크나이저 파일을 요구하는가**(2026-09-08(2차) 신설). "
     "`prepare()` 는 합성에 BPE 를 학습하지 않으므로 `tok-synthetic-*.json` 은 **설계상 영원히 없다** — "
     "그런데 스모크 팔 [21c] 가 `Tokenizer.from_file` 을 무조건 불러 `os error 2` 로 죽었고 "
     "**큐 전체가 멈췄다**. 기존 넷은 전부 통과했다: 플래그도(3) import 도(4) 축 커버리지도(23) "
     "멀쩡했고 진단 계약(32)은 **로그가 없어서** 못 봤다. ★함정 37 의 또 다른 얼굴 — "
     "*'팔을 넣었다 ≠ 그 팔이 돌 수 있다'*. ✅실물 결함 1건 검출 후 고치고 켰다(오탐 0)"),
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
