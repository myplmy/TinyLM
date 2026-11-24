"""Add prefix-only next-token learning to the frozen P109C table cohort."""

import argparse
from dataclasses import asdict
from datetime import datetime
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import signal
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F

from scripts import run_p109c_correction_scratch as trial
from scripts import run_p109c_table_grounding as original
from tinylm.model import TiedMLPTransformer
from tinylm.train.mtp_sft import IGNORE
from tinylm.train.recomputed_ce import target_nll


TAG = "p109c_table_context_ntp_scratch_gpu_v1_20261121"
OUT = trial.DATA.parent / TAG
WEIGHT, CE_ROWS = 0.5, 512
BASE_RECEIPT = "ad0302ebc24c510fb74e8d85ebbccdee10e79e67d9d32c3b7f8c4d29dc424edc"


def sources():
    from tinylm.train import recomputed_ce

    paths = (Path(__file__), Path(recomputed_ce.__file__))
    return {**original.pins(), **{str(path.relative_to(trial.ROOT)): trial.file_sha(path) for path in paths}}


def prefix_labels(x, answer, pad):
    is_answer = answer != IGNORE
    starts = np.argmax(is_answer, axis=1)
    before = np.arange(x.shape[1]-1) < starts[:, None]
    shifted = x[:, 1:]
    if np.any(shifted[before] == pad) or np.any(is_answer[:, :-1] & before):
        raise ValueError("context positions reached padding or the supervised response")
    labels = np.full_like(answer, IGNORE)
    labels[:, :-1][before] = shifted[before]
    return labels


def profile():
    cohort = original.sealed(BASE_RECEIPT)
    base = trial.read_json(original.OUT / "report.json")
    if base["tag"] != original.TAG or base["parent"] is not None or base["preflight_sha256"] != BASE_RECEIPT:
        raise ValueError("the previously run answer-only control is required")
    tok, tokens, _, _, _ = trial.load_cases()
    pad = tokens["<pad>"]
    x_test = np.array([[10, 11, 12, 13, pad], [pad]*5])
    y_test = np.array([[IGNORE, 12, 13, IGNORE, IGNORE], [IGNORE]*5])
    if not np.array_equal(prefix_labels(x_test, y_test, pad), np.array([[11, *([IGNORE]*4)], [IGNORE]*5])):
        raise AssertionError("prefix/answer/end/padding boundary regression")
    with np.load(original.DATA / "train.npz", allow_pickle=False) as batch:
        x, y = batch["x"], batch["y"]
    if x.shape != (original.ROWS, original.WIDTH) or y.shape != x.shape:
        raise ValueError("frozen cohort shape changed")
    context = prefix_labels(x, y, pad)
    stages = []
    for phase in cohort["profile"]:
        idx = slice(phase["offset"], phase["offset"]+phase["rows"])
        response = (y[idx] != IGNORE)
        if np.count_nonzero(response) != phase["targets"] or not np.all(response.any(axis=1)):
            raise ValueError("the preflight answer counts differ from the control")
        stages.append({**phase, "context_targets": int(np.count_nonzero(context[idx] != IGNORE))})
    return tok, tokens, (x, y, context), stages, base


def prepare():
    _, _, _, stages, base = profile()
    return dict(tag=TAG, stages=stages, sources=sources(), control_sha256=trial.file_sha(original.OUT/"report.json"),
                initial_sha256=base["initial_sha256"], cohort_sha256=BASE_RECEIPT,
                ce_block=CE_ROWS, context_weight=WEIGHT)


def read_receipt(path):
    receipt = trial.read_json(path)
    if (receipt["tag"] != TAG or receipt["sources"] != sources() or receipt["ce_block"] != CE_ROWS
            or receipt["context_weight"] != WEIGHT or receipt["cohort_sha256"] != BASE_RECEIPT
            or receipt["control_sha256"] != trial.file_sha(original.OUT/"report.json")):
        raise ValueError("the additional context experiment receipt changed")
    return receipt


def worker(receipt_path, fraction):
    receipt = read_receipt(receipt_path)
    tok, special, arrays, stages, _ = profile()
    if stages != receipt["stages"]:
        raise ValueError("context positions differ from the frozen CPU preflight")
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    if not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA BF16 required")
    x, y, context = [torch.from_numpy(data).to("cuda", dtype=torch.long) for data in arrays]
    torch.manual_seed(original.SEED)
    model = TiedMLPTransformer(trial.make_config())
    initial = trial.state_sha(model.state_dict())
    if initial != receipt["initial_sha256"] or len(model.visit_schedule()) != 28:
        raise ValueError("initial state or R2 schedule differs from the answer-only arm")
    model.to("cuda")
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0015, weight_decay=.01, fused=True)
    evaluation = trial.read_json(original.DATA/"evaluation.json")
    step = 0
    stage_reports = []
    started = time.perf_counter()
    print(f"START {TAG} child={os.getpid()}", flush=True)
    for phase in stages:
        offset, rows = phase["offset"], phase["rows"]
        sums = torch.zeros(2, device="cuda")
        answer_count, context_count = 0, 0
        for start in range(offset, offset+rows, original.BATCH):
            block = slice(start, start+original.BATCH)
            tokens, targets, prefix = x[block], y[block], context[block]
            keep, keep_ctx = targets.ne(IGNORE), prefix.ne(IGNORE)
            answer, context_ids = targets[keep], prefix[keep_ctx]
            step += 1
            optimizer.param_groups[0]["lr"] = .0015 * min(1., step/64) * (1 - .7*(step/original.UPDATES)**2)
            model.set_anneal(min(1., step/(.6*original.UPDATES)))
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                hidden = model(tokens, return_hidden=True)
                logits = model._head_logits(hidden[keep])
                a_sum = F.cross_entropy(logits.float(), answer, reduction="sum")
                c_nll, _ = target_nll(model, hidden[keep_ctx].unsqueeze(0), context_ids.unsqueeze(0), rows=CE_ROWS)
                c_sum = c_nll.sum()
                loss = a_sum/answer.numel() + WEIGHT*c_sum/context_ids.numel()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            answer_count += answer.numel()
            context_count += context_ids.numel()
            sums += torch.stack([a_sum.detach(), c_sum.detach()])
            if step % 128 == 0:
                r_sum, c_sum_host = sums.tolist()
                print(json.dumps(dict(stage=phase["stage"], step=step, answer_ce=r_sum/answer_count,
                       prefix_ce=c_sum_host/context_count, wall=time.perf_counter()-started)), flush=True)
        if answer_count != phase["targets"] or context_count != phase["context_targets"]:
            raise RuntimeError("actual context and answer exposure changed")
        model.eval()
        model.clear_quant()
        key = "two_digit" if phase["stage"] == "two_digit" else "wide"
        score = original.evaluate(model, tok, special, evaluation[key], paired=True)
        trial.publish(OUT / f"{phase['stage']}_eval.json", score)
        a_value, c_value = sums.tolist()
        stage_reports.append(dict(stage=phase["stage"], updates=step, answer_ce=a_value/answer_count,
                   prefix_ce=c_value/context_count, answer_tokens=answer_count, context_tokens=context_count,
                   joint=score["both_correct"], nonempty=score["nonempty_answers"], by_language=score["by_language"]))
        print(json.dumps(stage_reports[-1]), flush=True)
        model.train()
        model.clear_quant()
    if step != original.UPDATES:
        raise RuntimeError("optimizer update count changed")
    model.eval()
    val = original.evaluate(model, tok, special, evaluation["original"], paired=False)
    trial.publish(OUT / "original_eval.json", val)
    last = stage_reports[-1]
    gate = (last["joint"] >= original.GATE["wide_pairs"] and min(last["by_language"].values()) >= original.GATE["language_pairs"]
            and val["exact_with_eot"] >= original.GATE["original_single"])
    state = {name: value.detach().cpu() for name, value in model.state_dict().items()}
    checkpoint = OUT / "foundation.pt"
    with checkpoint.open("xb") as stream:
        torch.save(dict(model=state, config=asdict(model.cfg), parent=None, step=step, tag=TAG), stream)
    if receipt != read_receipt(receipt_path):
        raise RuntimeError("preflight changed during the run")
    trial.publish(OUT / "report.json", dict(tag=TAG, parent=None, initial_sha256=initial, torch=torch.__version__,
                  checkpoint_sha256=trial.file_sha(checkpoint), state_sha256=trial.state_sha(state),
                  preflight_sha256=trial.file_sha(receipt_path), stages=stage_reports, gate=gate, original=val["exact_with_eot"],
                  original_nonempty=val["nonempty_answers"], updates=step, wall=time.perf_counter()-started,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                  peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20))
    print(f"FINISH {TAG} gate={gate} wide={last['joint']}/64 original={val['exact_with_eot']}/64", flush=True)


def supervise(receipt, deadline):
    if deadline.tzinfo is None or deadline > trial.CUTOFF or deadline.timestamp()-time.time() < 1200:
        raise ValueError("requires 20 minutes remaining within the authorized window")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or OUT.exists():
        raise ValueError("requires a fresh output and a single explicit CUDA device")
    read_receipt(receipt)
    lock = os.open(trial.ROOT/"runs", os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        total, used = trial.idle_gpu()
        OUT.mkdir()
        process = multiprocessing.get_context("spawn").Process(target=worker,
                  args=(receipt, (trial.CARD_LIMIT_MIB-used-512)/total))
        started, peak, stop = time.time(), 0, None

        def interrupted(signum, _):
            raise KeyboardInterrupt(signal.Signals(signum).name)

        previous = signal.signal(signal.SIGTERM, interrupted)
        try:
            process.start()
            print(f"SUPERVISOR child={process.pid} stop={OUT / 'STOP'}", flush=True)
            with (OUT/"gpu.csv").open("x", encoding="utf-8", buffering=1) as telemetry:
                telemetry.write("unix_seconds,pid,card_used_mib,gpu_util_percent\n")
                while process.is_alive():
                    now = time.time()
                    if now >= deadline.timestamp()-35 or (OUT/"STOP").exists():
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
            trial.publish(OUT/"supervisor.json", dict(pid=process.pid, started=started, ended=time.time(),
                          returncode=process.exitcode, stop_reason=stop, peak_card_mib=peak,
                          card_after_exit=trial.observe_card_return()))
    finally:
        os.close(lock)
    return 0 if process.exitcode == 0 and stop is None else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "check":
        print(json.dumps(prepare(), indent=2))
        return 0
    if args.receipt is None or args.stop_by is None:
        parser.error("run requires --receipt and --stop-by")
    return supervise(args.receipt, args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
