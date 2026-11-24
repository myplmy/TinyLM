"""Score the newly trained WIP 182 pair on the pinned English and Korean choice tasks."""

import argparse
from datetime import datetime
from importlib import import_module
import json
import math
import os
from pathlib import Path
import signal
import time
from unittest.mock import patch

from scripts import diag_p109_frozen_g4_routes as frozen
from scripts import run_p109b_scratch_pair_20261120 as pair


OUT = pair.ROOT / "test_result/evidence/p109b_firstpass_chat32_choice_20261120"
END = datetime.fromisoformat("2026-11-20T17:00:00+09:00").timestamp()
TOKENIZER_SHA = "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
CONTROL, CANDIDATE = pair.ARMS


def read(path):
    return json.loads(path.read_bytes())


def prepare():
    # Keep the existing official source, dataset, task, and request checks intact.
    with (patch.object(frozen, "TOKENIZER", pair.TOKENIZER),
          patch.object(frozen, "TOKENIZER_SHA", TOKENIZER_SHA),
          patch.object(import_module("tinylm.data.prepare"), "tokenizer_path", return_value=pair.TOKENIZER)):
        pins, tasks = frozen.prepare_inputs()
    pins.add(Path(__file__).resolve())
    return pins, tasks


def profile(pins, tasks):
    return {"approval": "WIP 182", "files": pins.files, "train_pair": str(pair.OUT),
            "tasks": {name: task["receipt"] for name, task in tasks.items()},
            "common_inference": {"repeat": 2, "visits": 28, "anneal": 1, "precision": "FP32 MATH"}}


def load_model(torch, pins, policy):
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.paths import RUNS

    checkpoint = RUNS / "ckpt" / f"m100s12_g4_ko-en_300M_{pair.ARMS[policy]}.pt"
    checkpoint_pin = pins.add(checkpoint)
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    if (state["step"] != pair.STEPS or state["tokenizer_lineage"] != "chat32"
            or state["tokenizer_sha256"].upper() != TOKENIZER_SHA or "model" not in state):
        raise ValueError("official evaluation requires the exact final chat32 checkpoint")
    cfg = TMTConfig(**state["cfg"])
    if ((cfg.n_prelude, cfg.n_middle, cfg.n_coda, cfg.mlp_group, cfg.cla_group) != (2, 12, 2, 4, 2)
            or not cfg.tie_mlp or cfg.train_repeat != 2.0 or cfg.vocab_size != 32768):
        raise ValueError("checkpoint is outside the declared G4 comparison")
    cfg.infer_repeat = 2.0
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(state["model"], strict=True)
    model = model.cuda().float().eval()
    model.set_anneal(1.0)
    model.freeze_quant()
    if len(model.visit_schedule()) != 28:
        raise ValueError("common R2 must visit 28 layers")
    return model, checkpoint_pin


def score_task(task, scorers, raw, name, rng):
    import numpy as np

    rows = task["rows"]
    metrics = {policy: {} for policy in pair.ARMS}
    predictions = {policy: [] for policy in pair.ARMS}
    offset = 0
    for batch in task["batches"]:
        scores = {policy: scorer(batch) for policy, scorer in scorers.items()}
        count = len(batch["input_ids"])
        if count % 2 or any(len(value) != count for value in scores.values()):
            raise ValueError("every row requires exactly two scores in each arm")
        for index in range(0, count, 2):
            row = rows[offset]
            observed = {}
            for policy, result in scores.items():
                values = result[index:index + 2]
                if any(not math.isfinite(score) or score > 0 or type(greedy) is not bool for score, greedy in values):
                    raise ValueError("choice likelihood is invalid")
                prediction = max(range(2), key=lambda choice: values[choice][0])
                predictions[policy].append(prediction)
                official = task["task"].process_results(row["doc"], values)
                if official["acc"] != int(prediction == row["gold"]):
                    raise ValueError("official choice score differs from independent recount")
                for key, value in official.items():
                    metrics[policy].setdefault(key, []).append(value)
                observed[policy] = {"prediction": prediction, "choice_scores": values}
            print(json.dumps({"task": name, "index": row["index"], "gold": row["gold"], "arms": observed}), file=raw)
            offset += 1
        raw.flush()
    if offset != frozen.TASKS[name]:
        raise ValueError("official row coverage differs")
    aggregate = task["task"].aggregation()
    return {"rows": offset, "changed_choices": int(np.count_nonzero(np.asarray(predictions[CANDIDATE]) != predictions[CONTROL])),
            "by_arm": {policy: {key: float(aggregate[key](values)) for key, values in result.items()}
                       for policy, result in metrics.items()},
            "paired_accuracy": frozen.paired_delta(np.asarray(metrics[CANDIDATE]["acc"]) - metrics[CONTROL]["acc"], rng)}


def gpu():
    if time.time() + 90 >= END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise RuntimeError("insufficient authorized time or unselected GPU")
    signal.alarm(int(END - time.time()) - 3)
    receipt = pair.OUT / "queue.json"
    if not read(receipt)["complete"]:
        raise RuntimeError("official comparison requires two closed and matched arms")
    pair.idle_gpu()
    pins, tasks = prepare()
    if read(OUT / "profile.json") != profile(pins, tasks):
        raise ValueError("official inputs changed since CPU preparation")
    pins.add(receipt)
    import numpy as np
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    models, checkpoint_pins = {}, {}
    for policy in pair.ARMS:
        models[policy], checkpoint_pins[policy] = load_model(torch, pins, policy)
    scorers = {policy: frozen.adapter.TorchLikelihood({"torch": torch, "model": model, "cfg": model.cfg}, model)
               for policy, model in models.items()}
    rng = np.random.default_rng(1337)
    results = {}
    path = OUT / "choice_rows.jsonl"
    with path.open("x", encoding="utf-8") as raw, torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for policy, model in models.items():
            batch = tasks["winogrande"]["batches"][0]
            independent = frozen.adapter.direct_label_oracle(torch, model, batch, 32768)
            observed = scorers[policy](batch)
            if any(a[1] != b[1] or not math.isclose(a[0], b[0], abs_tol=1e-4, rel_tol=1e-5)
                   for a, b in zip(independent, observed)):
                raise ValueError("direct label masking and the likelihood adapter differ")
        for name, task in tasks.items():
            results[name] = score_task(task, scorers, raw, name, rng)
            print("P109B_TASK", name, results[name], flush=True)
    pins.unchanged()
    pair.publish(OUT / "report.json", {"checkpoints": checkpoint_pins, "tasks": results,
                                     "choice_rows_sha256": pair.file_sha(path),
                                     "profile_sha256": pair.file_sha(OUT / "profile.json"),
                                     "queue_sha256": pair.file_sha(receipt), "bootstrap_resamples": 20000})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "after-training"))
    phase = parser.parse_args().phase
    if phase == "prepare":
        pins, tasks = prepare()
        OUT.mkdir(exist_ok=False)
        pair.publish(OUT / "profile.json", profile(pins, tasks))
        print("P109B_EVAL_READY", {name: task["receipt"] for name, task in tasks.items()}, flush=True)
        return
    while time.time() < END - 90:
        queue = pair.OUT / "queue.json"
        if queue.is_file() and queue.read_bytes().endswith(b"\n"):
            gpu()
            return
        time.sleep(10)
    raise TimeoutError("two-armed training did not close with evaluation time remaining")


if __name__ == "__main__":
    main()
