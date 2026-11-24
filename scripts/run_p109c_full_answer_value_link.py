"""Train value-location selection at every content token of a numeric answer."""

import argparse
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from scripts import run_p109c_table_value_link as baseline


TAG = "p109c_full_answer_value_link_gpu_v1_20261121"
OUT = baseline.OUT.with_name(TAG)
trial, data, control = baseline.trial, baseline.data, baseline.control
REFERENCE = trial.ROOT / "test_result/109_log_20261121_P109C_TableValueLink_CPU.txt"
AUTHORIZATION_END = datetime.fromisoformat("2026-11-21T17:00:00+09:00")


def position_loss(selector, hidden, places, query_positions, weights):
    rows = torch.arange(len(places), device=hidden.device)
    query = selector.query(hidden[rows[:, None], query_positions])
    keys = selector.key(hidden[rows[:, None], places[:, 1:5]])
    scores = query @ keys.transpose(1, 2) / baseline.PROJECTION**0.5
    expected = places[:, -1, None].expand_as(query_positions)
    costs = F.cross_entropy(scores.transpose(1, 2).float(), expected, reduction="none")
    return (costs * weights).sum()


def check_single_position():
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(134)
        selector = baseline.ValueLink(8)
        hidden = torch.randn(2, 9, 8, requires_grad=True)
        sites = torch.tensor(((4, 0, 1, 2, 3, 0), (5, 0, 1, 2, 3, 3)))
        expected = F.cross_entropy(selector(hidden, sites), sites[:, -1], reduction="sum")
        actual = position_loss(selector, hidden, sites, sites[:, :1], torch.ones(2, 1))
        targets = (hidden, *selector.parameters())
        torch.testing.assert_close(actual, expected)
        for left, right in zip(torch.autograd.grad(actual, targets), torch.autograd.grad(expected, targets), strict=True):
            torch.testing.assert_close(left, right, atol=1e-6, rtol=1e-5)


def prepare():
    reference = baseline.load_receipt(REFERENCE)
    report_file = baseline.OUT / "report.json"
    terminal_file = baseline.OUT / "supervisor.json"
    report = trial.read_json(report_file)
    terminal = trial.read_json(terminal_file)
    if (report["tag"] != baseline.TAG or report["parent"] is not None or report["updates"] != data.UPDATES
            or reference["initial"] != report["initial_sha256"] or terminal["returncode"] or terminal["stop_reason"]
            or report["preflight_sha256"] != trial.file_sha(REFERENCE)):
        raise ValueError("requires the completed same-initialization value-link control")
    tok, special, arrays, stages, _ = control.profile()
    if stages != reference["stages"]:
        raise ValueError("the authored cohort schedule changed")
    _, y, _ = arrays
    with np.load(baseline.INPUT / "sites.npz", allow_pickle=False) as located:
        sites = located["sites"]
    end = special["<|im_end|>"]
    answers = (y != baseline.IGNORE) & (y != end)
    widths = answers.sum(axis=1)
    first = answers.argmax(axis=1)
    if (len(sites) != len(y) or np.any(widths < 1) or not np.array_equal(sites[:, 0], first)
            or np.any(sites[:, 1:5] >= first[:, None]) or np.any(first + widths >= y.shape[1])
            or np.any(y[np.arange(len(y)), first + widths] != end) or np.any((y == end).sum(axis=1) != 1)):
        raise ValueError("the value source or answer boundary changed")
    steps = np.arange(int(widths.max()))[None, :]
    active = steps < widths[:, None]
    positions = first[:, None] + np.where(active, steps, 0)
    weights = active.astype(np.float32) / widths.astype(np.float32)[:, None]
    if not answers[np.arange(len(y))[:, None], positions].all():
        raise ValueError("content positions must be consecutive and exclude ChatML termination")
    stage_widths = []
    for phase in stages:
        start = phase["offset"]
        counts = widths[start:start + phase["rows"]]
        stage_widths.append(dict(stage=phase["stage"], positions=int(counts.sum()),
                                 multi_piece=int((counts > 1).sum()), maximum=int(counts.max())))
    check_single_position()
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), reference=trial.file_sha(REFERENCE),
                reference_report=trial.file_sha(report_file), reference_terminal=trial.file_sha(terminal_file),
                initial=reference["initial"], weight=baseline.WEIGHT, projection=baseline.PROJECTION,
                stages=stages, supervision=stage_widths,
                positions_sha256=sha256(positions.tobytes()).hexdigest(),
                weights_sha256=sha256(weights.tobytes()).hexdigest())
    return plan, (tok, special, arrays, sites, positions, weights)


def worker(plan, fraction):
    checked, (tok, special, arrays, sites, positions, weights) = prepare()
    if checked != plan:
        raise ValueError("the sealed training condition changed")
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    if not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA BF16 required")
    x, y, context = [torch.as_tensor(v, device="cuda", dtype=torch.long) for v in arrays]
    links, locations = [torch.as_tensor(v, device="cuda", dtype=torch.long) for v in (sites, positions)]
    costs = torch.as_tensor(weights, device="cuda")
    validation = trial.read_json(baseline.INPUT / "validation.json")
    evaluation = trial.read_json(data.DATA / "evaluation.json")
    torch.manual_seed(data.SEED)
    model = baseline.TiedMLPTransformer(trial.make_config())
    if trial.state_sha(model.state_dict()) != plan["initial"] or len(model.visit_schedule()) != 28:
        raise ValueError("initial model state or recursive route differs")
    selector = baseline.ValueLink(model.cfg.dim)
    model.to("cuda")
    selector.to("cuda")
    parameters = [*model.parameters(), *selector.parameters()]
    optimizer = torch.optim.AdamW(parameters, lr=.0015, weight_decay=.01, fused=True)
    step, stage_reports = 0, []
    started = time.perf_counter()
    print(f"START {TAG}", flush=True)
    for phase, supervision in zip(plan["stages"], plan["supervision"], strict=True):
        stage = phase["stage"]
        use_all_positions = supervision["maximum"] > 1
        offset = phase["offset"]
        sums = torch.zeros(3, device="cuda")
        response_count, prefix_count, row_count = 0, 0, 0
        for start in range(offset, offset + phase["rows"], data.BATCH):
            block = slice(start, start + data.BATCH)
            answer, prefix = y[block], context[block]
            keep, keep_prefix = answer.ne(baseline.IGNORE), prefix.ne(baseline.IGNORE)
            answer_ids, context_ids = answer[keep], prefix[keep_prefix]
            step += 1
            optimizer.param_groups[0]["lr"] = .0015 * min(1., step / 64) * (1 - .7 * (step / data.UPDATES)**2)
            model.set_anneal(min(1., step / (.6 * data.UPDATES)))
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                hidden = model(x[block], return_hidden=True)
                answer_sum = F.cross_entropy(model._head_logits(hidden[keep]).float(), answer_ids, reduction="sum")
                nll, _ = control.target_nll(model, hidden[keep_prefix].unsqueeze(0),
                                            context_ids.unsqueeze(0), rows=control.CE_ROWS)
                prefix_sum = nll.sum()
                if use_all_positions:
                    link_sum = position_loss(selector, hidden, links[block], locations[block], costs[block])
                else:
                    link_sum = F.cross_entropy(selector(hidden, links[block]).float(),
                                               links[block, -1], reduction="sum")
                loss = (answer_sum / answer_ids.numel() + control.WEIGHT * prefix_sum / context_ids.numel()
                        + baseline.WEIGHT * link_sum / len(answer))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
            optimizer.step()
            response_count += answer_ids.numel()
            prefix_count += context_ids.numel()
            row_count += len(answer)
            sums += torch.stack([answer_sum.detach(), prefix_sum.detach(), link_sum.detach()])
            if step % 128 == 0:
                counts = response_count, prefix_count, row_count
                print(json.dumps(dict(stage=stage, step=step, elapsed=time.perf_counter()-started,
                                      ce=[value / n for value, n in zip(sums.tolist(), counts)])), flush=True)
        counts = response_count, prefix_count, row_count
        if counts != (phase["targets"], phase["context_targets"], phase["rows"]):
            raise ValueError("the original answer, context or row counts changed")
        model.eval()
        selector.eval()
        model.clear_quant()
        panel = validation["short" if stage == "two_digit" else "exchange"]
        greedy = data.evaluate(model, tok, special, panel, paired=True)
        slots = baseline.evaluate_slots(model, selector, panel, special["<pad>"])
        trial.publish(OUT / f"{stage}_eval.json", greedy)
        trial.publish(OUT / f"{stage}_slots.json", slots)
        stage_reports.append(dict(stage=stage, step=step, counts=counts,
                                  ce=[v / n for v, n in zip(sums.tolist(), counts)],
                                  greedy_joint=greedy["both_correct"], by_language=greedy["by_language"],
                                  selector_joint=slots["joint"]))
        model.train()
        selector.train()
        model.clear_quant()
    if step != data.UPDATES:
        raise ValueError("incorrect number of optimizer updates")
    model.eval()
    selector.eval()
    switch = data.evaluate(model, tok, special, validation["question_switch"], paired=True)
    switch_slots = baseline.evaluate_slots(model, selector, validation["question_switch"], special["<pad>"])
    original = data.evaluate(model, tok, special, evaluation["original"], paired=False)
    trial.publish(OUT / "question_switch_eval.json", switch)
    trial.publish(OUT / "question_switch_slots.json", switch_slots)
    trial.publish(OUT / "original_eval.json", original)
    for phase in stage_reports:
        print(json.dumps(phase), flush=True)
    state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    checkpoint = OUT / "foundation.pt"
    with checkpoint.open("xb") as out:
        torch.save(dict(tag=TAG, step=step, parent=None, model=state, config=asdict(model.cfg),
                        train_head={k: v.detach().cpu() for k, v in selector.state_dict().items()}), out)
    trial.publish(OUT / "report.json", dict(plan=plan, stages=stage_reports, updates=step,
                                          original=original["exact_with_eot"], switch=switch["both_correct"],
                                          switch_selector=switch_slots["individual"],
                                          checkpoint_sha256=trial.file_sha(checkpoint),
                                          state_sha256=trial.state_sha(state), wall=time.perf_counter()-started,
                                          peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                                          peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan, _ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires a sealed comparison and an authorized cutoff")
    return baseline.owner.supervise(worker, (plan,), OUT, args.stop_by,
                                    authorization_end=AUTHORIZATION_END, min_seconds=1200)


if __name__ == "__main__":
    raise SystemExit(main())
