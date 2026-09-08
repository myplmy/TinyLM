#!/usr/bin/env python3
"""★★**게이트 33 — 합성 데이터에 토크나이저를 요구하는 팔이 있는가.**

## 왜 이 게이트가 생겼나 (2026-09-08(2차), 사용자 지시 1)

2026-09-08 04:54 스모크에서 팔 **[21c]**(LUT 배포 상주)가 죽었다.

    python scripts\\mem_runtime.py --preset tiny --data synthetic ... --drop-latent --lut
    Exception: 지정된 파일을 찾을 수 없습니다. (os error 2)
    [runlog] 종료코드 1

원인은 한 줄이다 — `mem_runtime.py` 가 `Tokenizer.from_file(tokenizer_path("synthetic"))`
를 **무조건** 불렀는데, `prepare()` 는 `name == "synthetic"` 일 때 **BPE 를 학습하지 않는다.**
즉 `data_cache/tok-synthetic-32768.json` 은 **설계상 영원히 없다.**
🚫**파일이 없는 게 사고가 아니라, 없는 파일을 요구한 것이 사고다.**

## 왜 기존 32종이 못 잡았나

| 게이트 | 무엇을 보나 | 왜 놓쳤나 |
|---|---|---|
| `check_batch_flags` | 플래그가 **파서에 있는가** | 플래그는 다 있었다 |
| `check_imports` | `from A import B` 의 B 가 A 에 있는가 | import 는 멀쩡했다 |
| `check_smoke_diag` | 배치·소스·**로그** 세 곳의 표지 대조 | 그 팔은 **로그가 없었다**(처음 도는 팔) |
| `check_smoke_coverage` | 배치가 쓰는 **축**을 스모크가 켜는가 | 팔은 있었다. **실행이 안 됐을 뿐** |

★**공통점: 아무도 "이 팔이 요구하는 입력이 존재하는가" 를 안 봤다.**
함정 37 의 또 다른 얼굴 — *"팔을 넣었다 ≠ 그 팔이 돌 수 있다"*.

## 규칙

> **`--data synthetic` 을 받는 `scripts/*.py` 는 토크나이저를 `load_tokenizer()` 로 얻는다.**
> 🚫`Tokenizer.from_file(...)` 직접 호출 금지 — 그 경로에는 합성 분기가 없다.

`tinylm.data.load_tokenizer` 가 이름으로 갈라서 합성이면 스텁을, 실데이터면 실제 파일을 준다
(없으면 `SystemExit(2)`). **단일 소스**이므로 다음 도구가 같은 함정에 안 빠진다(R14).

면제: 소스 어딘가에 `# [tok-ok]` 주석을 두면 이 검사에서 뺀다. **면제에는 이유를 함께 적는다.**

✅**검출 확인**: 고치기 **전**의 실물(`tool_smoke.bat` x `mem_runtime.py`)에 대고 돌려
**위반 1건 · exit 1**, 고친 뒤 **0건 · exit 0**. 🚫자기시험용 플래그(`--root`)는 두지 않는다 —
실물에 결함이 있는 상태에서 확인했으므로 필요 없고, 배치에서 못 쓰는 플래그를
`flag_whitelist.tsv` 에 넣으면 그 표의 뜻이 흐려진다.

사용법
    python scripts/check_smoke_tokenizer.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# `python scripts\foo.py` 하나. 🚫**꼬리를 그룹으로 잡지 않는다** —
#   `([^\r\n]*)` 를 붙였더니 첫 매치가 줄 나머지를 통째로 삼켜서 `finditer` 가
#   한 줄에 **매치를 하나만** 냈고, 스모크의 `runlog.py -- python scripts\진짜.py`
#   형태에서 **언제나 runlog.py 만** 검사했다(초판이 위반 0건을 찍은 이유).
_CALL = re.compile(r"python\s+scripts[\\/]([A-Za-z0-9_]+)\.py")


def _batches(root: Path):
    out = list((root / "scripts" / "batch").glob("*.bat"))
    out += list(root.glob("*.bat"))
    return sorted(set(out))


def main() -> int:
    root = ROOT
    fails, checked = [], 0
    for bat in _batches(root):
        try:
            text = bat.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ln in text.split("\n"):
            s = ln.strip()
            if s.upper().startswith("REM") or "--data synthetic" not in s:
                continue
            # ★한 줄에 `python scripts\X.py` 가 둘 이상 나온다 —
            #   스모크는 전부 `runlog.py --name ... -- python scripts\진짜.py` 형태다.
            #   🚫`search()` 로 첫 매치를 잡으면 **언제나 runlog.py 를 검사**하게 되고
            #   그러면 이 게이트는 영구히 통과한다(자기 자신이 함정 38 이 된다).
            #   → `--data synthetic` **앞에 있는 마지막** 호출이 그 플래그의 주인이다.
            pos = s.index("--data synthetic")
            cands = [m for m in _CALL.finditer(s) if m.start() < pos]
            if not cands:
                continue                      # run100m.py train 등 — 학습은 토크나이저를 안 쓴다
            name = cands[-1].group(1)
            src = root / "scripts" / f"{name}.py"
            if not src.exists():
                continue                      # check_batch_flags 가 볼 일이다
            body = src.read_text(encoding="utf-8", errors="replace")
            if "# [tok-ok]" in body:
                continue
            checked += 1
            if "tokenizer_path(" not in body and "Tokenizer.from_file(" not in body:
                continue                      # 토크나이저를 아예 안 쓴다 — 문제 없다
            if "load_tokenizer(" in body:
                continue                      # ✅단일 소스를 쓴다
            fails.append((bat.name, name))

    print("=" * 78)
    print("  게이트 33 — 합성 데이터에 토크나이저 파일을 요구하는 팔")
    print("=" * 78)
    print(f"  검사한 (배치 x 스크립트) 조합: {checked}개")
    if not fails:
        print("  ✅ 위반 0건 — 합성 팔이 전부 `load_tokenizer()` 를 쓰거나 토크나이저를 안 쓴다.")
        return 0
    for bat, name in fails:
        print(f"  🚫 {bat} -> scripts/{name}.py")
        print("       `--data synthetic` 을 주는데 토크나이저를 직접 연다.")
        print("       ★고치는 법: `from tinylm.data import load_tokenizer` 후")
        print("         `tok = load_tokenizer(a.data)`. 합성이면 스텁, 실데이터면 실제 파일이다.")
        print("       (설계상 `data_cache/tok-synthetic-*.json` 은 영원히 없다)")
    print(f"\n  🚫 위반 {len(fails)}건 — 이 팔은 스모크에서 반드시 exit 1 이 된다.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
