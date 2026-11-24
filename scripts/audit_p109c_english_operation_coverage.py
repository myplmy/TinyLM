"""Count explicit English operation instructions at the admitted answer starts."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import re

import numpy as np
from tokenizers import Tokenizer

from scripts import audit_p109c_frozen_model_comparison as comparison
from scripts import p109c_native_curriculum as native


ROLE = re.compile(r"<\|im_start\|>user\n(.*?)<\|im_end\|>", re.DOTALL)
LIST = re.compile(r"\b(?:list|sequence|in order|following|these|ordered)\b", re.IGNORECASE)
PATTERNS = {
    "copy_code": re.compile(r"\b(?:copy|print|output|write|return)\b[^.!?\n]{0,70}"
                            r"\b(?:storage|access|reference|item|product|tracking)\s+code\b", re.I),
    "uppercase": re.compile(r"\b(?:convert|change|write|output|return|put|make|transform)\b[^.!?\n]{0,80}"
                            r"\b(?:upper[ -]?case|capital letters)\b", re.I),
    "last_number": re.compile(r"\b(?:write|return|give|select|pick|which|what|find|output)\b"
                              r"[^.!?\n]{0,40}\blast\s+(?:number|integer|value)\b", re.I),
    "last_name": re.compile(r"\b(?:write|return|give|select|pick|which|what|find|output)\b"
                            r"[^.!?\n]{0,40}\b(?:last|final)\s+(?:name|person)\b", re.I),
    "addition": re.compile(r"\b(?:(?:what is|calculate|compute|evaluate|find)\s+\d+\s*(?:\+|plus\b)"
                           r"|(?:add|sum of)\s+\d+\s+(?:and|to)\b)\s*\d+", re.I),
    "multiplication": re.compile(r"\b(?:(?:what is|calculate|compute|evaluate|find)\s+\d+\s*(?:[×*]|times\b)"
                                 r"|(?:multiply|product of)\s+\d+\s+(?:and|by)\b)\s*\d+", re.I),
    "boolean": re.compile(r"\bA\s+(?:is|=)\s*(?:true|false)\b.{0,35}\bB\s+(?:is|=)\s*(?:true|false)\b"
                           r".{0,90}\b(?:AND|OR|XOR|NOT)\b"),
    "add_then_remove": re.compile(r"\badd\s+\d+\b[^.!?\n]{0,55}\b(?:then\s+)?(?:remove|take out)\s+\d+\b", re.I),
}
ORDER = {
    "extract": ("copy_code", "uppercase", "last_number", "last_name"),
    "reasoning": ("addition", "multiplication", "boolean", "add_then_remove"),
}


def observed(prompt, operation):
    ordering = operation in {"last_name", "last_number"}
    return bool(PATTERNS[operation].search(prompt) and (not ordering or LIST.search(prompt)))


def panel_readback(frozen, archives):
    v2, v2_truth, _, _ = archives["tinylm_v2"]
    _, qwen_truth, _, _ = archives["qwen3508"]
    rows = {row["id"]: row for row in v2}
    baseline = set(v2_truth["en"]["usable"])
    comparator = set(qwen_truth["en"]["usable"])
    answer = {key: [] for key in PATTERNS}
    for row in frozen:
        category, item = row["category"], row["id"]
        if row["language"] != "en" or category not in ORDER:
            continue
        key = ORDER[category][int(item.rsplit("_", 1)[1]) % 4]
        record = rows[item]
        if (record["prompt"] != row["prompt"] or record["reference"] != row["reference"]
                or not observed(row["prompt"], key)):
            raise ValueError(f"the operation rule did not cover the canonical archive item {item}")
        answer[key].append(dict(id=item, reference=row["reference"], v2_answer=record["answer"],
                                v2_stop=record["metadata"]["finish_reason"], v2_usable=item in baseline,
                                qwen_usable=item in comparator))
    if any(len(rows) != 5 for rows in answer.values()):
        raise ValueError("each observed FINAL200 operation requires its five frozen cases")
    return answer


def course_readback(deadline, frozen):
    bundle, layout = native.inputs.load_inputs()
    driver = native.supervised
    slots = driver.terms.BilingualSlots(bundle, layout["layout_sha256"])
    tokenizer = Tokenizer.from_file(str(native.prep.TOKENIZER))
    had_prompt = {row["prompt"]: row["id"] for row in frozen}
    totals, unpacked, contamination = Counter(), Counter(), Counter()
    hits, distinct = defaultdict(Counter), defaultdict(lambda: defaultdict(set))
    pending = []

    def consume():
        for (group, _), text in zip(pending, tokenizer.decode_batch(
                [ids for _, ids in pending], skip_special_tokens=False), strict=True):
            messages = ROLE.findall(text)
            if not messages:
                unpacked[group] += 1
                continue
            prompt = messages[-1].strip()
            item = had_prompt.get(prompt)
            if item:
                contamination[item] += 1
            for operation in PATTERNS:
                if observed(prompt, operation):
                    hits[group][operation] += 1
                    distinct[group][operation].add(prompt)
        pending.clear()

    for address, row in enumerate(bundle.schedule):
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("the authorized coverage audit passed its deadline")
        for lane, index in row[row[:, 0] >= 0]:
            x, _, batch = driver.course_microbatch(bundle, slots, address, lane, index)
            group = "bilingual_addition" if lane == slots.lane else "inherited_v2"
            starts = np.zeros_like(batch.segments)
            columns = np.arange(1, starts.shape[1])
            starts[:, 1:] = np.where(batch.segments[:, 1:] != batch.segments[:, :-1], columns, 0)
            np.maximum.accumulate(starts, axis=1, out=starts)
            for line, end in zip(*np.where(batch.kinds == 1), strict=True):
                pending.append((group, x[line, starts[line, end]:end + 1].tolist()))
                totals[group] += 1
            if len(pending) >= 512:
                consume()
        if address + 1 in (512, 1024, 2048):
            print("updates reviewed", address + 1, "answer starts", totals.total(), flush=True)
    consume()
    expected = native.prep.read_json(native.inputs.V2_ONLY_AUDIT)["targets"]["answer_start"]
    if totals.total() != expected or totals["bilingual_addition"] != 2 * layout["bilingual_pairs"]:
        raise ValueError("the scan lost admitted answer-start positions")
    bundle.unchanged()
    return dict(input_manifest_sha256=bundle.digest, layout_sha256=layout["layout_sha256"],
                tokenizer_sha256=bundle.manifest["tokenizer_sha256"], updates=bundle.steps,
                answer_starts=dict(totals), no_user_role=dict(unpacked), exact_final_prompt_ids=dict(contamination),
                operation_hits={group: {op: dict(exposures=hits[group][op], distinct=len(distinct[group][op]))
                                        for op in PATTERNS} for group in totals})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None:
        parser.error("--stop-by requires an explicit time zone")
    frozen = comparison.panel.build("final")
    stamp = comparison.panel.digest(frozen).upper()
    archives, rubric = comparison.comparator_sources(stamp)
    rows = panel_readback(frozen, archives)
    exposures = course_readback(args.stop_by, frozen)
    result = dict(status="CPU_ENGLISH_OPERATION_COVERAGE_VERIFIED", source=comparison.source(Path(__file__).resolve()),
                  final200_sha256=stamp, rubric_sha256=rubric, source_archives={
                      name: archives[name][3] for name in ("tinylm_v2", "qwen3508")},
                  operation_patterns={name: dict(pattern=rule.pattern, flags=rule.flags)
                                      for name, rule in PATTERNS.items()},
                  list_required_pattern=LIST.pattern, frozen_response_pairs=rows, admitted_course=exposures)
    with args.output.open("x", encoding="utf-8") as stream:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)
    print(result["status"], exposures["answer_starts"], flush=True)


if __name__ == "__main__":
    main()
