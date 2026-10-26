#!/usr/bin/env python3
"""Verify that new readback budgets start at their call, without model work."""
from pathlib import Path
import importlib.util
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
BASE = Path(__file__).resolve().parent

def main():
    rows = []
    for name, function in (("run_native_official", "budget"), ("run_native_dialogue", "make_budget")):
        spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = time.monotonic()
        observed = getattr(module, function)()
        after = time.monotonic()
        assert before <= observed.started <= after
        assert 599 <= observed.remaining() <= 600 and observed.reserve == 120
        assert observed.end - time.monotonic() <= module.diag.END.timestamp() - time.time() + .01
        rows.append({"module": name, "started_in_call_interval": True, "remaining_sec": observed.remaining(),
                     "reserve_sec": observed.reserve, "original_absolute_deadline_retained": True})
    assert "torch" not in sys.modules
    from scripts import diag_p106b_native_format_training as training
    from scripts import diag_p106b_native_format_official as official
    from scripts import diag_p106b_native_format_dialogue as dialogue
    pins = [training.source_identity()["sha256"], official.source_identity()["sha256"], dialogue.source_identity()["sha256"]]
    assert pins == [dialogue.TRAINING_SHA, dialogue.OFFICIAL_SHA,
        "E059BA2DE73D14053021932ACD37B83505D3ABD5523488809392D66F91164E9B"]
    value = {"checks": rows, "source47_58_70_unchanged": True, "torch_imported": False, "gpu_calls": 0,
             "model_loaded": False, "module_import_started_not_reused": True}
    with (BASE / "root_readback_budget_check_v2.json").open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(value))

if __name__ == "__main__":
    main()
