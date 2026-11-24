"""Join sealed P079 IFEval replies to the original 541-key order on CPU."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from tokenizers import Tokenizer


ROOT = Path(__file__).resolve().parents[1]
TAG = "p106b_ifeval_p079_runtime1280_v1_20261120"
OUT = ROOT / "test_result/evidence" / TAG
SOURCE = ROOT / "data_cache/p106b_official_eval_assets/ifeval_google_966cd895_20261117/ifeval_input_data.jsonl"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768.json"
DATASET_SHA = "6A85310CA8CE15EFF755AA08A3A4FF931C7E273E7515EBB3C492EA85FD8288F2"
REVISION = "966cd89545d6b6acfd7638bc708b98261ca58e84"
ROWS, CAP, EOS = 541, 1280, 2


def file_bytes(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular evidence file: {path.name}")
    return path.read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def readback(out=OUT, source=SOURCE, tokenizer_path=TOKENIZER):
    profile_bytes = file_bytes(out / "profile.json")
    profile = json.loads(profile_bytes)
    source_bytes = file_bytes(source)
    if (profile["tag"] != TAG or profile["revision"] != REVISION or profile["rows"] != ROWS
            or profile["generation_cap"] != CAP or digest(source_bytes) != DATASET_SHA
            or digest(file_bytes(tokenizer_path)) != profile["pins"][TOKENIZER.relative_to(ROOT).as_posix()]):
        raise ValueError("IFEval source, tokenizer or generation contract differs")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    vocab_size = tokenizer.get_vocab_size()
    if vocab_size != 32768 or tokenizer.token_to_id("<eos>") != EOS:
        raise ValueError("The pinned tokenizer must use the original vocabulary and EOS")
    prompts = {row["key"]: row["prompt"] for row in map(json.loads, source_bytes.splitlines())}
    groups = profile["groups"]
    layout = {case["key"]: case["ids"] for batch in groups for case in batch}
    if (len(prompts) != ROWS or len(layout) != ROWS or sum(map(len, groups)) != ROWS
            or prompts.keys() != layout.keys() or max(map(len, layout.values())) + CAP != profile["capacity"]
            or any(tokenizer.encode(prompt, add_special_tokens=False).ids != layout[key]
                   for key, prompt in prompts.items())):
        raise ValueError("Sealed groups must cover each original prompt exactly")

    profile_sha = digest(profile_bytes)
    parts = sorted((out / "parts").glob("part_*.json"))
    if len(parts) > len(groups):
        raise ValueError("Too many published batches")
    predictions = {}
    part_hashes = {}
    n_eos = max_context = 0
    for i, path in enumerate(parts):
        part_bytes = file_bytes(path)
        part = json.loads(part_bytes)
        cases = groups[i]
        if (path.name != f"part_{i:03d}.json" or part["index"] != i or part["profile_sha256"] != profile_sha
                or [row["key"] for row in part["rows"]] != [case["key"] for case in cases]):
            raise ValueError(f"Batch metadata or ordering differs: {path.name}")
        actual_positions = []
        for row in part["rows"]:
            key, ids = row["key"], row["output_ids"]
            if (key in predictions or not isinstance(ids, list) or not 1 <= len(ids) <= CAP
                    or any(type(token) is not int or not 0 <= token < vocab_size for token in ids)
                    or EOS in ids[:-1] or row["prompt_tokens"] != len(layout[key])):
                raise ValueError(f"Repeated key or invalid token range in batch {i}")
            finish = "EOS" if ids[-1] == EOS else "MAX_NEW"
            if (row["finish"] != finish or (finish == "MAX_NEW" and len(ids) != CAP)
                    or tokenizer.decode(ids, skip_special_tokens=True) != row["answer"]):
                raise ValueError(f"Finish condition or response decode differs in batch {i}")
            predictions[key] = row["answer"]
            n_eos += finish == "EOS"
            actual_positions.append(len(layout[key]) + len(ids) - 1)
        if part["last_context"] != max(actual_positions):
            raise ValueError(f"Wrong final cached position in batch {i}")
        max_context = max(max_context, part["last_context"])
        part_hashes[path.name] = digest(part_bytes)

    ordered = [dict(key=key, response=predictions[key]) for key in prompts if key in predictions]
    return dict(
        profile_sha256=profile_sha, data_revision=REVISION, dataset_sha256=DATASET_SHA,
        total_rows=ROWS, verified_rows=len(ordered), published_parts=len(parts),
        n_eos=n_eos, n_max_new=len(ordered)-n_eos, actual_max_cached_positions=max_context,
        part_sha256=part_hashes, official_scores=None, responses=ordered,
    )


def publish_full(report, receipt):
    evidence = file_bytes(receipt)
    window = json.loads(evidence)
    fields = ("profile_sha256", "verified_rows", "published_parts", "n_eos", "n_max_new",
              "actual_max_cached_positions")
    if (receipt.parent != OUT or not receipt.name.startswith("window_")
            or report["verified_rows"] != ROWS or window["tag"] != TAG or not window["full_response_count"]
            or not window["state_restored"] or window["checkpoint_writes"] != 0
            or any(report[field] != window[field] for field in fields)):
        raise ValueError("The successful full GPU receipt and independently verified rows must agree")
    target = OUT / "official_response_index.json"
    payload = {**report, "full_window_file": receipt.name, "full_window_sha256": digest(evidence)}
    publish_json(target, payload)


def publish_json(target, payload):
    packed = (json.dumps(payload, ensure_ascii=False, allow_nan=False) + chr(10)).encode()
    with tempfile.NamedTemporaryFile(dir=target.parent) as temporary:
        temporary.write(packed)
        temporary.flush()
        os.fsync(temporary.fileno())
        try:
            os.link(temporary.name, target)
        except FileExistsError:
            if file_bytes(target) != packed:
                raise ValueError(f"Previously published evidence differs: {target.name}") from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish-from", type=Path, help="Full terminal GPU window receipt")
    args = parser.parse_args()
    report = readback()
    if args.publish_from is not None:
        publish_full(report, Path(os.path.abspath(args.publish_from)))
    print(json.dumps({k: v for k, v in report.items() if k not in ("part_sha256", "responses")}))
