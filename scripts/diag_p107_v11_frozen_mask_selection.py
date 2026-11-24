"""Measure adaptive mask sampling on published positions with a frozen P109B model."""

import argparse
from datetime import datetime, timedelta
import json
import mmap
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from tokenizers import Tokenizer
import torch

from scripts import audit_p109c_v11_release as v11
from scripts import build_p109c_position_cache as position
from scripts import diag_p107_lexical_mask_audit as lexical
from scripts import eval_p109b_first_use as readback
from scripts import run_p109c_scratch330 as supervisor
from tinylm.train.adaptive_masking import HardMaskPolicy, PolicyConfig
from tinylm.train.hybrid_mntp import mntp_batch


OUT = v11.ROOT / "test_result/evidence/p107_v11_frozen_mask_selection_v2_20261121"
END = datetime.fromisoformat("2026-11-22T13:00:00+09:00")
COUNTS = (512, 64, 64)
WIDTH, VALID_TRAIN_DOCUMENTS, SEED = 257, 1_437_385, 2026112107
POLICY = "uniform_r2"


def script_bucket(text):
    korean = sum("가" <= char <= "힣" for char in text)
    latin = sum(char.isascii() and char.isalpha() for char in text)
    if max(korean, latin) < 8:
        return "und"
    if min(korean, latin) * 5 >= max(korean, latin):
        return "mixed"
    return "ko" if korean > latin else "en"


def prepare(directory):
    audit = json.loads((v11.OUT / "report.json").read_bytes())
    if audit["position_revision"] != 661 or audit["original_indexed_train"]["documents"] != VALID_TRAIN_DOCUMENTS:
        raise ValueError("requires the independently counted published source")
    files = {key: v11.ROOT / "data_cache" / name for key, (name, _) in v11.FILES.items()}
    for path in files.values():
        position.regular_file(path)
    for field in ("positions", "scope", "tokenizer"):
        if supervisor.file_sha(files[field]).lower() != audit["source_sha256"][field]:
            raise ValueError(f"the counted published source changed: {field}")
    if supervisor.file_sha(files["text"]).lower() != audit["source_sha256"]["text"]:
        raise ValueError("the counted text file changed")
    state, rows = position.release_positions(files["positions"].read_bytes())
    bounds, splits = position.split_ends(json.loads(files["scope"].read_bytes()))
    selected_ordinals = Random(SEED).sample(range(VALID_TRAIN_DOCUMENTS), sum(COUNTS))
    ordinals = {ordinal: index for index, ordinal in enumerate(selected_ordinals)}
    selected = [None] * sum(COUNTS)
    tokenizer = Tokenizer.from_file(str(files["tokenizer"]))
    raw_positions = (row for row in position.indexed_documents(state, rows, bounds, splits, set()) if row[1] == "train")
    with files["text"].open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as body:
        for index, (number, _, start, stop) in enumerate(raw_positions):
            order = ordinals.get(index)
            if order is not None:
                text = body[start:stop - len(position.SEPARATOR)].decode("utf-8")[:2000]
                selected[order] = (number, text)
    if any(row is None for row in selected):
        raise ValueError("some sample ordinals are outside the published source")

    reference = np.zeros(supervisor.VOCAB, dtype=np.int64)
    tokens = np.zeros((sum(COUNTS[1:]), WIDTH), dtype=np.int64)
    documents = np.full_like(tokens, -1)
    decimals = np.zeros(tokens.shape, dtype=np.bool_)
    languages, positions, omitted = {}, [], []
    for index, (number, text) in enumerate(selected):
        encoded = tokenizer.encode(text, add_special_tokens=False)
        ids = encoded.ids[:WIDTH]
        if index < COUNTS[0]:
            reference += np.bincount(ids, minlength=supervisor.VOCAB)
            continue
        positions.append(number)
        if len(ids) < 3 or 13 in ids:
            omitted.append(number)
            continue
        at = index - COUNTS[0]
        tokens[at, :len(ids)] = ids
        documents[at, :len(ids)] = number
        decimals[at, :len(ids)] = lexical.decimal_token_flags(text, encoded.offsets[:WIDTH])
        languages[number] = script_bucket(text)

    arrays = directory / "audit.npz"
    np.savez(arrays, tokens=tokens, documents=documents, decimals=decimals, reference=reference)
    prior = readback.previous.read(readback.pair.OUT / "readback.json")
    checkpoint = prior["arms"][POLICY]
    pins = readback.previous.frozen.audit.Inputs()
    for file in (Path(__file__), Path(lexical.__file__), Path(position.__file__),
                 v11.ROOT / "tinylm/train/adaptive_masking.py", v11.ROOT / "tinylm/train/hybrid_mntp.py"):
        pins.add(file)
    pins.add(v11.ROOT / checkpoint["checkpoint"], checkpoint["checkpoint_sha256"])
    profile = directory / "profile.json"
    supervisor.publish(profile, dict(arrays_sha256=supervisor.file_sha(arrays), corpus=audit["source_sha256"],
        reference_positions=[number for number, _ in selected[:COUNTS[0]]], probe_positions=positions,
        languages=languages, omitted=omitted, pins=pins.files, width=WIDTH, counts=COUNTS, mask_rate=0.15))
    return profile, supervisor.file_sha(profile)


def worker(path, sha256, _resume, record, cutoff):
    profile = json.loads(supervisor.manifest_bytes(path, sha256))
    arrays = path.with_name("audit.npz")
    if supervisor.file_sha(arrays) != profile["arrays_sha256"]:
        raise ValueError("the sealed sample changed")
    pins = readback.previous.frozen.audit.Inputs()
    for item, fields in profile["pins"].items():
        pins.add(v11.ROOT / item, fields["sha256"])
    with np.load(arrays, allow_pickle=False) as saved:
        tokens, documents, decimals, reference = (torch.from_numpy(saved[key]) for key in ("tokens", "documents", "decimals", "reference"))
    model, _ = readback.previous.load_model(torch, pins, POLICY)
    # Select the existing fixed G4 training route accepted by explicit document visibility.
    model.cfg.infer_repeat = 1.0
    if len(model.visit_schedule()) != 28:
        raise ValueError("the fixed document-visible G4 must keep its 28 visits")
    import time

    torch.set_num_threads(2)
    config = PolicyConfig(vocab_size=supervisor.VOCAB, mask_rate=0.15, ema=0.2, refresh_updates=2,
        unseen_policy="keep", seed=1337, special_max=34, mask_id=13,
        corpus_sha256=profile["corpus"]["text"].upper(), run_sha256=supervisor.file_sha(Path(__file__)).upper())
    policy = HardMaskPolicy(config)
    trained_observations = 0
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        for index, start in enumerate(range(0, COUNTS[1], 8)):
            if time.time() >= cutoff:
                raise TimeoutError("the frozen observation window ended")
            rows = slice(start, start + 8)
            policy.begin_update(index, split="train", expected_observations=1)
            selected, _ = policy.select(tokens[rows], documents[rows], adaptive=False)
            batch = mntp_batch(tokens[rows], documents[rows], selected, vocab_size=config.vocab_size)
            logits = model(batch.inputs.cuda(), attention_mask=batch.attention_mask.cuda(), allow_fixed_g4_r2=True)
            policy.observe(batch, logits.argmax(-1).cpu(), observation_index=0)
            trained_observations += batch.target_count
            policy.finish_update(accepted=True)

    holdout = slice(COUNTS[1], None)
    outcomes = {}
    for mode in ("uniform", "adaptive"):
        candidate = HardMaskPolicy(config)
        candidate.load_state_dict(policy.state_dict())
        candidate.begin_update(COUNTS[1] // 8, split="train", expected_observations=1)
        selected, probabilities = candidate.select(tokens[holdout], documents[holdout], adaptive=mode == "adaptive")
        outcomes[mode] = lexical.audit_mntp_bias(tokens[holdout], documents[holdout], selected, probabilities,
            decimals=decimals[holdout], document_languages={int(key): value for key, value in profile["languages"].items()},
            reference_counts=reference, rare_max_count=2, config=config, comparison_dtype=candidate.draw_dtype)
    pins.unchanged()
    supervisor.publish(record / "report.json", dict(profile=profile, outcomes=outcomes,
        frozen_mntp_observed_targets=trained_observations, classifier="HANGUL_AND_ASCII_LETTER_PROXIES",
        reference_rare_max_count=2, optimizer_updates=0, official_train_admitted=False, causal_quality_evaluated=False,
        visit_route="FIXED_G4_R2_EXPLICIT_VISIBILITY", visits=len(model.visit_schedule())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    args = parser.parse_args()
    with TemporaryDirectory(prefix="p107_v11_mask_selection_") as directory:
        path, checksum = prepare(Path(directory))
        if args.mode == "check":
            receipt = json.loads(path.read_bytes())
            print("P107_MASK_CHECK", receipt["counts"], "omitted", len(receipt["omitted"]))
            return 0
        stop_by = min(END, datetime.now().astimezone() + timedelta(minutes=4))
        with patch.object(supervisor, "gpu_worker", worker):
            return supervisor.supervise(path, checksum, False, OUT, stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
