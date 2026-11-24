"""Queue the tied-head tail-KD comparison and three physical memory measurements."""

import argparse
import json
from pathlib import Path

from scripts import run_p013_p014e_gpu_followups_20261118 as serial


serial.PROFILE = serial.OUT / "GPU_SERIAL_TAIL_HF_PROFILE_v1.json"
serial.TERMINAL = serial.OUT / "GPU_SERIAL_TAIL_HF_TERMINAL_v1.json"
serial.STOP = serial.OUT / "GPU_SERIAL_TAIL_HF_STOP"
serial.JOBS = (
    ("093", "P102A_Stage2ibW_tiled_tail_KD_GPU", "scripts.diag_p102a_tiled_tail_kd",
     "p102a_tiled_topk_uniform_tail_v1_20261118", ("profile.json",), 365),
    ("101", "P106B_Stage11eW_hf_sampled_vram_GPU", "scripts.diag_p106b_hf_sampled_memory",
     "p106b_hf_sampled_generation_v1_20261118", ("profile.json",), 425),
)
LAUNCHER = Path(__file__).resolve()
LOCK = serial.OUT / "GPU_SERIAL_TAIL_HF_WRAPPER_v1.json"


def wrapper_lock():
    return dict(wrapper_sha256=serial.contract.digest(LAUNCHER),
                profile_sha256=serial.contract.digest(serial.PROFILE))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    if parser.parse_args().action == "prepare":
        assert not LOCK.exists()
        serial.prepare()
        serial.contract.write(LOCK, wrapper_lock())
    else:
        assert json.loads(LOCK.read_bytes()) == wrapper_lock()
        raise SystemExit(serial.run())
