"""Export the G4 inference body from a native bilingual-supervised checkpoint."""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
from tempfile import TemporaryFile
from time import perf_counter

import torch

from scripts import diag_p109c_bilingual_native_resume as diagnostic
from scripts import eval_p109c_completed as evaluation
from tinylm.train import packed_document_training


native, prep = diagnostic.native, diagnostic.prep
supervised = diagnostic.objective
TRAINING_HEADS = {"decimal_head.weight", "decimal_head.bias", "value_link.query.weight", "value_link.key.weight"}


def check_training_state(state, expected_step):
    context = state[supervised.trainer.CONTEXT_STATE_KEY]
    cursor = context["cursor"]["cursor"]
    tools = supervised.state_tools
    tools._validate_binding(context["binding"])
    tools.validate_trainer_control(context["control"], expected_step, cursor["optimizer_updates"])
    if (state["step"] != expected_step or cursor["next_update"] != expected_step
            or cursor["optimizer_updates"] != expected_step
            or state["tokenizer_sha256"].upper() != prep.TOKENIZER_SHA
            or context["payload_sha256"] != tools._payload_sha(context)
            or context["control"]["n_skip"] != 0 or not state["opt"]["state"] or not state["opt_muon"]["state"]):
        raise ValueError("the native checkpoint, optimizer, tokenizer and cursor must refer to the same update")
    return context


def evaluation_payload(state):
    model = state["model"]
    heads = {name for name in model if name.startswith(("decimal_head.", "value_link."))}
    if heads != TRAINING_HEADS:
        raise ValueError("the checkpoint must have exactly the two supported training-only heads")
    payload = {key: state[key] for key in ("step", "cfg", "tokenizer_sha256")}
    payload["model"] = {name: tensor for name, tensor in model.items() if name not in heads}
    return payload


def export_finished(checkpoint, expected_sha, expected_steps, output):
    """Publish a complete native inference file once the admitted horizon has closed."""
    if checkpoint.resolve(strict=True) != checkpoint or output.exists() or output.is_symlink():
        raise ValueError("use the exact original checkpoint and fresh destination")
    stamp = native.file_stamp(checkpoint)
    if prep.sha(checkpoint) != expected_sha.upper():
        raise ValueError("the completed checkpoint fingerprint changed")
    state = torch.load(checkpoint, map_location="cpu", mmap=True, weights_only=True)
    context = check_training_state(state, expected_steps)
    if context["binding"]["plan"]["steps"] != expected_steps:
        raise ValueError("a partial native checkpoint cannot be published as a completed evaluation body")
    payload = evaluation_payload(state)
    if native.file_stamp(checkpoint) != stamp:
        raise ValueError("the source changed during export")
    packed_document_training.save_packed_checkpoint(output, payload)
    return prep.sha(output)


@contextmanager
def temporary_payload(payload):
    with TemporaryFile(dir="/tmp") as stream:
        torch.save(payload, stream)
        stream.flush()
        yield Path("/proc/self/fd") / str(stream.fileno())


def audit():
    directory = prep.EVIDENCE / diagnostic.TAG
    report, terminal = (prep.read_json(directory / name) for name in ("report.json", "supervisor.json"))
    if (report["status"] != "NATIVE_CHECKPOINT_RECOVERY_MEASURED" or terminal["returncode"] != 0
            or terminal["stop_reason"] is not None or terminal["card_after_exit"]["compute_pids"]):
        raise ValueError("an existing completed supervised diagnostic is required")
    prefix = report["prefix"]
    checkpoint = Path(prefix["path"])
    if checkpoint.resolve(strict=True) != checkpoint or prep.sha(checkpoint) != prefix["sha256"]:
        raise ValueError("the exact unlinked supervised source is required")
    stamp = native.file_stamp(checkpoint)
    state = torch.load(checkpoint, map_location="cpu", mmap=True, weights_only=True)
    step = diagnostic.BOUNDARY
    ctx = check_training_state(state, step)
    if ctx["payload_sha256"] != prefix["native_payload_sha256"]:
        raise ValueError("the archived supervised checkpoint has different native state")
    payload = evaluation_payload(state)
    old_body = {name: value for name, value in state["model"].items() if not name.startswith("decimal_head.")}
    with temporary_payload(dict(payload, model=old_body)) as location:
        try:
            evaluation.load_model(location, step, "cpu")
        except RuntimeError as error:
            message = str(error)
            if ("Unexpected key(s)" not in message
                    or any(name not in message for name in TRAINING_HEADS if name.startswith("value_link."))):
                raise
        else:
            raise ValueError("expected the old export to retain the two training value matrices")
    with temporary_payload(payload) as location:
        reloaded = torch.load(location, map_location="cpu", mmap=True, weights_only=True)
        trained = state["model"]
        if set(reloaded["model"]) != set(trained) - TRAINING_HEADS:
            raise ValueError("the serialized evaluation payload has a different G4 tensor inventory")
        for name, value in reloaded["model"].items():
            if value.dtype != trained[name].dtype or not torch.equal(value, trained[name]):
                raise ValueError(f"the serialized body changed at {name}")
        model = evaluation.load_model(location, step, "cpu")
        visits = len(model.visit_schedule())
        vocabulary = model.cfg.vocab_size
    if native.file_stamp(checkpoint) != stamp:
        raise ValueError("the source supervised checkpoint changed during the audit")
    return dict(status="NATIVE_SUPERVISED_BODY_STRICT_EVAL_LOAD_VERIFIED", source_sha256=prep.sha(Path(__file__)),
                original_checkpoint_sha256=prefix["sha256"], native_context_sha256=ctx["payload_sha256"],
                source_step=step, body_tensors=len(payload["model"]), stripped_train_heads=sorted(TRAINING_HEADS),
                tokenizer_sha256=state["tokenizer_sha256"], legacy_unexpected_keys_detected=True,
                strict_loader_sha256=prep.sha(Path(evaluation.__file__)), visits=visits, vocabulary=vocabulary,
                validation_format="ANONYMOUS_TEMPFILE_CPU_PROBE", optimizer_updates=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("the existing diagnostic is checked on CPU")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    start = perf_counter()
    result = audit()
    result["elapsed_seconds"] = perf_counter() - start
    native.publish(args.output, result)
    print(result["status"], result["body_tensors"], result["visits"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
