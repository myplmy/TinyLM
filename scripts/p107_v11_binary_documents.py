"""Read the sealed uint16 v1.1 cache as explicit document-isolated windows."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from scripts import eval_p109c_completed as evaluation
from scripts import run_p109c_scratch330 as training


SPLITS = ("train", "val")
EOS, MASK = 2, 13


def pin(path):
    stamp = training.file_stamp(evaluation.regular_file(path))
    return dict(path=str(path), bytes=stamp[2], sha256=evaluation.core6.digest(path))


def write_index(path, output, expected_tokens, expected_documents):
    values = np.memmap(path, mode="r", dtype="<u2")
    if len(values) != expected_tokens or values[-1] != EOS:
        raise ValueError("the exact split length and terminal EOS are required")
    ends, mask_tokens, high_token = [], 0, 0
    stride = 8_388_608
    for start in range(0, len(values), stride):
        block = values[start:start + stride]
        ends.append((np.flatnonzero(block == EOS) + start).astype("<u4"))
        mask_tokens += int(np.count_nonzero(block == MASK))
        high_token = max(high_token, int(block.max()))
    ends = np.concatenate(ends)
    if (len(ends) != expected_documents or high_token >= training.VOCAB
            or ends[0] < 1 or np.any(np.diff(ends) < 2)):
        raise ValueError("the separate cache EOS count, vocabulary or document shape differs")
    with output.open("xb") as stream:
        np.save(stream, ends, allow_pickle=False)
    return dict(documents=len(ends), tokens=len(values), literal_mask_tokens=mask_tokens,
                max_document_tokens=max(int(ends[0]) + 1, int(np.diff(ends).max(initial=0))), index=pin(output))


def build_profile(parent, output):
    cache = parent["cache"]
    directory = Path(cache["cache_dir"])
    metadata_path = directory / "meta.json"
    metadata = evaluation.read_json(evaluation.regular_file(metadata_path))
    if (metadata["raw_manifest_sha256"] != "6DD3833367DB576660B88226D6C9765992AE3CB8A7387764DC160F04EC7E80EF"
            or metadata["tokenizer_sha256"] != evaluation.TOKENIZER_SHA
            or metadata["complete_train_val_overlap"] != 0 or metadata["eos_id"] != EOS
            or metadata["token_dtype"] != "uint16" or metadata["dir"] != str(directory)):
        raise ValueError("the exact adopted split release is required")
    output.mkdir(exist_ok=False)
    receipts = {}
    for split in SPLITS:
        path = directory / f"{split}.bin"
        bound = pin(path)
        stamp = training.file_stamp(path)
        if bound["sha256"] != cache["files"][f"{split}.bin"]["sha256"]:
            raise ValueError(f"the admitted {split} bytes changed")
        receipt = write_index(path, output / f"{split}_ends.npy", metadata[split], metadata[f"{split}_documents"])
        if training.file_stamp(path) != stamp:
            raise ValueError(f"the admitted {split} changed during indexing")
        receipt["binary"] = bound
        receipts[split] = receipt
    profile = dict(schema="P107_V11_BINARY_DOCUMENTS_V1", source_release_sha256=metadata["raw_manifest_sha256"],
                   tokenizer_sha256=evaluation.TOKENIZER_SHA, input_cache_sha256=cache["identity_sha256"],
                   sources={"scripts/p107_v11_binary_documents.py": evaluation.core6.digest(Path(__file__))},
                   splits=receipts)
    training.publish(output / "profile.json", profile)
    return profile


class BinaryDocumentSource:
    """One immutable read-only data/index pair with a replayable crop order."""

    def __init__(self, receipt, *, batch, micros, length, seed):
        self.bound = tuple(receipt[name] for name in ("binary", "index"))
        self.stamps = tuple(training.file_stamp(Path(item["path"])) for item in self.bound)
        for item, stamp in zip(self.bound, self.stamps, strict=True):
            if item["bytes"] != stamp[2] or pin(Path(item["path"])) != item:
                raise ValueError("the sealed binary windows or index changed")
        self.data = np.memmap(self.bound[0]["path"], mode="r", dtype="<u2")
        self.ends = np.load(self.bound[1]["path"], mmap_mode="r", allow_pickle=False)
        if (self.ends.dtype != np.dtype("<u4") or self.ends.shape != (receipt["documents"],)
                or self.ends[-1] != len(self.data) - 1 or len(self.data) != receipt["tokens"]
                or len(self.data) <= length + 1 or receipt["literal_mask_tokens"] != 0
                or min(batch, micros) < 1 or length < 2):
            raise ValueError("the explicit document index, recipe, or reserved mask support differs")
        self.batch, self.micros, self.length = batch, micros, length
        self.relative_positions = np.arange(length + 1, dtype=np.int64)
        self.rng = torch.Generator(device="cpu").manual_seed(seed)
        self.corpus_sha256 = self.bound[0]["sha256"]
        self.cursor = 0
        recipe = dict(corpus_sha256=self.corpus_sha256, ends_sha256=self.bound[1]["sha256"],
                      batch=batch, micros=micros, sequence=length, seed=seed)
        self.signature = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest().upper()

    def unchanged(self):
        if tuple(training.file_stamp(Path(item["path"])) for item in self.bound) != self.stamps:
            raise ValueError("a sealed document source file was replaced or changed")

    def state_dict(self):
        self.unchanged()
        return dict(signature=self.signature, cursor=self.cursor, rng=self.rng.get_state())

    def load_state_dict(self, state):
        self.unchanged()
        if (state["signature"] != self.signature or type(state["cursor"]) is not int or state["cursor"] < 0):
            raise ValueError("the document source recipe or committed cursor differs")
        self.rng.set_state(state["rng"])
        self.cursor = state["cursor"]

    def next_update(self):
        before = self.state_dict()
        try:
            starts = torch.randint(len(self.data) - self.length - 1,
                                   (self.micros, self.batch, 1), generator=self.rng).numpy()
            positions = starts + self.relative_positions
            ids = torch.from_numpy(self.data[positions].astype(np.int64))
            docs = torch.from_numpy(np.searchsorted(self.ends, positions, side="left"))
            self.unchanged()
        except BaseException:
            self.load_state_dict(before)
            raise
        self.cursor += 1
        return list(zip(ids.unbind(), docs.unbind(), strict=True))


def check_windows(profile):
    from tinylm.train.hybrid_mntp import causal_batch, eligible_mntp

    measurements = {}
    for split, receipt in profile["splits"].items():
        source = BinaryDocumentSource(receipt, batch=4, micros=32, length=1024, seed=1337)
        before = source.state_dict()
        first = source.next_update()
        source.load_state_dict(before)
        second = source.next_update()
        for (x, d), (xx, dd) in zip(first, second, strict=True):
            if not torch.equal(x, xx) or not torch.equal(d, dd) or not torch.equal(x[:, :-1] == EOS, d[:, 1:] != d[:, :-1]):
                raise ValueError("window replay or EOS/document adjacency differs")
        ntp = sum(causal_batch(x, d, vocab_size=training.VOCAB).target_count for x, d in first[:16])
        mntp = sum(int(eligible_mntp(x, d, vocab_size=training.VOCAB).sum()) for x, d in first[16:])
        measurements[split] = dict(checked_microbatches=len(first), causal_targets=ntp, eligible_mntp=mntp,
                                   same_replay=True, full_input_slots=4*32*1024)
    return measurements


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-record", required=True, type=Path)
    parser.add_argument("--training-manifest-sha256", required=True)
    parser.add_argument("--record", required=True, type=Path)
    args = parser.parse_args()
    torch.set_num_threads(1)
    parent = evaluation.training_input(args.training_record.absolute(), args.training_manifest_sha256)
    profile = build_profile(parent, args.record.absolute())
    measurements = check_windows(profile)
    training.publish(args.record / "window_check.json", measurements)
    print("P107_V11_BINARY_WINDOWS", measurements, flush=True)


if __name__ == "__main__":
    main()
