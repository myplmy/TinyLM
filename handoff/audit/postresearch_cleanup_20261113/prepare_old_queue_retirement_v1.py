"""Prepare retirement of completed launchers still exposed by the queue."""
from pathlib import Path
import json
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_exact_cleanup_v1 import ROOT, OUT, digest, identity, read, save

pins = {r["path"]: r["sha256"] for r in
        read("handoff/audit/nov13_value_edit/STATIC_INPUTS_v46_final.json")["inputs"]}
sources = []
future = "run_P106B_Stage4fsXW_user_supported_resume8h.sh"
for line in (ROOT / "experiments.tsv").read_text(encoding="utf-8").splitlines():
    if line.startswith("#"):
        continue
    cells = line.split("\t")
    if len(cells) < 9 or cells[1] == "-":
        continue
    name = cells[2]
    if name == future or not (ROOT / name).is_file() or name.endswith(("-done.sh", "-cancel.sh", "-hold.sh")):
        continue
    sources.append(name)
assert len(sources) == len(set(sources)) == 31
raw_logs = list((ROOT / "test_result").glob("*_log_*.txt"))
rows, holds = [], []
for name in sources:
    path = ROOT / name
    raw = path.read_bytes()
    sha = digest(path)
    logs = []
    needle = path.stem.removeprefix("run_")
    for log in raw_logs:
        if needle not in log.stem:
            continue
        text = log.read_text(encoding="utf-8", errors="replace")
        codes = re.findall(r"\[runlog\] 종료코드 (-?\d+)", text)
        if codes:
            logs.append(dict(path=str(log.relative_to(ROOT)), sha256=digest(log), exit_code=int(codes[-1])))
    row = dict(source=name, target=path.stem + "-done.sh", command_text=raw.decode("utf-8"),
               sha256=sha, identity=identity(path), logs=logs, source_pin_match=pins.get(name) == sha)
    if not logs or not row["source_pin_match"]:
        holds.append(row)
    else:
        rows.append(row)
save("OLD_QUEUE_LAUNCHER_PLAN_v1.json", dict(schema="NOV13_OLD_QUEUE_LAUNCHERS_V1", launchers=rows, holds=holds,
    reason="완료 원로그와 소스봉인은 있으나 원래 이름이 남아 메뉴에 재노출됐다. 명령 보존 후 -done 처리·삭제한다."))
print("queue_retire", len(rows), "hold", len(holds))
for row in holds:
    print("HOLD", row["source"], "logs", len(row["logs"]), "pin", row["source_pin_match"])
