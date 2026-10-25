#!/usr/bin/env python3
"""Seal root-owned native training metadata without importing Torch."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native_format_training as train

BASE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def ref(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}

def publish(name, value):
    path = BASE / name
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(data)
    return ref(path)

def main():
    for name in ("native_training_profile_v1.json", "native_training_f4_v1.json", "native_training_inputs_v1.json"):
        if (BASE / name).exists():
            raise FileExistsError(name)
    source = train.source_identity()
    if source["sha256"] != "9EA74842B672407044FB52B668B56EC8AD2C4390229409C7E12EE5F9B002F90C":
        raise ValueError("frozen training source differs")
    profile = {
        "schema": train.PROFILE, "recipe": train.RECIPE,
        "arms": [
            {"id": "format_muon", "corpus": "format", "optimizer": "muon", "required": True},
            {"id": "format_normuon", "corpus": "format", "optimizer": "normuon", "required": True},
        ],
        "normuon": {"beta2": .95, "eps": 1e-10, "implementation": "TINYLM_ADAPTED_POST_NS_ROW_EMA"},
        "train_deadline": train.TRAIN_END.isoformat(), "final_deadline": train.END.isoformat(),
        "cleanup_reserve_sec": 120, "evaluation_reserve_sec": 3600,
        "minimum_pair_training_sec": 15000, "entry_free_mib": 14000,
        "validation": {"path": str(train.native.VAL.relative_to(ROOT)), "sha256": train.native.VAL_SHA},
        "geometry_parent": {"path": str(train.native.PARENT.relative_to(ROOT)),
                            "sha256": train.native.PARENT_SHA, "use": "CONFIG_AND_TOKEN_METADATA_ONLY"},
        "pair_complete": ref(ROOT / "data_cache/p106b_native_format_pair_v1_20261026_s1337/complete.json"),
        "pair_policy": ref(BASE / "native_format_pair_policy.json"),
        "tokenizer": {"path": str(train.native.TOKENIZER.relative_to(ROOT)), "sha256": train.native.TOKENIZER_SHA},
        "generation": None,
        "scope": "FULL300M_NATIVE_NTP_OPTIMIZER_PAIR_NOT_TEACHER75M_SFT",
    }
    profile_ref = publish("native_training_profile_v1.json", profile)
    f4 = {
        "schema": "P106B_NATIVE_FORMAT_F4_V1", "root_approved": True,
        "source_sha256": source["sha256"], "profile_sha256": profile_ref["sha256"],
        "allowed_modes": ["cost", "train"], "authority": "USER_26OCT2026_17KST_CPU_GPU",
        "root_review": "FULL_DRIVER_AND_EXACT_CPU52_EXIT0",
        "cpu_log": ref(ROOT / "test_result/101_log_20261026_P106B_Stage10aWb_native_training_cpu.txt"),
        "preflight": ref(BASE / "native_format_pair_preflight.md"),
        "cost_before_main": True, "no_small_run_quality_decision": True,
        "no_teacher_student_coload": True, "global_article_leakage": "UNVERIFIED",
        "full_semantic_cleaning": False, "original_muon_arm": "PREPARED_NOT_RUN",
        "generation_after_complete": "SEPARATE_PLAIN_CHATML_GREEDY128",
        "matrix_scope": "TLINEAR_WEIGHTS_ONLY",
    }
    f4_ref = publish("native_training_f4_v1.json", f4)
    sealed = publish("native_training_inputs_v1.json", {"profile": profile_ref, "f4": f4_ref, "source": source})
    if "torch" in sys.modules:
        raise RuntimeError("unexpected Torch import")
    print(json.dumps({"sealed": sealed, "profile": profile_ref, "f4": f4_ref, "torch_imported": False}))

if __name__ == "__main__":
    main()
