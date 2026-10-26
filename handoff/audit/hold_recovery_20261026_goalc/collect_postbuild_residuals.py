"""Locate all newly adopted rare structural signals in a completed cache.

Literal signals select context checks; they do not classify every match as bad.
The already preserved baseline is reported separately and never edited here.
"""
from pathlib import Path
import argparse
import json
import sys
import re

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_corpus_cache as cache
from scripts import p106b_hold_recovery as recovery
from scripts.p106b_native_text_audit import write_json, file_sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", default="cache_v3")
    parser.add_argument("--receipt-name", default="postbuild_rare_residuals_v1")
    args = parser.parse_args()
    assert all(v.isascii() and v.replace("_", "").isalnum() for v in (args.output_name, args.receipt_name))
    out = recovery.BASE / args.output_name
    built = cache.read(out / "built.json")
    found = []
    counts = {}
    for split in ("val", "train"):
        for row in cache.rows(out / "text" / split, built["manifests"]["text_" + split]):
            if row["parent_decision"] != "HOLD":
                continue
            text = row["text"]
            info, _ = cache.signals(text)
            keys = [k for k in ["empty_or_adjacent_heading_lines", "wiki_markup_openers", "html_tag_occurrences", "html_comment_openers"] if info.get(k)]
            if not keys:
                continue
            contexts = []
            for pattern in [r"\[\[|\{\{", r"</?[a-zA-Z][a-zA-Z0-9-]*(?:\s+[^<>]*?)?/?>", r"<!--"]:
                for match in re.finditer(pattern, text):
                    contexts.append(text[max(0, match.start() - 110):match.end() + 160])
            if info.get("empty_or_adjacent_heading_lines"):
                contexts.append(text[-1800:])
            found.append(dict(id=row["id"], source=row["source"], source_ids=row["source_ids"],
                source_ids_sha256=row["source_ids_sha256"], original_text_sha256=row["original_text_sha256"],
                clean_text_sha256=row["clean_text_sha256"], decision=row["decision"], signals={k: info[k] for k in keys},
                manual=row.get("manual"), contexts=contexts))
            for key in keys:
                counts[key] = counts.get(key, 0) + 1
    target = Path(__file__).with_name(args.receipt_name + ".json")
    write_json(target, dict(schema="P106B_POSTBUILD_RARE_CONTEXT_CANDIDATES_V1", cache=args.output_name,
        built_sha256=file_sha(out / "built.json"), rows=found, counts=counts,
        baseline_adopted_texts_unchanged=True, signals_are_not_errors=True))
    print(json.dumps(dict(rows=len(found), counts=counts, cases=[dict(id=r["id"], signals=r["signals"]) for r in found]), ensure_ascii=False))


if __name__ == "__main__":
    main()
