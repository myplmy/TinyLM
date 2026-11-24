"""Fill the Falcon 90M FINAL200 comparison using the admitted CPU runtime."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import time

from scripts import diag_p106b_night_falcon as falcon
from scripts import diag_p106b_official_core6 as official
from scripts import eval_p109c_external_final200 as house
from scripts import p106b_final_holdout as panel
from scripts.interactive_research_infer import state_fingerprint
from scripts.p106b_shards import ShardWriter, verify


TAG = "p109c_falcon90m_final200_cpu_v1_20261124"
RECORD = official.ROOT / "test_result/evidence" / TAG
END = datetime.fromisoformat("2026-11-25T17:00:00+09:00")
MAX_CONTEXT = 1024


def prepare():
    if (official.digest(official.FALCON_REFERENCE) != official.FALCON_REFERENCE_SHA
            or falcon.ASSET != official.FALCON):
        raise ValueError("the established local Falcon CPU anchor must match")
    prior = json.loads(official.FALCON_REFERENCE.read_bytes())
    if (prior["status"] != "FALCON_CPU_STRICT_FROZEN" or not prior["actual_model_cpu_loaded"]
            or prior["precision"] != "FP32_MATH" or not prior["use_cache_generation"]
            or prior["add_special_tokens"] or prior["explicit_bos_added"]
            or {name: official.digest(falcon.ASSET / name) for name in prior["asset_sha256"]}
            != prior["asset_sha256"]):
        raise ValueError("the CPU prompt/cache and same immutable Falcon asset are required")
    rows = panel.build("final")
    inputs = json.loads((house.EVIDENCE / "p109c_external_final200_v1_20261124/semantic_readback.json").read_bytes())
    frozen = panel.digest(rows).upper()
    if frozen != inputs["frozen_final_sha256"] or len(rows) != 200:
        raise ValueError("the same frozen set of 200 real-use prompts is required")
    engines = [Path(module.__file__).resolve() for module in (falcon, official, house, panel)] + [Path(__file__).resolve()]
    return dict(tag=TAG, model="falcon90m", final_sha256=frozen, count=len(rows), max_new=panel.MAX_NEW,
                precision="FP32_MATH", device="cpu", add_special_tokens=False, use_cache=True, context=MAX_CONTEXT,
                strict_cpu_anchor_sha256=official.FALCON_REFERENCE_SHA, asset_sha256=prior["asset_sha256"],
                sources={path.relative_to(official.ROOT).as_posix(): official.digest(path) for path in engines}), rows, prior


def emit(active, prompt, *, max_new):
    torch, model, tokens = active
    ids = tokens.encode(prompt).ids
    vocab = model.config.vocab_size
    if not ids or len(ids) + max_new > MAX_CONTEXT or min(ids) < 0 or max(ids) >= vocab:
        raise ValueError("use the complete authorized content without automatic truncation")
    x = torch.tensor([ids], dtype=torch.long, device="cpu")
    with torch.inference_mode():
        result = model.generate(input_ids=x, max_new_tokens=max_new, do_sample=False, use_cache=True,
                                eos_token_id=model.config.eos_token_id, pad_token_id=model.config.pad_token_id)
    generated = result[0, len(ids):].tolist()
    end = model.config.eos_token_id
    stop = bool(generated and generated[-1] == end)
    if not generated or (not stop and len(generated) != max_new):
        raise ValueError("the CPU generation left the sealed stop rules")
    answer = tokens.decode(generated[:-1] if stop else generated)
    return answer, dict(generated_ids=generated, generated_tokens=len(generated),
                        finish_reason="EOS" if stop else "MAX_NEW", prompt_tokens=len(ids),
                        terminal_ids=[end] if stop else [])


def run(receipt, deadline):
    import torch

    contract, cases, prior = prepare()
    if (contract != receipt or RECORD.exists() or deadline.tzinfo is None or deadline > END
            or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or datetime.now(deadline.tzinfo) >= deadline):
        raise ValueError("the exact CPU receipt and approved time are required")
    started = datetime.now().astimezone().isoformat()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    _, model, tokens, runtime = falcon.load()
    before = state_fingerprint(model)
    if before != prior["initial_core_sha256"] or any(p.device.type != "cpu" for p in model.parameters()):
        raise ValueError("the original approved model must be entirely on the CPU")
    lengths = [len(tokens.encode(house.render(case)).ids) for case in cases]
    if max(lengths) + panel.MAX_NEW > MAX_CONTEXT:
        raise ValueError("a frozen input cannot fit without modifying the question")

    def check():
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("Falcon reached the authorized CPU cutoff")

    def interrupt(_number, _frame):
        raise InterruptedError("Falcon CPU evaluation was stopped")

    RECORD.mkdir()
    writer = ShardWriter(RECORD, "responses")
    report = dict(contract=contract, pid=os.getpid(), started=started, runtime=runtime, completed_rows=0,
                  max_input_tokens=max(lengths), initial_core_sha256=before, status="STARTED")
    handler = signal.signal(signal.SIGTERM, interrupt)
    try:
        house.collect(cases, (torch, model, tokens), emit, writer, report, check)
        if state_fingerprint(model) != before or torch.cuda.is_initialized():
            raise ValueError("CPU model state or execution device changed")
        report["status"] = "RESPONSES_COMPLETE_SEMANTIC_REVIEW_NOT_RUN"
    except BaseException as error:
        report.update(status="INCOMPLETE", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        signal.signal(signal.SIGTERM, handler)
        if report["completed_rows"]:
            report["responses"] = writer.close(lineage=contract)
            verify(RECORD, report["responses"])
        report["finished"] = datetime.now().astimezone().isoformat()
        with (RECORD / "report.json").open("x", encoding="utf-8") as stream:
            print(json.dumps(report, ensure_ascii=False, indent=2), file=stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        contract, *_ = prepare()
        with args.profile.open("x", encoding="utf-8") as stream:
            print(json.dumps(contract, ensure_ascii=False, indent=2), file=stream)
        print(official.digest(args.profile), len(contract["asset_sha256"]), flush=True)
        return 0
    if args.stop_by is None:
        parser.error("the authorized CPU cutoff is required")
    run(json.loads(args.profile.read_bytes()), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
