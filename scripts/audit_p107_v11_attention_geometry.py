"""Count the document-local attention pairs on the fixed v1.1 draw schedule."""

import json
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from scripts import run_p107_v11_mask_pair as pair


INDEX_ROOT = Path(__file__).resolve().parents[1] / "test_result/evidence/p107_v11_binary_documents_v1_20261121"
PROFILE = INDEX_ROOT / "profile.json"
PROFILE_SHA = "01429D19DC7919EAE95EC81045F12AC924618F2A4A0BCAD2D2BE14C99F858079"
OUT = INDEX_ROOT.with_name("p107_v11_attention_geometry_cpu_20261121")


def scheduled_starts(tokens, updates, micros, seed):
    rng = torch.Generator(device="cpu").manual_seed(seed)
    return np.stack([torch.randint(tokens - pair.LENGTH - 1, (micros, pair.BATCH, 1),
                                   generator=rng).numpy()[..., 0] for _ in range(updates)])


def geometry(starts, ends):
    width = pair.LENGTH
    stop = starts + width
    first = np.searchsorted(ends, starts, side="left")
    last = np.searchsorted(ends, stop - 1, side="left")
    left = np.minimum(stop, ends[first] + 1) - starts
    right = stop - (ends[np.maximum(last - 1, 0)] + 1)
    doc_lengths = np.diff(ends, prepend=-1)
    squares = np.concatenate(([0], np.cumsum(np.square(doc_lengths), dtype=np.int64)))
    inner = np.where(first != last, squares[last] - squares[first + 1], 0)
    local_pairs = left**2 + np.where(first != last, right**2, 0) + inner
    document_counts = last - first + 1
    sample = np.unique([0, starts.size // 2, starts.size - 1, int(document_counts.argmax()),
                        int(local_pairs.argmin())])
    for position in sample:
        ids = np.searchsorted(ends, starts.flat[position] + np.arange(width), side="left")
        _, counts = np.unique(ids, return_counts=True)
        if document_counts.flat[position] != len(counts) or local_pairs.flat[position] != counts @ counts:
            raise ValueError("span arithmetic differs from the literal visibility geometry")
    return document_counts, local_pairs


def summary(counts, local_pairs, *, causal):
    width = pair.LENGTH
    total_local = int(local_pairs.sum())
    dense = counts.size * width**2
    allowed = (total_local + counts.size * width) // 2 if causal else total_local
    unsegmented_allowed = (dense + counts.size * width) // 2 if causal else dense
    return dict(windows=counts.size, micros=counts.size // pair.BATCH,
                single_document_windows=int(np.count_nonzero(counts == 1)),
                all_single_document_micros=int(np.count_nonzero(np.all(counts == 1, axis=-1))),
                maximum_documents_in_window=int(counts.max()), document_spans=int(counts.sum()),
                dense_positions=dense, local_span_positions=total_local,
                local_span_fraction=total_local / dense, allowed_pairs=allowed,
                unsegmented_allowed_pairs=unsegmented_allowed,
                allowed_fraction=allowed / unsegmented_allowed)


def count_split(receipt, *, updates, micros, seed):
    index = receipt["index"]
    path = pair.evaluation.regular_file(INDEX_ROOT / Path(index["path"]).name)
    if pair.documents.pin(path) != index:
        raise ValueError("the admitted EOS index changed")
    raw = np.load(path, mmap_mode="r", allow_pickle=False)
    ends = raw.astype(np.int64)
    if (raw.shape != (receipt["documents"],) or raw.dtype != np.dtype("<u4")
            or ends[-1] + 1 != receipt["tokens"] or not np.all(np.diff(ends, prepend=-1) > 0)):
        raise ValueError("the admitted EOS index does not delimit the declared corpus")
    starts = scheduled_starts(receipt["tokens"], updates, micros, seed)
    counts, local = geometry(starts, ends)
    if pair.documents.pin(path) != index:
        raise ValueError("the admitted EOS index changed during measurement")
    return counts, local


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    started = perf_counter()
    torch.set_num_threads(1)
    profile = json.loads(pair.supervisor.manifest_bytes(PROFILE, PROFILE_SHA))
    training = count_split(profile["splits"]["train"], updates=pair.STEPS, micros=pair.MICROS, seed=pair.SEED)
    validation = count_split(profile["splits"]["val"], updates=1, micros=16, seed=99)
    phase = pair.MICROS // 2
    report = dict(profile_sha256=PROFILE_SHA, runner_sha256=pair.evaluation.core6.digest(Path(pair.__file__)),
                  source_sha256=pair.evaluation.core6.digest(Path(__file__)), width=pair.LENGTH,
                  causal=summary(*(data[:, :phase] for data in training), causal=True),
                  mntp=summary(*(data[:, phase:] for data in training), causal=False),
                  validation=summary(*validation, causal=True), seconds=perf_counter() - started)
    OUT.mkdir(exist_ok=False)
    pair.supervisor.publish(OUT / "report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
