"""Admit an exact-shape output route for the held Bonsai HellaSwag task only."""

import argparse
import os
from pathlib import Path
import signal
import sysconfig
import time
from types import SimpleNamespace

import numpy as np

from scripts import diag_p106b_bonsai_native_core6 as original
from scripts.p106b_prism_selected_logits import MAX_OUTPUT_ROWS, SelectedLogits


ROOT = original.ROOT
PRISM = original.PRISM
OUT = ROOT / "test_result/evidence/p106b_bonsai_hellaswag_remaining_v1_20261118"
PROFILE = OUT / "profile.json"
PARENT_SHA = "389099A54223256CF9832A6306BF048A14C33DEA1F49D1B42EA5EA9074C1D890"
TASK = "hellaswag"
CAP = 6000


def single_batch(plan, batch_limit):
    return len(plan.input_ids) <= batch_limit and len(plan.continuation_ids) <= MAX_OUTPUT_ROWS


class SingleBatch:
    def __init__(self, reference, selected, batch_limit):
        self.reference = reference
        self.selected = selected
        self.batch_limit = batch_limit
        self.qualified_calls = 0
        self.fallback_calls = 0

    def score(self, plans):
        fallback = []
        outputs = [None] * len(plans)
        for index, plan in enumerate(plans):
            if single_batch(plan, self.batch_limit):
                outputs[index] = self.selected.score_plan(plan)
                self.qualified_calls += 1
            else:
                fallback.append((index, plan))
        if fallback:
            values = self.reference.score([plan for _, plan in fallback])
            for (index, _), value in zip(fallback, values, strict=True):
                outputs[index] = value
            self.fallback_calls += len(fallback)
        return outputs


def proof():
    profile, native = original.verify()
    assert PRISM.digest(original.PROFILE) == PARENT_SHA
    path = original.OUT / "actual/report.json"
    parent = PRISM.read(path)
    assert parent["exit"] == 8 and parent["handles_closed"] and not Path(f"/proc/{parent['PID']}").exists()
    assert parent["profile_sha256"] == PARENT_SHA and parent["sources_unchanged"]
    assert parent["tasks"][TASK]["status"] == "COST_HOLD" and parent["tasks"][TASK]["rows"] == 0
    assert not list((original.OUT / "actual").glob(f"{TASK}*"))
    done = {n: t for n, t in parent["tasks"].items() if t["status"] == "COMPLETE"}
    assert set(done) == set(profile["primary"]) - {TASK} and sum(t["rows"] for t in done.values()) == 9923
    canaries = parent["bulk_oracle"]["pair_oracles"]
    assert not parent["bulk_oracle"]["eligible"] and all(canaries[i]["pass_oracle"] for i in (0, 1, 4))
    assert {i for i, item in enumerate(canaries) if not item["pass_oracle"]} == {2, 3}
    payload = dict(parent_profile_sha256=PARENT_SHA, parent_report_sha256=PRISM.digest(path),
        run_source_sha256=PRISM.digest(Path(__file__)), completed={n:t["manifest"]["concat_sha256"] for n,t in done.items()},
        task=TASK, input=profile["tasks"]["items"][TASK], seconds=CAP, max_outputs=MAX_OUTPUT_ROWS,
        input_for_single_native_batch=512, old_boundary_failures=[2, 3], model_asset=native["model"],
        fallback="ORIGINAL_LAST_LOGIT_PREFIXES", output_byte_cap=original.TOTAL_LIMIT)
    return payload, profile, native


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    data, _, _ = proof()
    def case(n, target):
        return SimpleNamespace(input_ids=[0]*n, continuation_ids=[1]*target)
    assert single_batch(case(512, 64), 512)
    assert not single_batch(case(513, 64), 512) and not single_batch(case(511, 65), 512)
    folded = SingleBatch(SimpleNamespace(score=lambda plans: ["prefix"]*len(plans)),
        SimpleNamespace(score_plan=lambda plan: "one-batch"), 512)
    assert folded.score([case(512, 64), case(513, 64), case(511, 65), case(42, 3)]) == ["one-batch", "prefix", "prefix", "one-batch"]
    assert folded.qualified_calls == folded.fallback_calls == 2
    OUT.mkdir(exist_ok=False)
    PRISM.write(PROFILE, data)
    print("BONSAI_HELLASWAG_ONLY_CPU_READY", PRISM.digest(PROFILE), flush=True)


def frozen():
    data, profile, native = proof()
    assert PRISM.read(PROFILE) == data
    return data, profile, native


def qualify(reference, selected, items, model, check):
    plans, _, examples, rejected = original.mc.token_jobs(reference, items, check)
    if rejected:
        raise original.mc.lambada.Hold(f"original token boundary gate rejected {rejected} items")
    limit = min(512, model.batch_limit)
    counts = [sum(single_batch(p, limit) for p in row) for row in plans]
    assert sum(len(row) for row in plans) == 40168
    assert any(counts)
    largest = max(range(len(items)), key=lambda i: max(len(p.input_ids) for p in plans[i]))
    longest_target = max(range(len(items)), key=lambda i: max(len(p.continuation_ids) for p in plans[i]))
    largest_eligible = max((i for i, count in enumerate(counts) if count),
        key=lambda i: max(len(p.input_ids) for p in plans[i] if single_batch(p, limit)))
    indices = sorted({i*(len(items)-1)//31 for i in range(32)} | {largest, longest_target, largest_eligible})
    oracle = []
    for i in indices:
        permitted = [p for p in plans[i] if single_batch(p, limit)]
        if permitted:
            oracle.extend(original.verify_match(reference, selected, f"official_item_{i}", permitted))
    return dict(eligible=bool(oracle) and all(p["pass_oracle"] for p in oracle),
        comparisons=oracle, indices=indices, qualifying_candidates=sum(counts),
        prefix_fallback_candidates=40168-sum(counts), single_batch_limit=limit,
        original_token_boundary_rejections=rejected, largest_input=max(len(p.input_ids) for row in plans for p in row),
        largest_continuation=max(len(p.continuation_ids) for row in plans for p in row))


def actual():
    from scripts.interactive_research_infer import require_idle_gpu

    data, previous, native = frozen()
    assert time.time()+CAP+90 < original.CUTOFF
    assert os.environ.get("LD_LIBRARY_PATH") == native["bundle"]
    assert not any(key.startswith(("LLAMA_ARG_", "GGML_")) for key in os.environ)
    stage = OUT / "actual"
    stage.mkdir(exist_ok=False)
    start = time.monotonic()
    result = dict(tag=OUT.name, PID=os.getpid(), profile_sha256=PRISM.digest(PROFILE), task=TASK,
        completed_tasks_reused=len(data["completed"]), new_training_steps=0)

    def remaining():
        return min(CAP - (time.monotonic()-start), original.CUTOFF-time.time()-45)

    def check():
        if remaining() <= 0 or (OUT / "STOP").exists():
            raise original.mc.lambada.Hold("owned work cap or STOP")

    def interrupt(_sig, _frame):
        raise original.mc.lambada.Hold("owned interrupt")

    handler = signal.signal(signal.SIGINT, interrupt)
    model = None
    try:
        result["gpu_entry"] = require_idle_gpu()
        tasks, items, metadata = original.inputs()
        assert original.canonical(metadata) == original.canonical(previous["tasks"]) and len(items[TASK]) == 10042
        template, _ = original.prepare_harness(runtime_root=Path(sysconfig.get_paths()["purelib"]))
        with PRISM.native.NativeModel(native["bundle"], ROOT/native["model"], check=check) as model:
            witness = np.load(PRISM.OUT / "actual/A0_logits_fp32.npy", allow_pickle=False)
            logit = model.logits(native["prompts"]["A"]["native_ids"])
            assert np.array_equal(witness.view(np.uint32), logit.view(np.uint32))
            reference = original.PrismLikelihood(model, template, original.mc.lambada.EOT, check=check)
            selected = SelectedLogits(model)
            numeric = result["single_batch_oracle"] = qualify(reference, selected, items[TASK], model, check)
            print("BONSAI_HELLASWAG_ONE_BATCH_GATE", numeric["eligible"], numeric["qualifying_candidates"],
                numeric["prefix_fallback_candidates"], len(numeric["comparisons"]), flush=True)
            if not numeric["eligible"]:
                raise original.mc.lambada.Hold("single-batch HellaSwag shapes exceeded the original tolerance")
            scored = SingleBatch(reference, SelectedLogits(model), numeric["single_batch_limit"])
            result["task_result"] = original.evaluate(reference, scored, TASK, tasks[TASK], items[TASK], check, remaining, stage, [0])
            result["calls_including_numerical_and_cost_probes"] = dict(selected=scored.qualified_calls, prefix=scored.fallback_calls)
        done = result["task_result"]["status"] == "COMPLETE"
        result.update(status="COMPLETE" if done else "COST_HOLD", exit=0 if done else 8)
    except Exception as error:
        hold = isinstance(error, original.mc.lambada.Hold)
        result.update(status="HOLD" if hold else "ERROR", exit=8 if hold else 1,
            error=dict(type=type(error).__name__, message=str(error)[:1000]))
    finally:
        signal.signal(signal.SIGINT, handler)
        result["handles_closed"] = model is None or not (model.context or model.model or model.backend)
        result["wall_seconds"] = time.monotonic()-start
        frozen()
        PRISM.write(stage / "report.json", result)
    print("BONSAI_HELLASWAG_ONLY_TERMINAL", result["status"], result["exit"], result["handles_closed"], flush=True)
    return result["exit"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "actual"))
    phase = parser.parse_args().action
    if phase == "prepare":
        prepare()
    elif phase == "check":
        frozen()
        print("BONSAI_HELLASWAG_ONLY_CHECK", PRISM.digest(PROFILE), flush=True)
    else:
        raise SystemExit(actual())
