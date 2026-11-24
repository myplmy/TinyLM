"""Compare a protected FP16 output correction on the small packed CPU runtime."""

import argparse
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p077_compact_chat32_request as mapped
from scripts import train_p108_guarded_output_sidecar as trained
from scripts.diag_p108_g4_compact_fixed_edit_text import seal


TAG = "p108_native_output_overlay_cpu_v2_20261121"
OUT = trained.OUT.with_name(TAG)
native, wide, trial = mapped.native, mapped.wide, trained.trial
prior = trained.prior
CHECKPOINT = trained.solver.first.CHECKPOINT
LEARNED = trained.OUT / "trained_overlay.pt"
ARMS = ("clean", "composed", "trained")


def engine_source(stop):
    runtime = native.tiled_rope.render(native.source_for(2048, 3, *stop))
    runtime = wide.render(runtime, "online8")
    edits = (
        (b'"TLMG4R6"', b'"TLMG4R7"'),
        (b'        require(in.remaining == 0, "unexpected trailing model bytes");',
         b'''        overlay_count = *in.take<uint32_t>(1);
        require(overlay_count <= 8, "too many output overlay rows");
        overlay_ids = in.take<uint32_t>(overlay_count);
        overlay_values = in.take<uint16_t>(overlay_count * E);
        for (uint32_t row = 0; row < overlay_count; ++row) {
            require(overlay_ids[row] < V && (row == 0 || overlay_ids[row - 1] < overlay_ids[row]),
                    "invalid output overlay ID");
        }
        require(in.remaining == 0, "unexpected trailing model bytes");'''),
        (b"    const float *scales, *embed_up, *rope_frequencies, *norm_f;",
         b"""    const float *scales, *embed_up, *rope_frequencies, *norm_f;
    uint32_t overlay_count;
    const uint32_t* overlay_ids;
    const uint16_t* overlay_values;"""),
        (b"        uint32_t best_id = 0;",
         b"        uint32_t best_id = 0;\n        uint32_t overlay_row = 0;"),
        (b"            const float score = output_dot(hidden.data(), row, model.scales[token]);",
         b"""            float score = output_dot(hidden.data(), row, model.scales[token]);
            if (overlay_row < model.overlay_count &&
                    static_cast<uint32_t>(token) == model.overlay_ids[overlay_row]) {
                std::array<float, E> correction;
                load_half(correction.data(), model.overlay_values + overlay_row * E, E);
                score += dot(hidden.data(), correction.data(), E);
                require(std::isfinite(score), "invalid corrected score");
                ++overlay_row;
            }"""),
    )
    for before, after in edits:
        runtime = native.port.replace_once(runtime, before, after)
    return runtime


def prepare():
    recipe, (tok, special, cases, dev, novel, _) = trained.prepare()
    report_path = trained.OUT / "report.json"
    terminal_path = trained.OUT / "supervisor.json"
    report = trial.read_json(report_path)
    terminal = trial.read_json(terminal_path)
    control = trial.read_json(prior.CONTROL)
    if (report["plan"] != recipe or report["requests"] != novel or terminal["returncode"] != 0
            or terminal["stop_reason"] or trial.file_sha(CHECKPOINT) != control["checkpoint_sha256"]
            or control["state_sha256"] != recipe["body_state_sha256"]
            or trial.file_sha(LEARNED) != report["new_expressions"]["saved_sha256"]):
        raise ValueError("requires the completed GPU output correction and its original frozen checkpoint")
    native_plan, (native_tok, native_special, texts, _, model, decoder, encoder) = mapped.prepare()
    stop = (special["<|im_end|>"], tok.token_to_id("<eos>"))
    if (tok.to_str() != native_tok.to_str() or special != native_special or len(novel) != 16
            or len(cases["test"]) != 64 or len(recipe["base"]["guard"]) != 24):
        raise ValueError("the ChatML tokenizer or registered cohorts changed")
    plan = dict(tag=TAG, sources=trial.file_sha(Path(__file__)),
                engine_sha256=sha256(engine_source(stop)).hexdigest(),
                checkpoint=control["checkpoint_sha256"], body=recipe["body_state_sha256"],
                control=trial.file_sha(prior.CONTROL), gpu_report=trial.file_sha(report_path),
                gpu_terminal=trial.file_sha(terminal_path), native=native_plan,
                composed=recipe["start_overlay_sha256"], trained=report["new_expressions"]["saved_sha256"],
                cohorts={"fit": len(recipe["targets"]), "novel": len(novel), "guard": 24, "test": 64},
                max_new=8, stop=list(stop))
    return plan, (tok, cases, dev, novel, recipe, texts, model, decoder, encoder, control, report)


def pack_body(stack, body_sha):
    base = native.base
    fds = [base.memfile(f"p108-cpu-base-r{version}") for version in (4, 5, 6)]
    for fd in fds:
        stack.callback(os.close, fd)
    state = torch.load(CHECKPOINT, weights_only=True, map_location="cpu")
    if trial.state_sha(state["model"]) != body_sha:
        raise ValueError("incorrect frozen-body checkpoint")
    config = replace(native.wide.TMTConfig(**state["config"]), max_seq_len=1024)
    model = native.wide.TiedMLPTransformer(config)
    model.load_state_dict(state["model"])
    model.eval()
    model.freeze_quant()
    pack = base.prior.embedding.PACK
    packed = pack.load_payload(pack.export_payload(model, provenance={"tag": TAG}, head_rows=128))
    packed.quantize_embedding("int8")
    packed.eval()
    base.model_blob(packed, fds[0], base.prior.model_storage(packed)["unique_storage_bytes"], small=True)
    native.port.extend_positions(fds[0], fds[1], packed)
    info = native.tiled_rope.pack(fds[1], fds[2], packed.cfg, OUT)
    raw = os.pread(fds[2], info["artifact_bytes"], 0)
    if sha256(raw).hexdigest().upper() != info["artifact_sha256"]:
        raise ValueError("the compact base image changed")
    return raw, info


def pack_images(stack, raw, plan):
    paths = {"composed": trained.INITIAL, "trained": LEARNED}
    images = {}
    token_ids = {}
    if not raw.startswith(b"TLMG4R6\x00"):
        raise ValueError("invalid R6 base image")
    body = raw[8:]
    for arm in ARMS:
        payload = struct.pack("<I", 0)
        token_ids[arm] = []
        if arm in paths:
            path = paths[arm]
            if trial.file_sha(path) != plan[arm]:
                raise ValueError("an output correction changed")
            overlay = torch.load(path, weights_only=True, map_location="cpu")
            ids, delta = overlay["ids"], overlay["delta"]
            if (overlay["body_sha256"] != plan["body"] or len(set(ids)) != 3
                    or any(not isinstance(token, int) or not 0 <= token < 32768 for token in ids)
                    or delta.dtype != torch.float16 or delta.shape != (3, 128) or not delta.isfinite().all()):
                raise ValueError("invalid sparse output correction")
            order = sorted(range(len(ids)), key=ids.__getitem__)
            token_ids[arm] = [ids[i] for i in order]
            payload = struct.pack("<4I", 3, *token_ids[arm]) + delta[order].numpy().astype("<f2").tobytes()
        fd = native.base.memfile(f"p108-cpu-r7-{arm}")
        stack.callback(os.close, fd)
        native.bounded.text.store(fd, b"TLMG4R7\x00" + body + payload)
        seal(fd)
        images[arm] = fd
    if token_ids["composed"] != token_ids["trained"]:
        raise ValueError("the learned correction has a different output-row support")
    return images, token_ids


def evaluate(binary, images, plan, data, gate):
    tok, cases, dev, novel, recipe, _, _, _, _, control, gpu = data
    stop = plan["stop"]
    prompts = []
    for root in recipe["targets"]:
        row = dev[root]
        prompts.append(("fit", root, "correction", row["gold"], row["prompts"]["correction"], ARMS, None))
    for index, row in enumerate(novel):
        choices = gpu["new_expressions"]
        reference = {arm: choices[phase][index] for arm, phase in (("composed", "before"), ("trained", "after"))}
        prompts.append(("novel", row["root"], row["family"], row["wanted"], row["ids"], ARMS, reference))
    for cohort, bucket, roots in (("guard", "validation", recipe["base"]["guard"]), ("test", "test", cases["test"])):
        for root in roots:
            row = cases[bucket][root]
            for view in prior.VIEWS:
                reference = {"clean": control[bucket]["rows"][root][view]}
                if bucket == "test":
                    reference["trained"] = gpu["new_expressions"]["test"]["rows"][root][view]
                prompts.append((cohort, root, view, row["gold"], row["prompts"][view], ("clean", "trained"), reference))
    outputs = []
    for cohort, root, view, gold, ids, arms, reference in prompts:
        gate(10)
        results = {}
        for arm in arms:
            row, seconds, _ = native.token_request(binary, images[arm], ids, plan["max_new"])
            results[arm] = dict(native.decoded(tok, row, gold, stop), seconds=seconds)
        outputs.append(dict(cohort=cohort, root=root, view=view, gold=gold, prompt_ids=ids,
                            gpu=reference, cpu=results))
    return outputs


def quality_summary(rows, eot):
    summary = {}
    for cohort in ("fit", "novel", "guard", "test"):
        group = {}
        for row in (row for row in rows if row["cohort"] == cohort):
            view = row["view"]
            clean = row["cpu"]["clean"]
            for arm, result in row["cpu"].items():
                group.setdefault(view, {})
                stats = group[view].setdefault(arm, dict(count=0, exact=0, eot=0, lost_clean_exact=0,
                                                       changed_clean_exact_ids=0, gpu_exact=0,
                                                       gpu_agreement=0, gpu_count=0))
                stats["count"] += 1
                stats["exact"] += result["exact"]
                stats["eot"] += result["eot"]
                stats["lost_clean_exact"] += clean["exact"] and not result["exact"]
                stats["changed_clean_exact_ids"] += clean["exact"] and clean["ids"] != result["ids"]
                reference = (row["gpu"] or {}).get(arm)
                if reference is not None:
                    reference_ids = [*reference["ids"], eot] if reference["eot"] else reference["ids"]
                    stats["gpu_count"] += 1
                    stats["gpu_exact"] += reference["eot"] and reference["answer"] == row["gold"]
                    stats["gpu_agreement"] += result["ids"] == reference_ids
        summary[cohort] = group
    return summary


def measure_requests(binaries, images, data, gate, stack):
    tok, _, _, _, _, texts, _, decoder, encoder, _, _ = data
    normal, parts = native.text_codec(OUT)
    mapped.request.render_decoder(normal, decoder)
    wrapper = OUT / "mapped_request.py"
    mapped.render_input(wrapper, normal, encoder)
    assets = []
    for i, part in enumerate(parts):
        fd = native.base.memfile(f"p108-chat32-wire-{i}")
        stack.callback(os.close, fd)
        native.bounded.text.store(fd, part)
        seal(fd)
        assets.append(fd)
    measures = []
    for index, case in enumerate((wide.CASES[0], wide.CASES[1])):
        text = texts[case]["text"]
        ids = tok.encode(text, add_special_tokens=False).ids
        reference, _, _ = native.token_request(binaries[0], images["clean"], ids, native.GEN)
        order = ("clean", "trained", "trained", "clean")
        if index == 1:
            order = tuple(reversed(order[:2])) + order[:2]
        for sample, arm in enumerate(order):
            gate(30)
            fd = images[arm]
            expected = dict(encoding=dict(ids=ids), native=dict(reference, model_bytes=os.fstat(fd).st_size))
            path = OUT / f"request_{case}_{sample}_{arm}.json"
            stats = native.port.request(binaries[1], [fd, *assets], text.encode("utf-8"), path, expected, wrapper=wrapper)
            result = trial.read_json(path)
            measures.append(dict(case=case, arm=arm, input_tokens=len(ids), seconds=stats["seconds"],
                                 peak_rss=stats["peak_rss"], model_bytes=result["native"]["model_bytes"],
                                 kv_bytes=stats["kv_bytes"], generated_ids=result["native"]["ids"]))
    return measures


def run(plan, stop_by):
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or OUT.exists() or not stop_by.tzinfo
            or stop_by > trained.solver.AUTHORIZATION_END):
        raise ValueError("requires a new CPU-only experiment in the authorized window")

    def gate(reserve):
        if (OUT / "STOP").exists() or (stop_by - datetime.now(stop_by.tzinfo)).total_seconds() < reserve:
            raise TimeoutError("the CPU output-correction comparison reached its stop boundary")

    gate(260)
    checked, data = prepare()
    if checked != plan:
        raise ValueError("the sealed CPU profile changed")
    cpu = min(set(data[6]["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    with patch.object(native.bounded, "OUT", OUT):
        binaries = native.bounded.build(engine_source(plan["stop"]), caps=(64,))[64]
    with ExitStack() as stack:
        raw, base = pack_body(stack, plan["body"])
        images, tokens = pack_images(stack, raw, plan)
        print(json.dumps(dict(stage="packed", image_bytes={arm: os.fstat(fd).st_size for arm, fd in images.items()})),
              flush=True)
        sample = data[3][0]["ids"]
        traces = {arm: native.token_request(binaries[0], fd, sample, 1, trace=True)[2] for arm, fd in images.items()}
        changed = {}
        for arm in ARMS[1:]:
            changed[arm] = np.flatnonzero(traces["clean"].view("<u4") != traces[arm].view("<u4")).tolist()
            if changed[arm] != tokens[arm]:
                raise ValueError("the actual logit changes do not match the requested rows")
        outputs = evaluate(binaries[0], images, plan, data, gate)
        trial.publish(OUT / "quality.json", dict(plan=plan, outputs=outputs, changed_logits=changed))
        print(json.dumps(dict(stage="quality", count=len(outputs))), flush=True)
        requests = measure_requests(binaries, images, data, gate, stack)
    trial.publish(OUT / "report.json", dict(plan=plan, cpu=cpu, base=base, changed_logits=changed, requests=requests,
                                          quality=quality_summary(outputs, plan["stop"][0]),
                                          quality_sha256=trial.file_sha(OUT / "quality.json")))
    return 0


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
        parser.error("requires a preflight receipt and stop boundary")
    return run(plan, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
