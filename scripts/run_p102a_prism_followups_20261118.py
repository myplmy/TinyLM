"""Queue the independent P102A precision and Prism memory experiments."""

import argparse

from scripts import run_p013_p014e_gpu_followups_20261118 as serial


serial.PROFILE = serial.OUT / "GPU_SERIAL_P102A_PRISM_PROFILE_v1.json"
serial.TERMINAL = serial.OUT / "GPU_SERIAL_P102A_PRISM_TERMINAL_v1.json"
serial.STOP = serial.OUT / "GPU_SERIAL_P102A_PRISM_STOP"
serial.JOBS = (
    ("093","P102A_Stage2iaW_weighted_fp32_ns_GPU","scripts.diag_p102a_weighted_fp32_ns",
     "p102a_weighted_fp32_ns_v1_20261118",("profile.json","variation.json"),470),
    ("101","P106B_Stage8pr8W_prism_sampled_vram_GPU","scripts.diag_p106b_prism_sampled_memory",
     "p106b_prism_context_sampled_vram_v1_20261118",("profile.json",),330),
)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run"))
    if parser.parse_args().action=="prepare":
        serial.prepare()
    else:
        raise SystemExit(serial.run())
