"""Train the existing authored correction cohort from scratch in three matched arms."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime
import fcntl
import json
import math
import multiprocessing
import os
from pathlib import Path
import signal
import sys
import time

import torch
import torch.nn.functional as F
from tokenizers import Tokenizer

from scripts import p108b_correction_course as course
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.run_p109b_scratch_pair_20261120 import ROOT, file_sha, gpu_status, idle_gpu, publish
from scripts.run_p109c_scratch330 import CARD_LIMIT_MIB, observe_card_return
from tinylm.chat.serialize import serialize
from tinylm.config import PRESETS
from tinylm.data.prepare import verify_chat_tokenizer
from tinylm.model import TiedMLPTransformer
from tinylm.train.mtp_sft import IGNORE, encode_record, pad_records


TAG = "p109c_authored_correction_scratch_gpu_v1_20261121"
DATA = ROOT / "test_result/evidence/p109c_authored_curriculum_schedule_cpu_v1_20261121"
OUT = DATA.parent / TAG
CUTOFF = datetime.fromisoformat("2026-11-21T13:00:00+09:00")
STOP_AT = datetime.fromisoformat("2026-11-21T03:58:00+09:00")
COURSE_SHA = "a087205430ebb9c78c40c9a60ecb9025d62edeb41bf6196e420f9ff7281df291"
ORDER_SHA = "c3e7c7161503b962c45548a9c7ff0277744398e6a8d879bc01dc64519878c8be"
SEED, BATCH, WIDTH, CYCLES, GENERATION = 1337, 16, 128, 4, 8
EPOCHS = CYCLES * 4
VIEWS = ("single", "correction")


def read_json(path):
    return json.loads(path.read_bytes())


def on_disk(reference):
    name = reference["file"]
    path = DATA / name
    if path.name != name or path.is_symlink() or file_sha(path).upper() != reference["sha256"]:
        raise ValueError(f"invalid course file or digest: {name}")
    return path


def source_pins():
    files = (Path(__file__).relative_to(ROOT), "scripts/p108b_correction_course.py",
             "scripts/run_p109b_scratch_pair_20261120.py", "scripts/run_p109c_scratch330.py",
             "scripts/diag_p102a_g4_full_delta_train.py", "tinylm/config.py",
             "tinylm/model/transformer.py", "tinylm/model/ternary.py", "tinylm/train/mtp_sft.py",
             "tinylm/chat/serialize.py", "tinylm/data/sft.py")
    return {str(name): file_sha(ROOT / name) for name in files}


def load_cases():
    report_path, schedule_path = DATA / "report.json", DATA / "correction_orders.json"
    if file_sha(report_path) != COURSE_SHA or file_sha(schedule_path) != ORDER_SHA:
        raise ValueError("the verified authored cohort or its order changed")
    report, schedule = read_json(report_path), read_json(schedule_path)
    tokenizer = Tokenizer.from_file(str(on_disk(report["tokenizer"])))
    special = verify_chat_tokenizer(tokenizer)
    cases = {}
    for split, count in (("train", 458), ("validation", 64), ("test", 64)):
        pairs = on_disk(report["files"][split]["correction_pairs"])
        seen = {}
        for line in pairs.read_text(encoding="utf-8").splitlines():
            pair = json.loads(line)
            root = pair["root"]
            if root in seen:
                raise ValueError(f"repeated root: {root}")
            records, prompts, targets = {}, {}, {}
            for view in VIEWS:
                row = pair[view]["record"]
                records[view] = item = encode_record(row, tokenizer, context=WIDTH)
                messages = row["messages"][:-1]
                prompt = serialize({"messages": messages}, add_generation_prompt=True)
                prompts[view] = tokenizer.encode(prompt).ids
                targets[view] = [token for token in item.y if token != IGNORE]
                first = next(index for index, token in enumerate(item.y) if token != IGNORE)
                if prompts[view] != item.x[:first+1] or first + 1 + GENERATION > WIDTH:
                    raise ValueError(f"generation prefix mismatch or too long: {root}/{view}")
            single, correction = (pair[view]["record"]["messages"] for view in VIEWS)
            gold = single[-1]["content"][0]["text"]
            foil = correction[1]["content"][0]["text"]
            if (single[0] != correction[0] or single[-1] != correction[-1] or gold == foil
                    or targets["single"] != targets["correction"]
                    or targets["single"][-1] != special["<|im_end|>"]):
                raise ValueError(f"paired records or target IDs differ: {root}")
            seen[root] = dict(records=records, prompts=prompts, gold=gold, foil=foil,
                              language=pair["single"]["record"]["meta"]["language"])
        if len(seen) != count or any(set(seen) & set(other) for other in cases.values()):
            raise ValueError(f"invalid split count or overlap: {split}")
        cases[split] = seen

    train = cases["train"]
    orders = schedule["orders"]
    reference = [[entry["case_id"] for entry in epoch] for epoch in orders["SINGLE_ONLY"]]
    profile = {}
    for arm in course.ARMS:
        epochs = orders[arm]
        roots = [[entry["case_id"] for entry in epoch] for epoch in epochs]
        if roots != reference or len(epochs) != 4 or any(len(row) != len(train) or set(row) != set(train) for row in roots):
            raise ValueError(f"unmatched case order: {arm}")
        ordered = [train[entry["case_id"]]["records"][entry["view"]] for epoch in epochs for entry in epoch]
        count = sum(row.targets for row in ordered)
        length = sum(len(row.x) for row in ordered)
        expected = schedule["summary"][arm]
        if (count, length) != (5960, expected["input_tokens"]):
            raise ValueError(f"unmatched target or input accounting: {arm}")
        profile[arm] = dict(targets=count*CYCLES, actual_input_tokens=length*CYCLES,
                            updates=math.ceil(len(train)/BATCH)*EPOCHS,
                            padded_input_slots=BATCH*WIDTH*math.ceil(len(train)/BATCH)*EPOCHS)
    return tokenizer, special, cases, orders, profile


def make_config():
    return replace(PRESETS["m100s12_g4"](WIDTH, False), dim=256, ffn_dim=768, emb_rank=128,
                   n_q_heads=4, n_kv_heads=2, train_repeat=2.0, quant_anneal=0.0)


@torch.inference_mode()
def generate(model, tokenizer, special, prompts):
    active = list(range(len(prompts)))
    tokens = [list(prompt) for prompt in prompts]
    outputs = [[] for _ in prompts]
    stopped = [False] * len(prompts)
    for _ in range(GENERATION):
        length = [len(tokens[index]) for index in active]
        width = max(length)
        x = torch.tensor([tokens[index] + [special["<pad>"]]*(width-size)
                          for index, size in zip(active, length)], device="cuda")
        positions = torch.tensor([size-1 for size in length], device=x.device)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            hidden = model(x, return_hidden=True)
            predicted = model._head_logits(hidden[torch.arange(len(active), device=x.device), positions]).argmax(-1)
        for index, token in zip(active, predicted.tolist()):
            stopped[index] = token == special["<|im_end|>"]
            if not stopped[index]:
                outputs[index].append(token)
                tokens[index].append(token)
        active = [index for index in active if not stopped[index]]
        if not active:
            break
    return [dict(answer=tokenizer.decode(out, skip_special_tokens=False).strip(), ids=out, eot=end)
            for out, end in zip(outputs, stopped)]


def evaluate(model, tokenizer, special, data):
    roots = sorted(data)
    results = {root: {key: data[root][key] for key in ("gold", "foil", "language")} for root in roots}
    for view in VIEWS:
        for start in range(0, len(roots), BATCH):
            batch = roots[start:start+BATCH]
            answers = generate(model, tokenizer, special, [data[root]["prompts"][view] for root in batch])
            for root, output in zip(batch, answers):
                results[root][view] = output
    totals = {view: dict(exact=sum(row[view]["answer"] == row["gold"] for row in results.values()),
                         exact_with_eot=sum(row[view]["answer"] == row["gold"] and row[view]["eot"]
                                            for row in results.values()),
                         foil=sum(row[view]["answer"] == row["foil"] for row in results.values()),
                         eot=sum(row[view]["eot"] for row in results.values())) for view in VIEWS}
    transitions = {f"{left}->{right}": 0 for left in (0, 1) for right in (0, 1)}
    for row in results.values():
        left, right = (int(row[view]["answer"] == row["foil"]) for view in VIEWS)
        transitions[f"{left}->{right}"] += 1
    return dict(n=len(roots), totals=totals, foil_transitions=transitions, rows=results)


def train_arm(arm, tokenizer, special, cases, order, profile, initial):
    model = TiedMLPTransformer(make_config())
    model.load_state_dict(initial)
    model.to("cuda")
    if list(model.visit_schedule()) != [0, 1, *range(2, 14), *range(2, 14), 14, 15]:
        raise ValueError("training path is not the fixed 16-layer R2 schedule")
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0015, weight_decay=0.01, fused=True)
    train = cases["train"]
    step, total_targets, actual_inputs = 0, 0, 0
    stats = []
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    for number, epoch in enumerate(order*CYCLES, 1):
        rolling = torch.zeros((), device="cuda")
        epoch_targets = 0
        rows = [train[row["case_id"]]["records"][row["view"]] for row in epoch]
        for start in range(0, len(rows), BATCH):
            batch = rows[start:start+BATCH]
            x, y, _ = pad_records(batch, special["<pad>"], "cuda", fixed_width=WIDTH, batch_size=BATCH)
            step += 1
            optimizer.param_groups[0]["lr"] = 0.0015 * min(1, step/29) * (1 - 0.7*(step/profile["updates"])**2)
            model.set_anneal(min(1., step/(0.6*profile["updates"])))
            optimizer.zero_grad(set_to_none=True)
            selected = y.ne(IGNORE)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                hidden = model(x, return_hidden=True)
                logits = model._head_logits(hidden[selected])
                loss = F.cross_entropy(logits.float(), y[selected], reduction="sum")
            count = sum(row.targets for row in batch)
            (loss / count).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            epoch_targets += count
            actual_inputs += sum(len(row.x) for row in batch)
            rolling += loss.detach()
        total_targets += epoch_targets
        receipt = dict(epoch=number, updates=step, targets=total_targets, ce=rolling.item()/epoch_targets,
                       wall_seconds=time.perf_counter()-started)
        stats.append(receipt)
        print(json.dumps(dict(arm=arm, **receipt)), flush=True)
    if (step, total_targets, actual_inputs) != (profile["updates"], profile["targets"], profile["actual_input_tokens"]):
        raise RuntimeError("actual training exposure differs from the preflight")
    trained = state_sha(model.state_dict())
    model.eval()
    model.clear_quant()
    sample = {root: train[root] for root in sorted(train)[:32]}
    validation = evaluate(model, tokenizer, special, cases["validation"])
    final = evaluate(model, tokenizer, special, cases["test"])
    return dict(arm=arm, profile=profile, trained_sha256=trained, epochs=stats, validation=validation,
                test=final, train_probe=evaluate(model, tokenizer, special, sample),
                peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20, wall_seconds=time.perf_counter()-started)


def run_worker(pins, memory_fraction):
    if source_pins() != pins:
        raise RuntimeError("experiment sources changed before worker import")
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(memory_fraction)
    if not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA BF16 is required")
    tokenizer, special, cases, orders, profile = load_cases()
    torch.manual_seed(SEED)
    initial_model = TiedMLPTransformer(make_config())
    initial = initial_model.state_dict()
    initial_sha = state_sha(initial)
    parameters = sum(value.numel() for value in initial_model.parameters())
    del initial_model
    print(f"START {TAG} pid={os.getpid()} parameters={parameters} seed={SEED}", flush=True)
    for arm in course.ARMS:
        report = train_arm(arm, tokenizer, special, cases, orders[arm], profile[arm], initial)
        publish(OUT / f"{arm.lower()}.json", report)
        print(json.dumps(dict(arm=arm, test=report["test"]["totals"], wall=report["wall_seconds"])), flush=True)
        torch.cuda.empty_cache()
    if source_pins() != pins:
        raise RuntimeError("experiment sources changed during execution")
    publish(OUT / "report.json", dict(tag=TAG, parent=None, torch=torch.__version__, seed=SEED,
                     initial_sha256=initial_sha, parameters=parameters, config=asdict(make_config()),
                     profile=profile, sources=pins, cohort_sha256=COURSE_SHA, order_sha256=ORDER_SHA,
                     reports=[f"{arm.lower()}.json" for arm in course.ARMS]))


def supervise(pins):
    start = time.time()
    cutoff = min(CUTOFF, STOP_AT).timestamp() - 35
    if cutoff - start < 900 or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("requires one explicit CUDA device and 15 minutes remaining in its execution window")
    lock = os.open(ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        total, used = idle_gpu()
        OUT.mkdir(exist_ok=False)
        child = multiprocessing.get_context("spawn").Process(target=run_worker,
                    args=(pins, (CARD_LIMIT_MIB-used-512)/total))
        peak, stop = 0, None

        def interrupted(signum, _):
            raise KeyboardInterrupt(signal.Signals(signum).name)

        previous = signal.signal(signal.SIGTERM, interrupted)
        try:
            child.start()
            print(f"SUPERVISOR child={child.pid} stop={OUT / 'STOP'}", flush=True)
            with (OUT / "gpu.csv").open("x", encoding="utf-8", buffering=1) as telemetry:
                telemetry.write("unix_seconds,pid,card_used_mib,gpu_util_percent\n")
                while child.is_alive():
                    now = time.time()
                    if now >= cutoff or (OUT / "STOP").exists():
                        stop = "DEADLINE_OR_STOP"
                        break
                    _, used, utilization = gpu_status()
                    telemetry.write(f"{now:.3f},{child.pid},{used},{utilization}\n")
                    peak = max(used, peak)
                    if used > CARD_LIMIT_MIB:
                        stop = "CARD_MEMORY_LIMIT"
                        break
                    child.join(timeout=2)
        except BaseException as error:
            stop = repr(error)
            raise
        finally:
            signal.signal(signal.SIGTERM, previous)
            if child.pid is not None:
                if child.is_alive():
                    child.terminate()
                    child.join(timeout=8)
                    if child.is_alive():
                        child.kill()
                child.join()
            ended = time.time()
            publish(OUT / "supervisor.json", dict(pid=child.pid, started=start, ended=ended, returncode=child.exitcode,
                    peak_card_mib=peak, stop_reason=stop, card_after_exit=observe_card_return()))
    finally:
        os.close(lock)
    return 0 if child.exitcode == 0 and stop is None else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--preflight", type=Path)
    args = parser.parse_args()
    pins = source_pins()
    if args.mode == "check":
        _, _, cases, _, profile = load_cases()
        print(json.dumps(dict(profile=profile, splits={key: len(rows) for key, rows in cases.items()},
                              sources=pins, launch_cutoff=STOP_AT.isoformat()), indent=2))
        return 0
    if OUT.exists():
        raise FileExistsError(OUT)
    if args.preflight is None or read_json(args.preflight)["sources"] != pins:
        raise ValueError("run requires the matching CPU preflight receipt")
    return supervise(pins)


if __name__ == "__main__":
    sys.exit(main())
