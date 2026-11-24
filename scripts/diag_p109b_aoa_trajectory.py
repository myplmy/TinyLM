"""Use the fixed BabyLM AoA functions on each owned P109B trajectory snapshot."""

import argparse
from datetime import datetime
from importlib import import_module
import json
import math
import os
from pathlib import Path
import signal
from statistics import median
import sys
import time

from scripts import run_p109b_scratch_pair_20261120 as pair


OUT = pair.ROOT / "test_result/evidence/p109b_firstpass_chat32_aoa_20261120"
SOURCE = pair.ROOT / "data_cache/p106b_aoa_official_source_6f825c_20261120"
ASSETS = pair.ROOT / "data_cache/p106b_official_eval_assets/babylm_2026_strict_8d52da9/evaluation_data/full_eval/aoa"
ASSET_SHA = {"cdi_childes.json": "bfb28dbe974970e559c257cda7bfeb6ebefe55478e2de0ce84535d63e9d8b929",
             "cdi_human.csv": "fd6e47955fa3efb3889ff97736253fd267a28682283f438247d292c51ce42037"}
MANIFEST_SHA = "97f3765cc11dde4e45af1f1e7934ffd7458eb518fbbd1a6e6fab256367a625c9"
TOKENIZER_SHA = "9716f40e4c504d6af37dde76cca578e30b45e9ca86c8b6bb79b2fa095d3ac88e"
END = datetime.fromisoformat("2026-11-20T17:00:00+09:00").timestamp()
STEPS = (572, 1144, 1716, 2289)
BATCH_SIZE = 16


def read(path):
    return json.loads(path.read_bytes())


def official_modules():
    manifest = SOURCE / "manifest.json"
    if pair.file_sha(manifest) != MANIFEST_SHA:
        raise ValueError("AoA official source manifest changed")
    for name, record in read(manifest)["files"].items():
        if pair.file_sha(SOURCE / "source" / name) != record["sha256"]:
            raise ValueError("AoA official source changed: " + name)
    for name, expected in ASSET_SHA.items():
        if pair.file_sha(ASSETS / name) != expected:
            raise ValueError("AoA official input changed: " + name)
    sys.path.insert(0, str(SOURCE / "source/strict"))
    utility, functions, metric = (
        import_module("evaluation_pipeline." + name)
        for name in ("AoA_word.eval_util", "AoA_word.evaluation_functions", "utils")
    )
    if any(not Path(module.__file__).is_relative_to(SOURCE) for module in (utility, functions, metric)):
        raise ValueError("AoA imports must resolve to the checked source tree")
    return utility, functions, metric


class TokenizerView:
    bos_token = "<bos>"

    def __init__(self):
        from tokenizers import Tokenizer

        if pair.file_sha(pair.TOKENIZER) != TOKENIZER_SHA:
            raise ValueError("AoA requires the same chat32 vocabulary")
        self.tokenizer = Tokenizer.from_file(str(pair.TOKENIZER))
        self.vocab_size = self.tokenizer.get_vocab_size()

    def __call__(self, text, *, add_special_tokens, return_offsets_mapping=False):
        value = self.tokenizer.encode(text, add_special_tokens=add_special_tokens)
        return {"input_ids": value.ids, "attention_mask": value.attention_mask, "offset_mapping": value.offsets}


def prepare():
    utility, functions, metric = official_modules()
    tokenizer = TokenizerView()
    extractor = object.__new__(functions.StepSurprisalExtractor)
    extractor.device = "cpu"
    words, contexts = utility.load_eval(ASSETS / "cdi_childes.json", min_context=0)
    rows = []
    for word, group in zip(words, contexts, strict=True):
        for index, context in enumerate(group):
            inputs, targets, attention, mask = extractor.process_causal_input(tokenizer, tokenizer, context, word, False)
            if (inputs.shape != targets.shape or inputs.shape != mask.shape or not bool(attention.all())
                    or not bool(mask.any()) or inputs.shape[1] > 1024):
                raise ValueError("original AoA prefix and tracked targets must fit the native context")
            rows.append({"target_word": word, "context_id": index, "context": context, "input_ids": inputs[0].tolist(),
                         "target_ids": targets[0].tolist(), "phrase_mask": mask[0].tolist()})
    return extractor, tokenizer, metric.AoAEvaluator(ASSETS / "cdi_human.csv"), rows


def load_model(path, step):
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    state = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if state["step"] != step or state["tokenizer_sha256"].lower() != TOKENIZER_SHA:
        raise ValueError("checkpoint step or tokenizer lineage differs")
    cfg = TMTConfig(**state["cfg"])
    if (cfg.n_layers, cfg.mlp_group, cfg.cla_group, cfg.train_repeat) != (16, 4, 2, 2.0):
        raise ValueError("AoA requires the actual G4 training geometry")
    cfg.infer_repeat = 2.0
    model = TiedMLPTransformer(cfg).eval()
    model.load_state_dict(state["model"], strict=True)
    model.set_anneal(1.0)
    model.freeze_quant()
    return model


def batch_surprisal(model, rows):
    import torch

    width = max(len(row["input_ids"]) for row in rows)
    pad = lambda values: torch.tensor([values(row) + [0] * (width - len(row["input_ids"])) for row in rows])
    inputs = pad(lambda row: row["input_ids"])
    targets = pad(lambda row: row["target_ids"])
    mask = pad(lambda row: row["phrase_mask"]).bool()
    logits = model(inputs, use_cache=False)[mask]
    log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
    relevant = log_probs.gather(-1, targets[mask].unsqueeze(-1)).neg().squeeze(-1)
    return [float(value.sum()) for value in relevant.split(mask.sum(dim=1).tolist())]


def compare_oracle(extractor, tokenizer, model, rows):
    def native_forward(input_ids, attention_mask):
        if not bool(attention_mask.all()):
            raise ValueError("an unpadded official single input is expected")
        return {"logits": model(input_ids, use_cache=False)}

    expected = [extractor.compute_surprisal_causal(native_forward, tokenizer, tokenizer,
                row["context"], row["target_word"], False) for row in rows]
    observed = batch_surprisal(model, rows)
    error = max(abs(x - y) for x, y in zip(expected, observed, strict=True))
    if not all(math.isfinite(x) for x in (*expected, *observed)) or error > 0.001:
        raise ValueError(f"official unbatched and batched AoA differ by {error:.6g}")
    return error


def profile(rows, batch_seconds):
    widths = sorted(len(row["input_ids"]) for row in rows)
    return {"words": len({row["target_word"] for row in rows}), "contexts": len(rows),
            "token_width_min_median_max": [min(widths), median(widths), max(widths)],
            "preflight_batch_seconds": batch_seconds, "profiles": list(pair.ARMS),
            "expected_steps": list(STEPS), "official_source_sha256": MANIFEST_SHA, "source_assets": ASSET_SHA,
            "tokenizer_sha256": TOKENIZER_SHA, "source_sha256": pair.file_sha(Path(__file__)),
            "x_axis": "native optimizer updates, one fixed subword budget per update; pilot AoA"}


def score(policy, step, report, model, rows, oracle_error):
    import torch

    begin = time.monotonic()
    values = [None] * len(rows)
    ordered = sorted(range(len(rows)), key=lambda index: len(rows[index]["input_ids"]))
    with torch.inference_mode():
        for begin_index in range(0, len(ordered), BATCH_SIZE):
            batch = ordered[begin_index:begin_index+BATCH_SIZE]
            scores = batch_surprisal(model, [rows[index] for index in batch])
            for index, value in zip(batch, scores, strict=True):
                if not math.isfinite(value) or value < 0:
                    raise ValueError("AoA surprisal must be finite and nonnegative")
                values[index] = {key: rows[index][key] for key in ("target_word", "context_id")}
                values[index].update(step=str(step), surprisal=value)
    return dict(policy=policy, step=step, checkpoint_sha256=report, results=values,
                oracle_max_abs_error=oracle_error, seconds=time.monotonic() - begin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "score", "fit"))
    parser.add_argument("policy", choices=tuple(pair.ARMS), nargs="?")
    parser.add_argument("step", type=int, choices=STEPS, nargs="?")
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or time.time() + 60 >= END:
        raise ValueError("AoA runs on CPU within the authorized window")
    signal.alarm(int(END - time.time()) - 2)
    import torch

    torch.set_num_threads(2)
    extractor, tokenizer, official, rows = prepare()
    if args.phase == "fit":
        results = {}
        for policy in pair.ARMS:
            all_rows = []
            for step in STEPS:
                snapshot = read(OUT / f"{policy}_{step}.json")
                if (snapshot["policy"], snapshot["step"], len(snapshot["results"])) != (policy, step, len(rows)):
                    raise ValueError("minimum four complete same-lineage checkpoints per arm")
                all_rows.extend(snapshot["results"])
            results[policy] = official.compute_curve_fitness({"results": all_rows}, tokenizer)
        pair.publish(OUT / "report.json", results)
        print(results, flush=True)
        return
    if args.phase == "prepare":
        path = next((pair.PROBE.parent / "native").glob("*_20261120.pt"))
        model = load_model(path, 4)
        ordered = sorted(rows, key=lambda row: len(row["input_ids"]))
        batch = ordered[len(ordered)//2:len(ordered)//2+BATCH_SIZE]
        with torch.inference_mode():
            error = compare_oracle(extractor, tokenizer, model, ordered[::len(ordered)//8][:8])
            start = time.monotonic()
            batch_surprisal(model, batch)
            seconds = time.monotonic() - start
        OUT.mkdir(exist_ok=False)
        pair.publish(OUT / "profile.json", {**profile(rows, seconds), "oracle_max_abs_error": error})
        print("AOA_CPU_PROFILE", len(rows), seconds, error, flush=True)
        return
    if args.policy is None or args.step is None:
        parser.error("score requires policy and recorded training step")
    pin = read(OUT / "profile.json")
    if any(pin[key] != value for key, value in profile(rows, pin["preflight_batch_seconds"]).items()):
        raise ValueError("AoA inputs or source changed since CPU validation")
    if args.step == pair.STEPS:
        train = read(pair.OUT / "queue.json")
        if not train["complete"]:
            raise ValueError("a complete matched final pair is required")
        path = pair.ROOT / "runs" / "ckpt" / f"m100s12_g4_ko-en_300M_{pair.ARMS[args.policy]}.pt"
    else:
        path = pair.OUT / args.policy / f"aoa_step_{args.step}.pt"
    checkpoint_sha = pair.file_sha(path)
    model = load_model(path, args.step)
    with torch.inference_mode():
        error = compare_oracle(extractor, tokenizer, model, rows[:8])
    result = score(args.policy, args.step, checkpoint_sha, model, rows, error)
    if pair.file_sha(path) != checkpoint_sha:
        raise ValueError("AoA snapshot changed during scoring")
    pair.publish(OUT / f"{args.policy}_{args.step}.json", result)
    print("AOA_CPU_SNAPSHOT", args.policy, args.step, len(rows), result["seconds"], flush=True)


if __name__ == "__main__":
    main()
