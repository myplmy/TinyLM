"""Replay a fixed next-question boundary and audit termination in archived FINAL200 outputs."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from scripts import p106b_final_holdout as panel


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_result" / "evidence"
EXTERNAL = EVIDENCE / "p109c_external_final200_v1_20261124"
TINYLM = EVIDENCE / "p109c_v2_common_eval_run1_20261123"
MODELS = ("gemma270", "qwen3508", "bonsai2b", "tinylm_v2")
NEXT_QUESTION = re.compile(r"^[ \t]*(?:Question|질문):", re.MULTILINE)
RUBRIC_KEYS = ("stable", "responsive", "correct", "usable")


def pinned_json(path, expected):
    source = path.read_bytes()
    if sha256(source).hexdigest().upper() != expected:
        raise ValueError(f"the reference artifact changed: {path}")
    return json.loads(source)


def pinned_rows(path, expected):
    source = path.read_bytes()
    if sha256(source).hexdigest().upper() != expected:
        raise ValueError(f"the frozen response shard changed: {path}")
    return [json.loads(line) for line in source.splitlines()]


def evidence(model, external, own):
    if model == "tinylm_v2":
        record = own
        rubric = own["semantic_true_ids"]
        counts = own["counts"]
        asset = None
        src = TINYLM / record["source_file"]
    else:
        record = external["models"][model]
        rubric = {lang: item["semantic_true_ids"] for lang, item in record["languages"].items()}
        counts = {lang: item["counts"] for lang, item in record["languages"].items()}
        receipt = pinned_json(ROOT / record["generation_receipt"], record["receipt_sha256"])
        if receipt["completed_rows"] != 200 or receipt["status"] != "RESPONSES_COMPLETE_SEMANTIC_REVIEW_NOT_RUN":
            raise ValueError("the evaluation must supply all original raw answers")
        asset = receipt["contract"]["model_spec"]
        src = ROOT / record["source_file"]
    return pinned_rows(src, record["source_sha256"]), rubric, counts, asset


def token_details(model, asset, ids):
    if model == "tinylm_v2":
        if ids != {4}:
            raise ValueError("the archived TinyLM ChatML run must use its single authorized end token")
        return dict(stops={"4": "<|im_end|>"}, sources={})
    if model == "bonsai2b":
        from scripts.diag_p106b_teacher_tokenizer_map import selected_metadata

        path = (ROOT / asset["weights"]["path"]).resolve(strict=True)
        if not path.is_relative_to((ROOT / "HF").resolve()) or path.stat().st_size != asset["weights"]["bytes"]:
            raise ValueError("the original Bonsai artifact must supply the tokenizer metadata")
        with path.open("rb") as stream:
            metadata, end = selected_metadata(stream)
            stream.seek(0)
            header_sha = sha256(stream.read(end)).hexdigest().upper()
        tokens = metadata["tokenizer.ggml.tokens"]
        return dict(stops={str(i): tokens[i] for i in sorted(ids)}, sources={str(path.relative_to(ROOT)): header_sha},
                    source_scope="GGUF_TOKENIZER_METADATA", eos_id=metadata.get("tokenizer.ggml.eos_token_id"))
    tokenizer = asset["tokenizer"]
    config = asset["config"]
    parsed = pinned_json(ROOT / tokenizer["path"], tokenizer["sha256"])
    values = {row["id"]: row["content"] for row in parsed["added_tokens"]}
    model_config = pinned_json(ROOT / config["path"], config["sha256"])
    eos = model_config.get("eos_token_id")
    wanted = set(ids)
    if isinstance(eos, int):
        wanted.add(eos)
    return dict(stops={str(i): values[i] for i in sorted(wanted)}, eos_id=eos,
                sources={tokenizer["path"]: tokenizer["sha256"], config["path"]: config["sha256"]})


def language_stats(rows, decisions):
    ids = {row["id"] for row in rows}
    flags = {key: set(decisions[key]) for key in RUBRIC_KEYS}
    if (len(ids) != 100 or any(not v <= ids for v in flags.values())
            or flags["usable"] != flags["stable"] & flags["responsive"] & flags["correct"]):
        raise ValueError("the archived semantic intersections must reproduce")
    existing = {key: len(value) for key, value in flags.items()}
    stable_only = (flags["correct"] & flags["responsive"]) - flags["stable"]
    counters, terminal, empty = Counter(), Counter(), Counter()
    gained, lost = [], []
    for row in rows:
        text, metadata = row["answer"], row["metadata"]
        tokens, stop = metadata["generated_ids"], metadata["terminal_ids"]
        capped = metadata["finish_reason"] == "MAX_NEW"
        if (len(tokens) != metadata["generated_tokens"] or capped != (not stop)
                or (capped and len(tokens) != panel.MAX_NEW) or (stop and tokens[-len(stop):] != stop)):
            raise ValueError("the raw token termination did not verify")
        before = panel.reference_match(text, row)
        if before is not row["reference_match"]:
            raise ValueError("the unchanged automatic reference match must reproduce")
        boundary = NEXT_QUESTION.search(text)
        prefix = text[:boundary.start()] if boundary else text
        # Select the delimiter before looking at any reference or semantic annotation.
        after = panel.reference_match(prefix, row)
        if before is False and after is True:
            gained.append(dict(id=row["id"], category=row["category"], capped=capped))
        if before is True and after is False:
            lost.append(row["id"])
        counters.update(dict(capped=capped, empty=not text.strip(), stopped=bool(stop),
                             question_boundary=bool(boundary), capped_with_question_boundary=capped and bool(boundary),
                             empty_before_question=bool(boundary) and not prefix.strip(),
                             think_open="<think>" in text, think_close="</think>" in text,
                             thought_without_close="<think>" in text and "</think>" not in text,
                             reference_rows=before is not None, exact_before=before is True, exact_prefix=after is True))
        terminal.update(stop)
        if not text.strip():
            empty[("_".join(map(str, stop)), len(tokens))] += 1
    return dict(original_semantic=existing, unqualified_only_by_stability=len(stable_only),
                content_correct_but_unstable=len(flags["correct"] - flags["stable"]), **dict(counters),
                terminal_ids=dict(terminal), empty_token_lengths=[dict(terminal=stop, generated_tokens=n, rows=count)
                            for (stop, n), count in sorted(empty.items())], new_exact_prefixes=gained, lost_exact_prefixes=lost)


def audit():
    e_file, t_file = EXTERNAL / "semantic_readback.json", TINYLM / "semantic_readback.json"
    ext, tiny = [json.loads(path.read_bytes()) for path in (e_file, t_file)]
    final = panel.build("final")
    if panel.digest(final).upper() != ext["frozen_final_sha256"] or ext["rubric_sha256"] != tiny["rubric_sha256"]:
        raise ValueError("the same canonical FINAL200 and original rubric must apply")
    rubric = ROOT / ext["rubric_file"]
    if sha256(rubric.read_bytes()).hexdigest().upper() != ext["rubric_sha256"]:
        raise ValueError("the recorded rubric changed")
    grouped = {}
    for model in MODELS:
        rows, decisions, counts, asset = evidence(model, ext, tiny)
        if len(rows) != len(final) or any(any(row[key] != val for key, val in baseline.items())
                                             for row, baseline in zip(rows, final, strict=True)):
            raise ValueError("the archived model did not use the same frozen rows")
        groups = {lang: language_stats([row for row in rows if row["language"] == lang], decisions[lang])
                  for lang in ("ko", "en")}
        all_tokens = {i for group in groups.values() for i in group["terminal_ids"]}
        for lang, group in groups.items():
            if model == "tinylm_v2":
                expected = group["original_semantic"] == counts[lang]
            else:
                expected = all(group[new] == counts[lang][recorded]
                               for new, recorded in (("capped", "capped"), ("empty", "empty"),
                                                     ("stopped", "stop"), ("exact_before", "reference_match")))
            if not expected:
                raise ValueError("the archived aggregate and raw output differ")
        grouped[model] = dict(languages=groups, token_details=token_details(model, asset, all_tokens))
    return dict(status="AUDITED_ORIGINAL_TERMINATION_AND_EXACT_PREFIX", frozen_final_sha256=ext["frozen_final_sha256"],
                archived_semantic_sha256={str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest().upper()
                                          for p in (e_file, t_file, rubric)}, modes=grouped,
                next_question_pattern=NEXT_QUESTION.pattern, archived_requests=4 * len(final),
                new_model_requests=0, scoring_use="RETROSPECTIVE_DIAGNOSTIC_ONLY")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    proof = audit()
    with args.receipt.open("x", encoding="utf-8") as output:
        json.dump(proof, output, ensure_ascii=False, allow_nan=False, indent=2)
        print(file=output)
    for name, model in proof["modes"].items():
        print(name, model["token_details"]["stops"],
              [(lang, row["capped"], row["empty"], row["exact_before"], row["exact_prefix"])
               for lang, row in model["languages"].items()])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
