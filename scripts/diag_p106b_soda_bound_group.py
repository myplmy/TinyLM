"""CPU witness for the existing producer parser with source-bound SODA groups."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from tokenizers import Tokenizer

from scripts import diag_p106b_soda_source_binding as bound
from scripts.p106b_mixed_scale import TOKENIZER, TOK_SHA
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_soda_manifest_source import canonical, digest
from scripts.p106b_soda_production_group import produce_bound_group


ROOT, io = bound.ROOT, bound.io
TAG = "p106b_soda_bound_group_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
MODEL_SHA = "A" * 64


class AuthoredInterruption(RuntimeError):
    pass


class FixtureSession:
    """Provide only authored, local responses to the real group's transport calls."""

    def __init__(self, replies, tokenizer):
        self.replies = iter(replies)
        self.tokenizer = tokenizer
        self.calls = 0

    def check(self):
        return None

    def request(self, endpoint, body, *, timeout=None):
        if endpoint == "/apply-template":
            return {"prompt": canonical(body["messages"]).decode("utf-8")}
        if endpoint == "/tokenize":
            return {"tokens": self.tokenizer.encode(body["content"], add_special_tokens=False).ids}
        if endpoint != "/v1/chat/completions":
            raise AssertionError(f"unexpected test endpoint {endpoint}")
        self.calls += 1
        response = next(self.replies)
        if isinstance(response, Exception):
            raise response
        return {"choices": [{"message": {"content": response, "reasoning_content": "PRIVATE_FIXTURE_TRACE"},
                              "finish_reason": "stop"}]}


def load(path):
    return json.loads(path.read_bytes())


def rows(directory, manifest):
    for shard in manifest["shards"]:
        yield from map(json.loads, (directory / shard["path"]).read_text(encoding="utf-8").splitlines())


def invoke(reader, cursor, tokenizer, raw, replies, task="qa", language="en"):
    session = FixtureSession(replies, tokenizer)
    result = produce_bound_group(reader, cursor, session=session, raw=raw, tokenizer=tokenizer,
                                 teacher_model_sha256=MODEL_SHA, language=language, profile=task,
                                 seed=650000 + cursor["next_row"])
    return result, session.calls


def checkpoint(directory, raw, candidates, cursor, states):
    lineage = {"scope": "AUTHORED_RESPONSE_FIXTURE", "corpus_admitted": False}
    raw_manifest, candidate_manifest = raw.close(lineage=lineage), candidates.close(lineage=lineage)
    verify(directory, raw_manifest)
    verify(directory, candidate_manifest)
    value = dict(cursor=cursor, states=states, raw_manifest=raw_manifest, candidate_manifest=candidate_manifest)
    io.write(directory / "commit.json", value)
    return value


def record(result, candidates, calls):
    if calls != len(result.request_shas):
        raise ValueError("transport calls and stored completed attempts differ")
    if result.candidate is not None:
        meta = result.candidate["meta"]
        if (meta["corpus_admitted"] or meta["candidate_status"] != "PREPARED_NOT_ADMITTED"
                or not 0 < meta["actual_x_tokens"] <= 1024 or "PRIVATE_FIXTURE_TRACE" in
                canonical(result.candidate).decode("utf-8")):
            raise ValueError("student wire lost the pending status or contains teacher reasoning")
        if meta["source_request_sha256"] != list(result.request_shas):
            raise ValueError("candidate request lineage differs")
        candidates.append(result.candidate)
    return dict(outcome=result.outcome, attempts=calls, source_raw_sha256=result.raw_sha256,
                requests=list(result.request_shas))


def tokenize():
    if io.digest(TOKENIZER) != TOK_SHA:
        raise ValueError("existing chat32 tokenizer SHA differs")
    return Tokenizer.from_file(str(TOKENIZER))


def finish():
    parent = OUT / "batch_000000"
    previous = load(parent / "commit.json")
    verify(parent, previous["raw_manifest"])
    verify(parent, previous["candidate_manifest"])
    reader, tokenizer = bound.source(), tokenize()
    directory = OUT / "batch_000001"
    raw, candidates = ShardWriter(directory, "raw"), ShardWriter(directory, "candidate")
    answers = (
        "QUESTION: 앨리스가 읽는 책은 몇 권인가요?\nANSWER: 4권입니다.\nNOTE:",
        "QUESTION: 답변 형식을 바꿔 주세요.\nANSWER: 네, 바꾸겠습니다.\nNOTE:",
        'QUESTION: 첫 질문에 다시 답해 주세요.\nANSWER: {"answer":"4권"}\nNOTE:',
    )
    result, count = invoke(reader, previous["cursor"], tokenizer, raw, answers, "multiturn", "ko")
    state = record(result, candidates, count)
    if state["outcome"] != "PREPARED" or count != 3 or result.next_cursor["next_row"] != 5:
        raise ValueError("multiturn candidate or resumed cursor differs")
    spans = result.candidate["meta"]["assistant_turn_target_counts"]
    if len(spans) != 3 or min(spans) <= 0:
        raise ValueError("each visible answer must contribute supervised tokens")
    checkpoint(directory, raw, candidates, result.next_cursor, [state])
    print("SODA_GROUP_RESUMED", count, spans, flush=True)


def run():
    OUT.mkdir()
    reader, tokenizer = bound.source(), tokenize()
    directory = OUT / "batch_000000"
    raw, candidates = ShardWriter(directory, "raw"), ShardWriter(directory, "candidate")
    cursor = reader.start()
    states = []
    plans = (
        (),
        ("invalid response", "QUESTION: What is Alice reading?\nANSWER: Volume 1.\nNOTE:"),
        (),
        ("invalid response", "still invalid", "invalid again"),
    )
    for replies in plans:
        result, count = invoke(reader, cursor, tokenizer, raw, replies)
        states.append(record(result, candidates, count))
        cursor = result.next_cursor
    if [(s["outcome"], s["attempts"]) for s in states] != [
            ("HOLD", 0), ("PREPARED", 2), ("HOLD", 0), ("REJECTED", 3)]:
        raise ValueError("hold, retry, or terminal rejection semantics differ")
    before = checkpoint(directory, raw, candidates, cursor, states)
    if before["candidate_manifest"]["rows"] != 1 or before["raw_manifest"]["rows"] != 5:
        raise ValueError("published first batch row counts differ")
    first = list(rows(directory, before["candidate_manifest"]))[0]
    original = reader.read_next(dict(reader.start(), next_row=1)).prepared
    if first["meta"]["source_group_id"] != original.parent_key:
        raise ValueError("legacy source group's original parent key changed")
    before_sha = io.digest(directory / "commit.json")
    pause_directory = OUT / "interrupted_attempt"
    partial = ShardWriter(pause_directory, "raw")
    try:
        invoke(reader, cursor, tokenizer, partial, ("invalid response", AuthoredInterruption()), "multiturn", "ko")
    except AuthoredInterruption:
        partial_manifest = partial.close(lineage={"scope": "UNCOMMITTED_AUTHORED_ATTEMPT"})
        verify(pause_directory, partial_manifest)
    else:
        raise AssertionError("authored interruption did not propagate")
    if partial_manifest["rows"] != 1 or io.digest(directory / "commit.json") != before_sha:
        raise ValueError("interrupted attempt advanced the committed position")

    child = subprocess.run([sys.executable, "-B", "-m", "scripts.diag_p106b_soda_bound_group", "resume"],
                           cwd=ROOT, timeout=45, check=True)
    final_directory = OUT / "batch_000001"
    final = load(final_directory / "commit.json")
    verify(final_directory, final["raw_manifest"])
    verify(final_directory, final["candidate_manifest"])
    old_attempt = next(rows(pause_directory, partial_manifest))
    new_attempt = next(rows(final_directory, final["raw_manifest"]))
    if (final["raw_manifest"]["rows"] != 3 or final["candidate_manifest"]["rows"] != 1 or
            old_attempt["source_request_sha256"] != new_attempt["source_request_sha256"] or
            old_attempt["source_raw_sha256"] != new_attempt["source_raw_sha256"]):
        raise ValueError("the explicitly uncommitted group was not replayed from the same source")
    import torch
    if torch.cuda.is_initialized():
        raise ValueError("source fixture initialized CUDA")
    io.write(OUT / "report.json", dict(tag=TAG, approval="WIP177", first_batch=states, final=final["states"],
             committed_cursor=final["cursor"], completed_fixture_attempts=8, interrupted_fixture_attempts=1,
             candidate_rows=2, actual_teacher_calls=0, corpus_admitted_rows=0, resume_child_exit=child.returncode,
             byte_identical_first_resumed_request=True, original_cursors_preserved=True,
             producer_sha256=io.digest(ROOT / "scripts/diag_p106b_gemma_deficit_production.py")))
    print("SODA_GROUP_RESULT", before["raw_manifest"]["rows"], final["raw_manifest"]["rows"],
          final["cursor"]["next_row"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "resume"))
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("authored response validation requires an isolated CPU")
    (run if parser.parse_args().mode == "run" else finish)()
