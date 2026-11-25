"""Find short-input positive controls from actual long v3 arithmetic answer exposures."""

from argparse import ArgumentParser
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from time import time
from types import SimpleNamespace
import unicodedata

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import audit_p109c_answer_length_exposure as exposure
from scripts import diag_p109c_json_output_baseline_cpu as output
from tinylm.infer.generate import sample


BASE = output.baseline
REF = BASE.reference
OUT = REF.EVIDENCE / "p109c_v3_seen_long_arithmetic_cpu_20261126"
END = datetime.fromisoformat("2026-11-26T06:48:00+09:00")
PER_LANGUAGE = 12


class FrozenPrefix(BASE.first.DecodeSuffix):
    def encode(self, prompt):
        return SimpleNamespace(ids=self.input_ids)


def prepare(tokenizer):
    numbers = REF.completed.read_json(exposure.OUTPUT)
    if numbers["status"] != "COMPLETE_READ_ONLY_EXPOSURE" or numbers["checkpoint_sha256"] != REF.CHECKPOINT_SHA256:
        raise ValueError("the actual positive answer exposure must already be accounted for")
    old, bundle, slots, _ = exposure.integrated.prepare("original", "capped", "proportional", 0., True)
    if numbers["layout"] != old["signature"]["layout"]:
        raise ValueError("the counted long answers belong to another curriculum layout")
    names = {lane["name"]: index for index, lane in enumerate(bundle.manifest["lanes"])}
    cases = {}
    for lang in ("ko", "en"):
        name = f"verified_arithmetic_{lang}_plain"
        lane = names[name]
        exposures = 0
        candidates = {}
        for address, position in np.argwhere(bundle.schedule[:, :, 0] == lane).tolist():
            _, slot = bundle.schedule[address, position]
            x, y, batch = exposure.integrated.supervised.course_microbatch(bundle, slots, address, lane, slot)
            for row, kinds in enumerate(batch.kinds):
                lengths = exposure.lengths(kinds, batch.segments[row])
                starts, ends = np.flatnonzero(kinds == 1), np.flatnonzero(kinds == 3)
                for size, start, end in zip(lengths, starts, ends, strict=True):
                    if size < 12:
                        continue
                    exposures += 1
                    first = int(np.flatnonzero(batch.segments[row] == batch.segments[row, start])[0])
                    ids = x[row, first:start+1].tolist()
                    answer_ids = y[row, start:end].tolist()
                    if len(ids) + BASE.MAX_NEW > 1024 or int(y[row, end]) != 4:
                        raise ValueError("a saved arithmetic case exceeds the sealed context or lacks EOT")
                    stamp = sha256(json.dumps(ids).encode()).hexdigest().upper()
                    token_text = tokenizer.decode(ids, skip_special_tokens=False)
                    answer = tokenizer.decode(answer_ids, skip_special_tokens=False)
                    existing = candidates.get(stamp)
                    if existing and existing["answer_ids"] != answer_ids:
                        raise ValueError("one training input has different expected long answers")
                    if existing is None:
                        candidates[stamp] = dict(language=lang, id=stamp, address=address, slot=position, row=row,
                                                 question=token_text, ids=ids, answer_ids=answer_ids, expected=answer)
        if exposures != numbers["groups"][name]["at_least"]["12"]["exposures"] or len(candidates) < PER_LANGUAGE:
            raise ValueError("the long candidate denominator differs from the recorded exposure")
        cases[lang] = [candidates[key] for key in sorted(candidates)[:PER_LANGUAGE]]
    bundle.unchanged()
    return cases, old["signature"]["layout"]


def canonical(text):
    return unicodedata.normalize("NFC", text).strip()


def score(model, tokenizer, case):
    prompt = case["question"]
    capture = FrozenPrefix(tokenizer, case["ids"])
    _, meta = sample(model, model.cfg, capture, prompt, max_new=BASE.MAX_NEW, temperature=0., top_k=1,
                     device="cpu", eos_id=2, use_cache=True, logits_last_only=True,
                     return_metadata=True, stop_token_sequences=[[4]])
    answer, meta = BASE.manual.answer_from_tokens(tokenizer, case["ids"], case["ids"] + capture.ids, meta, BASE.MAX_NEW)
    exact = canonical(answer) == canonical(case["expected"])
    normal = meta["finish_reason"] in ("STOP_SEQUENCE", "EOS")
    content_ids = meta["generated_ids"][:meta["content_tokens"]]
    return dict(id=case["id"], language=case["language"], answer=answer, metadata=meta, exact=exact,
                exact_ids=content_ids == case["answer_ids"], usable=exact and normal and len(content_ids) >= 12)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 and a cutoff before the matched raw validation phase")
    cutoff = args.stop_by.timestamp()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    checkpoint = REF.checkpoint()
    tokenizer = BASE.completed.load_tokenizer()
    cases, layout = prepare(tokenizer)
    OUT.mkdir(exist_ok=False)
    inputs = OUT / "inputs.json"
    BASE.native.publish(inputs, dict(cases=cases, layout=layout, body_sha256=REF.CHECKPOINT_SHA256,
                                     observed_exposure_sha256=REF.file_sha(exposure.OUTPUT),
                                     source_sha256=REF.file_sha(Path(__file__)), max_new=BASE.MAX_NEW,
                                     selection="12 smallest distinct frozen prompt digests per language"))
    rows = []
    model = BASE.completed.load_model(checkpoint, 2942, "cpu")
    model.cfg.kv_dtype = "fp32"
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for pair in zip(cases["ko"], cases["en"], strict=True):
            for case in pair:
                if time() >= cutoff:
                    raise TimeoutError("the copied training answers reached the approved stop time")
                rows.append(score(model, tokenizer, case))
    if REF.file_sha(checkpoint) != REF.CHECKPOINT_SHA256:
        raise ValueError("the source v3 weights changed")
    counts = {lang: dict(exact=sum(row["exact"] for row in rows if row["language"] == lang),
                         exact_ids=sum(row["exact_ids"] for row in rows if row["language"] == lang),
                         usable=sum(row["usable"] for row in rows if row["language"] == lang)) for lang in cases}
    BASE.native.publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=REF.file_sha(inputs),
                                                  summary=counts, rows=rows,
                                                  interpretation="Observed training cases, not independent generalization"))
    print("P109C_SEEN_LONG_ARITHMETIC", json.dumps(counts), flush=True)


if __name__ == "__main__":
    main()
