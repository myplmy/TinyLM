"""Learn table lookup without a parent, then check paired value swaps on unseen tables."""

import argparse
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
from random import Random
import re
import signal
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F

from scripts import build_p109c_authored_course as authored
from scripts import run_p109c_correction_scratch as trial
from tinylm.chat.serialize import serialize
from tinylm.model import TiedMLPTransformer
from tinylm.train.mtp_sft import IGNORE, encode_record


TAG = "p109c_table_grounding_scratch_gpu_v1_20261121"
DATA = trial.DATA.parent / (TAG + "_inputs")
OUT = trial.DATA.parent / TAG
STAGES = (("two_digit", 11, 100, 16384), ("three_digit", 100, 1000, 32768), ("wide", 11, 9980, 65536))
BATCH, SEED, PROFILE_SEED = 32, 1337, 621127
WIDTH = trial.WIDTH
ROWS = sum(stage[3] for stage in STAGES)
UPDATES = ROWS // BATCH
GATE = dict(wide_pairs=32, language_pairs=12, original_single=32)


def pins():
    return {**trial.source_pins(),
            str(Path(__file__).relative_to(trial.ROOT)): trial.file_sha(Path(__file__)),
            str(Path(authored.__file__).relative_to(trial.ROOT)): trial.file_sha(Path(authored.__file__))}


def form(values, order, field, language, phrasing):
    lead = "작업표에는 다음과 같이 적혀 있습니다. " if language == "ko" else "The work log has these entries. "
    prompt = lead + authored.values_text(language, values, order) + " " + authored.field_question(language, field, phrasing)
    gold = str(values[field])
    row = authored.row(authored.digest(["table", values]), "table_lookup", language,
                       [("user", prompt), ("assistant", gold)], view="single")
    return row["record"], gold


def source_keys(tokenizer, cases):
    keys = set()
    for split in cases.values():
        for case in split.values():
            prompt = tokenizer.decode(case["prompts"]["single"], skip_special_tokens=False)
            table = tuple(sorted(map(int, re.findall(r": ([0-9]+)", prompt))))
            if len(table) != 4 or len(set(table)) != 4:
                raise ValueError("authored lineage must have four distinct numbers")
            keys.add(table)
    return keys


def draw(rng, index, lo, hi, used):
    language = authored.LANGUAGES[index % 2]
    field = (index // 2) % 4
    position = (index // 8) % 4
    other = rng.choice([k for k in range(4) if k != field])
    sides = rng.sample([k for k in range(4) if k != field], 3)
    sides.insert(position, field)
    while True:
        values = tuple(rng.sample(range(lo, hi), 4))
        key = tuple(sorted(values))
        if key not in used:
            used.add(key)
            return values, sides, field, other, language


def generation_prompt(tokenizer, row):
    text = serialize({"messages": row["messages"][:-1]}, add_generation_prompt=True)
    prompt = tokenizer.encode(text).ids
    if len(prompt) + trial.GENERATION > WIDTH:
        raise ValueError("table decode exceeds fixed width")
    return prompt


def eval_pairs(tokenizer, rng, lo, hi, used):
    pairs = []
    for index in range(64):
        values, order, field, other, language = draw(rng, index, lo, hi, used)
        swap = list(values)
        swap[field], swap[other] = swap[other], swap[field]
        inputs = [form(table, order, field, language, 2) for table in (values, tuple(swap))]
        prompts = [generation_prompt(tokenizer, row) for row, _ in inputs]
        gold = [answer for _, answer in inputs]
        if len(prompts[0]) != len(prompts[1]) or gold[0] == gold[1] or prompts[0] == prompts[1]:
            raise ValueError("swapped evaluation must keep the same prompt width and change the expected value")
        pairs.append(dict(root=authored.digest(["table_values", sorted(values)]), values=values,
                          order=order, field=field, other=other, language=language, prompts=prompts, gold=gold))
    return pairs


def prepare():
    if DATA.exists() or OUT.exists():
        raise FileExistsError(DATA)
    tok, special, cases, _, _ = trial.load_cases()
    rng = Random(PROFILE_SEED)
    used = source_keys(tok, cases)
    existing = len(used)
    evaluation = dict(two_digit=eval_pairs(tok, rng, 11, 100, used), wide=eval_pairs(tok, rng, 11, 9980, used),
                      original=[dict(root=root, prompt=entry["prompts"]["single"], gold=entry["gold"],
                                     language=entry["language"]) for root, entry in sorted(cases["validation"].items())])
    x = np.full((ROWS, WIDTH), special["<pad>"], dtype=np.uint16)
    y = np.full((ROWS, WIDTH), IGNORE, dtype=np.int16)
    receipt = []
    offset = 0
    keys = sha256()
    for name, lo, hi, count in STAGES:
        lengths, max_prompt = 0, 0
        for index in range(count):
            values, order, field, _, language = draw(rng, index, lo, hi, used)
            row, _ = form(values, order, field, language, (index // 32) % 2)
            example = encode_record(row, tok, context=WIDTH)
            first = next(i for i, label in enumerate(example.y) if label != IGNORE)
            last = next(label for label in reversed(example.y) if label != IGNORE)
            if last != special["<|im_end|>"]:
                raise ValueError("expected one final end marker")
            x[offset+index, :len(example.x)] = example.x
            y[offset+index, :len(example.y)] = example.y
            lengths += len(example.x)
            max_prompt = max(max_prompt, first+1)
            keys.update(bytes.fromhex(authored.digest(["table_values", sorted(values)])))
        stage_targets = y[offset:offset+count]
        valid = stage_targets[stage_targets != IGNORE]
        eot = int(np.count_nonzero(valid == special["<|im_end|>"]))
        if eot != count:
            raise ValueError("expected exactly one end label per training row")
        freqs = np.bincount(valid)
        probs = freqs[freqs > 0] / valid.size
        receipt.append(dict(stage=name, rows=count, offset=offset, max_prompt=max_prompt,
                            input_ids=lengths, targets=valid.size, eot=eot,
                            unigram_ce=-float(np.sum(probs*np.log(probs)))))
        offset += count
        print(json.dumps(receipt[-1]), flush=True)
    if len(used) != existing + 128 + ROWS:
        raise ValueError("new and previously authored number groups overlap")
    DATA.mkdir()
    with (DATA / "train.npz").open("xb") as stream:
        np.savez_compressed(stream, x=x, y=y)
    trial.publish(DATA / "evaluation.json", evaluation)
    report = dict(tag=TAG, seed=PROFILE_SEED, source=pins(), sources_excluded=existing,
                  train_values_sha256=keys.hexdigest(), profile=receipt, rows=ROWS, updates=UPDATES,
                  input_slots=ROWS*WIDTH, gate=GATE, input_hash={f: trial.file_sha(DATA / f)
                  for f in ("train.npz", "evaluation.json")})
    trial.publish(DATA / "preflight.json", report)
    print(f"SEALED {trial.file_sha(DATA / 'preflight.json')}", flush=True)


def sealed(digest):
    file = DATA / "preflight.json"
    if trial.file_sha(file) != digest:
        raise ValueError("preflight receipt digest mismatch")
    report = trial.read_json(file)
    if report["source"] != pins() or report["tag"] != TAG or report["gate"] != GATE:
        raise ValueError("preflight source, tag or gate mismatch")
    if any(trial.file_sha(DATA / name) != report["input_hash"][name] for name in ("train.npz", "evaluation.json")):
        raise ValueError("prepared data digest mismatch")
    return report


def decoded(model, tokenizer, special, prompts):
    return [row for start in range(0, len(prompts), BATCH)
            for row in trial.generate(model, tokenizer, special, prompts[start:start+BATCH])]


def evaluate(model, tokenizer, special, data, *, paired):
    if paired:
        predictions = decoded(model, tokenizer, special, [prompt for row in data for prompt in row["prompts"]])
        by_language = {language: 0 for language in authored.LANGUAGES}
        rows, joint, answered = [], 0, 0
        for index, row in enumerate(data):
            pair = predictions[index*2:index*2+2]
            success = all(output["answer"] == gold and output["eot"] for output, gold in zip(pair, row["gold"]))
            joint += success
            answered += sum(bool(output["ids"]) for output in pair)
            by_language[row["language"]] += success
            rows.append({**row, "outputs": pair, "both_correct": success})
        return dict(pairs=len(data), both_correct=joint, by_language=by_language, nonempty_answers=answered, rows=rows)
    predictions = decoded(model, tokenizer, special, [row["prompt"] for row in data])
    correct = sum(output["answer"] == row["gold"] and output["eot"] for output, row in zip(predictions, data))
    return dict(n=len(data), exact_with_eot=correct, nonempty_answers=sum(bool(row["ids"]) for row in predictions),
                rows=[{**row, "output": score} for row, score in zip(data, predictions)])


def worker(digest, memory_fraction):
    report = sealed(digest)
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(memory_fraction)
    if not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA BF16 required")
    tok, special, _, _, _ = trial.load_cases()
    evaluation = trial.read_json(DATA / "evaluation.json")
    with np.load(DATA / "train.npz", allow_pickle=False) as arrays:
        x = torch.from_numpy(arrays["x"]).to("cuda", dtype=torch.long)
        y = torch.from_numpy(arrays["y"]).to("cuda", dtype=torch.long)
    if x.shape != (ROWS, WIDTH) or y.shape != x.shape:
        raise ValueError("prepared training tensor shape mismatch")
    torch.manual_seed(SEED)
    model = TiedMLPTransformer(trial.make_config())
    initial = trial.state_sha(model.state_dict())
    model.to("cuda")
    params = sum(value.numel() for value in model.parameters())
    if len(model.visit_schedule()) != 28:
        raise ValueError("expected G4 uniform R2 train schedule")
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0015, weight_decay=.01, fused=True)
    step, observed_targets = 0, 0
    phases = {}
    started = time.perf_counter()
    print(f"START {TAG} child={os.getpid()} params={params}", flush=True)
    for phase in report["profile"]:
        offset, rows = phase["offset"], phase["rows"]
        rolling, count = torch.zeros((), device=x.device), 0
        for start in range(offset, offset+rows, BATCH):
            tokens, targets = x[start:start+BATCH], y[start:start+BATCH]
            selected = targets.ne(IGNORE)
            labels = targets[selected]
            step += 1
            optimizer.param_groups[0]["lr"] = .0015 * min(1., step/64) * (1 - .7*(step/UPDATES)**2)
            model.set_anneal(min(1., step/(.6*UPDATES)))
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model._head_logits(model(tokens, return_hidden=True)[selected])
                loss = F.cross_entropy(logits.float(), labels, reduction="sum")
            (loss / labels.numel()).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            count += labels.numel()
            rolling += loss.detach()
            if step % 128 == 0:
                print(json.dumps(dict(stage=phase["stage"], step=step, phase_ce=rolling.item()/count,
                                      prompt_rows=step*BATCH, wall=time.perf_counter()-started)), flush=True)
        if count != phase["targets"]:
            raise RuntimeError("real supervision dosage differs from the sealed training data")
        observed_targets += count
        model.eval()
        model.clear_quant()
        key = "two_digit" if phase["stage"] == "two_digit" else "wide"
        phases[phase["stage"]] = result = evaluate(model, tok, special, evaluation[key], paired=True)
        trial.publish(OUT / f"{phase['stage']}_eval.json", result)
        print(json.dumps(dict(stage=phase["stage"], both_correct=result["both_correct"],
                              nonempty_answers=result["nonempty_answers"])), flush=True)
        model.train()
        model.clear_quant()

    if step != UPDATES:
        raise RuntimeError("optimizer update count differs from plan")
    model.eval()
    model.clear_quant()
    original = evaluate(model, tok, special, evaluation["original"], paired=False)
    trial.publish(OUT / "original_eval.json", original)
    wide = phases["wide"]
    gate = (wide["both_correct"] >= GATE["wide_pairs"] and min(wide["by_language"].values()) >= GATE["language_pairs"]
            and original["exact_with_eot"] >= GATE["original_single"])
    state = {name: value.detach().cpu() for name, value in model.state_dict().items()}
    checkpoint = OUT / "foundation.pt"
    with checkpoint.open("xb") as stream:
        torch.save(dict(model=state, config=asdict(model.cfg), parent=None, step=step, tag=TAG), stream)
    trial.publish(OUT / "report.json", dict(tag=TAG, parent=None, seed=SEED, torch=torch.__version__, params=params,
                    initial_sha256=initial, checkpoint_sha256=trial.file_sha(checkpoint), state_sha256=trial.state_sha(state),
                    preflight_sha256=digest, updates=step, targets=observed_targets, gate=gate,
                    wide_joint=wide["both_correct"], wide_by_language=wide["by_language"], original=original["exact_with_eot"],
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20, wall=time.perf_counter()-started))
    print(f"FINISH {TAG} gate={gate} wide={wide['both_correct']}/64 original={original['exact_with_eot']}/64", flush=True)


def supervise(digest, deadline):
    if deadline.tzinfo is None or deadline > trial.CUTOFF or deadline.timestamp() - time.time() < 1200:
        raise ValueError("deadline must give at least 20 minutes in the authorized window")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or OUT.exists():
        raise ValueError("a single explicit CUDA device and a fresh output are required")
    sealed(digest)
    lock = os.open(trial.ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        total, used = trial.idle_gpu()
        OUT.mkdir()
        process = multiprocessing.get_context("spawn").Process(target=worker,
                  args=(digest, (trial.CARD_LIMIT_MIB-used-512)/total))
        start, peak, stop = time.time(), 0, None

        def signal_stop(signum, _):
            raise KeyboardInterrupt(signal.Signals(signum).name)

        previous = signal.signal(signal.SIGTERM, signal_stop)
        try:
            process.start()
            print(f"SUPERVISOR child={process.pid} stop={OUT / 'STOP'}", flush=True)
            with (OUT / "gpu.csv").open("x", encoding="utf-8", buffering=1) as telemetry:
                telemetry.write("unix_seconds,pid,card_used_mib,gpu_util_percent\n")
                while process.is_alive():
                    now = time.time()
                    if now >= deadline.timestamp()-35 or (OUT / "STOP").exists():
                        stop = "DEADLINE_OR_STOP"
                        break
                    _, used, utilization = trial.gpu_status()
                    peak = max(peak, used)
                    telemetry.write(f"{now:.3f},{process.pid},{used},{utilization}\n")
                    if used > trial.CARD_LIMIT_MIB:
                        stop = "CARD_MEMORY_LIMIT"
                        break
                    process.join(timeout=2)
        except BaseException as error:
            stop = repr(error)
            raise
        finally:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=8)
                    if process.is_alive():
                        process.kill()
                process.join()
            signal.signal(signal.SIGTERM, previous)
            trial.publish(OUT / "supervisor.json", dict(pid=process.pid, started=start, ended=time.time(),
                          peak_card_mib=peak, stop_reason=stop, returncode=process.exitcode,
                          card_after_exit=trial.observe_card_return()))
    finally:
        os.close(lock)
    return 0 if process.exitcode == 0 and stop is None else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--preflight-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
        return 0
    if args.preflight_sha256 is None or args.stop_by is None:
        parser.error("run requires --preflight-sha256 and --stop-by")
    return supervise(args.preflight_sha256.lower(), args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
