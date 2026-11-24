"""After the two main studies, check native-shape per-micro STE reuse on CUDA."""

from datetime import datetime
import hashlib
import json
import os
import signal
import time

from scripts import run_p109b_scratch_pair_20261120 as pair


END = datetime.fromisoformat("2026-11-20T17:00:00+09:00").timestamp()
QUALITY_REPORT = pair.ROOT / "test_result/evidence/p109b_firstpass_chat32_choice_20261120/report.json"
CPU_PROOF = pair.ROOT / "test_result/evidence/p109b_g4_ste_per_micro_exact_cpu_20261120/report.json"
OUT = pair.ROOT / "test_result/evidence/p109b_g4_ste_per_micro_exact_cuda_20261120"


def read(path):
    return json.loads(path.read_bytes())


def wait_for_main_study():
    while time.time() + 240 < END:
        if QUALITY_REPORT.is_file() and QUALITY_REPORT.read_bytes().endswith(bytes([10])):
            result = read(QUALITY_REPORT)
            if (set(result["tasks"]) != {"winogrande", "kobest_copa"}
                    or result["queue_sha256"] != pair.file_sha(pair.OUT / "queue.json")
                    or not read(pair.OUT / "queue.json")["complete"]):
                raise ValueError("main training and quality evidence must both close first")
            break
        time.sleep(10)
    else:
        raise TimeoutError("the optional native-shape STE check lacks authorized time")
    for _ in range(4):
        try:
            return pair.idle_gpu()
        except RuntimeError:
            time.sleep(3)
    return pair.idle_gpu()


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("one explicitly selected physical GPU is required")
    source_proof = read(CPU_PROOF)
    if not all(value["loss_gradient_clip_and_post_muon_adamw_weights_exact"] for value in source_proof["results"].values()):
        raise ValueError("CPU same-update evidence is required")
    total, background = wait_for_main_study()
    signal.alarm(min(150, int(END - time.time()) - 3))
    if pair.input_pins() != read(pair.OUT / "profile.json")["pins"]:
        raise ValueError("the admitted pilot or original training sources changed")
    import numpy as np
    import torch

    from scripts import diag_p109b_ste_exact_micro as ste
    from scripts import p109_train_visit_policy as route
    from tinylm.config import build_config

    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction((pair.CARD_LIMIT_MIB - background - 512) / total)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.manual_seed(1337)
    cfg = build_config("m100s12_g4", "tied", pair.SEQ, ckpt=False)
    cfg.train_repeat = 2.0
    model = route.RoutedG4(cfg).cuda().train()
    model.set_anneal(ste.reference.ANNEAL)
    model.training_route = route.route_for(cfg, model.owner, "second_shuffle_r2", 1337, 19, pair.STEPS)
    initial = {name: value.detach().to(device="cpu", copy=True) for name, value in model.state_dict().items()}
    data = np.memmap(pair.PILOT / "train.bin", dtype="<u2", mode="r")
    starts = np.random.default_rng(1234).integers(0, len(data) - pair.SEQ - 1, (pair.ACCUM, pair.MICRO))
    tokens = data[starts[:, :, None] + np.arange(pair.SEQ + 1)].astype(np.int64)
    batches = [(torch.from_numpy(row[:, :-1].copy()).cuda(), torch.from_numpy(row[:, 1:].copy()).cuda()) for row in tokens]
    comparison = ste.compare(model, initial, batches, bf16=True, ce_rows=1024)
    OUT.mkdir(exist_ok=False)
    pair.publish(OUT / "report.json", {**comparison, "hardware": torch.cuda.get_device_name(), "trial_order": "ABBA",
        "visits": 28, "targets_per_trial": pair.MICRO * pair.ACCUM * pair.SEQ, "sequence": pair.SEQ,
        "micro_bsz": pair.MICRO, "accumulation": pair.ACCUM, "ce_recompute_rows": 1024,
        "all_token_bytes_sha256": hashlib.sha256(tokens.tobytes()).hexdigest(), "driver_memory_ceiling_mib": pair.CARD_LIMIT_MIB,
        "speed_scope": "forward, backward, quantization; CPU copies and optimizer step excluded from time",
        "saved_checkpoints": 0, "full_training_quality": "NOT_RUN"})
    print("P109B_STE_GPU", comparison, flush=True)


if __name__ == "__main__":
    main()
