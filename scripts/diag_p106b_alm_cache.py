#!/usr/bin/env python3
"""P106B Stage7b: opt-in frozen selection and native teacher-logp cache.

Import/check-only use stdlib and source files only. Actual tokenizer/data I/O,
owned teacher startup and tests belong to the authorized caller. This module
does not load a student/checkpoint, train, repair data, or grade answer truth.
Each teacher invocation owns one fixed bilingual 16-row cache batch or the
original first16 plus failed34 canary17. Partial directories are preserved
and cannot be resumed or silently replaced.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import threading
import time
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = "P106B_ALM_NATIVE_CACHE_V1"
SEED, PER_LANGUAGE, BATCH_SIZE, BATCHES = 1337, 512, 16, 64
STUDENT_CONTEXT, MAX_CE_TARGETS, TEACHER_CONTEXT = 1024, 64, 1024
MAX_BYTES = 19_999_999
ATOL = 1e-5
SHUTDOWN_RESERVE = 30
HARD_STOP = datetime(2026, 10, 23, 7, 30, tzinfo=timezone.utc)
SOURCE = ROOT / "HF/sft_ready/p101a_sft_mtp_cleanbilingual_v3_s1337/corpus"
SOURCE_REPORT_SHA = "7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
TOKENIZER_SHA = "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
# V7 tightens actual response/matrix/reference-recovery guards only. Student
# data/root order and native no-thinking conditioning stay unchanged.
# Historical source snapshots, preparations and partial raw remain preserved.
BASE = ROOT / "HF/sft_ready/p106b_alm_context_v7_s1337"
TEACHER_CONTRACT = "NATIVE_TEMPLATE_THINKING_FALSE_EDGE_COLD_UTF8_PROBE_STRICT_ACTUAL_V4"
CANARY_EXTRA_SELECTION_INDEX = 34
FAILED_TARGET_EXPECTATION = dict(selection_index=34, target_id=36054, piece_hex="ec9b",
    native_prefix_ids_sha256="5661E32015CBC28C7FC8D38BC1243052D37319CF7CB36BEA9D78A3D6858AA6F6")
PREPARED = BASE / "prepared"
CANARY = BASE / "canary" / "batch_000000"
TF_REPORT = ROOT / "test_result/evidence/p106b_qwen_tf_v1_s1337/report.json"
CODE = (
    "scripts/diag_p106b_alm_cache.py", "scripts/test_p106b_alm_cache.py",
    "scripts/p106b_alm_bytes.py", "scripts/p101a_sft_mtp_data.py",
    "tinylm/train/mtp_sft.py", "tinylm/data/sft.py",
    "tinylm/chat/serialize.py", "tinylm/chat/canonical.py",
    "scripts/diag_p106b_teacher_tf.py", "scripts/p106b_qwen_teacher.py",
    "scripts/diag_p106b_qwen_coload.py", "scripts/diag_p106b_mtp_teacher.py",
    "scripts/p106b_mtp_teacher.py", "scripts/diag_p106_coload.py",
    "scripts/diag_p106_full_coload_accum.py", "scripts/diag_p106b_online_rate5.py",
    "scripts/diag_p106_vram_sample.py", "scripts/p106b_gate_runtime.py",
    "scripts/p106b_http_errors.py", "scripts/p106b_shards.py",
    "scripts/p106b_alm_template_alignment.py", "scripts/test_p106b_alm_template_alignment.py",
    "scripts/p106b_alm_utf8_probability.py", "scripts/test_p106b_alm_utf8_probability.py",
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest().upper()


def object_sha(value):
    return sha(canonical(value))


def regular(path):
    path = Path(path)
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("linked input/output is forbidden: " + str(path))
    return path


def digest(path):
    path = regular(path)
    if not path.is_file():
        raise FileNotFoundError("exact regular file required: " + str(path))
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest().upper()


def sources():
    return {name: digest(ROOT / name) for name in CODE}


def read_json(path):
    path = regular(path)
    if path.stat().st_size >= 20_000_000:
        raise ValueError("one JSON file must be below20MB")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    raw = canonical(value) + b"\n"
    if len(raw) >= 20_000_000:
        raise ValueError("one JSON file must be below20MB")
    with regular(path).open("xb") as stream:
        stream.write(raw)


def new_directory(path):
    path = regular(path)
    if path.exists():
        raise FileExistsError("existing/partial output preserved: " + str(path))
    path.mkdir(parents=True, exist_ok=False)


def message_text(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list) or any(
        not isinstance(block, dict) or block.get("type") != "text"
        or not isinstance(block.get("text"), str) for block in content
    ):
        raise ValueError("text-only message required")
    return "".join(block["text"] for block in content)


def overlap_identity(row):
    """Exact messages/prompt; no answer score, normalization or paraphrase oracle."""
    meta = row.get("meta", {})
    roots = {meta[key] for key in ("semantic_root_id", "parent_concept_id", "root")
             if isinstance(meta.get(key), str) and meta[key]}
    context = meta.get("context_id")
    contexts = {context} if isinstance(context, str) and context else set()
    first = next((m for m in row["messages"] if m.get("role") == "user"), None)
    if first is None:
        raise ValueError("all source rows need an exact first-user prompt")
    try:
        prompt = {"text": message_text(first)}
    except ValueError:
        prompt = {"canonical_content": first.get("content")}
    return roots, contexts, object_sha(row["messages"]), object_sha(prompt)


def validation_index(rows):
    index = dict(roots=set(), contexts=set(), conversations=set(), prompts=set(), rows=0)
    for row in rows:
        roots, contexts, conversation, prompt = overlap_identity(row)
        index["roots"].update(roots)
        index["contexts"].update(contexts)
        index["conversations"].add(conversation)
        index["prompts"].add(prompt)
        index["rows"] += 1
    if not index["rows"]:
        raise ValueError("complete nonempty original VAL is required")
    return index


def candidate_reason(row, val):
    meta = row.get("meta", {})
    if (meta.get("source") != "explicit_public_context_qa"
            or type(meta.get("wrapper_view")) is not int or meta["wrapper_view"] != 0):
        return "not_original_context_wrapper0"
    if ([m.get("role") for m in row.get("messages", [])] != ["user", "assistant"]
            or meta.get("language") not in ("ko", "en")
            or meta.get("source_original_split") != "train"
            or meta.get("source_split") != "train"):
        return "not_two_turn_original_train"
    root = meta.get("semantic_root_id")
    if (not isinstance(root, str) or not root or meta.get("parent_concept_id", root) != root
            or not isinstance(meta.get("context_id"), str) or not meta["context_id"]
            or any(not isinstance(meta.get(key), str) or not meta[key]
                   for key in ("context_original", "question_original", "source_path", "source_sha256"))
            or not isinstance(meta.get("answers"), list) or not meta["answers"]):
        return "missing_explicit_context_annotation_lineage"
    # Presence/transport integrity is checked, not semantic truth or answer quality.
    if any(not isinstance(answer, dict) or not isinstance(answer.get("text"), str)
           or type(answer.get("answer_start")) is not int for answer in meta["answers"]):
        return "missing_original_annotation_fields"
    if meta.get("supervised_assistant_turns", [1]) != [1]:
        return "different_assistant_supervision"
    user, assistant = map(message_text, row["messages"])
    if (not assistant or meta["context_original"] not in user
            or meta["question_original"] not in user):
        return "missing_context_question_or_answer_bytes"
    roots, contexts, conversation, prompt = overlap_identity(row)
    if (roots & val["roots"] or contexts & val["contexts"]
            or conversation in val["conversations"] or prompt in val["prompts"]):
        return "original_val_overlap"
    return None


def root_order(language, root):
    return object_sha([SCHEMA, SEED, "ROOT_ORDER", language, root])


def choose_rows(train_rows, val, encode, *, per_language=PER_LANGUAGE):
    """Injected encoder core; runtime fixes per_language=512, tests use toy counts."""
    if type(per_language) is not int or per_language <= 0:
        raise ValueError("positive selection count required")
    rejected, by_root = Counter(), {}
    for source_index, row in enumerate(train_rows):
        reason = candidate_reason(row, val)
        if reason:
            rejected[reason] += 1
            continue
        record = encode(row)
        if not 0 < record.x_tokens <= STUDENT_CONTEXT or not 0 < record.targets <= MAX_CE_TARGETS:
            rejected["student_context_or_target_budget"] += 1
            continue
        meta, row_sha = row["meta"], object_sha(row)
        root, language = meta["semantic_root_id"], meta["language"]
        old = by_root.get(root)
        if old is not None and old["language"] != language:
            raise ValueError("one semantic root has conflicting languages")
        spec = dict(row=row, row_sha256=row_sha, language=language, root=root,
                    source_index=source_index, root_order_sha256=root_order(language, root),
                    x_tokens=record.x_tokens, ce_targets=record.targets)
        if old is None or (row_sha, source_index) < (old["row_sha256"], old["source_index"]):
            by_root[root] = spec
        if old is not None:
            rejected["same_root_duplicate"] += 1
    lanes = {language: sorted((spec for spec in by_root.values() if spec["language"] == language),
                             key=lambda spec: (spec["root_order_sha256"], spec["root"]))
             for language in ("ko", "en")}
    if any(len(values) < per_language for values in lanes.values()):
        raise ValueError("insufficient eligible roots; no replacement/relaxed admission")
    chosen = [lanes[language][i] for i in range(per_language) for language in ("ko", "en")]
    summary = dict(eligible_roots={key: len(value) for key, value in lanes.items()},
                   rejections=dict(rejected), selected_per_language=per_language,
                   selected_root_fraction={key: per_language / len(value) for key, value in lanes.items()},
                   quality_or_teacher_score_selection=False,
                   order="SHA256([schema,1337,ROOT_ORDER,language,root]); ko/en interleaved")
    return chosen, summary


def char_spans_to_bytes(text, spans):
    if not isinstance(text, str):
        raise ValueError("serialized text required")
    offsets, position = [0], 0
    for char in text:
        position += len(char.encode("utf-8", errors="strict"))
        offsets.append(position)
    result, previous = [], 0
    for pair in spans:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or any(type(value) is not int for value in pair)):
            raise ValueError("character span pair required")
        left, right = pair
        if not previous <= left < right <= len(text):
            raise ValueError("ordered nonempty original character spans required")
        result.append([offsets[left], offsets[right]])
        previous = right
    return result


def owners_for_offsets(offsets, spans):
    mask, turns = [], []
    for left, right in offsets:
        owners = [index + 1 for index, (start, stop) in enumerate(spans)
                  if right > left and left >= start and right <= stop]
        if len(owners) > 1:
            raise ValueError("overlapping semantic assistant spans")
        mask.append(bool(owners))
        turns.append(owners[0] if owners else 0)
    return mask, turns


def special_json(special):
    return dict(raw_index=special.raw_index, token_id=special.token_id,
                kind=special.kind, source_bytes_hex=special.source_bytes.hex())


def special_records(values):
    from scripts.p106b_alm_bytes import SpecialToken
    return [SpecialToken(value["raw_index"], value["token_id"], value["kind"],
                         bytes.fromhex(value["source_bytes_hex"])) for value in values]


def stream_summary(stream):
    return [dict(raw_index=token.raw_index, token_id=token.token_id,
                 byte_start=token.byte_start, byte_end=token.byte_end,
                 bytes_sha256=sha(token.data), supervised=token.supervised,
                 turn_id=token.turn_id, special_kind=token.special_kind)
            for token in stream.tokens]


def pack_student(spec, tok, encode_record, encode_conversation, loss_spans, special_ids):
    from scripts.p106b_alm_bytes import SpecialToken, build_student_stream
    row = spec["row"]
    record = encode_record(row, tok, context=STUDENT_CONTEXT)
    ids, labels, text = encode_conversation(row, tok, "chatml")
    encoding = tok.encode(text)
    offsets = [list(pair) for pair in encoding.offsets]
    spans = [list(pair) for pair in loss_spans(row, "chatml")]
    keep, turns = owners_for_offsets(offsets, spans)
    if (list(encoding.ids) != ids or len(ids) != len(offsets)
            or labels != [token if mask else -100 for token, mask in zip(ids, keep)]
            or record.x != ids[:-1] or record.y != labels[1:]
            or record.segments != turns[1:] or record.x_tokens != spec["x_tokens"]
            or record.targets != spec["ce_targets"]):
        raise ValueError("original encoder/offset/segment/full-shift contract differs")
    pieces = [tok.id_to_token(token) for token in ids]
    declarations = []
    for index, token in enumerate(ids):
        if token in special_ids:
            literal = special_ids[token]
            if pieces[index] != literal:
                raise ValueError("student native special spelling differs")
            declarations.append(SpecialToken(index, token, literal, literal.encode("utf-8")))
    stream = build_student_stream(text, ids, pieces, supervised=keep,
                                  turn_ids=turns, specials=declarations)
    if not any(value.kind == "<|im_end|>" and keep[value.raw_index] for value in declarations):
        raise ValueError("original assistant EOT must remain CE-supervised")
    student = dict(ids=ids, labels=labels, pieces=pieces, char_offsets=offsets,
                   supervised=keep, turn_ids=turns, specials=[special_json(v) for v in declarations],
                   loss_spans_chars=spans, loss_spans_bytes=char_spans_to_bytes(text, spans),
                   x_tokens=record.x_tokens, ce_targets=record.targets,
                   byte_spans=stream_summary(stream), ids_sha256=object_sha(ids),
                   offsets_sha256=object_sha(offsets), pieces_sha256=object_sha(pieces),
                   utf8_bytes_sha256=sha(text.encode("utf-8")))
    return dict(schema=SCHEMA, source_row=row, source_row_sha256=spec["row_sha256"],
                source_train_index=spec["source_index"], semantic_root_id=spec["root"],
                language=spec["language"], root_order_sha256=spec["root_order_sha256"],
                text=text, text_sha256=sha(text.encode("utf-8")), student=student)


def rebuild_student(row):
    from scripts.p106b_alm_bytes import build_student_stream
    value = row["student"]
    if (object_sha(row["source_row"]) != row["source_row_sha256"]
            or sha(row["text"].encode("utf-8")) != row["text_sha256"]
            or value["utf8_bytes_sha256"] != row["text_sha256"]
            or object_sha(value["ids"]) != value["ids_sha256"]
            or object_sha(value["char_offsets"]) != value["offsets_sha256"]
            or object_sha(value["pieces"]) != value["pieces_sha256"]
            or value["x_tokens"] != len(value["ids"]) - 1
            or value["ce_targets"] != sum(label != -100 for label in value["labels"][1:])):
        raise ValueError("prepared original row/byte/ID/offset identity differs")
    mask, turns = owners_for_offsets(value["char_offsets"], value["loss_spans_chars"])
    if (mask != value["supervised"] or turns != value["turn_ids"]
            or value["loss_spans_bytes"] != char_spans_to_bytes(row["text"], value["loss_spans_chars"])
            or value["labels"] != [token if keep else -100 for token, keep in zip(value["ids"], mask)]):
        raise ValueError("prepared full-sequence labels/turns changed")
    stream = build_student_stream(row["text"], value["ids"], value["pieces"], supervised=mask,
                                  turn_ids=turns, specials=special_records(value["specials"]))
    if stream_summary(stream) != value["byte_spans"]:
        raise ValueError("prepared native byte spans changed")
    return stream


def source_inputs():
    """Explicit V3 corpus/tokenizer only; never an upstream source-data traversal."""
    from scripts.p106b_shards import verify
    if digest(SOURCE / "report.json") != SOURCE_REPORT_SHA or digest(TOKENIZER) != TOKENIZER_SHA:
        raise ValueError("pinned V3 corpus report/tokenizer differs")
    report = read_json(SOURCE / "report.json")
    if (report.get("status") != "CORPUS_READY" or report.get("family") != "mtp"
            or report.get("tokenizer_sha256") != TOKENIZER_SHA):
        raise ValueError("original complete V3 MTP corpus required")
    paths = [SOURCE / "report.json", TOKENIZER]
    for split in ("train", "val"):
        manifest = report["manifests"][split]
        path = SOURCE / (split + "_shards_manifest.json")
        if read_json(path) != manifest:
            raise ValueError("original split manifest differs from frozen report")
        verify(SOURCE, manifest)
        paths.append(path)
        paths.extend(SOURCE / value["path"] for value in manifest["shards"])
    return report, {str(path.relative_to(ROOT)): digest(path) for path in paths}


def snapshot_matches(snapshot):
    return all(digest(ROOT / name) == expected for name, expected in snapshot.items())


def prepare():
    # All real-data/tokenizer imports are behind this explicit CPU preparation.
    import tokenizers as tokenizer_runtime
    from tokenizers import Tokenizer
    from scripts.p101a_sft_mtp_data import stream_rows
    from scripts.p106b_shards import ShardWriter, verify
    from tinylm.train.mtp_sft import encode_record
    from tinylm.data.sft import encode_conversation
    from tinylm.chat.serialize import loss_spans
    regular(PREPARED)
    if PREPARED.exists():
        raise FileExistsError("frozen/partial preparation preserved")
    began = time.perf_counter()
    code = sources()
    original, inputs = source_inputs()
    metadata = read_json(TOKENIZER)
    special_ids = {entry["id"]: entry["content"] for entry in metadata.get("added_tokens", [])
                   if entry.get("special") is True}
    if not {"<|im_start|>", "<|im_end|>"} <= set(special_ids.values()):
        raise ValueError("explicit native ChatML special metadata required")
    tok = Tokenizer.from_file(str(TOKENIZER))
    if tok.get_vocab_size(with_added_tokens=True) != 32768:
        raise ValueError("strict original chat32 vocabulary required")
    val = validation_index(stream_rows(SOURCE, original["manifests"]["val"]))
    selected, summary = choose_rows(stream_rows(SOURCE, original["manifests"]["train"]), val,
                                    lambda row: encode_record(row, tok, context=STUDENT_CONTEXT))
    if len(selected) != 1024:
        raise ValueError("runtime selection is exactly1024, never a reduced sample")
    new_directory(PREPARED)
    writer = ShardWriter(PREPARED, "selection", limit=MAX_BYTES)
    report = dict(schema=SCHEMA, status="PREPARING", returncode=9, seed=SEED,
                  source_report_sha256=SOURCE_REPORT_SHA, tokenizer_sha256=TOKENIZER_SHA,
                  source_code_sha256=code, input_sha256=inputs, selection=summary,
                  python_version=sys.version, tokenizers_version=tokenizer_runtime.__version__,
                  complete_original_val_rows=val["rows"], rows=0, language_rows={},
                  model_loads=0, gpu_calls=0, teacher_requests=0, checkpoint_writes=0,
                  source_rows_modified=False, semantic_exhaustive_review=False,
                  formal_train_ready=False)
    row_shas, counts = [], Counter()
    try:
        for index, spec in enumerate(selected):
            row = pack_student(spec, tok, encode_record, encode_conversation, loss_spans, special_ids)
            messages = row["source_row"]["messages"]
            question, answer = map(message_text, messages)
            spans = row["student"]["loss_spans_chars"]
            if ([v.get("role") for v in messages] != ["user", "assistant"]
                    or not question.strip() or not answer or len(spans) != 1
                    or row["text"][spans[0][0]:spans[0][0]+len(answer)] != answer):
                raise ValueError("original user/body boundaries must be CPU-validated before teacher entry")
            row.update(row_id=f"alm_{index:06d}", selection_index=index, batch_index=index // BATCH_SIZE)
            row["prepared_row_sha256"] = object_sha(row)
            writer.append(row)
            row_shas.append(row["prepared_row_sha256"])
            counts[row["language"]] += 1
            report["rows"] += 1
        report["inputs_unchanged"] = snapshot_matches(inputs)
        report["sources_unchanged"] = sources() == code
        if not report["inputs_unchanged"] or not report["sources_unchanged"]:
            raise ValueError("source/data/tokenizer changed during preparation")
        report.update(status="SELECTION_FROZEN", returncode=0, language_rows=dict(counts),
                      prepared_row_sha256=row_shas, canary_row_sha256=row_shas[:BATCH_SIZE],
                      batches=BATCHES, batch_size=BATCH_SIZE,
                      native_question_edge_whitespace_rows=sum(
                          message_text(v["row"]["messages"][0]) != message_text(v["row"]["messages"][0]).strip()
                          for v in selected),
                      native_renderer_effect="ONLY_NATIVE_USER_EDGE_WHITESPACE_TRIM_DISCLOSED; STUDENT_UNCHANGED",
                      semantic_quality="SOURCE_ANNOTATION_NOT_FULL_SEMANTIC_REVIEW")
    except BaseException as exc:
        report.update(status="PREPARATION_PARTIAL", error_type=type(exc).__name__, error=str(exc)[:2000])
        raise
    finally:
        if writer._total_rows:
            manifest = writer.close(lineage=dict(schema=SCHEMA, source_report_sha256=SOURCE_REPORT_SHA))
            verify(PREPARED, manifest)
            report["selection_manifest"] = manifest
        report["wall_seconds"] = time.perf_counter() - began
        write_json(PREPARED / "report.json", report)
    return report


def validate_prepared_rows(rows):
    if len(rows) != 1024 or len({row["semantic_root_id"] for row in rows}) != 1024:
        raise ValueError("exact1024 distinct frozen roots required")
    for index, row in enumerate(rows):
        value = dict(row)
        expected = value.pop("prepared_row_sha256")
        if (object_sha(value) != expected or row["language"] != ("ko" if index % 2 == 0 else "en")
                or row["selection_index"] != index or row["batch_index"] != index // BATCH_SIZE
                or row["row_id"] != f"alm_{index:06d}"):
            raise ValueError("frozen row/order/hash differs")
        rebuild_student(row)
    return rows


def load_prepared(code):
    from scripts.p101a_sft_mtp_data import stream_rows
    report = read_json(PREPARED / "report.json")
    if (report.get("schema") != SCHEMA or report.get("status") != "SELECTION_FROZEN"
            or report.get("returncode") != 0 or report.get("rows") != 1024
            or report.get("language_rows") != {"ko": 512, "en": 512}
            or report.get("source_report_sha256") != SOURCE_REPORT_SHA
            or report.get("tokenizer_sha256") != TOKENIZER_SHA
            or report.get("source_code_sha256") != code
            or not report.get("inputs_unchanged") or not report.get("sources_unchanged")):
        raise ValueError("closed prepared selection/code/lineage required")
    rows = validate_prepared_rows(list(stream_rows(PREPARED, report["selection_manifest"])))
    if [row["prepared_row_sha256"] for row in rows] != report["prepared_row_sha256"]:
        raise ValueError("selection row list differs from closed report")
    return report, rows


def tokenize_payload(text, *, with_pieces):
    return dict(content=text, add_special=False, parse_special=True, with_pieces=with_pieces)


def token_ids(reply):
    values = reply.get("tokens") if isinstance(reply, dict) else None
    if not isinstance(values, list) or not values or any(type(v) is not int or v < 0 for v in values):
        raise ValueError("native nonempty token-ID list required")
    return values


def piece_rows(reply):
    values = reply.get("tokens") if isinstance(reply, dict) else None
    if not isinstance(values, list) or not values or any(
        not isinstance(value, dict) or type(value.get("id")) is not int or value["id"] < 0
        or not isinstance(value.get("piece"), (str, list)) for value in values
    ):
        raise ValueError("native token pieces must preserve integer IDs")
    return values


def teacher_stream(row, ids, pieces, special_ids):
    from scripts.p106b_alm_bytes import SpecialToken, build_teacher_stream
    if not 1 < len(ids) <= TEACHER_CONTEXT or [v["id"] for v in pieces] != ids:
        raise ValueError("teacher full sequence must preserve IDs and fit1024 without truncation")
    declarations = [SpecialToken(index, token, literal, literal.encode("utf-8"))
                    for index, token in enumerate(ids) if (literal := special_ids.get(token)) is not None]
    native = [value["piece"] for value in pieces]
    blank = build_teacher_stream(row["text"], ids, native, supervised=[False] * len(ids),
                                 turn_ids=[0] * len(ids), specials=declarations)
    offsets = [(token.byte_start, token.byte_end) for token in blank.tokens]
    mask, turns = owners_for_offsets(offsets, row["student"]["loss_spans_bytes"])
    return build_teacher_stream(row["text"], ids, native, supervised=mask,
                                turn_ids=turns, specials=declarations)


def alignment_json(alignment):
    chunks = [dict(byte_start=value.byte_start, byte_end=value.byte_end,
                   bytes_sha256=sha(value.data), data_hex=value.data.hex(), turn_id=value.turn_id,
                   student_raw_indices=list(value.student_raw_indices),
                   student_shifted_indices=list(value.student_shifted_indices),
                   teacher_raw_indices=list(value.teacher_raw_indices),
                   teacher_shifted_indices=list(value.teacher_shifted_indices)) for value in alignment.chunks]
    rejected = [dict(byte_start=value.byte_start, byte_end=value.byte_end,
                     student_raw_indices=list(value.student_raw_indices),
                     teacher_raw_indices=list(value.teacher_raw_indices), reasons=list(value.reasons))
                for value in alignment.rejected]
    return dict(chunks=chunks, rejected=rejected,
                student_special_indices=list(alignment.student_special_indices),
                teacher_special_indices=list(alignment.teacher_special_indices),
                input_byte_count=alignment.input_byte_count, covered_byte_count=alignment.covered_byte_count,
                student_supervised_byte_count=alignment.student_supervised_byte_count,
                teacher_supervised_byte_count=alignment.teacher_supervised_byte_count)


def compare_cache(cold, warm, *, atol=ATOL):
    same = (cold["chosen"]["id"] == warm["chosen"]["id"]
            and abs(cold["chosen"]["logprob"] - warm["chosen"]["logprob"]) <= atol
            and len(cold["top"]) == len(warm["top"])
            and all(a["id"] == b["id"] and abs(a["logprob"] - b["logprob"]) <= atol
                    for a, b in zip(cold["top"], warm["top"])))
    if not same:
        raise ValueError("cold/warm native ID/raw chosen logp/top2 mismatch; no cold fallback")
    return dict(passed=True, absolute_tolerance=atol,
                chosen_logprob_difference=abs(cold["chosen"]["logprob"] - warm["chosen"]["logprob"]))


def compare_reference_scores(left, right, *, atol=ATOL):
    """reference 확률과 실제 선택 probe를 섞지 않고 원 target/top2를 비교한다."""
    top_left, top_right = left["observed"]["top"][:2], right["observed"]["top"][:2]
    values = [left["raw_logprob"], right["raw_logprob"]] + [v["logprob"] for v in top_left + top_right]
    if any(type(value) not in (int, float) or not math.isfinite(value) or value > 0 for value in values):
        raise ValueError("reference comparison requires finite nonpositive original logp")
    difference=abs(left["raw_logprob"]-right["raw_logprob"])
    if (not left.get("native_prefix_ids_sha256")
            or left.get("native_prefix_ids_sha256") != right.get("native_prefix_ids_sha256")
            or left.get("raw_index") != right.get("raw_index")
            or left["target_id"]!=right["target_id"] or difference>atol
            or len(top_left)!=2 or len(top_right)!=2
            or any(a["id"]!=b["id"] or abs(a["logprob"]-b["logprob"])>atol for a,b in zip(top_left,top_right))):
        raise ValueError("same-prefix reference target/raw logp/top2 mismatch; no cold fallback or alternate-value imputation")
    return dict(passed=True,absolute_tolerance=atol,reference_target_id=left["target_id"],
        reference_logprob_difference=difference,actual_selected_ids_may_differ=True,
        native_prefix_ids_sha256=left["native_prefix_ids_sha256"])


def canary_rows(rows):
    selected=rows[:BATCH_SIZE]+[rows[CANARY_EXTRA_SELECTION_INDEX]]
    if len({row["prepared_row_sha256"] for row in selected})!=BATCH_SIZE+1:
        raise ValueError("original first16 plus failed original row34 required")
    return selected


def compact_payload(payload, row):
    """Losslessly reconstruct full-prefix requests from the earlier row event."""
    value = dict(payload)
    prompt = value.pop("prompt", None)
    ids = row["teacher_ids"]
    if (not isinstance(prompt, list) or not prompt or prompt != ids[:len(prompt)]
            or len(prompt) >= len(ids)):
        raise ValueError("request is not an exact frozen native prefix")
    return dict(payload_without_prompt=value, prompt_reference=dict(
        row_id=row["row_id"], full_teacher_ids_sha256=object_sha(ids), prefix_stop=len(prompt)),
        full_payload_sha256=object_sha(payload))


def restore_payload(record, rows):
    reference = record["prompt_reference"]
    ids = rows[reference["row_id"]]
    stop = reference["prefix_stop"]
    if (object_sha(ids) != reference["full_teacher_ids_sha256"]
            or type(stop) is not int or not 0 < stop < len(ids)):
        raise ValueError("prefix reconstruction identity differs")
    value = dict(record["payload_without_prompt"], prompt=ids[:stop])
    if object_sha(value) != record["full_payload_sha256"]:
        raise ValueError("reconstructed actual request SHA differs")
    return value


def deadline_value(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed > HARD_STOP:
        raise ValueError("aware deadline no later than2026-10-23 16:30KST required")
    return parsed.astimezone(timezone.utc)


class Budget:
    def __init__(self, seconds, deadline, *, now=None, clock=None):
        if type(seconds) is not int or not 60 <= seconds <= 600:
            raise ValueError("explicit wall limit60..600 seconds required")
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.clock = clock or time.monotonic
        if deadline.tzinfo is None or deadline > HARD_STOP or self.now().timestamp() + seconds > deadline.timestamp():
            raise ValueError("whole bounded invocation must fit current hard stop")
        self.deadline, self.start, self.seconds = deadline, self.clock(), seconds

    def remaining(self):
        left = min(self.seconds - (self.clock() - self.start), (self.deadline - self.now()).total_seconds())
        if left <= 0:
            raise TimeoutError("ALM cache wall/deadline reached; partial preserved")
        return left


def redact(value, key):
    if isinstance(value, str):
        # Do not regex-rewrite source/prompt bytes. The exact secret is removed
        # here; HTTP error bodies use the existing broader credential filter.
        return value.replace(key, "<redacted-api-key>") if key else value
    if isinstance(value, dict):
        return {name: redact(item, key) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item, key) for item in value]
    return value


class Recorder:
    """Serialize main/log/sampler writes; latch daemon persistence failures."""
    def __init__(self, writer, report, budget):
        self.writer, self.report, self.budget = writer, report, budget
        self.lock = threading.RLock()
        self.errors, self.key, self.row = [], "", None
        self.kind, self.serial, self.request_serial = "startup", 0, 0
        self.sealed = False

    def append(self, event, **value):
        with self.lock:
            if self.sealed:
                raise RuntimeError("raw recorder sealed; late background append rejected")
            self.serial += 1
            self.writer.append(dict(event=event, event_index=self.serial,
                                    utc=datetime.now(timezone.utc).isoformat(),
                                    monotonic_seconds=time.monotonic(), **redact(value, self.key)))

    def flush(self):
        """Make buffered request bytes visible before I/O; not fsync durability."""
        with self.lock:
            stream = getattr(self.writer, "_file", None)
            if stream is not None:
                stream.flush()

    def seal(self):
        with self.lock:
            self.sealed = True

    def background(self, event, **value):
        try:
            self.append(event, **value)
        except BaseException as exc:
            self.errors.append(type(exc).__name__ + ": " + str(exc)[:500])

    def check(self):
        if self.budget.remaining() <= SHUTDOWN_RESERVE:
            raise TimeoutError("owned teacher shutdown reserve reached; partial preserved")
        if self.errors:
            raise RuntimeError("raw log/telemetry persistence failed: " + ";".join(self.errors))

    def request(self, session, request, route, payload=None, timeout=10):
        self.check()
        self.request_serial += 1
        attempt = self.request_serial
        self.report["http_attempted"] += 1
        self.report["completion_attempted"] += int(route == "/completion")
        if route == "/completion":
            self.report["cache_verification_completion_requests"] += int(self.kind == "cache_prompt_verification")
            self.report["bias200_completion_requests"] += int(payload.get("logit_bias", [[None, None]])[0][1] == 200)
        evidence = compact_payload(payload, self.row) if route == "/completion" else dict(payload=payload)
        began = time.perf_counter()
        self.append("request_attempt", attempt=attempt, route=route, kind=self.kind,
                    row_id=None if self.row is None else self.row["row_id"],
                    timeout_seconds=min(timeout, self.budget.remaining() - SHUTDOWN_RESERVE), **evidence)
        self.flush()
        try:
            request_timeout = min(timeout, self.budget.remaining() - SHUTDOWN_RESERVE)
            if request_timeout <= 0:
                raise TimeoutError("shutdown reserve reached before I/O")
            reply = request(route, payload, timeout=request_timeout)
        except BaseException as exc:
            error = dict(type=type(exc).__name__, message=redact(str(exc), self.key)[:2000])
            if isinstance(exc, HTTPError):
                from scripts.p106b_http_errors import capture_http_error
                error["http"] = capture_http_error(exc, self.key)
            self.append("request_failed", attempt=attempt, route=route, kind=self.kind,
                        wall_seconds=time.perf_counter() - began, error=error)
            raise
        self.report["http_succeeded"] += 1
        self.report["completion_succeeded"] += int(route == "/completion")
        self.append("request_succeeded", attempt=attempt, route=route, kind=self.kind,
                    wall_seconds=time.perf_counter() - began, reply=reply)
        return reply


class RecordedList(list):
    def __init__(self, recorder, event):
        super().__init__()
        self.recorder, self.event = recorder, event

    def append(self, value):
        super().append(value)
        self.recorder.background(self.event, value=value)


def thread_exit_proof(session, recorder):
    live = [worker.name for worker in getattr(session, "workers", []) if worker.is_alive()]
    recorder.report["owned_threads_closed"] = not live
    if live:
        recorder.errors.append("owned background threads still alive after teardown: " + ",".join(live))
    return live


@contextmanager
def recorded_session(profile, recorder, holder):
    """Instrument existing owned QwenSession; no alternate server lifecycle."""
    from unittest.mock import patch
    from scripts import diag_p106b_qwen_coload as runtime
    from scripts import diag_p106b_online_rate5 as online
    from scripts import diag_p106b_teacher_tf as tf
    original_class, original_log, original_rss = runtime.QwenSession, online.capture_server_line, runtime.owned_rss

    class Session(original_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            recorder.key = self.key
            holder["session"] = self
            self.samples = RecordedList(recorder, "memory_sample_200ms")
            self.errors = RecordedList(recorder, "telemetry_error")

        def __enter__(self):
            recorder.check()
            recorder.report["teacher_server_start_attempted"] = True
            return super().__enter__()

        def __exit__(self, *args):
            before = time.perf_counter()
            try:
                return super().__exit__(*args)
            finally:
                live = thread_exit_proof(self, recorder)
                recorder.background("owned_session_exit", wall_seconds=time.perf_counter() - before,
                    pid=None if self.process is None else self.process.pid,
                    returncode=None if self.process is None else self.process.poll(), live_threads=live)

        def request(self, route, payload=None, timeout=10):
            return recorder.request(self, super().request, route, payload, timeout)

        def check(self):
            recorder.check()
            return super().check()

    def capture(line, signals, tail, key):
        original_log(line, signals, tail, key)
        recorder.background("server_log", line=line)

    def rss(pid):
        value = original_rss(pid)
        if value is None:
            recorder.background("telemetry_missing", field="owned_server_rss", pid=pid)
            recorder.errors.append("owned server RSS sample absent")
        return value

    with patch.object(runtime, "QwenSession", Session), patch.object(online, "capture_server_line", capture), patch.object(runtime, "owned_rss", rss):
        with tf.session_for(profile) as session:
            yield session


def force_target(session, recorder, ids, raw_index, *, cache_prompt, initial_bias=100,
                 require_cold_prefix=False, target_piece=None, probe_k_values=None):
    from scripts.diag_p106b_teacher_tf import payload
    from scripts.p106b_alm_utf8_probability import (
        NativeNotForcedError, build_direct_payload, parse_native_response,
    )
    if type(raw_index) is not int or not 0 < raw_index < len(ids):
        raise ValueError("positive raw target index and original prefix required")
    if target_piece is not None:
        from scripts.p106b_alm_utf8_probability import piece_is_complete_utf8
        if not piece_is_complete_utf8(target_piece):
            if cache_prompt or not require_cold_prefix:
                raise ValueError("UTF-8 probe requires actual original cold prefix")
            return probe_target(session, recorder, ids, raw_index, initial_bias=initial_bias,
                                k_values=probe_k_values, reference_piece=target_piece)
    vocab_size = getattr(recorder, "native_vocab_size", None)
    if type(vocab_size) is not int or vocab_size < 2:
        raise ValueError("actual native vocabulary registry required for direct target")
    target, attempts = ids[raw_index], []
    biases = (100, 200) if initial_bias == 100 else (200,) if initial_bias == 200 else ()
    if not biases:
        raise ValueError("only preregistered bias100/200 allowed")
    for bias in biases:
        session.check()
        value = payload(ids[:raw_index], target, bias)
        value["cache_prompt"] = cache_prompt
        value = build_direct_payload(value, vocab_size=vocab_size)
        reply = session.request("/completion", value, timeout=90)
        actual = parse_native_response(reply, request_payload=value, vocab_size=vocab_size,
            expected_token_id=target, expected_piece_bytes=target_piece,
            require_cold_prefix=require_cold_prefix)
        observed = dict(chosen=actual["raw_chosen"], top=actual["raw_top_logprobs"])
        attempt = dict(request_attempt=recorder.request_serial, bias=bias,
                       target_id=target, actual_id=observed["chosen"]["id"], observed=observed,
                       actual_status=actual["status"])
        attempts.append(attempt)
        recorder.append("target_attempt", row_id=recorder.row["row_id"],
                        raw_index=raw_index, shifted_index=raw_index - 1,
                        cache_prompt=cache_prompt, **attempt)
        if actual["status"] == "FORCED":
            return dict(raw_index=raw_index, shifted_index=raw_index - 1, target_id=target,
                        raw_logprob=observed["chosen"]["logprob"], bias=bias,
                        observed=observed, attempts=attempts,
                        native_prefix_ids_sha256=object_sha(ids[:raw_index]),
                        probability_origin="native.completion_probabilities[0].logprob")
    raise NativeNotForcedError(actual,
        "reference target ID not forced after100/200; not an answer-correctness verdict")


class TargetMissingFromBoundedTopK(ValueError):
    """유효한 probe를 선택했으나 원 reference ID가 반환 top-K에 없다."""


def probe_target(session,recorder,ids,raw_index,*,initial_bias=100,probe=None,k_values=None,bias_values=None,
                 reference_piece=None):
    from scripts.diag_p106b_teacher_tf import payload
    from scripts.p106b_alm_utf8_probability import (
        ALLOWED_N_PROBS, NativeNotForcedError, build_probe_payload, parse_probe_response,
    )
    if type(raw_index) is not int or not 0 < raw_index < len(ids):
        raise ValueError("positive raw target index and original prefix required")
    probes=getattr(recorder,"ascii_probes",None)
    if not probes:raise ValueError("actual native ASCII probe registry required")
    probe=probes[0] if probe is None else probe
    if probe not in probes:
        raise ValueError("probe is not in the actual native ASCII registry")
    if reference_piece is not None and type(reference_piece) is not bytes:
        raise ValueError("original reference piece must be immutable bytes")
    biases=(100,200) if initial_bias==100 else (200,) if initial_bias==200 else ()
    if bias_values is not None:
        if tuple(bias_values) not in ((100,),(200,),(100,200)):raise ValueError("unregistered probe bias subset")
        biases=tuple(bias_values)
    if not biases:raise ValueError("only preregistered probe bias100/200 allowed")
    ks = ALLOWED_N_PROBS if k_values is None else tuple(k_values)
    if ks not in (ALLOWED_N_PROBS, *((value,) for value in ALLOWED_N_PROBS)):
        raise ValueError("only registered full K order or one same-K control allowed")
    attempts=[];target=ids[raw_index]
    for k in ks:
        forced = False
        for bias in biases:
            session.check()
            value=build_probe_payload(payload(ids[:raw_index],target,bias),probe=probe,n_probs=k,bias=bias)
            reply=session.request("/completion",value,timeout=90)
            try:
                observed=parse_probe_response(reply,request_payload=value,probe=probe,reference_target_id=target)
            except NativeNotForcedError as exc:
                # 실제 envelope/확률 계약이 유효한 다른 선택만 제한 bias 재시도한다.
                not_forced = exc
                attempt = dict(request_attempt=recorder.request_serial, k=k, bias=bias,
                    status="PROBE_NOT_FORCED", actual_ids=[exc.observed["raw_chosen"]["id"]])
                attempts.append(attempt)
                recorder.append("probe_target_attempt", row_id=recorder.row["row_id"], raw_index=raw_index, **attempt)
                continue
            forced = True
            attempt={key:observed[key] for key in ("status","reference_target_id","target_logprob","target_rank",
                "target_probability_origin","requested_n_probs","actual_n_probs","bias","probe_id","chosen_probe",
                "top_k_probability_mass","known_probability_mass_including_probe","mass_equals_one","mass_exceeds_one","mass_policy")}
            attempt["request_attempt"]=recorder.request_serial
            if observed["status"] == "FOUND":
                if reference_piece is not None and observed["raw_target"]["bytes"] != list(reference_piece):
                    raise ValueError("raw top-K reference ID bytes differ from the original native piece")
                attempt["raw_target"] = observed["raw_target"]
            attempts.append(attempt);recorder.append("probe_target_attempt",row_id=recorder.row["row_id"],raw_index=raw_index,**attempt)
            if observed["status"]=="FOUND":
                return dict(raw_index=raw_index,shifted_index=raw_index-1,target_id=target,
                    raw_logprob=observed["target_logprob"],bias=bias,probability_origin=observed["target_probability_origin"],
                    observed=dict(chosen_probe=observed["chosen_probe"],reference_target=dict(id=target,logprob=observed["target_logprob"]),
                        top=observed["raw_top2"]),
                    probe=attempt,attempts=attempts,native_prefix_ids_sha256=object_sha(ids[:raw_index]),
                    reference_piece_hex=None if reference_piece is None else reference_piece.hex())
            # target 누락은 bias로 바뀌지 않는다. 같은 K의 두 번째 강제는 하지 않는다.
            break
        if not forced:
            raise not_forced
    raise TargetMissingFromBoundedTopK(
        "original target absent from bounded native top-K " + str(list(ks)) + "; no zero/imputed logp")


def native_ascii_registry(session,recorder,special_ids):
    from scripts import p106b_qwen_teacher as profile
    from scripts.p106b_mtp_teacher import gguf_metadata
    from scripts.p106b_alm_bytes import teacher_piece_bytes
    from scripts.p106b_alm_utf8_probability import ValidatedAsciiProbe
    with regular(profile.MODEL).open("rb") as stream:header=gguf_metadata(stream)
    emb=header["tensors"].get("token_embd.weight",{}).get("shape")
    head=header["tensors"].get("output.weight",{}).get("shape")
    if not emb or emb!=head or len(emb)!=2:raise ValueError("native GGUF embedding/output vocabulary proof required")
    vocab=emb[1];probes=[]
    for literal in ("A","B"):
        recorder.kind="native_ascii_probe_registry"
        results=[]
        for parse in (False,True):
            values=piece_rows(session.request("/tokenize",dict(content=literal,add_special=False,parse_special=parse,with_pieces=True),timeout=90))
            if len(values)!=1 or teacher_piece_bytes(values[0]["piece"])!=literal.encode("ascii"):
                raise ValueError("normal ASCII literal must be one unchanged native piece")
            results.append(values[0]["id"])
        if results[0]!=results[1]:raise ValueError("special parsing changes ASCII probe identity")
        probes.append(ValidatedAsciiProbe(results[0],literal.encode("ascii"),vocab,tuple(sorted(special_ids))))
    if probes[0].token_id==probes[1].token_id:raise ValueError("two independent native ASCII probe IDs required")
    recorder.ascii_probes=probes
    recorder.native_vocab_size=vocab
    recorder.append("native_ascii_probe_registry",vocab_size=vocab,embedding_shape=emb,output_shape=head,
        probes=[dict(token_id=p.token_id,piece_hex=p.piece_bytes.hex()) for p in probes],
        ordinary_token_evidence="PARSE_SPECIAL_FALSE_AND_TRUE_IDENTICAL_NATIVE_SINGLE_ID_BYTES; NOT_A_GLOBAL_SPECIAL_REGISTRY")
    recorder.report["ascii_probe_registry"]=dict(vocab_size=vocab,
        probes=[dict(token_id=p.token_id,piece_hex=p.piece_bytes.hex()) for p in probes])


def validate_probe_controls(controls, registry):
    """네 개라는 개수뿐 아니라 같은 사건의 정확2×2와 모든 교차값을 검사한다."""
    from scripts.p106b_alm_utf8_probability import ALLOWED_N_PROBS, ValidatedAsciiProbe
    if not isinstance(registry, dict) or not isinstance(registry.get("probes"), list) or len(registry["probes"]) != 2:
        raise ValueError("closed actual two-probe registry required")
    probes = []
    for item in registry["probes"]:
        probes.append(ValidatedAsciiProbe(item["token_id"], bytes.fromhex(item["piece_hex"]),
                                         registry["vocab_size"], ()))
    probe_ids = {probe.token_id for probe in probes}
    if len(probe_ids) != 2 or not isinstance(controls, list) or len(controls) != 4:
        raise ValueError("exact four distinct native probe/bias combinations required")
    combinations = [(value.get("probe_id"), value.get("bias")) for value in controls]
    if (any(type(a) is not int or type(b) is not int for a, b in combinations)
            or len(set(combinations)) != 4
            or set(combinations) != {(probe, bias) for probe in probe_ids for bias in (100, 200)}):
        raise ValueError("exact A/B x100/200 control combinations required")
    k = controls[0].get("k")
    reference = controls[0]["direct"]
    prefix_sha = reference.get("native_prefix_ids_sha256")
    if (type(k) is not int or k not in ALLOWED_N_PROBS or not isinstance(prefix_sha, str)
            or len(prefix_sha) != 64 or any(char not in "0123456789ABCDEF" for char in prefix_sha)
            or type(reference.get("raw_index")) is not int or reference["raw_index"] <= 0):
        raise ValueError("one registered K and exact original prefix identity required")
    checks = []
    for control in controls:
        direct, found = control["direct"], control["probe_result"]
        lookup = found.get("probe", {})
        rank = lookup.get("target_rank")
        if (control.get("k") != k or control.get("raw_index") != reference["raw_index"]
                or direct.get("bias") != control["bias"] or found.get("bias") != control["bias"]
                or direct.get("requested_n_probs") != k or direct.get("actual_n_probs") != min(k, registry["vocab_size"])
                or found.get("probe", {}).get("requested_n_probs") != k
                or found.get("probe", {}).get("actual_n_probs") != min(k, registry["vocab_size"])
                or found.get("probe", {}).get("status") != "FOUND"
                or found.get("probe", {}).get("probe_id") != control["probe_id"]
                or lookup.get("bias") != control["bias"]
                or type(rank) is not int or not 1 <= rank <= min(k, registry["vocab_size"])
                or lookup.get("reference_target_id") != reference["target_id"]
                or lookup.get("target_logprob") != found["raw_logprob"]
                or lookup.get("raw_target", {}).get("id") != reference["target_id"]
                or lookup.get("raw_target", {}).get("logprob") != found["raw_logprob"]
                or lookup.get("raw_target", {}).get("bytes") != direct.get("observed", {}).get("chosen", {}).get("bytes")
                or found.get("observed", {}).get("chosen_probe", {}).get("id") != control["probe_id"]
                or direct.get("observed", {}).get("chosen", {}).get("id") != reference["target_id"]
                or direct.get("observed", {}).get("chosen", {}).get("logprob") != direct["raw_logprob"]
                or control.get("comparison", {}).get("passed") is not True):
            raise ValueError("same-K actual control identity differs")
        checks.append(dict(probe_id=control["probe_id"], bias=control["bias"],
            pair=compare_reference_scores(direct, found),
            reference_to_direct=compare_reference_scores(reference, direct),
            reference_to_probe=compare_reference_scores(reference, found)))
    return dict(passed=True, k=k, native_prefix_ids_sha256=prefix_sha,
                reference_target_id=reference["target_id"], raw_index=reference["raw_index"],
                exact_combinations=sorted([list(value) for value in combinations]), comparisons=checks,
                scope="SAME_PREFIX_SAME_K_ALL_A_B_X100_200_REFERENCE_TARGET_AND_RAW_TOP2")


def probe_controls(session, recorder, ids, raw_index, *, target_piece):
    """같은 K에서4쌍과 네 조건 전체를 검사한다. 누락 때만 K를 올린다."""
    from scripts.diag_p106b_teacher_tf import payload
    from scripts.p106b_alm_utf8_probability import (
        ALLOWED_N_PROBS, NativeNotForcedError, build_direct_payload, parse_native_response,
    )
    if len(recorder.ascii_probes) != 2:
        raise ValueError("two actual native probes required before controls")
    for k in ALLOWED_N_PROBS:
        controls, missing = [], False
        recorder.report["normal_forcing_probe_controls"] = controls
        for probe in recorder.ascii_probes:
            for bias in (100, 200):
                recorder.kind = "normal_target_direct_probe_control"
                value = build_direct_payload(payload(ids[:raw_index], ids[raw_index], bias),
                    vocab_size=recorder.native_vocab_size, n_probs=k)
                reply = session.request("/completion", value, timeout=90)
                actual = parse_native_response(reply, request_payload=value,
                    vocab_size=recorder.native_vocab_size, expected_token_id=ids[raw_index],
                    expected_piece_bytes=target_piece, require_cold_prefix=True)
                if actual["status"] != "FORCED":
                    raise NativeNotForcedError(actual, "fixed control bias did not force original normal target")
                direct = dict(target_id=ids[raw_index], raw_index=raw_index, bias=bias,
                    requested_n_probs=k, actual_n_probs=actual["actual_n_probs"],
                    native_prefix_ids_sha256=object_sha(ids[:raw_index]),
                    raw_logprob=actual["raw_chosen"]["logprob"],
                    observed=dict(chosen=actual["raw_chosen"], top=actual["raw_top2"]))
                try:
                    found = probe_target(session, recorder, ids, raw_index, initial_bias=bias,
                        probe=probe, k_values=(k,), bias_values=(bias,), reference_piece=target_piece)
                except TargetMissingFromBoundedTopK:
                    missing = True
                    recorder.append("normal_control_k_missing", k=k, probe_id=probe.token_id,
                                    bias=bias, completed_pairs=len(controls))
                    break
                comparison = compare_reference_scores(direct, found)
                control = dict(probe_id=probe.token_id, bias=bias, k=k, raw_index=raw_index,
                    direct=direct, probe_result=found, comparison=comparison)
                controls.append(control)
                recorder.append("normal_forcing_probe_control", control=control)
                # 이미 관측된 교차 불일치를 뒤의 누락/K 상향으로 가리지 않는다.
                compare_reference_scores(controls[0]["direct"], direct)
                compare_reference_scores(controls[0]["direct"], found)
            if missing:
                break
        if missing:
            continue
        recorder.report["normal_forcing_probe_controls"] = controls
        matrix = validate_probe_controls(controls, recorder.report["ascii_probe_registry"])
        recorder.report["normal_forcing_probe_matrix"] = matrix
        recorder.append("normal_forcing_probe_controls", controls=controls, matrix=matrix)
        return
    raise TargetMissingFromBoundedTopK("normal original target absent from bounded same-K control matrix")


def teacher_special_registry(session, recorder, rows):
    from scripts.p106b_alm_bytes import teacher_piece_bytes
    literals = sorted({bytes.fromhex(value["source_bytes_hex"]).decode("utf-8")
                       for row in rows for value in row["student"]["specials"]}
                      | {"<think>", "</think>"})
    if not {"<|im_start|>", "<|im_end|>"} <= set(literals):
        raise ValueError("literal native ChatML markers required")
    result = {}
    for literal in literals:
        recorder.kind = "special_native_id_probe"
        values = piece_rows(session.request("/tokenize", tokenize_payload(literal, with_pieces=True), timeout=90))
        if len(values) != 1 or teacher_piece_bytes(values[0]["piece"]) != literal.encode("utf-8"):
            raise ValueError("teacher must recognize each literal ChatML special as one native ID")
        token = values[0]["id"]
        if token in result and result[token] != literal:
            raise ValueError("teacher special IDs alias different literal markers")
        result[token] = literal
    recorder.append("teacher_special_registry", native_id_to_literal=result)
    return result


def native_teacher_input(session, recorder, row):
    """Real renderer owns template bytes; reference answer is NEVER rendered/trimmed."""
    messages=row["source_row"]["messages"]
    if [m.get("role") for m in messages] != ["user","assistant"]:
        raise ValueError("fixed original two-turn QA required")
    question,answer=map(message_text,messages)
    rendered_question = question.strip()
    if not rendered_question or not answer:
        raise ValueError("nonempty original user and reference body required")
    request=dict(messages=[dict(role="user",content=question)],add_generation_prompt=True,
                 chat_template_kwargs=dict(enable_thinking=False))
    recorder.kind="native_no_thinking_template"
    reply=session.request("/apply-template",request,timeout=90)
    prefix=reply.get("prompt") if isinstance(reply,dict) else None
    if (not isinstance(prefix,str) or prefix.count(rendered_question)!=1
            or "<|im_start|>assistant" not in prefix):
        raise ValueError("native prefix must preserve original user content except declared native edge trim")
    suffix=prefix.rsplit("<|im_start|>assistant",1)[1]
    if (suffix.count("<think>")!=1 or suffix.count("</think>")!=1
            or suffix.index("</think>")<suffix.index("<think>")
            or not suffix.rstrip().endswith("</think>")):
        raise ValueError("native thinking=false must actually close its empty reasoning prefix")
    inside=suffix.split("<think>",1)[1].split("</think>",1)[0]
    if inside.strip():raise ValueError("no generated reasoning content may precede the reference answer")
    spans=row["student"]["loss_spans_chars"]
    if len(spans)!=1 or row["text"][spans[0][0]:spans[0][0]+len(answer)]!=answer:
        raise ValueError("original exact assistant body boundary differs")
    start=len(row["text"][:spans[0][0]].encode("utf-8"))
    teacher_start=len(prefix.encode("utf-8"));body_bytes=len(answer.encode("utf-8"))
    text=prefix+answer+"<|im_end|>\n"
    return dict(teacher_text=text,teacher_text_sha256=sha(text.encode("utf-8")),
        teacher_prefix=prefix,teacher_prefix_sha256=sha(prefix.encode("utf-8")),
        template_request=request,teacher_contract=TEACHER_CONTRACT,
        student_body_span=[start,start+body_bytes],teacher_body_span=[teacher_start,teacher_start+body_bytes],
        question_sha256=sha(question.encode("utf-8")),answer_sha256=sha(answer.encode("utf-8")),
        rendered_question_sha256=sha(rendered_question.encode("utf-8")),
        native_question_edge_trim=dict(applied=question!=rendered_question,
            leading_bytes=len(question.encode("utf-8"))-len(question.lstrip().encode("utf-8")),
            trailing_bytes=len(question.encode("utf-8"))-len(question.rstrip().encode("utf-8")),
            original_question=question, rendered_question=rendered_question,
            operation="OFFICIAL_NATIVE_TEMPLATE_USER_EDGE_TRIM_ONLY"),
        full_templates_identical=False,student_source_modified=False)


def cache_row(session, recorder, row, special_ids, *, cache_prompt, verify_all_cache=False,
              native_template=False, cold_replicate=False):
    from scripts.p106b_alm_bytes import align_assistant_chunks
    student = rebuild_student(row)
    recorder.row = dict(row_id=row["row_id"], teacher_ids=[])
    recorder.append("frozen_source_row", row=row)
    native=None
    if native_template:
        if cache_prompt or not cold_replicate:
            raise ValueError("V7 native template contract requires cold-only replication")
        native=native_teacher_input(session,recorder,row)
        recorder.append("native_teacher_input",row_id=row["row_id"],**native)
    text=native["teacher_text"] if native else row["text"]
    recorder.kind = "full_input_native_ids"
    ids = token_ids(session.request("/tokenize", tokenize_payload(text, with_pieces=False), timeout=90))
    recorder.kind = "full_input_native_pieces"
    pieces = piece_rows(session.request("/tokenize", tokenize_payload(text, with_pieces=True), timeout=90))
    projection=None
    if native:
        from scripts.p106b_alm_template_alignment import align_answer_contents
        teacher=teacher_stream(dict(text=text,student=dict(loss_spans_bytes=[native["teacher_body_span"]])),ids,pieces,special_ids)
        projection=align_answer_contents(student,teacher,native["student_body_span"],native["teacher_body_span"])
        aligned=projection.alignment
    else:
        teacher = teacher_stream(row, ids, pieces, special_ids)
        aligned = align_assistant_chunks(student, teacher)
    if not aligned.chunks:
        raise ValueError("zero exact assistant chunks; frozen row cannot be replaced")
    selected = sorted({index for chunk in aligned.chunks for index in chunk.teacher_raw_indices})
    recorder.row = dict(row_id=row["row_id"], teacher_ids=ids)
    alignment = alignment_json(aligned)
    recorder.append("native_alignment", row_id=row["row_id"], teacher_ids=ids,
                    teacher_ids_sha256=object_sha(ids), teacher_pieces=pieces,
                    teacher_byte_spans=stream_summary(teacher), alignment=alignment,
                    selected_teacher_raw_indices=selected)
    if native and recorder.report.get("mode")=="canary" and not recorder.report.get("normal_forcing_probe_controls"):
        from scripts.p106b_alm_bytes import teacher_piece_bytes
        from scripts.p106b_alm_utf8_probability import piece_is_complete_utf8
        normal=next((index for index in selected if piece_is_complete_utf8(teacher_piece_bytes(pieces[index]["piece"]))),None)
        if normal is None:raise ValueError("first original row lacks a complete token for direct/probe canary")
        probe_controls(session, recorder, ids, normal,
                       target_piece=teacher_piece_bytes(pieces[normal]["piece"]))
    def score(index,**kwargs):
        extra={}
        if native:
            from scripts.p106b_alm_bytes import teacher_piece_bytes
            extra["target_piece"]=teacher_piece_bytes(pieces[index]["piece"])
        return force_target(session,recorder,ids,index,**extra,**kwargs)
    scores, verification, verifications = [], None, []
    cold_pass = {}
    if (cache_prompt or cold_replicate) and verify_all_cache:
        # All cold references first, then ONE increasing-prefix warm chain.
        # Interleaving OFF_i/ON_i would test same-prefix replay only, not the
        # state trajectory used by the production ON_i -> ON_(i+1) sequence.
        for raw_index in selected:
            recorder.kind = "reference_target_cold"
            cold_pass[raw_index] = score(raw_index, cache_prompt=False,
                                               **(dict(require_cold_prefix=True) if cold_replicate else {}))
    for position, raw_index in enumerate(selected):
        recorder.kind = "reference_target_cold" if position == 0 else "reference_target"
        cold = cold_pass[raw_index] if cold_pass else score(raw_index,
                            cache_prompt=cache_prompt and position > 0,
                            **(dict(require_cold_prefix=True) if cold_replicate else {}))
        if (cache_prompt or cold_replicate) and (position == 0 or verify_all_cache):
            recorder.kind = "cache_prompt_verification"
            warm = score(raw_index,
                                cache_prompt=not cold_replicate, initial_bias=cold["bias"],
                                **(dict(probe_k_values=(cold["probe"]["requested_n_probs"],))
                                   if "probe" in cold else {}),
                                **(dict(require_cold_prefix=True) if cold_replicate else {}))
            current = dict(raw_index=raw_index, cold=cold, warm=warm,
                                comparison=compare_reference_scores(cold,warm),
                                mode="COLD_COLD_REPLICATE" if cold_replicate else "COLD_WARM")
            if position == 0:verification=current
            verifications.append(current)
            recorder.append("cache_prompt_verified", row_id=row["row_id"], verification=current)
        scores.append(cold)
        recorder.report["unique_targets_completed"] += 1
    by_index = {value["raw_index"]: value for value in scores}
    for chunk in alignment["chunks"]:
        chunk["teacher_raw_logprob_sum"] = math.fsum(by_index[index]["raw_logprob"]
                                                    for index in chunk["teacher_raw_indices"])
    total_student = aligned.student_supervised_byte_count
    total_teacher = aligned.teacher_supervised_byte_count
    student_targets = sum(token.supervised and token.special_kind is None for token in student.tokens)
    teacher_targets = sum(token.supervised and token.special_kind is None for token in teacher.tokens)
    student_kd_targets = len({index for chunk in aligned.chunks for index in chunk.student_raw_indices})
    assistant_spans = row["student"]["loss_spans_bytes"]
    reference_bytes = sum(right - left for left, right in assistant_spans) - sum(
        max(0, min(token.byte_end, right) - max(token.byte_start, left))
        for token in student.tokens if token.special_kind is not None for left, right in assistant_spans)
    result = dict(schema=SCHEMA, row_id=row["row_id"], selection_index=row["selection_index"],
                  language=row["language"], semantic_root_id=row["semantic_root_id"],
                  source_row_sha256=row["source_row_sha256"], prepared_row_sha256=row["prepared_row_sha256"],
                  text=row["text"], text_sha256=row["text_sha256"], student=row["student"], source_row=row["source_row"],
                  teacher_ids=ids, teacher_ids_sha256=object_sha(ids), teacher_pieces=pieces,
                  teacher_byte_spans=stream_summary(teacher), alignment=alignment, target_scores=scores,
                  cache_prompt=cache_prompt, cache_verification=verification,
                  cache_verifications=verifications,
                  cache_verification_scope=("NO_CACHE_VERIFICATION" if not cache_prompt else
                      "ALL_COLD_THEN_INCREMENTAL_WARM" if verify_all_cache else "FIRST_SELECTED_TARGET_PER_ROW"),
                  ce_targets=row["student"]["ce_targets"], kd_chunks=len(aligned.chunks),
                  teacher_targets=len(selected), covered_bytes=aligned.covered_byte_count,
                  student_supervised_targets=student_targets, teacher_supervised_targets=teacher_targets,
                  student_kd_targets=student_kd_targets,
                  reference_assistant_non_special_bytes=reference_bytes,
                  student_supervised_bytes=total_student, teacher_supervised_bytes=total_teacher,
                  student_target_acceptance=student_kd_targets / student_targets if student_targets else 0.,
                  teacher_target_acceptance=len(selected) / teacher_targets if teacher_targets else 0.,
                  student_byte_acceptance=aligned.covered_byte_count / total_student if total_student else 0.,
                  teacher_byte_acceptance=aligned.covered_byte_count / total_teacher if total_teacher else 0.,
                  reference_byte_acceptance=aligned.covered_byte_count / reference_bytes if reference_bytes else 0.,
                  eot_kd=False, eot_ce=True, quality_claim=False)
    if native:
        result.update(native_teacher_input=native,answer_projection=projection.metadata,
            cache_verification_scope="ALL_COLD_REPLICATES" if verify_all_cache else "FIRST_TARGET_COLD_REPLICATE_PER_ROW",
            verification_legacy_field_note="warm key contains a second COLD result; actual cache_prompt=False in every payload")
    result["cache_row_sha256"] = object_sha(result)
    recorder.append("cache_row_complete", row_id=row["row_id"], cache_row_sha256=result["cache_row_sha256"],
                    ce_targets=result["ce_targets"], kd_chunks=result["kd_chunks"], teacher_targets=len(selected))
    recorder.row = None
    return result


def language_totals(rows):
    result = {}
    for language in ("ko", "en"):
        selected = [row for row in rows if row["language"] == language]
        values = {key: sum(row[key] for row in selected) for key in
                  ("ce_targets", "kd_chunks", "teacher_targets", "covered_bytes",
                   "student_supervised_targets", "teacher_supervised_targets", "student_kd_targets",
                   "reference_assistant_non_special_bytes",
                   "student_supervised_bytes", "teacher_supervised_bytes")}
        values["rows"] = len(selected)
        values["student_byte_acceptance"] = values["covered_bytes"] / values["student_supervised_bytes"] if values["student_supervised_bytes"] else 0.
        values["teacher_byte_acceptance"] = values["covered_bytes"] / values["teacher_supervised_bytes"] if values["teacher_supervised_bytes"] else 0.
        values["student_target_acceptance"] = values["student_kd_targets"] / values["student_supervised_targets"] if values["student_supervised_targets"] else 0.
        values["teacher_target_acceptance"] = values["teacher_targets"] / values["teacher_supervised_targets"] if values["teacher_supervised_targets"] else 0.
        values["reference_byte_acceptance"] = values["covered_bytes"] / values["reference_assistant_non_special_bytes"] if values["reference_assistant_non_special_bytes"] else 0.
        result[language] = values
    return result


def failed_target_recovery(rows, registry):
    """원 실패 사건의 실제 조회 metadata 없이는17행 완료를 복구 PASS로 쓰지 않는다."""
    from scripts.p106b_alm_bytes import teacher_piece_bytes
    from scripts.p106b_alm_utf8_probability import ALLOWED_N_PROBS, TARGET_ORIGIN
    expected = FAILED_TARGET_EXPECTATION
    selected = [row for row in rows if row.get("selection_index") == expected["selection_index"]]
    if len(selected) != 1 or selected[0].get("row_id") != "alm_000034":
        raise ValueError("failed original selection34 must be present exactly once")
    row = selected[0]
    scores = [value for value in row.get("target_scores", [])
              if value.get("target_id") == expected["target_id"]
              and value.get("native_prefix_ids_sha256") == expected["native_prefix_ids_sha256"]]
    if len(scores) != 1:
        raise ValueError("original failed target/prefix event was not actually recovered")
    score = scores[0]
    index, ids, pieces = score.get("raw_index"), row.get("teacher_ids", []), row.get("teacher_pieces", [])
    if (type(index) is not int or not 0 < index < len(ids) or len(pieces) != len(ids)
            or ids[index] != expected["target_id"] or pieces[index].get("id") != expected["target_id"]
            or object_sha(ids[:index]) != expected["native_prefix_ids_sha256"]
            or teacher_piece_bytes(pieces[index]["piece"]).hex() != expected["piece_hex"]):
        raise ValueError("failed native target ID/piece/prefix identity differs")
    checks = [value for value in row.get("cache_verifications", []) if value.get("raw_index") == index]
    if len(checks) != 1 or checks[0].get("mode") != "COLD_COLD_REPLICATE":
        raise ValueError("failed target requires its own two independent cold observations")
    check = checks[0]
    compare_reference_scores(score, check["cold"])
    comparison = compare_reference_scores(check["cold"], check["warm"])
    allowed_probes = {value["token_id"] for value in registry["probes"]}
    k = score.get("probe", {}).get("requested_n_probs")
    if type(k) is not int or k not in ALLOWED_N_PROBS or len(allowed_probes) != 2:
        raise ValueError("bounded K and actual two-probe registry required for failed target")
    observations = []
    for label, value in (("saved", score), ("cold", check["cold"]), ("replicate", check["warm"])):
        probe = value.get("probe", {})
        chosen = value.get("observed", {}).get("chosen_probe", {})
        target = probe.get("raw_target", {})
        rank = probe.get("target_rank")
        if (value.get("raw_index") != index or value.get("target_id") != expected["target_id"]
                or value.get("native_prefix_ids_sha256") != expected["native_prefix_ids_sha256"]
                or value.get("reference_piece_hex") != expected["piece_hex"]
                or value.get("probability_origin") != TARGET_ORIGIN
                or probe.get("status") != "FOUND" or probe.get("requested_n_probs") != k
                or probe.get("actual_n_probs") != min(k, registry["vocab_size"])
                or type(rank) is not int or not 1 <= rank <= min(k, registry["vocab_size"])
                or type(value.get("bias")) is not int or value["bias"] not in (100, 200)
                or probe.get("bias") != value["bias"] or probe.get("target_logprob") != value["raw_logprob"]
                or probe.get("reference_target_id") != expected["target_id"]
                or probe.get("target_probability_origin") != TARGET_ORIGIN
                or target.get("id") != expected["target_id"] or target.get("bytes") != list(bytes.fromhex(expected["piece_hex"]))
                or target.get("logprob") != value["raw_logprob"]
                or value.get("observed", {}).get("reference_target") != dict(id=expected["target_id"], logprob=value["raw_logprob"])
                or chosen.get("id") not in allowed_probes or chosen["id"] == expected["target_id"]
                or probe.get("probe_id") != chosen["id"]
                or probe.get("chosen_probe") != chosen):
            raise ValueError("failed event must be real FOUND reference probability, never selected probe/imputation")
        observations.append(dict(kind=label, probe_id=chosen["id"], bias=value["bias"],
                                 raw_logprob=value["raw_logprob"], k=k))
    return dict(expected, passed=True, row_id=row["row_id"], raw_index=index,
                recovery="NATIVE_RAW_TOPK_FOUND_WITH_TWO_COLD_OBSERVATIONS", observations=observations,
                comparison=comparison, quality_claim=False)


def prerequisite():
    from scripts.p106b_shards import verify
    report = read_json(TF_REPORT)
    if (report.get("status") != "TF_SIGNAL_CANARY_COMPLETE" or report.get("returncode") != 0
            or report.get("mtp") is not False or report.get("spec_type") != "none"
            or not report.get("sources_unchanged") or len(report.get("cases", [])) != 2
            or not all(value.get("passed") for value in report["cases"])):
        raise ValueError("closed successful Stage7a native-probability prerequisite required")
    for name, expected in report["source_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Stage7a source has changed since probability validation")
    verify(TF_REPORT.parent, report["raw_manifest"])
    return digest(TF_REPORT)


def batch_identity(code, prepared_sha, rows, tf_sha, *, cache_prompt, batch_index):
    from scripts import p106b_qwen_teacher as profile
    return dict(schema=SCHEMA, source_code_sha256=code, prepared_report_sha256=prepared_sha,
                prepared_row_sha256=[row["prepared_row_sha256"] for row in rows],
                source_report_sha256=SOURCE_REPORT_SHA, tokenizer_sha256=TOKENIZER_SHA,
                tf_prerequisite_report_sha256=tf_sha, teacher_model_sha256=profile.MODEL_SHA,
                teacher_runtime_sha256=profile.LIBRARIES, batch_index=batch_index,
                cache_prompt=cache_prompt, bias_order=[100, 200], absolute_tolerance=ATOL,
                teacher_context=TEACHER_CONTEXT, spec_type="none", mtp=False,
                teacher_conditioning_contract=TEACHER_CONTRACT,
                expected_language_rows=dict(Counter(row["language"] for row in rows)),
                utf8_probability_policy="DIRECT_COMPLETE_PIECE_ELSE_ASCII_PROBE_RAW_TOPK_64_512_2048; MASS_OBSERVATION_ONLY",
                teacher_template_kwargs=dict(enable_thinking=False),
                alignment_scope="ANSWER_CONTENT_BYTES_ONLY",
                canary_failed_target_expectation=dict(FAILED_TARGET_EXPECTATION),
                cold_replicate_tolerance=ATOL)


def closed_batch(directory, identity, *, canary=False):
    from scripts.p101a_sft_mtp_data import stream_rows
    from scripts.p106b_shards import verify
    report = read_json(directory / "report.json")
    if not isinstance(identity.get("expected_language_rows"),dict):
        raise ValueError("explicit expected language/count identity required")
    if canary and (len(identity["prepared_row_sha256"]) != BATCH_SIZE + 1
                   or identity["expected_language_rows"] != {"ko": 9, "en": 8}):
        raise ValueError("closed canary must retain original16 plus failed34 with ko9/en8")
    wanted = "ALM_CANARY_COMPLETE" if canary else "ALM_CACHE_BATCH_COMPLETE"
    if (report.get("schema") != SCHEMA or report.get("status") != wanted or report.get("returncode") != 0
            or report.get("identity") != identity or report.get("rows_completed") != len(identity["prepared_row_sha256"])
            or any(report.get("language_totals",{}).get(language,{}).get("rows")!=count
                   for language,count in identity["expected_language_rows"].items())
            or not all(report.get(key) is True for key in
                       ("sources_unchanged", "inputs_unchanged", "teacher_assets_unchanged"))
            or report.get("owned_threads_closed") is not True
            or report.get("telemetry_errors") or report.get("raw_persistence_errors")):
        raise ValueError("old/partial/incompatible batch preserved; reuse forbidden")
    verify(directory, report["raw_manifest"])
    rows = list(stream_rows(directory, report["cache_manifest"]))
    if len(rows) != len(identity["prepared_row_sha256"]) or [row["prepared_row_sha256"] for row in rows] != identity["prepared_row_sha256"]:
        raise ValueError("closed cache rows differ")
    hashes = []
    for row in rows:
        value = dict(row)
        expected = value.pop("cache_row_sha256")
        if object_sha(value) != expected:
            raise ValueError("cached row content SHA differs")
        if identity.get("teacher_conditioning_contract") == TEACHER_CONTRACT:
            native = row.get("native_teacher_input", {})
            projection = row.get("answer_projection", {})
            checks = row.get("cache_verifications", [])
            if (row.get("cache_prompt") is not False
                    or native.get("teacher_contract") != TEACHER_CONTRACT
                    or native.get("student_source_modified") is not False
                    or projection.get("alignment_scope") != "ANSWER_CONTENT_BYTES_ONLY"
                    or projection.get("full_template_equality_claim") is not False
                    or not checks or any(c.get("mode") != "COLD_COLD_REPLICATE"
                        or c.get("comparison", {}).get("passed") is not True for c in checks)
                    or (canary and len(checks) != row.get("teacher_targets"))):
                raise ValueError("native-template cold-only row contract differs")
        hashes.append(expected)
    if hashes != report.get("cache_row_sha256") or language_totals(rows) != report["language_totals"]:
        raise ValueError("closed report does not describe immutable rows")
    if canary:
        matrix = validate_probe_controls(report.get("normal_forcing_probe_controls"),
                                         report.get("ascii_probe_registry"))
        if matrix != report.get("normal_forcing_probe_matrix"):
            raise ValueError("closed exact same-K four-control cross matrix differs")
        recovery = failed_target_recovery(rows, report["ascii_probe_registry"])
        if recovery != report.get("failed_target_recovery"):
            raise ValueError("closed failed original target recovery metadata differs")
    return report


def execute(args):
    from scripts import p106b_qwen_teacher as profile
    from scripts.diag_p106b_teacher_tf import command
    from scripts.p106b_gate_runtime import wall_limit, idle_before_gpu
    from scripts.p106b_shards import ShardWriter, verify
    began = time.perf_counter()
    budget = Budget(args.max_wall_sec, deadline_value(args.deadline))
    before = time.perf_counter()
    code = sources()
    timings = dict(source_code_hash_before_seconds=time.perf_counter() - before)
    before = time.perf_counter()
    prepared, all_rows = load_prepared(code)
    timings["prepared_selection_read_seconds"] = time.perf_counter() - before
    before = time.perf_counter()
    tf_sha = prerequisite()
    timings["tf_prerequisite_verify_seconds"] = time.perf_counter() - before
    batch_index = 0 if args.canary else args.batch_index
    rows = canary_rows(all_rows) if args.canary else all_rows[batch_index * BATCH_SIZE:(batch_index + 1) * BATCH_SIZE]
    identity = batch_identity(code, digest(PREPARED / "report.json"), rows, tf_sha,
                              cache_prompt=args.cache_prompt, batch_index=batch_index)
    directory = CANARY if args.canary else BASE / "teacher_cache" / f"batch_{batch_index:06d}"
    regular(directory)
    if directory.exists():
        if args.canary:
            raise FileExistsError("canary/partial evidence preserved; no rerun or replacement")
        if not snapshot_matches(prepared["input_sha256"]):
            raise ValueError("original V3/VAL/tokenizer changed; old cache preserved, reuse refused")
        closed_batch(directory, identity)
        print(json.dumps(dict(status="ALM_CACHE_BATCH_REUSED", batch_index=batch_index,
                              teacher_requests=0, model_loads=0, teacher_asset_rehash="NOT_RUN_NO_MODEL_ENTRY",
                              full_cache_complete=False), ensure_ascii=False))
        return 0
    if args.cache:
        canary_identity = batch_identity(code, identity["prepared_report_sha256"], canary_rows(all_rows), tf_sha,
                                         cache_prompt=args.cache_prompt, batch_index=0)
        closed_batch(CANARY, canary_identity, canary=True)
    budget.remaining()
    new_directory(directory)
    raw = ShardWriter(directory, "raw", limit=MAX_BYTES)
    cache = ShardWriter(directory, "cache", limit=MAX_BYTES)
    report = dict(schema=SCHEMA, status="STARTED", returncode=9, identity=identity,
                  mode="canary" if args.canary else "cache", rows_planned=len(rows),
                  language_selected_ce_targets={language: sum(row["student"]["ce_targets"] for row in rows
                      if row["language"] == language) for language in ("ko", "en")},
                  language_totals_scope="completed rows only; partial row events retained in raw shards",
                  rows_completed=0, batch_index=batch_index, batches_required=BATCHES,
                  full_cache_complete=False, production8h_resumed=False,
                  max_wall_seconds=args.max_wall_sec, deadline=args.deadline,
                  http_attempted=0, http_succeeded=0, completion_attempted=0, completion_succeeded=0,
                  cache_verification_completion_requests=0, bias200_completion_requests=0,
                  unique_targets_completed=0, student_loads=0, checkpoint_writes=0,
                  teacher_server_start_attempted=False, shutdown_reserve_seconds=SHUTDOWN_RESERVE,
                  owned_threads_closed=None,
                  cache_verification_scope=("ALL_COLD_REPLICATES" if args.canary
                                            else "FIRST_TARGET_COLD_REPLICATE_PER_ROW"),
                  teacher_conditioning_contract=TEACHER_CONTRACT,
                  teacher_template_kwargs=dict(enable_thinking=False),
                  cache_prompt=False,
                  raw_request_persistence="USER_BUFFER_FLUSH_BEFORE_HTTP; NOT_FSYNC_OR_CRASH_DURABILITY",
                  sources_unchanged=None, inputs_unchanged=None, teacher_assets_unchanged=None,
                  quality_claim=False, semantic_exhaustive_review=False,
                  teacher_probability_definition="QUANTIZED_MAIN_MODEL_PRE_SAMPLING_TARGET_LOGPROB",
                  cache_prompt_verification_overhead="separate from unique reference targets",
                  timings=timings)
    recorder, holder, completed, assets = Recorder(raw, report, budget), {}, [], None
    try:
        remaining = budget.remaining()
        if remaining < 60:
            raise TimeoutError("source preflight left less than60 seconds; no server started")
        with wall_limit(remaining):
            recorder.append("invocation", identity=identity, prepared_report_sha256=identity["prepared_report_sha256"])
            before = time.perf_counter()
            if not snapshot_matches(prepared["input_sha256"]):
                raise ValueError("original V3/VAL/tokenizer differs at teacher admission")
            report["timings"]["input_hash_before_seconds"] = time.perf_counter() - before
            before = time.perf_counter()
            assets = profile.assets(True)
            report["assets"] = assets
            report["timings"]["teacher_asset_full_hash_before_seconds"] = time.perf_counter() - before
            budget.remaining()
            idle_before_gpu()
            with recorded_session(profile, recorder, holder) as session:
                report.update(startup_seconds=session.startup_sec, props=redact(session.props, session.key),
                              redacted_command=command(profile, session.port, "<REDACTED>"))
                special_ids = teacher_special_registry(session, recorder, rows)
                native_ascii_registry(session,recorder,special_ids)
                scoring_begin = time.perf_counter()
                for row in rows:
                    session.check()
                    result = cache_row(session, recorder, row, special_ids, cache_prompt=args.cache_prompt,
                                       verify_all_cache=args.canary,
                                       native_template=True, cold_replicate=True)
                    cache.append(result)
                    completed.append(result)
                    report["rows_completed"] += 1
                    print("[ALM_ROW] " + json.dumps(dict(row_id=row["row_id"], language=row["language"],
                        ce_targets=result["ce_targets"], kd_chunks=result["kd_chunks"],
                        teacher_targets=result["teacher_targets"], rows_completed=len(completed)), ensure_ascii=False), flush=True)
                if args.canary:
                    report["normal_forcing_probe_matrix"] = validate_probe_controls(
                        report.get("normal_forcing_probe_controls"), report.get("ascii_probe_registry"))
                    report["failed_target_recovery"] = failed_target_recovery(completed, report["ascii_probe_registry"])
                    recorder.append("failed_target_recovery", metadata=report["failed_target_recovery"])
                report["timings"]["native_tokenize_and_scoring_seconds"] = time.perf_counter() - scoring_begin
                session.check()
                report["memory"] = session.memory()
                if session.errors or not session.samples:
                    raise ValueError("missing/failed200ms memory samples")
            # Full model SHA is checked after owned process teardown, not while a
            # second model/server is admitted. It is included in total cost.
            before = time.perf_counter()
            report["teacher_assets_unchanged"] = profile.assets(True) == assets
            report["timings"]["teacher_asset_full_hash_after_seconds"] = time.perf_counter() - before
            before = time.perf_counter()
            report["inputs_unchanged"] = snapshot_matches(prepared["input_sha256"])
            report["timings"]["input_hash_after_seconds"] = time.perf_counter() - before
            before = time.perf_counter()
            report["sources_unchanged"] = sources() == code
            report["timings"]["source_code_hash_after_seconds"] = time.perf_counter() - before
            budget.remaining()
            if recorder.errors:
                raise RuntimeError("raw log/telemetry persistence failed")
            if not all(report[key] for key in ("teacher_assets_unchanged", "inputs_unchanged", "sources_unchanged")):
                raise ValueError("source/VAL/tokenizer/teacher asset changed")
            if len(completed) != len(rows):
                raise ValueError("one invocation must close every original selected row")
            if args.canary and any(len(row["cache_verifications"]) != row["teacher_targets"] for row in completed):
                raise ValueError("canary must close every independent cold/cold target comparison")
            report.update(status="ALM_CANARY_COMPLETE" if args.canary else "ALM_CACHE_BATCH_COMPLETE", returncode=0)
    except BaseException as exc:
        report.update(status="ALM_CACHE_EXECUTION_PARTIAL", returncode=130 if isinstance(exc, KeyboardInterrupt) else 9,
                      error_type=type(exc).__name__, error=redact(str(exc), recorder.key)[:2500])
        recorder.background("invocation_failed", error_type=report["error_type"], error=report["error"])
    finally:
        session = holder.get("session")
        if session is not None:
            report.update(server_signals=session.signals, server_tail=list(session.tail),
                          telemetry_errors=list(session.errors), successful_memory_samples=len(session.samples),
                          owned_teacher_pid=None if session.process is None else session.process.pid,
                          owned_teacher_exitcode=None if session.process is None else session.process.poll())
            if session.process is not None and session.process.poll() is None:
                report.update(status="ALM_CACHE_OWNED_PROCESS_NOT_CLOSED", returncode=9)
        # On an interrupted run an end hash may not fit the original budget.
        # Null means NOT_VERIFIED, never an inferred unchanged/PASS. Complete
        # reports above require every full before/after check to be True.
        report["end_identity_verification"] = {
            key: "MATCH" if report[key] is True else "CHANGED" if report[key] is False else "NOT_VERIFIED_AFTER_PARTIAL_FAILURE"
            for key in ("sources_unchanged", "inputs_unchanged", "teacher_assets_unchanged")}
        report["raw_persistence_errors"] = list(recorder.errors)
        if recorder.errors or report.get("telemetry_errors"):
            report.update(status="ALM_CACHE_TELEMETRY_PARTIAL", returncode=9)
        report["language_totals"] = language_totals(completed)
        report["cache_row_sha256"] = [row["cache_row_sha256"] for row in completed]
        report["nonunique_or_verification_completion_requests"] = report["completion_attempted"] - report["unique_targets_completed"]
        recorder.background("invocation_final", status=report["status"], rows_completed=len(completed),
                        telemetry_errors=report.get("telemetry_errors", []), language_totals=report["language_totals"])
        # Serialize closing against all appenders. If a worker failed to exit,
        # the report is already negative and late writes cannot corrupt shards.
        recorder.seal()
        report["raw_persistence_errors"] = list(recorder.errors)
        if recorder.errors:
            report.update(status="ALM_CACHE_TELEMETRY_PARTIAL", returncode=9)
        for name, writer in (("raw", raw), ("cache", cache)):
            if not writer._total_rows:
                continue
            try:
                report[name + "_manifest"] = writer.close(lineage=identity)
                verify(directory, report[name + "_manifest"])
            except BaseException as exc:
                report.update(status="ALM_CACHE_PERSISTENCE_PARTIAL", returncode=9)
                report[name + "_close_error"] = redact(type(exc).__name__ + ": " + str(exc), recorder.key)[:2000]
        report["wall_seconds"] = time.perf_counter() - began
        if report["wall_seconds"] > args.max_wall_sec:
            report.update(status="ALM_CACHE_WALL_PARTIAL", returncode=9)
        report["timings"]["full_wall_including_hash_startup_shutdown_seconds"] = report["wall_seconds"]
        report["other_batches_not_observed_in_this_invocation"] = BATCHES if args.canary else BATCHES - 1
        write_json(directory / "report.json", redact(report, recorder.key))
        print("[ALM_FINAL] " + json.dumps({key: report.get(key) for key in
            ("status", "returncode", "batch_index", "rows_completed", "completion_attempted",
             "unique_targets_completed", "wall_seconds", "full_cache_complete")}, ensure_ascii=False), flush=True)
    return report["returncode"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true")
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--execute", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--canary", action="store_true")
    mode.add_argument("--cache", action="store_true")
    parser.add_argument("--batch-index", type=int)
    parser.add_argument("--cache-prompt", action="store_true")
    parser.add_argument("--deadline")
    parser.add_argument("--max-wall-sec", type=int, default=600)
    args = parser.parse_args(argv)
    if args.execute:
        if args.cache_prompt:
            parser.error("V7 native-template likelihood permits cold-only requests; warm cache is not admitted")
        if (not (args.canary or args.cache) or not args.deadline
                or not 60 <= args.max_wall_sec <= 600
                or (args.canary and args.batch_index is not None)
                or (args.cache and (args.batch_index is None or not 0 <= args.batch_index < BATCHES))):
            parser.error("execute requires canary OR cache+batch-index0..63, aware deadline and wall60..600")
    elif args.canary or args.cache or args.batch_index is not None or args.cache_prompt or args.deadline:
        parser.error("teacher-mode flags require explicit --execute")
    try:
        if args.check_only:
            print(json.dumps(dict(schema=SCHEMA, status="SOURCE_ONLY", source_sha256=sources(),
                asset_reads=0, data_reads=0, tokenizer_loads=0, model_loads=0, gpu_calls=0,
                planned_rows=1024, per_language=512, batch_size=16, batches=64,
                planned_canary_rows=17, canary_language_rows=dict(ko=9, en=8),
                output_base=str(BASE.relative_to(ROOT)),
                canary_failed_target_expectation=dict(FAILED_TARGET_EXPECTATION),
                teacher_context=1024, cache_prompt_default=False, max_wall_seconds=600,
                teacher_conditioning_contract=TEACHER_CONTRACT,
                full_cache_complete=False), ensure_ascii=False))
            return 0
        if args.prepare:
            result = prepare()
            print("[ALM_PREPARED] " + json.dumps({key: result.get(key) for key in
                ("status", "rows", "language_rows", "wall_seconds")}, ensure_ascii=False))
            return result["returncode"]
        return execute(args)
    except (ValueError, FileNotFoundError, FileExistsError, TimeoutError) as exc:
        print("[ALM_PRECHECK_ERROR] " + str(exc), file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
