"""Read the render, operand coverage and answer form of the v2 addition exposures."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import numpy as np
from tokenizers import Tokenizer

from scripts import audit_p109c_english_operation_coverage as audit


ROOT = audit.comparison.ROOT
COVERAGE = ROOT / "handoff/audit/P109C_ENGLISH_OPERATION_COVERAGE_20261124.json"
OPERAND = re.compile(r"[0-9]+")
INT_ANSWER = re.compile(r"(?:(Answer)\s*:\s*)?([+-]?[0-9]+)\s*\.?", re.I)


def preferred_answer(text, expected):
    if pair := INT_ANSWER.fullmatch(text.strip()):
        form = "prefixed" if pair[1] else "bare"
        return f"{form}_{'correct' if int(pair[2]) == expected else 'incorrect'}"
    return "multi_token_explanation_or_other"


def verify():
    native = audit.native
    anchor = native.prep.read_json(COVERAGE)
    bundle = native.inputs.mixed.Bundle(native.inputs.MANIFEST, anchor["admitted_course"]["input_manifest_sha256"])
    tok = Tokenizer.from_file(str(native.prep.TOKENIZER))
    by_lane, by_render = defaultdict(Counter), defaultdict(Counter)
    by_digits, seen, prompts = Counter(), Counter(), set()

    for lane, metadata in enumerate(bundle.manifest["lanes"]):
        lane_name = metadata["name"]
        for slot, pack in enumerate(bundle.data[lane]):
            x, target, segments = pack.transpose(1, 0, 2)
            kinds = native.base.label_kinds(target, segments)
            relation = native.supervised.relation
            groups = relation.relation_groups_for(bundle.aux[lane][slot], native.prep.BATCH)
            relation.keep_relation_winners(kinds, segments, groups)
            pending = []
            for row, start in zip(*np.where(kinds == 1), strict=True):
                stops = np.flatnonzero(segments[row, :start + 1] != segments[row, start])
                left = int(stops[-1] + 1) if len(stops) else 0
                pending.append((row, start, x[row, left:start + 1].tolist()))
            if not pending:
                continue
            decoded = tok.decode_batch([tokens for _, _, tokens in pending], skip_special_tokens=False)
            for (row, start, _), transcript in zip(pending, decoded, strict=True):
                match = audit.ROLE.findall(transcript)
                if not match:
                    continue
                prompt = match[-1].strip()
                add = audit.PATTERNS["addition"].search(prompt)
                if add is None:
                    continue
                a, b = map(int, OPERAND.findall(add[0]))
                response_end = np.flatnonzero(kinds[row, start + 1:] != 2)
                end = int(start + 1 + response_end[0]) if len(response_end) else kinds.shape[1]
                answer = tok.decode(target[row, start:end].tolist(), skip_special_tokens=False)
                form = preferred_answer(answer, a + b)
                verb = add[0].split()[0].lower()
                notation = "symbol" if "+" in add[0] else "word"
                by_lane[lane_name][form] += 1
                by_render[f"{verb}/{notation}"][form] += 1
                by_digits[f"{len(str(a))}+{len(str(b))}"] += 1
                seen[tuple(sorted((a, b)))] += 1
                prompts.add(prompt)
    frozen = audit.comparison.panel.build("final")
    if audit.comparison.panel.digest(frozen).upper() != anchor["final200_sha256"]:
        raise ValueError("the frozen evaluation panel changed")
    case_ids = {row["id"] for row in anchor["frozen_response_pairs"]["addition"]}
    examples = {}
    for row in frozen:
        if row["id"] not in case_ids:
            continue
        pair = tuple(sorted(map(int, OPERAND.findall(row["prompt"]))))
        examples[row["id"]] = dict(operands=pair, exposures_for_pair=seen[pair])
    expected = anchor["admitted_course"]["operation_hits"]["inherited_v2"]["addition"]
    if expected != dict(exposures=seen.total(), distinct=len(prompts)) or len(examples) != len(case_ids):
        raise ValueError("the original v2 and inherited addition tallies do not reconcile")
    bundle.unchanged()
    return dict(status="V2_ADDITION_FORMATS_CPU_VERIFIED", manifest_sha256=bundle.digest,
                initial_coverage=audit.comparison.source(COVERAGE),
                source=audit.comparison.source(Path(__file__).resolve()), totals=expected,
                by_lane=dict(by_lane), by_render=dict(by_render), by_operand_digits=dict(by_digits),
                final_operand_pairs=examples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify()
    with args.output.open("x", encoding="utf-8") as stream:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)
    print(result["status"], result["totals"], flush=True)


if __name__ == "__main__":
    main()
