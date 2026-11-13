"""Match three legacy child commands; preserve the unexecuted fresh router as HOLD."""
from pathlib import Path
import re
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_exact_cleanup_v1 import ROOT, OUT, digest, read, save

plan = read("handoff/audit/postresearch_cleanup_20261113/OLD_QUEUE_LAUNCHER_PLAN_v1.json")
hold = []
python = "/home/uranus/miniforge3/envs/tlm_torch/bin/python"
for row in plan["holds"]:
    if row["source"].startswith("run_P078_"):
        row["hold_target"] = Path(row["source"]).stem + "-hold.sh"
        row["hold_reason"] = "새 fresh512/별도 권한을 요구하는 미실행 경로다. 과거 historical router 완료와 구분하고 실행 큐에서 보류한다."
        hold.append(row)
        continue
    assert len(row["logs"]) == 1
    line = next(line for line in row["command_text"].splitlines()
                if "scripts/runlog.py" in line and " -- " in line)
    tokens = shlex.split(line)
    expected = [v.replace("${PY}", python) for v in tokens[tokens.index("--") + 1:]]
    text = (ROOT / row["logs"][0]["path"]).read_text(encoding="utf-8")
    actual = [shlex.split(value) for value in re.findall(r"^\[runlog\] cmd=(.*)$", text, re.M)]
    assert expected in actual, (row["source"], expected, actual)
    row["child_command_matches_raw_log"] = expected
    row["source_pin_match"] = "LATEST_SCOPE_NOT_INCLUDED_CHILD_COMMAND_VERIFIED"
    plan["launchers"].append(row)
plan["holds"] = hold
assert len(plan["launchers"]) == 30 and len(hold) == 1
plan["parent_plan_sha256"] = digest(OUT / "OLD_QUEUE_LAUNCHER_PLAN_v1.json")
save("OLD_QUEUE_LAUNCHER_PLAN_v2.json", plan)
print("completed_retire", len(plan["launchers"]), "fresh_router_hold", len(plan["holds"]),
      "plan_sha", digest(OUT / "OLD_QUEUE_LAUNCHER_PLAN_v2.json"))
