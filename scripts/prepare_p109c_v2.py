"""Compile and seal the eligible P109C v2 curriculum and a fixed mixed schedule."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import numpy as np
from tokenizers import Tokenizer

from scripts import p106b_shards, p109_mix_masked_course as native_course
from scripts import run_p109c_scratch330 as v1
from tinylm.chat import normalize
from tinylm.data.sft import IGNORE
from tinylm.train.mtp_sft import encode_record


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_result/evidence"
HF = ROOT / "HF/sft_ready"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
TOKENIZER_SHA = "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
CACHE = ROOT / "data_cache/ko-en_p109c_adopted_v11_20261121_chat32"
INVENTORY = ROOT / "handoff/audit/P109C_V2_CURRICULUM_DEDUP_20261122.json"
AUTHORED = EVIDENCE / "p109c_authored_curriculum_correction_only_cpu_v1_20261121"
WIDTH, BATCH, ACCUM, WARMUP = 1024, 4, 32, 100
RAW_TOKENS = 300_023_808
END, EOS = 4, 2
SCHEMA = "P109C_V2_MIXED_SCHEDULE_V1"
DTYPE = np.dtype("<i2")
AUTHORED_COURSES = (
    ("verified_arithmetic", "p101a_sft_mtp_verified_direct_v3_s1337"),
    ("verified_arithmetic", "p101a_sft_mtp_verified_trace_v3_s1337"),
    ("value_binding", "p106b_binding_scale_v1_s1337"),
    ("value_binding", "p106b_binding_aux_v1_s1337"),
    ("value_binding", "p106b_binding_course_v1_s1337"),
    ("binding_arithmetic_and_state", "p106b_joint_decimal_v1_s1337"),
    ("state_update", "p106b_state_update_aux_v1_s1337"),
    ("code_replay", "p106b_context_replay_v2_s1337"),
    ("context_transfer", "p106b_context_broad_v2_s1337"),
    ("role_repair", "p106b_repair_role_v1_s1337"),
    ("evidence_recovery", "p106b_evidence_recovery_v1_s1337"),
    ("rule_transfer", "p106d_ruleviews_v1_s1337"),
    ("rule_transfer", "p106d_ruleviews_v3_length_s1337"),
)


def sha(path):
    return v1.file_sha(path).upper()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def text_signature(text):
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()


def row_signature(tokens):
    return hashlib.sha256(np.asarray(tokens, dtype=DTYPE).tobytes()).digest()


def content(message):
    value = message["content"]
    if isinstance(value, str):
        return value
    return "".join(part["text"] for part in value if part.get("type") == "text")


def verified_rows(path, pins):
    path = path.absolute()
    manifest = read_json(path)
    pins[str(path.relative_to(ROOT))] = sha(path)
    p106b_shards.verify(path.parent, manifest)
    for shard in manifest["shards"]:
        with (path.parent / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                yield json.loads(line)


def source_pins():
    paths = (
        "scripts/prepare_p109c_v2.py", "scripts/p106b_shards.py", "scripts/p106b_night_qa_data.py",
        "scripts/p106b_subject_role_data.py", "scripts/p106b_relation_bind_data.py",
        "tinylm/chat/serialize.py", "tinylm/train/mtp_sft.py", "tinylm/data/sft.py",
    )
    return {path: sha(ROOT / path) for path in paths}


def set_forbidden_questions():
    """Take full questions from the already-frozen authored evaluation assets."""
    from scripts import p106b_final_holdout as final

    questions = []
    for split in ("dev", "final"):
        questions.extend(final.build(split))
    return {text_signature(item["prompt"]) for item in questions}


def record_checks(x, y):
    if (x.ndim != 1 or x.shape != y.shape or not 1 <= len(x) <= WIDTH
            or x.min() < 0 or x.max() >= v1.VOCAB
            or np.any((y != IGNORE) & ((y < 0) | (y >= v1.VOCAB)))):
        return "length_or_vocab"
    supervised = y != IGNORE
    if not supervised.any() or np.any(supervised[:-1] & (y[:-1] != x[1:])) or np.any(y == EOS):
        return "answer_shift_or_document_eos"
    starts = np.flatnonzero(supervised & ~np.r_[False, supervised[:-1]])
    ends = np.flatnonzero(supervised & ~np.r_[supervised[1:], False])
    if np.any(y[starts] == END) or np.any(y[ends] != END):
        return "empty_or_unterminated_answer"
    if starts[-1] + 1 > 896 or np.any(ends - starts + 1 > 128):
        return "first_use_context_or_answer_budget"
    return None


class Lane:
    """Store four independently packed causal rows per microbatch."""

    def __init__(self, directory, name, kind, stack):
        self.name, self.kind = name, kind
        self.tensor = directory / (name + ".bin")
        self.metadata = directory / (name + ".jsonl")
        self.output = stack.enter_context(self.tensor.open("xb"))
        self.description = stack.enter_context(self.metadata.open("x", encoding="utf-8"))
        self.block = np.zeros((BATCH, 3, WIDTH), dtype=DTYPE)
        self.block[:, 1] = IGNORE
        self.events = []
        self.row = self.position = self.segment = self.micros = 0
        self.tokens = self.records = 0

    def flush(self, gold=-1):
        self.output.write(self.block.tobytes())
        self.description.write(json.dumps(dict(gold=gold, decimal=self.events)) + "\n")
        self.block[:, 0] = 0
        self.block[:, 1] = IGNORE
        self.block[:, 2] = 0
        self.events = []
        self.row = self.position = self.segment = 0
        self.micros += 1

    def put(self, x, y, decimal=None):
        if self.position + len(x) > WIDTH:
            self.row += 1
            self.position = self.segment = 0
            if self.row == BATCH:
                self.flush()
        self.segment += 1
        start, end = self.position, self.position + len(x)
        self.block[self.row, 0, start:end] = x
        self.block[self.row, 1, start:end] = y
        self.block[self.row, 2, start:end] = self.segment
        if decimal is not None:
            label, position = decimal
            self.events.append([self.row, start + position, label])
        self.position = end
        self.tokens += len(x)
        self.records += 1

    def relation(self, candidates, gold):
        if self.row or self.position or not 0 <= gold < BATCH or len(candidates) != BATCH:
            raise ValueError("the entire contrast question must occupy one dedicated microbatch")
        for index, (x, y) in enumerate(candidates):
            self.row = index
            self.position = self.segment = 0
            self.put(x, y)
        self.flush(gold)

    def finish(self):
        if self.position:
            self.flush()
        self.output.close()
        self.description.close()
        return dict(name=self.name, kind=self.kind, micros=self.micros, tokens=self.tokens, records=self.records,
                    array=dict(file=self.tensor.name, sha256=sha(self.tensor)),
                    metadata=dict(file=self.metadata.name, sha256=sha(self.metadata)))


class Course:
    def __init__(self, directory, stack, tok, forbidden):
        self.directory, self.stack, self.tok, self.forbidden = directory, stack, tok, forbidden
        self.lanes, self.pins, self.seen = {}, {}, set()
        self.counts = defaultdict(Counter)

    def lane(self, family, language, kind="plain"):
        key = family, language, kind
        if key not in self.lanes:
            self.lanes[key] = Lane(self.directory, "_".join(key), kind, self.stack)
        return self.lanes[key]

    def add(self, family, language, x, y, *, decimal=None):
        counts = self.counts[family]
        counts["checked"] += 1
        x, y = np.asarray(x, dtype=np.int32), np.asarray(y, dtype=np.int32)
        if reject := record_checks(x, y):
            counts[reject] += 1
            return
        # Same inputs can carry different validated masks. Their supervision remains distinct.
        identity = row_signature(x), row_signature(y), decimal
        if identity in self.seen:
            counts["identical_input_and_mask"] += 1
            return
        self.seen.add(identity)
        self.lane(family, language).put(x, y, decimal)
        counts["accepted_rows"] += 1
        counts["accepted_tokens"] += len(x)
        counts["answer_targets"] += int(np.count_nonzero(y != IGNORE))

    def canonical(self, family, row):
        meta = row["meta"]
        language = meta.get("language")
        split = meta.get("source_split", meta.get("split", "train")).casefold()
        users = (content(message) for message in row["messages"] if message["role"] == "user")
        if language not in ("ko", "en") or split != "train":
            self.counts[family]["source_language_or_split"] += 1
            return
        if any(text_signature(prompt) in self.forbidden for prompt in users):
            self.counts[family]["frozen_question_match"] += 1
            return
        try:
            record = encode_record(row, self.tok)
        except ValueError:
            self.counts[family]["canonical_encoder_reject"] += 1
            return
        self.add(family, language, record.x, record.y)

    def contrast(self, family, language, candidates, gold):
        arrays = [(np.asarray(x, dtype=np.int32), np.asarray(y, dtype=np.int32)) for x, y in candidates]
        counts = self.counts[family]
        if any(record_checks(x, y) for x, y in arrays):
            counts["context_or_mask_reject"] += 1
            return
        self.lane(family, language, "relation").relation(arrays, gold)
        counts["accepted_questions"] += 1
        counts["accepted_tokens"] += sum(len(x) for x, _ in arrays)
        counts["answer_targets"] += int(np.count_nonzero(arrays[gold][1] != IGNORE))


def qa32k(course):
    from scripts import diag_p106b_night_diversity as archive

    proof = read_json(INVENTORY)["archived_qa"]
    archive_report = ROOT / proof["archived_reports"][0]["path"]
    if sha(archive_report) != proof["archived_reports"][0]["sha256"].upper():
        raise ValueError("the verified 32K corpus receipt changed")
    source = read_json(archive_report)
    frozen = archive.CORPUS / "report.json"
    report = read_json(frozen)
    course.pins[str(archive_report.relative_to(ROOT))] = sha(archive_report)
    course.pins[str(frozen.relative_to(ROOT))] = sha(frozen)
    data = archive.qa.data
    training = list(archive.stream(report["manifests"]["train"]))
    if len(training) != 32768 or data.sha(training) != source["source_split_sha256"]["train"]:
        raise ValueError("the admitted original 32K TRAIN sources changed")
    for row in training:
        for view in ("0", "1"):
            course.canonical("grounded_qa", row["views"][view])
        # New presentation of the training question. The held-out renderer is untouched.
        marker = "근거 자료" if row["language"] == "ko" else "Evidence"
        view = row["views"]["0"]
        user = row["question"] + "\n\n" + marker + "\n" + row["context"]
        example = normalize(dict(messages=[dict(role="user", content=user), view["messages"][1]], meta=view["meta"]))
        course.canonical("grounded_qa_question_first", example)


def broaden(course):
    broad = ROOT / "data_cache/p106b_broad_curriculum_v2_s1337/wire/train_shards_manifest.json"
    for row in verified_rows(broad, course.pins):
        meta = row["meta"]
        if meta["first_user_sha256"].lower() not in course.forbidden:
            course.add("broad", meta["language"], row["x"], row["y"])


def unpad(x, y):
    # Both the shifted supervision and the input must survive trailing padding removal.
    return max(int(np.flatnonzero(x)[-1]), int(np.flatnonzero(y != IGNORE)[-1])) + 1


def authored_p109(course):
    manifest = AUTHORED / "compiled_manifest.json"
    course.pins[str(manifest.relative_to(ROOT))] = sha(manifest)
    spec = read_json(manifest)["course"]
    items = {}
    for name in ("plain", "decimal", "all_axes"):
        path = v1.bundle_path(AUTHORED, spec[name]["file"])
        expected = v1.digest(spec[name]["sha256"])
        if sha(path) != expected:
            raise ValueError("the verified P109 authored source changed")
        course.pins[str(path.relative_to(ROOT))] = expected
        items[name] = np.load(path, mmap_mode="r", allow_pickle=False)
    for (x, y), (position, left, right) in zip(items["plain"], items["decimal"], strict=True):
        width = unpad(x, y)
        language = "ko" if re.search(r"[가-힣]", course.tok.decode(x[:width].tolist())) else "en"
        event = None
        if position >= 0:
            total, _, _, carry = native_course.joint_decimal.decimal_parts(int(left), int(right))
            start = int(np.flatnonzero(y != IGNORE)[0])
            answer = course.tok.decode(y[(y != IGNORE) & (y != END)].tolist())
            if start != position or answer.strip() != str(total):
                raise ValueError("a decimal label is not aligned to a verified first answer")
            event = int(1000 + total + 200 * carry), int(position)
        course.add("p109_correction_and_decimal", language, x[:width], y[:width], decimal=event)
    array = items["all_axes"]
    for question, gold in enumerate(spec["all_axes"]["gold"]):
        candidates = [(x[:unpad(x, y)], y[:unpad(x, y)]) for x, y in array[BATCH*question:BATCH*(question+1)]]
        language = "ko" if re.search(r"[가-힣]", course.tok.decode(candidates[0][0].tolist())) else "en"
        course.contrast("p109_all_axes", language, candidates, gold)


def authored_other(course):
    for family, tag in AUTHORED_COURSES:
        directory = HF / tag / "corpus"
        paths = sorted(directory.glob("*train*_shards_manifest.json"))
        if not paths:
            raise ValueError(f"eligible curriculum manifest absent: {tag}")
        for path in paths:
            for row in verified_rows(path, course.pins):
                # Source-only public QA is admitted through the verified 32K path.
                if row["meta"].get("kind") == "public_qa":
                    course.counts[family]["legacy_public_qa_held"] += 1
                    continue
                course.canonical(family, row)

    from scripts import p106b_relation_bind_data as binding, p106b_subject_role_data as role

    for name, module in (("p106b_relation_bind_v1_s1337", binding), ("p106b_subject_role_v1_s1337", role)):
        path = EVIDENCE / "local" / name / "corpus/train_shards_manifest.json"
        for row in verified_rows(path, course.pins):
            records, crossed = module.encode_bundle(row, course.tok)
            language = row["language"]
            if module is binding:
                for record in records:
                    course.add("relation_binding", language, record.x, record.y)
                continue
            by_index = dict(zip((*role.POSITIVE_LAYOUT, *role.CROSSED_LAYOUT), (*records, *crossed), strict=True))
            for q in range(BATCH):
                course.contrast("subject_role_all_axes", language,
                                [(by_index[q, a].x, by_index[q, a].y) for a in range(BATCH)], q)


def arrange(lanes, train_tokens):
    """Allocate every raw and course microbatch once, with a fixed warmup."""
    raw_micros, remainder = divmod(RAW_TOKENS, BATCH * WIDTH)
    if remainder or len(lanes) < 2:
        raise ValueError("the admitted P109C requires complete raw batches and mixed curriculum")
    course_micros = sum(lane["micros"] for lane in lanes)
    total_micros = raw_micros + course_micros
    steps, last = divmod(total_micros, ACCUM)
    steps += bool(last)
    if steps <= WARMUP or steps * ACCUM * BATCH * WIDTH * 2 > train_tokens:
        raise ValueError("the actual packed schedule does not meet the raw-pool rule")
    if course_micros < steps - WARMUP or raw_micros - WARMUP * ACCUM < steps - WARMUP:
        raise ValueError("both raw and curricular learning must be represented in every mixed update")
    shape = steps, ACCUM, 2
    slots = np.full(shape, -2, dtype="<i4")
    slots[:WARMUP, :, 0] = -1
    slots[:WARMUP, :, 1] = np.arange(WARMUP * ACCUM).reshape(WARMUP, ACCUM)
    rng = np.random.default_rng(1337)
    queues = [deque(rng.permutation(lane["micros"]).tolist()) for lane in lanes]
    consumed = [0] * len(lanes)
    raw = WARMUP * ACCUM
    mixed = steps - WARMUP
    available = total_micros - raw
    for update in range(WARMUP, steps):
        offset = update - WARMUP
        after = (offset + 1) / mixed
        previous_course = sum(consumed)
        count = round(course_micros * after) - previous_course
        fill = available * (offset + 1) // mixed - available * offset // mixed
        if not 1 <= count < fill or raw + fill - count > raw_micros:
            raise ValueError("the deterministic mixed schedule could not retain both streams")
        locations = set(np.linspace(0, fill - 1, count + 2, dtype=int)[1:-1])
        if len(locations) != count:
            raise ValueError("course microbatch positions collapsed")
        for slot in range(fill):
            if slot not in locations:
                slots[update, slot] = -1, raw
                raw += 1
                continue
            index = max((i for i, queue in enumerate(queues) if queue),
                        key=lambda i: after * lanes[i]["micros"] - consumed[i])
            slots[update, slot] = index, queues[index].popleft()
            consumed[index] += 1
    if any(queues) or raw != raw_micros:
        raise ValueError("the mixed schedule did not consume the sealed input streams")
    raw_starts = np.random.default_rng(1234).integers(0, train_tokens - WIDTH - 1, (raw_micros, BATCH))
    return slots, raw_starts


def build(directory):
    directory.mkdir(exist_ok=False)
    if sha(TOKENIZER) != TOKENIZER_SHA:
        raise ValueError("the exact admitted chat32 tokenizer is required")
    tok = Tokenizer.from_file(str(TOKENIZER))
    if tok.token_to_id("<|im_end|>") != END:
        raise ValueError("the admitted ChatML EOT differs")
    from tinylm.train.context_training_state import cache_identity

    cache = cache_identity(CACHE)
    meta = read_json(CACHE / "meta.json")
    if meta["tokenizer_sha256"] != TOKENIZER_SHA or meta["train"] != 1_183_367_026:
        raise ValueError("the previous v1.1 admitted TRAIN source changed")
    with ExitStack() as stack:
        course = Course(directory, stack, tok, set_forbidden_questions())
        for action in (authored_p109, qa32k, broaden, authored_other):
            action(course)
            print("P109C_V2_PREPARED", action.__name__, len(course.lanes), flush=True)
        lanes = [value.finish() for value in course.lanes.values()]
    slots, raw_starts = arrange(lanes, meta["train"])
    np.save(directory / "schedule.npy", slots, allow_pickle=False)
    np.save(directory / "raw_starts.npy", raw_starts, allow_pickle=False)
    result = dict(schema=SCHEMA, corpus_sources=course.pins, code_sources=source_pins(), cache=cache,
                  tokenizer_sha256=TOKENIZER_SHA, lanes=lanes, counts=course.counts,
                  warmup=WARMUP, steps=len(slots), raw_tokens=RAW_TOKENS,
                  course_tokens=sum(lane["tokens"] for lane in lanes),
                  schedule_sha256=sha(directory / "schedule.npy"),
                  raw_starts_sha256=sha(directory / "raw_starts.npy"),
                  legacy_public_rows_held={"75M": 503940, "P101A_8M": 105447},
                  legacy_hold_evidence="CARD_ONLY/PUBLIC_SOURCE_UNVERIFIED and earlier language-retention loss")
    v1.publish(directory / "manifest.json", result)
    print("P109C_V2_SEALED", len(slots), result["course_tokens"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output.absolute())


if __name__ == "__main__":
    main()
