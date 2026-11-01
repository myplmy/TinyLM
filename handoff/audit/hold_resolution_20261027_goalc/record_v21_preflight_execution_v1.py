"""Attach observed tool chunks to the immutable preflight without rewriting it."""
from pathlib import Path
import json
import hashlib

base = Path(__file__).resolve().parent
names = ["V21_DRAFT_PREFLIGHT_V1.json", "test_refinement_v9_v2.log", "prepare_v21_execution_v1.log"]
result = dict(status="ACTUAL_PREFLIGHT_AND_FRESH_REPLAY_EXITS_ZERO_NOT_CORPUS_COMPLETION",
              fresh_replay=dict(observed_tool_chunk="61725e", actual_exit_code=0, tests=40),
              preflight=dict(observed_tool_chunk="e795d9", actual_exit_code=0),
              pins={name: hashlib.sha256((base / name).read_bytes()).hexdigest().upper() for name in names},
              explanation="The preflight placeholder refers to this exact recorded fresh replay result; the original preflight is immutable.",
              cache_admitted=0, goal_complete=False, training_authorized=False)
with (base / "V21_PREFLIGHT_EXECUTION_RECEIPT_V1.json").open("x", encoding="utf-8") as out:
    json.dump(result, out, ensure_ascii=False, indent=2)
