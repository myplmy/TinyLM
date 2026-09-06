#!/usr/bin/env python3
"""PM moonshot 산출물이 일반 실험 계보와 branch 밖으로 새지 않는지 검사한다. torch 0."""
from __future__ import annotations

import io
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_BRANCH = "moonshot"
PLAN_DIR = ROOT / "plan"
BATCH_DIR = ROOT / "moonshot_batch"
RESULT_DIR = ROOT / "moonshot_result"
PM = re.compile(r"PM\d{3,}", re.I)
BATCH_NAME = re.compile(
    r"^run_(PM\d{3,})__MOONSHOT__(Stage\d+[A-Za-z]?)_[A-Za-z0-9_]+?(-done)?\.bat$")


def branch_name() -> str:
    try:
        p = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        return p.stdout.strip() if p.returncode == 0 else ""
    except Exception:  # noqa: BLE001 — 검사 결과로 보고한다
        return ""


def stage_present(doc: Path, stage: str) -> bool:
    text = doc.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(stage)}(?![A-Za-z0-9])", text, re.I))


def check_schedule_contract(errors: list[str], infos: list[str]) -> None:
    """전용 순수 모듈과 config re-export 계약을 검사한다. torch import 없음."""
    try:
        sys.path.insert(0, str(ROOT))
        from tinylm.config import PRESETS, gqa_pass_order as config_gqa_pass_order
        from tinylm.moonshot import pm000_latin_gqa as pm000

        if "torch" in sys.modules:
            errors.append("PM000 순수 정적 계약 로드가 torch를 import했다")
        src = (ROOT / "tinylm" / "moonshot" / "pm000_latin_gqa.py").read_text(
            encoding="utf-8", errors="replace")
        if re.search(r"^\s*(?:from\s+torch\b|import\s+torch\b)", src, re.M):
            errors.append("PM000 알고리즘 정본이 torch를 직접 import한다")
        if pm000.gqa_pass_order("fixed", 3, 17) != (0,):
            errors.append("fixed GQA pass order가 identity가 아니다")
        if pm000.gqa_pass_order("latin", 3, 17) != (0, 1, 2):
            errors.append("Latin GQA pass order가 0,1,2가 아니다")
        orders = [pm000.gqa_pass_order("random", 5, seed) for seed in range(16)]
        if not all(order[0] == 0 and sorted(order) == list(range(5)) for order in orders):
            errors.append("random GQA pass order가 R1 identity 또는 완전 균형을 깨뜨린다")
        if len(set(orders)) < 2:
            errors.append("random GQA pass seed가 순서를 바꾸지 못한다")
        if config_gqa_pass_order is not pm000.gqa_pass_order:
            errors.append("config.py가 PM000 schedule 정본을 re-export하지 않는다")
        visits: dict[int, int] = {}
        if [pm000.next_layer_pass_id(visits, 7) for _ in range(3)] != [0, 1, 2]:
            errors.append("PM000 pass_id가 실제 layer visit을 증가시키지 않는다")
        shifts = [pm000.gqa_pass_shift((0, 1, 2), pass_id) for pass_id in range(5)]
        if shifts != [0, 1, 2, 0, 1]:
            errors.append("PM000 pass_id가 schedule 주기를 따라 shift를 선택하지 않는다")
        tiny = PRESETS["tinygqa"](128, True)
        if not (tiny.n_q_heads == 4 and tiny.n_kv_heads == 2):
            errors.append("tinygqa smoke preset이 nontrivial GQA가 아니다")
        infos.append("PM000 core=tinylm/moonshot/pm000_latin_gqa.py, torch-free")
        infos.append("PM000 schedule=fixed identity, Latin balanced, random deterministic")
    except Exception as exc:  # noqa: BLE001 — 정적 gate 결과로 전환
        errors.append(f"PM000 schedule contract 로드 실패: {type(exc).__name__}: {exc}")


def main() -> int:
    errors: list[str] = []
    infos: list[str] = []

    check_schedule_contract(errors, infos)

    smoke_tool = ROOT / "scripts" / "batch" / "tool_smoke.bat"
    smoke_text = smoke_tool.read_text(encoding="ascii", errors="replace")
    smoke_call = next((line for line in smoke_text.splitlines()
                       if "--gqa-pass-schedule latin" in line and " run100m.py train " in line), "")
    smoke_tag = re.search(r"--tag\s+(\S+)", smoke_call)
    if not smoke_tag or "_pm000__" not in smoke_tag.group(1).lower():
        errors.append("PM000 공통 smoke tag에 _pm000__ 격리 표식이 없다")
    elif not smoke_tag.group(1).endswith("sm_gqapass"):
        errors.append("PM000 공통 smoke tag가 check_smoke의 sm_gqapass suffix 계약과 다르다")
    else:
        infos.append(f"PM000 smoke tag={smoke_tag.group(1)} (normal registry excluded)")

    branch = branch_name()
    if branch != EXPECTED_BRANCH:
        errors.append(f"현재 branch={branch or '(unknown)'}; PM 실행 허용 branch={EXPECTED_BRANCH}")
    else:
        infos.append(f"branch={branch}")

    for directory in (PLAN_DIR, BATCH_DIR, RESULT_DIR):
        if not directory.is_dir():
            errors.append(f"필수 moonshot 경로 없음: {directory.relative_to(ROOT)}")

    plan_by_id: dict[str, list[Path]] = {}
    if PLAN_DIR.is_dir():
        for path in sorted(PLAN_DIR.glob("*.md")):
            if path.name == "README.md":
                continue
            m = re.match(r"^(PM\d{3,})__MOONSHOT__.+__PLAN\.md$", path.name)
            if not m:
                errors.append(f"moonshot 계획 이름 규약 위반: plan/{path.name}")
                continue
            plan_by_id.setdefault(m.group(1), []).append(path)
        for pnum, docs in plan_by_id.items():
            if len(docs) != 1:
                errors.append(f"{pnum} 계획서가 {len(docs)}개다: {[p.name for p in docs]}")

    batches = sorted(BATCH_DIR.glob("*.bat")) if BATCH_DIR.is_dir() else []
    for path in batches:
        m = BATCH_NAME.match(path.name)
        if not m:
            errors.append(f"moonshot batch 이름 규약 위반: moonshot_batch/{path.name}")
            continue
        pnum, stage = m.group(1), m.group(2)
        docs = plan_by_id.get(pnum, [])
        if len(docs) != 1:
            errors.append(f"{path.name}: 대응 계획서가 정확히 1개가 아니다")
        elif not stage_present(docs[0], stage):
            errors.append(f"{path.name}: 계획서에 {stage}가 없다")

        text = path.read_text(encoding="ascii", errors="replace")
        if "tool_wandb_push" in text:
            errors.append(f"{path.name}: PM 결과를 일반 W&B push 도구로 보내면 안 된다")
        runlog_lines = [line for line in text.splitlines()
                        if "scripts\\runlog.py" in line and not line.lstrip().upper().startswith("REM")]
        if not runlog_lines:
            errors.append(f"{path.name}: runlog 호출이 없다")
        for line in runlog_lines:
            if "--outdir moonshot_result" not in line:
                errors.append(f"{path.name}: runlog에 --outdir moonshot_result 누락")
            name = re.search(r"--name\s+(\S+)", line)
            if not name or not name.group(1).startswith(f"{pnum}__MOONSHOT__{stage}_"):
                got = name.group(1) if name else "(none)"
                errors.append(f"{path.name}: runlog name 불일치: {got}")
        for line in text.splitlines():
            if "run100m.py train" not in line or line.lstrip().upper().startswith("REM"):
                continue
            tag = re.search(r"--tag\s+(\S+)", line)
            if not tag or f"_pm{pnum[2:]}__" not in tag.group(1).lower():
                got = tag.group(1) if tag else "(none)"
                errors.append(f"{path.name}: PM checkpoint tag namespace 누락: {got}")

    # 일반 계보에는 파일명뿐 아니라 본문에도 PM 번호가 없어야 한다.
    for directory in (ROOT / "test_plan", ROOT / "test_result"):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*")):
            if not path.is_file():
                continue
            try:
                text = io.open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if PM.search(path.name) or PM.search(text):
                errors.append(f"일반 실험 영역에 PM 참조가 섞였다: {path.relative_to(ROOT)}")
    registry = ROOT / "experiments.tsv"
    if registry.exists() and PM.search(registry.read_text(encoding="utf-8", errors="replace")):
        errors.append("experiments.tsv에 PM 번호가 섞였다")
    run_registry = ROOT / "runs" / "registry.tsv"
    if run_registry.exists() and PM.search(
            run_registry.read_text(encoding="utf-8", errors="replace")):
        errors.append("일반 runs/registry.tsv에 PM tag가 섞였다")
    for path in ROOT.glob("run_PM*.bat"):
        errors.append(f"PM batch가 repo root에 있다: {path.name}")

    if RESULT_DIR.is_dir():
        for path in sorted(RESULT_DIR.iterdir()):
            if path.name in {"README.md", "registry.tsv"} or not path.is_file():
                continue
            if not re.search(r"PM\d{3,}__MOONSHOT__", path.name):
                errors.append(f"moonshot_result 파일 이름에 예약 표식이 없다: {path.name}")
        registry = RESULT_DIR / "registry.tsv"
        if registry.exists():
            lines = registry.read_text(encoding="utf-8", errors="replace").splitlines()
            if not lines or lines[0] != "tag\tplan_stage\tlog_file\tjson_file\trecorded_at":
                errors.append("moonshot_result/registry.tsv 헤더가 다르다")
            for line in lines[1:]:
                if line.strip() and not re.match(r"[^\t]*_pm\d{3,}__[^\t]*\tPM\d{3,}/stage", line, re.I):
                    errors.append(f"moonshot 전용 registry 행 규약 위반: {line[:80]}")

    print("=" * 92)
    print("  PM moonshot branch/namespace gate (torch 0)")
    print("=" * 92)
    for info in infos:
        print(f"  [ok] {info}")
    print(f"  plans={sum(len(v) for v in plan_by_id.values())} batches={len(batches)}")
    if errors:
        for error in errors:
            print(f"  [E] {error}")
        print(f"\n  FAIL: {len(errors)} error(s). PM batch must not run.")
        return 1
    print("  PASS: PM artifacts are isolated from normal experiment paths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
