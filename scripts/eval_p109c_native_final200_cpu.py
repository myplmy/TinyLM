"""Fill the two missing native FINAL200 comparisons with local frozen weights."""

import argparse
from datetime import datetime
import os
from pathlib import Path
from time import perf_counter, time
from types import SimpleNamespace

from scripts import diag_p106b_final_holdout as protocol
from scripts import eval_p109b_first_use as decode
from scripts import eval_p109c_completed as current
from scripts import interactive_research_infer as manual
from scripts import p106b_weight_route as weights
from scripts.p106b_shards import ShardWriter, verify
from tinylm.chat.serialize import serialize
from tinylm.config import TMTConfig
from tinylm.infer.generate import sample
from tinylm.model import TiedMLPTransformer


MODELS = ("native595-f", "new595-broad-f")
MANIFEST_SHA = "F9964B44990AD5769B76821CC37DD6E8EEFD809B18FD7F91C7ACED0A4C4E2589"


def emit(active, question, max_new):
    model, tok, route = active
    prompt = serialize({"messages": manual.prompt_messages(question)}, "chatml", add_generation_prompt=True)
    ids = tok.encode(prompt).ids
    if len(ids) + max_new > model.cfg.max_seq_len:
        raise ValueError("the frozen request exceeds the native context")
    route.assert_active()
    capture = decode.DecodeSuffix(tok, ids)
    _, metadata = sample(model, model.cfg, capture, prompt, max_new=max_new, temperature=0., top_k=1,
                         device="cpu", eos_id=2, use_cache=True, logits_last_only=True,
                         return_metadata=True, mtp_tokens=1, stop_token_sequences=[[4]])
    return manual.answer_from_tokens(tok, ids, ids + capture.ids, metadata, max_new)


def run_comparator(name, manifest, questions, contract, output, deadline, pins):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    def check():
        if time() >= deadline:
            raise TimeoutError("the CPU comparison deadline was reached")

    spec = manual.resolve_model(name)
    entry = manifest["entries"][name]
    report = dict(model=name, device="cpu", precision="FP32_MATH", max_new=protocol.data.MAX_NEW,
                  final_input_sha256=contract["final_sha256"], completed_rows=0, semantic_review="NOT_RUN",
                  checkpoint_sha256=entry["checkpoint"]["sha256"], core_sha256=entry["core_sha256"],
                  manifest_sha256=MANIFEST_SHA, sources=pins, status="STARTED")
    started = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(output / "answers", "responses")
    try:
        check()
        manual.verify_descriptor(entry["report"], spec.report)
        manual.verify_descriptor(entry["activity"], spec.activity)
        tokenizer = manual.local_tokenizer(manifest)
        payload = manual.read_selected_payload(torch, spec, entry)
        cfg = TMTConfig(**payload["cfg"])
        manual.validate_cfg(cfg, entry["header"])
        model = TiedMLPTransformer(cfg)
        with weights.weight_route(model, spec.arm) as route, torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
            weights.validate_route_metadata(payload["quantization_route"], spec.arm)
            weights.load_routed_state(model, payload, spec.arm)
            del payload
            model.eval()
            model.set_anneal(1.)
            model.freeze_quant()
            if (route.metadata != entry["header"]["quantization_route"]
                    or manual.state_fingerprint(model) != entry["core_sha256"]):
                raise ValueError("the CPU model core or weight route differs from the original evidence")
            protocol.collect((model, tokenizer, route), questions, writer, SimpleNamespace(check=check), report,
                             emit=emit)
            if manual.state_fingerprint(model) != entry["core_sha256"]:
                raise ValueError("the model core changed during generation")
        if report["completed_rows"] != len(questions) or any(current.core6.digest(Path(p)) != h for p, h in pins.items()):
            raise ValueError("the answer count or a source fingerprint changed")
        report["status"] = "RESPONSES_COMPLETE_SEMANTIC_REVIEW_NOT_RUN"
    except Exception as error:
        report.update(status="ERROR", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report["seconds"] = perf_counter() - started
        report["answers"] = writer.close(lineage=dict(model=name, checkpoint_sha256=report["checkpoint_sha256"]))
        verify(output / "answers", report["answers"])
        current.training.publish(output / "report.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", nargs="+", choices=MODELS, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None:
        parser.error("a CPU-only device and explicit authorized deadline are required")
    import torch

    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    path = current.ROOT / manual.MANIFEST
    manifest = current.read_json(current.regular_file(path))
    if current.core6.digest(path) != MANIFEST_SHA or manifest["schema"] != manual.MANIFEST_SCHEMA:
        raise ValueError("the original read-only checkpoint manifest differs")
    questions, contract = current.final200_inputs()
    paths = (Path(__file__), Path(protocol.__file__), Path(protocol.data.__file__), Path(decode.__file__),
             Path(current.__file__), Path(manual.__file__), Path(weights.__file__), path,
             *(current.ROOT / name for name in manual.REQUIRED_SOURCES if name.startswith("tinylm/")))
    pins = {str(path.resolve()): current.core6.digest(path) for path in paths}
    for name in args.model:
        run_comparator(name, manifest, questions, contract, args.record.absolute() / name,
                       args.stop_by.timestamp(), pins)


if __name__ == "__main__":
    main()
