"""P106B Stage7b pure/mock guards; no real data/tokenizer/model/server imports.

Writing these tests is not an execution result. The root caller owns running
them. Small fixture counts exercise helper algorithms, not the runtime1024-row
selection, fixed16-row cache batch or original17-row canary contract.
"""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_alm_cache as m


def source_row(root, language="ko", *, context=None, question=None):
    context = context or "context-" + root
    question = question or "question-" + root
    return dict(messages=[dict(role="user", content=context + "\n" + question),
                          dict(role="assistant", content="a")],
                meta=dict(source="explicit_public_context_qa", wrapper_view=0, language=language,
                          source_original_split="train", source_split="train",
                          semantic_root_id=root, parent_concept_id=root,
                          context_id="ctx-" + root, context_original=context,
                          question_original=question, source_path="fixture.json", source_sha256="A" * 64,
                          answers=[dict(text="a", answer_start=0)], supervised_assistant_turns=[1]))


def val_index():
    return m.validation_index([source_row("held-out")])


def toy_encode(row):
    return SimpleNamespace(x_tokens=row.get("fixture_x", 10), targets=row.get("fixture_targets", 3))


def prepared_fixture():
    end = "<|im_end|>"
    text = "P가" + end
    ids, pieces = [10, 11, 12, 99], ["P", "ê", "°Ģ", end]
    labels, offsets = [-100, 11, 12, 99], [(0, 1), (1, 2), (1, 2), (2, len(text))]
    row = source_row("fixture-root")
    spec = dict(row=row, row_sha256=m.object_sha(row), language="ko", root="fixture-root",
                source_index=9, root_order_sha256=m.root_order("ko", "fixture-root"),
                x_tokens=3, ce_targets=3)
    tok = SimpleNamespace(encode=lambda _: SimpleNamespace(ids=ids, offsets=offsets),
                          id_to_token=lambda token: dict(zip(ids, pieces))[token])
    encode_record = lambda *args, **kwargs: SimpleNamespace(x=ids[:-1], y=labels[1:],
        segments=[1, 1, 1], x_tokens=3, targets=3)
    value = m.pack_student(spec, tok, encode_record, lambda *args: (ids, labels, text),
                           lambda *args: [(1, len(text))], {99: end})
    value.update(row_id="alm_000000", selection_index=0, batch_index=0)
    value["prepared_row_sha256"] = m.object_sha(value)
    return value


def native_reply(target=21, logprob=-2.5, *, top_delta=0.0, payload=None):
    from scripts.diag_p106b_teacher_tf import payload as original_payload
    from scripts.p106b_alm_utf8_probability import _NEUTRAL
    value = original_payload([20], target, 100) if payload is None else payload
    settings = copy.deepcopy(value)
    settings.pop("prompt", None)
    settings.pop("cache_prompt", None)
    settings.pop("return_tokens", None)
    settings.update(_NEUTRAL)
    settings.update(grammar="", lora=[], stop=[], max_tokens=1,
                    backend_sampling=False, samplers=["temperature"],
                    logit_bias=[dict(token=value["logit_bias"][0][0], bias=value["logit_bias"][0][1])])
    settings["speculative.types"] = "none,none"
    piece = "가".encode() if target == 21 else b"\n" if target == 22 else b"Z"
    return dict(content=piece.decode(), tokens=[target], tokens_predicted=1,
        tokens_evaluated=len(value["prompt"]), stop=True, stop_type="limit", stopping_word="",
        truncated=False, timings=dict(cache_n=1 if value["cache_prompt"] else 0, predicted_n=1),
        generation_settings=settings,
        completion_probabilities=[dict(id=target, logprob=logprob, bytes=list(piece),
            top_logprobs=[dict(id=30, logprob=-.5 + top_delta, bytes=[77]),
                          dict(id=31, logprob=-1.5, bytes=[78])])])


class MemoryWriter:
    def __init__(self):
        self.rows = []

    def append(self, value):
        # Round-trip simulates a JSON writer and catches non-JSON cache fields.
        self.rows.append(json.loads(m.canonical(value)))


def fresh_report():
    return dict(http_attempted=0, http_succeeded=0, completion_attempted=0,
                completion_succeeded=0, unique_targets_completed=0,
                cache_verification_completion_requests=0, bias200_completion_requests=0)


def recorder_fixture():
    result = m.Recorder(MemoryWriter(), fresh_report(), SimpleNamespace(remaining=lambda: 600.))
    result.native_vocab_size = 4096
    return result


class NativeSession:
    """Injected transport; no sockets/processes/tokenizer. Native IDs are fixed."""
    def __init__(self, recorder, *, wrong_first=False, wrong_always=False, warm_delta=0.0):
        self.recorder, self.calls = recorder, []
        self.wrong_first, self.wrong_always, self.warm_delta = wrong_first, wrong_always, warm_delta
        self.key = "mock-api-secret"

    def check(self):
        self.recorder.check()

    def request(self, route, payload=None, timeout=10):
        return self.recorder.request(self, self.transport, route, payload, timeout)

    def transport(self, route, payload, timeout):
        self.calls.append((route, copy.deepcopy(payload)))
        if route == "/tokenize":
            ids = [20, 21, 90]
            return dict(tokens=[dict(id=20, piece="P"), dict(id=21, piece="가"),
                                dict(id=90, piece="<|im_end|>")] if payload["with_pieces"] else ids)
        bias = payload["logit_bias"][0][1]
        wanted = payload["logit_bias"][0][0]
        wrong = self.wrong_always or (self.wrong_first and bias == 100)
        return native_reply(999 if wrong else wanted,
                            -2.5 + (self.warm_delta if payload["cache_prompt"] else 0.), payload=payload)


class SelectionContract(unittest.TestCase):
    def test_balanced_hash_order_independent_of_source_iteration(self):
        rows = [source_row(f"{language}-{i}", language) for i in range(9) for language in ("ko", "en")]
        first, summary = m.choose_rows(rows, val_index(), toy_encode, per_language=3)
        second, _ = m.choose_rows(list(reversed(rows)), val_index(), toy_encode, per_language=3)
        self.assertEqual([v["root"] for v in first], [v["root"] for v in second])
        self.assertEqual([v["language"] for v in first], ["ko", "en"] * 3)
        self.assertEqual(summary["eligible_roots"], {"ko": 9, "en": 9})
        self.assertFalse(summary["quality_or_teacher_score_selection"])

    def test_original_rows_and_metadata_are_not_modified(self):
        rows = [source_row("ko", "ko"), source_row("en", "en")]
        before = copy.deepcopy(rows)
        m.choose_rows(rows, val_index(), toy_encode, per_language=1)
        self.assertEqual(rows, before)

    def test_all_validation_overlap_units_excluded(self):
        original = source_row("val-root")
        val = m.validation_index([original])
        by_root = source_row("val-root", question="other-q", context="other-c")
        by_context = source_row("new-root")
        by_context["meta"]["context_id"] = original["meta"]["context_id"]
        by_conversation = source_row("conversation-root")
        by_conversation["messages"] = copy.deepcopy(original["messages"])
        by_conversation["meta"].update(context_original=original["meta"]["context_original"],
                                        question_original=original["meta"]["question_original"])
        by_prompt = copy.deepcopy(by_conversation)
        by_prompt["messages"][1]["content"] = "different assistant"
        for row in (by_root, by_context, by_conversation, by_prompt):
            self.assertEqual(m.candidate_reason(row, val), "original_val_overlap")

    def test_wrapper_train_lineage_and_turn_admission(self):
        changes = (("wrapper_view", 1), ("wrapper_view", False), ("source_original_split", "dev"),
                   ("source_split", "val"), ("source", "other"), ("answers", []),
                   ("semantic_root_id", ""), ("supervised_assistant_turns", [2]))
        for key, value in changes:
            row = source_row("admission")
            row["meta"][key] = value
            with self.subTest(key=key, value=value):
                self.assertIsNotNone(m.candidate_reason(row, val_index()))

    def test_true_context_and_target_limits_no_quota_shrink(self):
        rows = [source_row("ko", "ko"), source_row("en", "en")]
        rows[0]["fixture_x"] = 1025
        with self.assertRaisesRegex(ValueError, "insufficient"):
            m.choose_rows(rows, val_index(), toy_encode, per_language=1)
        rows[0]["fixture_x"] = 1024
        rows[0]["fixture_targets"] = 65
        with self.assertRaisesRegex(ValueError, "insufficient"):
            m.choose_rows(rows, val_index(), toy_encode, per_language=1)
        rows[0]["fixture_targets"] = 64
        selected, _ = m.choose_rows(rows, val_index(), toy_encode, per_language=1)
        self.assertEqual(len(selected), 2)

    def test_one_root_is_not_counted_twice(self):
        rows = [source_row("ko", "ko"), source_row("ko", "ko"), source_row("en", "en")]
        chosen, summary = m.choose_rows(rows, val_index(), toy_encode, per_language=1)
        self.assertEqual(len(chosen), 2)
        self.assertEqual(summary["rejections"]["same_root_duplicate"], 1)

    def test_answer_text_is_not_used_as_a_truth_score(self):
        rows = [source_row("ko", "ko"), source_row("en", "en")]
        rows[0]["messages"][1]["content"] = "unreviewed answer; not a semantic oracle"
        selected, _ = m.choose_rows(rows, val_index(), toy_encode, per_language=1)
        self.assertEqual(len(selected), 2)


class ByteContract(unittest.TestCase):
    def test_character_spans_are_converted_to_utf8_not_character_counts(self):
        self.assertEqual(m.char_spans_to_bytes("P가나", [(1, 3)]), [[1, 7]])

    def test_overlapping_or_unbounded_spans_rejected(self):
        for spans in ([(1, 3), (2, 3)], [(0, 4)], [(True, 2)], [(2, 2)]):
            with self.subTest(spans=spans), self.assertRaises(ValueError):
                m.char_spans_to_bytes("abc", spans)

    def test_student_piece_offset_labels_and_eot_preserved(self):
        row = prepared_fixture()
        stream = m.rebuild_student(row)
        self.assertEqual(b"".join(v.data for v in stream.tokens), row["text"].encode())
        self.assertEqual(row["student"]["labels"], [-100, 11, 12, 99])
        self.assertEqual(row["student"]["ce_targets"], 3)
        self.assertEqual(stream.tokens[-1].special_kind, "<|im_end|>")

    def test_rebuild_rejects_shift_or_bytes_or_offsets_change(self):
        for key in ("ids", "labels", "char_offsets", "pieces"):
            row = prepared_fixture()
            if key == "char_offsets":
                row["student"][key][1] = [0, 1]
            elif key == "pieces":
                row["student"][key][1] = "X"
            else:
                row["student"][key][1] = 77
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.rebuild_student(row)

    def test_both_native_streams_reconstruct_same_full_input(self):
        from scripts.p106b_alm_bytes import align_assistant_chunks
        row = prepared_fixture()
        teacher = m.teacher_stream(row, [20, 21, 90], [dict(id=20, piece="P"),
            dict(id=21, piece=[234, 176, 128]), dict(id=90, piece="<|im_end|>")], {90: "<|im_end|>"})
        alignment = align_assistant_chunks(m.rebuild_student(row), teacher)
        self.assertEqual(len(alignment.chunks), 1)
        chunk = alignment.chunks[0]
        self.assertEqual(list(chunk.student_raw_indices), [1, 2])
        self.assertEqual(list(chunk.student_shifted_indices), [0, 1])
        self.assertEqual(list(chunk.teacher_raw_indices), [1])
        self.assertEqual(chunk.data, "가".encode())
        self.assertEqual(alignment.covered_byte_count, 3)
        self.assertTrue(any("special_token" in value.reasons for value in alignment.rejected))

    def test_teacher_id_piece_mismatch_and_cap_rejected_without_truncation(self):
        row = prepared_fixture()
        with self.assertRaises(ValueError):
            m.teacher_stream(row, [20, 21, 90], [dict(id=20, piece="P"),
                dict(id=999, piece="가"), dict(id=90, piece="<|im_end|>")], {90: "<|im_end|>"})
        with self.assertRaisesRegex(ValueError, "fit1024"):
            m.teacher_stream(row, list(range(1025)), [], {})

    def test_teacher_mask_uses_complete_byte_containment(self):
        mask, turns = m.owners_for_offsets([(0, 4), (4, 6), (6, 8)], [(2, 6)])
        self.assertEqual(mask, [False, True, False])
        self.assertEqual(turns, [0, 1, 0])

    def test_tokenization_flags_no_template_or_bos_insertion(self):
        value = m.tokenize_payload(" source\n", with_pieces=True)
        self.assertEqual(value, dict(content=" source\n", add_special=False,
                                     parse_special=True, with_pieces=True))


class ProbabilityContract(unittest.TestCase):
    def test_small_positive_logp_is_rejected_without_clamp(self):
        recorder=recorder_fixture();session=NativeSession(recorder)
        session.transport=lambda route,payload,timeout: native_reply(target=21,logprob=5e-7,payload=payload)
        recorder.row=dict(row_id="row",teacher_ids=[20,21,90])
        with self.assertRaisesRegex(ValueError,"비양수"):
            m.force_target(session,recorder,[20,21,90],1,cache_prompt=False)
        self.assertEqual(recorder.writer.rows[-1]["reply"]["completion_probabilities"][0]["logprob"],5e-7)

    def test_canary_compares_cold_warm_for_every_selected_target(self):
        class SplitSession(NativeSession):
            def transport(self,route,payload,timeout):
                self.calls.append((route,copy.deepcopy(payload)))
                if route=="/tokenize":
                    return dict(tokens=[dict(id=20,piece="P"),dict(id=21,piece=[234]),
                        dict(id=22,piece=[176,128]),dict(id=90,piece="<|im_end|>")]
                        if payload["with_pieces"] else [20,21,22,90])
                return native_reply(target=payload["logit_bias"][0][0],payload=payload)
        recorder=recorder_fixture();session=SplitSession(recorder)
        result=m.cache_row(session,recorder,prepared_fixture(),{90:"<|im_end|>"},
            cache_prompt=True,verify_all_cache=True)
        self.assertEqual([p["cache_prompt"] for r,p in session.calls if r=="/completion"],[False,False,True,True])
        self.assertEqual(len(result["cache_verifications"]),2)
        self.assertEqual(result["cache_verification_scope"],"ALL_COLD_THEN_INCREMENTAL_WARM")
        self.assertEqual(recorder.report["unique_targets_completed"],2)

    def test_cache_row_stores_native_logp_sum_and_excludes_eot_only_from_kd(self):
        recorder = recorder_fixture()
        session = NativeSession(recorder)
        row = prepared_fixture()
        result = m.cache_row(session, recorder, row, {90: "<|im_end|>"}, cache_prompt=False)
        self.assertEqual(result["ce_targets"], 3)
        self.assertEqual(result["kd_chunks"], 1)
        self.assertEqual(result["teacher_targets"], 1)
        self.assertEqual(result["alignment"]["chunks"][0]["teacher_raw_logprob_sum"], -2.5)
        self.assertFalse(result["eot_kd"])
        self.assertTrue(result["eot_ce"])
        completion = [payload for route, payload in session.calls if route == "/completion"]
        self.assertEqual(completion[0]["prompt"], [20])
        self.assertEqual(completion[0]["logit_bias"], [[21, 100]])
        self.assertEqual(completion[0]["n_predict"], 1)
        self.assertEqual(completion[0]["n_probs"], 2)
        self.assertFalse(completion[0]["post_sampling_probs"])
        self.assertFalse(result["quality_claim"])
        self.assertEqual(result["cache_verification_scope"],"NO_CACHE_VERIFICATION")

    def test_cache_prompt_requires_cold_warm_same_target_and_counts_overhead(self):
        recorder = recorder_fixture()
        session = NativeSession(recorder, warm_delta=5e-6)
        result = m.cache_row(session, recorder, prepared_fixture(), {90: "<|im_end|>"}, cache_prompt=True)
        requests = [payload for route, payload in session.calls if route == "/completion"]
        self.assertEqual([value["cache_prompt"] for value in requests], [False, True])
        self.assertEqual(recorder.report["unique_targets_completed"], 1)
        self.assertEqual(recorder.report["completion_attempted"], 2)
        self.assertEqual(recorder.report["cache_verification_completion_requests"], 1)
        self.assertTrue(result["cache_verification"]["comparison"]["passed"])

    def test_cache_prompt_mismatch_is_failure_not_cold_fallback(self):
        recorder = recorder_fixture()
        session = NativeSession(recorder, warm_delta=2e-5)
        with self.assertRaisesRegex(ValueError, "no cold fallback"):
            m.cache_row(session, recorder, prepared_fixture(), {90: "<|im_end|>"}, cache_prompt=True)
        self.assertEqual(recorder.report["unique_targets_completed"], 0)
        self.assertEqual(len([v for v in session.calls if v[0] == "/completion"]), 2)

    def test_wrong_id_gets_only_one_bias200_retry_and_all_attempts_survive(self):
        recorder = recorder_fixture()
        session = NativeSession(recorder, wrong_first=True)
        result = m.cache_row(session, recorder, prepared_fixture(), {90: "<|im_end|>"}, cache_prompt=False)
        self.assertEqual([value["bias"] for value in result["target_scores"][0]["attempts"]], [100, 200])
        self.assertEqual(len([row for row in recorder.writer.rows if row["event"] == "target_attempt"]), 2)
        self.assertEqual(recorder.report["bias200_completion_requests"], 1)

    def test_unforced_id_after_retry_is_failure_not_wrong_answer_grade(self):
        recorder = recorder_fixture()
        session = NativeSession(recorder, wrong_always=True)
        with self.assertRaisesRegex(ValueError, "not an answer-correctness verdict"):
            m.cache_row(session, recorder, prepared_fixture(), {90: "<|im_end|>"}, cache_prompt=False)
        self.assertEqual(len([v for v in session.calls if v[0] == "/completion"]), 2)
        self.assertEqual(recorder.report["unique_targets_completed"], 0)

    def test_warm_replays_the_successful_cold_bias_without_extra100_try(self):
        recorder = recorder_fixture()
        session = NativeSession(recorder, wrong_first=True)
        result = m.cache_row(session, recorder, prepared_fixture(), {90: "<|im_end|>"}, cache_prompt=True)
        self.assertEqual([payload["logit_bias"][0][1] for route, payload in session.calls
                          if route == "/completion"], [100, 200, 200])
        self.assertEqual(result["teacher_targets"], 1)

    def test_sentinel_nonfinite_and_positive_logp_rejected(self):
        from scripts.diag_p106b_teacher_tf import probability_entry
        for value in (-1e30, float("nan"), float("inf"), 1., True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probability_entry(native_reply(logprob=value))

    def test_top_ids_or_raw_top_prob_changes_invalidate_cache(self):
        from scripts.diag_p106b_teacher_tf import probability_entry
        cold = probability_entry(native_reply())
        changed = probability_entry(native_reply(top_delta=2e-5))
        with self.assertRaises(ValueError):
            m.compare_cache(cold, changed)
        changed = copy.deepcopy(cold)
        changed["top"][0]["id"] = 1234
        with self.assertRaises(ValueError):
            m.compare_cache(cold, changed)


class EvidenceContract(unittest.TestCase):
    def test_real_request_bytes_flushed_before_transport_not_fsync_claim(self):
        from scripts.p106b_shards import ShardWriter
        with tempfile.TemporaryDirectory() as tmp:
            writer=ShardWriter(Path(tmp),"raw")
            recorder=m.Recorder(writer,fresh_report(),SimpleNamespace(remaining=lambda:600.))
            def transport(*args,**kwargs):
                data=(Path(tmp)/"raw_000000.jsonl").read_text()
                self.assertEqual(json.loads(data)["event"],"request_attempt")
                return {"ok":True}
            recorder.request(None,transport,"/tokenize",{"content":"P"})
            writer.close(lineage={"fixture":True})

    def test_sealed_recorder_cannot_race_with_final_manifest(self):
        recorder=recorder_fixture();recorder.seal();recorder.background("late",value=1)
        self.assertEqual(recorder.writer.rows,[])
        self.assertIn("sealed",recorder.errors[0])

    def test_alive_teardown_thread_is_latched_as_incomplete(self):
        recorder=recorder_fixture()
        session=SimpleNamespace(workers=[SimpleNamespace(name="late-worker",is_alive=lambda:True)])
        self.assertEqual(m.thread_exit_proof(session,recorder),["late-worker"])
        self.assertFalse(recorder.report["owned_threads_closed"])
        with self.assertRaises(RuntimeError):recorder.check()
    def test_owned_session_wrapper_reuses_lifecycle_and_records_startup(self):
        scripts = sys.modules['scripts']
        from scripts import diag_p106b_teacher_tf as tf
        runtime, online = ModuleType("mock_qwen_runtime"), ModuleType("mock_online")
        original_profile = SimpleNamespace(command=lambda *args: [])
        runtime.profile = original_profile
        runtime.owned_rss = lambda pid: 32.
        online.capture_server_line = lambda line, signals, tail, key: tail.append(line.replace(key, "REDACTED"))
        recorder, holder = recorder_fixture(), {}

        class Owned:
            def __init__(self, condition):
                self.condition, self.port, self.key = condition, 12345, "mock-session-secret"
                self.samples, self.errors, self.tail, self.signals = [], [], [], {}
                self.process = SimpleNamespace(pid=123, poll=lambda: 0)
                self.exited = False

            def __enter__(self):
                self.actual_command = runtime.profile.command(self.port, self.key)
                online.capture_server_line("startup " + self.key, self.signals, self.tail, self.key)
                self.samples.append(dict(used=200, free=10000, rss_mib=runtime.owned_rss(123)))
                self.props = self.request("/props")
                self.startup_sec = .1
                return self

            def request(self, route, payload=None, timeout=10):
                self.last_request_was_pre_recorded = recorder.writer.rows[-1]["event"] == "request_attempt"
                return {"total_slots": 1}

            def check(self):
                return None

            def __exit__(self, *args):
                self.exited = True

        runtime.QwenSession = Owned
        profile = SimpleNamespace(command=lambda port, key: ["server", "--ctx-size", "8192",
            "--spec-type", "draft-mtp", "--spec-draft-n-max", "2"])
        names = {"scripts.diag_p106b_qwen_coload": runtime, "scripts.diag_p106b_online_rate5": online}
        with patch.dict(sys.modules, names), \
             patch.object(scripts, "diag_p106b_qwen_coload", runtime, create=True), \
             patch.object(scripts, "diag_p106b_online_rate5", online, create=True):
            with m.recorded_session(profile, recorder, holder) as session:
                self.assertTrue(session.last_request_was_pre_recorded)
                self.assertEqual(session.actual_command[-2:], ["--spec-type", "none"])
                self.assertEqual(session.actual_command[session.actual_command.index("--ctx-size") + 1], "1024")
                self.assertIs(holder["session"], session)
            self.assertTrue(session.exited)
            self.assertIs(runtime.QwenSession, Owned)
            self.assertIs(runtime.profile, original_profile)
        events = {value["event"] for value in recorder.writer.rows}
        self.assertTrue({"server_log", "memory_sample_200ms", "request_attempt", "owned_session_exit"} <= events)
        self.assertNotIn("mock-session-secret", json.dumps(recorder.writer.rows))

    def test_prefix_payload_is_reconstructible_with_all_other_actual_keys(self):
        from scripts.diag_p106b_teacher_tf import payload
        ids = [20, 21, 22, 90]
        actual = payload(ids[:2], ids[2], 100)
        compact = m.compact_payload(actual, dict(row_id="row", teacher_ids=ids))
        self.assertNotIn("prompt", compact["payload_without_prompt"])
        self.assertEqual(m.restore_payload(compact, {"row": ids}), actual)
        with self.assertRaises(ValueError):
            m.restore_payload(compact, {"row": [20, 999, 22, 90]})

    def test_not_an_original_prefix_cannot_be_compressed(self):
        with self.assertRaises(ValueError):
            m.compact_payload(dict(prompt=[99]), dict(row_id="row", teacher_ids=[20, 21]))

    def test_request_is_on_disk_before_transport_and_raw_reply_retained(self):
        recorder = recorder_fixture()
        def transport(route, payload, timeout):
            self.assertEqual(recorder.writer.rows[-1]["event"], "request_attempt")
            self.assertEqual(recorder.writer.rows[-1]["payload"], payload)
            return {"tokens": [1, 2]}
        reply = recorder.request(SimpleNamespace(key=""), transport, "/tokenize", {"content": "P가"}, 90)
        self.assertEqual(reply, {"tokens": [1, 2]})
        self.assertEqual(recorder.writer.rows[-1]["reply"], reply)

    def test_http_errors_keep_bounded_body_and_redact_secret(self):
        recorder = recorder_fixture()
        recorder.key = "secret-token"
        def transport(*args, **kwargs):
            raise HTTPError("http://127.0.0.1", 500, "secret-token", {},
                            BytesIO(b'{"error":{"message":"Bearer secret-token failed"}}'))
        with self.assertRaises(HTTPError):
            recorder.request(SimpleNamespace(key="secret-token"), transport, "/tokenize", {"content": "P"}, 90)
        record = recorder.writer.rows[-1]
        self.assertEqual(record["event"], "request_failed")
        self.assertEqual(record["error"]["http"]["http_status"], 500)
        self.assertNotIn("secret-token", json.dumps(record))

    def test_source_text_is_not_changed_by_generic_bearer_regex(self):
        text = "Bearer is the word in this source; preserve it."
        self.assertEqual(m.redact(text, "random-api-key"), text)
        self.assertNotIn("random-api-key", m.redact("Bearer random-api-key", "random-api-key"))

    def test_threaded_server_logs_and_memory_samples_are_serialized(self):
        recorder = recorder_fixture()
        samples = m.RecordedList(recorder, "memory_sample_200ms")
        workers = [threading.Thread(target=lambda: [samples.append(dict(used=i, free=100, rss_mib=1.))
                    for i in range(8)]) for _ in range(3)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual(len(recorder.writer.rows), 24)
        self.assertEqual([row["event_index"] for row in recorder.writer.rows], list(range(1, 25)))

    def test_background_persistence_failure_latches_and_blocks_progress(self):
        recorder = recorder_fixture()
        recorder.writer.append = lambda value: (_ for _ in ()).throw(OSError("mock disk failure"))
        recorder.background("server_log", line="a")
        with self.assertRaisesRegex(RuntimeError, "persistence failed"):
            recorder.check()

    def test_write_once_json_and_byte_guard(self):
        with tempfile.TemporaryDirectory(prefix="p106b_alm_fixture_") as temporary:
            path = Path(temporary) / "new.json"
            m.write_json(path, {"한국어": "가"})
            first = path.read_bytes()
            with self.assertRaises(FileExistsError):
                m.write_json(path, {"other": True})
            self.assertEqual(path.read_bytes(), first)
            with patch.object(m, "canonical", return_value=b"x" * 20_000_000):
                with self.assertRaisesRegex(ValueError, "below20MB"):
                    m.write_json(Path(temporary) / "large.json", {})

    def test_shards_rotate_below20mb_without_partial_line(self):
        from scripts.p106b_shards import ShardWriter, verify
        with tempfile.TemporaryDirectory(prefix="p106b_alm_shard_fixture_") as temporary:
            directory = Path(temporary)
            writer = ShardWriter(directory, "raw", limit=128)
            for index in range(8):
                writer.append(dict(index=index, text="가나다"))
            manifest = writer.close(lineage={"fixture": True})
            verify(directory, manifest)
            self.assertGreater(len(manifest["shards"]), 1)
            self.assertTrue(all(part["bytes"] <= 128 for part in manifest["shards"]))

    def test_existing_partial_directory_and_symlink_preserved(self):
        with tempfile.TemporaryDirectory(prefix="p106b_alm_path_fixture_") as temporary:
            path = Path(temporary) / "partial"
            path.mkdir()
            with self.assertRaises(FileExistsError):
                m.new_directory(path)
            link = Path(temporary) / "linked"
            link.symlink_to(path, target_is_directory=True)
            with self.assertRaises(ValueError):
                m.new_directory(link)
            self.assertTrue(path.is_dir())
            self.assertTrue(link.is_symlink())


def closed_fixture():
    rows = []
    for index in range(16):
        value = dict(prepared_row_sha256=str(index), language="ko" if index % 2 == 0 else "en",
                     ce_targets=3, kd_chunks=1, teacher_targets=1, covered_bytes=3,
                     student_supervised_targets=2, teacher_supervised_targets=1, student_kd_targets=2,
                     reference_assistant_non_special_bytes=3,
                     student_supervised_bytes=3, teacher_supervised_bytes=3)
        value["cache_row_sha256"] = m.object_sha(value)
        rows.append(value)
    identity = dict(prepared_row_sha256=[row["prepared_row_sha256"] for row in rows], code="fixture",expected_language_rows=dict(ko=8,en=8))
    report = dict(schema=m.SCHEMA, status="ALM_CACHE_BATCH_COMPLETE", returncode=0, identity=identity,
                  rows_completed=16, language_totals=m.language_totals(rows),
                  sources_unchanged=True, inputs_unchanged=True, teacher_assets_unchanged=True,
                  telemetry_errors=[], raw_persistence_errors=[], raw_manifest={}, cache_manifest={},owned_threads_closed=True,
                  cache_row_sha256=[row["cache_row_sha256"] for row in rows])
    return rows, identity, report


class ImmutableBatchContract(unittest.TestCase):
    def invoke(self, rows, identity, report):
        with patch.object(m, "read_json", return_value=report), \
             patch("scripts.p106b_shards.verify"), \
             patch("scripts.p101a_sft_mtp_data.stream_rows", return_value=iter(rows)):
            return m.closed_batch(Path("unused-fixture"), identity)

    def test_closed_exact16_rows_can_be_reused(self):
        rows, identity, report = closed_fixture()
        self.assertIs(self.invoke(rows, identity, report), report)

    def test_partial_cannot_be_resumed_or_promoted(self):
        rows, identity, report = closed_fixture()
        report["status"] = "ALM_CACHE_EXECUTION_PARTIAL"
        with self.assertRaisesRegex(ValueError, "reuse forbidden"):
            self.invoke(rows, identity, report)

    def test_code_or_row_identity_mismatch_rejected(self):
        rows, identity, report = closed_fixture()
        changed = dict(identity, code="different")
        with self.assertRaises(ValueError):
            self.invoke(rows, changed, report)
        rows[0]["covered_bytes"] = 2
        with self.assertRaises(ValueError):
            self.invoke(rows, identity, report)

    def test_missing_telemetry_is_not_a_closed_cache(self):
        rows, identity, report = closed_fixture()
        report["telemetry_errors"] = ["missing200ms"]
        with self.assertRaises(ValueError):
            self.invoke(rows, identity, report)

    def test_per_language_mass_and_acceptance_are_separate(self):
        rows, _, _ = closed_fixture()
        rows[0].update(covered_bytes=1, student_supervised_bytes=2, teacher_supervised_bytes=4)
        result = m.language_totals(rows)
        self.assertEqual(result["ko"]["ce_targets"], 24)
        self.assertEqual(result["en"]["kd_chunks"], 8)
        self.assertEqual(result["ko"]["teacher_targets"], 8)
        self.assertNotEqual(result["ko"]["student_byte_acceptance"], result["en"]["student_byte_acceptance"])


class NativeTemplateContract(unittest.TestCase):
    def fixture(self):
        row = prepared_fixture()
        row["source_row"]["messages"] = [dict(role="user", content="original question"),
                                          dict(role="assistant", content="가")]
        row["source_row_sha256"] = m.object_sha(row["source_row"])
        return row

    def prefix(self, row):
        return ("<|im_start|>user\n" + row["source_row"]["messages"][0]["content"]
                + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n")

    def test_real_template_request_has_nested_false_and_exact_reference_body(self):
        row, recorder = self.fixture(), recorder_fixture()
        prefix = self.prefix(row)
        session = SimpleNamespace(request=lambda route, payload, timeout:
            dict(prompt=prefix) if route == "/apply-template" and
            payload == dict(messages=[row["source_row"]["messages"][0]], add_generation_prompt=True,
                            chat_template_kwargs=dict(enable_thinking=False)) else None)
        value = m.native_teacher_input(session, recorder, row)
        self.assertEqual(value["teacher_text"], prefix + "가<|im_end|>\n")
        self.assertFalse(value["student_source_modified"])
        self.assertFalse(value["full_templates_identical"])
        self.assertEqual(value["teacher_body_span"], [len(prefix.encode()), len(prefix.encode())+3])

    def test_native_template_refuses_open_reasoning_or_modified_question(self):
        for reason in ("open_think", "nonempty_think", "missing_question"):
            row, recorder = self.fixture(), recorder_fixture()
            prefix = self.prefix(row)
            if reason == "open_think": prefix = prefix.replace("</think>", "")
            elif reason == "nonempty_think": prefix = prefix.replace("<think>\n", "<think>generated")
            else: prefix = prefix.replace("original question", "different")
            session = SimpleNamespace(request=lambda *args, **kwargs: dict(prompt=prefix))
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                m.native_teacher_input(session, recorder, row)

    def test_native_renderer_edge_trim_is_explicit_and_student_original_is_preserved(self):
        row, recorder = self.fixture(), recorder_fixture()
        prefix = self.prefix(row)
        row["source_row"]["messages"][0]["content"] = " \noriginal question\t\n"
        before = copy.deepcopy(row)
        session = SimpleNamespace(request=lambda *args, **kwargs:dict(prompt=prefix))
        value = m.native_teacher_input(session, recorder, row)
        self.assertEqual(row,before)
        effect=value["native_question_edge_trim"]
        self.assertEqual((effect["leading_bytes"],effect["trailing_bytes"]),(2,2))
        self.assertTrue(effect["applied"])
        self.assertEqual(effect["rendered_question"],"original question")
        self.assertEqual(value["template_request"]["messages"][0]["content"],
                         row["source_row"]["messages"][0]["content"])
        self.assertFalse(value["student_source_modified"])

    def test_native_cache_projects_body_and_replicates_only_full_cold_requests(self):
        row, recorder = self.fixture(), recorder_fixture()
        prefix = self.prefix(row)
        class ColdSession(NativeSession):
            def transport(self, route, payload, timeout):
                if route == "/apply-template":
                    self.calls.append((route, copy.deepcopy(payload)))
                    return dict(prompt=prefix)
                if route == "/tokenize":
                    self.calls.append((route, copy.deepcopy(payload)))
                    self.asserted_text = payload["content"]
                    parts = [dict(id=20, piece=prefix),dict(id=21,piece="가"),
                             dict(id=90,piece="<|im_end|>"),dict(id=22,piece="\n")]
                    return dict(tokens=parts if payload["with_pieces"] else [20,21,90,22])
                result = super().transport(route, payload, timeout)
                result["timings"] = dict(cache_n=0)
                return result
        session = ColdSession(recorder)
        result = m.cache_row(session, recorder, row, {90:"<|im_end|>"},
            cache_prompt=False, verify_all_cache=True, native_template=True, cold_replicate=True)
        completions = [payload for route,payload in session.calls if route == "/completion"]
        self.assertEqual(len(completions),2)
        self.assertTrue(all(payload["cache_prompt"] is False for payload in completions))
        self.assertEqual(result["cache_verification_scope"],"ALL_COLD_REPLICATES")
        self.assertEqual(result["answer_projection"]["covered_byte_count"],3)
        self.assertFalse(result["answer_projection"]["full_template_equality_claim"])
        self.assertEqual(result["cache_verifications"][0]["mode"],"COLD_COLD_REPLICATE")
        self.assertEqual(result["alignment"]["chunks"][0]["student_raw_indices"],[1,2])
        self.assertEqual(result["alignment"]["chunks"][0]["teacher_raw_indices"],[1])

    def test_cold_replicate_rejects_reported_prefix_reuse_or_missing_timings(self):
        for timings in (None, dict(cache_n=1)):
            recorder = recorder_fixture(); recorder.row = dict(row_id="fixture",teacher_ids=[20,21])
            session = NativeSession(recorder)
            original = session.transport
            def transport(route,payload,timeout):
                reply = original(route,payload,timeout)
                if timings is not None: reply["timings"] = timings
                else: reply.pop("timings",None)
                return reply
            session.transport = transport
            with self.subTest(timings=timings),self.assertRaisesRegex(ValueError,"cache_n=0"):
                m.force_target(session,recorder,[20,21],1,cache_prompt=False,require_cold_prefix=True)


class EntrypointContract(unittest.TestCase):
    def test_import_of_new_module_uses_no_external_runtime_or_data(self):
        # A fresh module name exercises the import body without touching assets.
        spec = importlib.util.spec_from_file_location("p106b_alm_import_fixture", Path(m.__file__))
        module = importlib.util.module_from_spec(spec)
        original_import = __import__
        def guarded(name, *args, **kwargs):
            if name.startswith(("torch", "tokenizers", "transformers", "lm_eval", "tinylm", "scripts.")):
                raise AssertionError("non-stdlib import on module import: " + name)
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            spec.loader.exec_module(module)
        self.assertEqual(module.SCHEMA, m.SCHEMA)

    def test_check_only_does_not_read_assets_or_start_models(self):
        output = StringIO()
        with patch.object(m, "sources", return_value={"fixture.py": "A" * 64}), \
             patch.object(m, "source_inputs", side_effect=AssertionError("data read")), \
             patch.object(m, "load_prepared", side_effect=AssertionError("data read")), \
             patch.object(m, "prepare", side_effect=AssertionError("prepare called")), \
             patch.object(m, "execute", side_effect=AssertionError("execute called")), redirect_stdout(output):
            self.assertEqual(m.main(["--check-only"]), 0)
        value = json.loads(output.getvalue())
        self.assertEqual(value["asset_reads"], 0)
        self.assertEqual(value["planned_rows"], 1024)
        self.assertEqual(value["batch_size"], 16)
        self.assertEqual(value["planned_canary_rows"], 17)
        self.assertEqual(value["canary_language_rows"], {"ko": 9, "en": 8})
        self.assertEqual(value["output_base"], "HF/sft_ready/p106b_alm_context_v7_s1337")
        self.assertEqual(value["batches"], 64)
        self.assertFalse(value["cache_prompt_default"])

    def test_execute_requires_one_fixed_mode_and_exact_batch_index(self):
        invalid = (["--execute"], ["--execute", "--cache", "--deadline", "2026-10-23T16:00:00+09:00"],
                   ["--execute", "--cache", "--batch-index", "64", "--deadline", "2026-10-23T16:00:00+09:00"],
                   ["--execute", "--canary", "--batch-index", "0", "--deadline", "2026-10-23T16:00:00+09:00"],
                   ["--check-only", "--canary"], ["--prepare", "--cache-prompt"],
                   ["--execute","--canary","--cache-prompt","--deadline","2026-10-23T16:30:00+09:00"])
        for argv in invalid:
            with self.subTest(argv=argv), redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                m.main(argv)

    def test_deadline_is_aware_and_no_later_than_hard_stop(self):
        self.assertEqual(m.deadline_value("2026-10-23T16:30:00+09:00"), m.HARD_STOP)
        for invalid in ("2026-10-23T16:30:00", "2026-10-23T16:31:00+09:00"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                m.deadline_value(invalid)

    def test_budget_counts_preflight_time_and_refuses_late_entry(self):
        now = m.HARD_STOP - timedelta(seconds=700)
        clock = [100.]
        budget = m.Budget(600, m.HARD_STOP, now=lambda: now, clock=lambda: clock[0])
        clock[0] += 250
        self.assertEqual(budget.remaining(), 350.)
        clock[0] += 351
        with self.assertRaises(TimeoutError):
            budget.remaining()
        with self.assertRaises(ValueError):
            m.Budget(600, m.HARD_STOP, now=lambda: m.HARD_STOP - timedelta(seconds=599))

    def test_shutdown_reserve_prevents_a_last_second_request(self):
        recorder = recorder_fixture()
        recorder.budget = SimpleNamespace(remaining=lambda: float(m.SHUTDOWN_RESERVE))
        with self.assertRaises(TimeoutError):
            recorder.check()


class Utf8ProbeControllerContract(unittest.TestCase):
    def fixture(self):
        from scripts.test_p106b_alm_utf8_probability import fixture_probe,fixture_response
        recorder=recorder_fixture();recorder.row=dict(row_id="fragment_fixture",teacher_ids=[10,17])
        recorder.ascii_probes=[fixture_probe()]
        session=NativeSession(recorder)
        session.transport=lambda route,payload,timeout:fixture_response(payload)
        return session,recorder

    def test_fragment_uses_same_prefix_raw_topk_target_not_selected_probe(self):
        session,recorder=self.fixture()
        result=m.force_target(session,recorder,[10,17],1,cache_prompt=False,
            require_cold_prefix=True,target_piece=bytes([234]))
        self.assertEqual(result["target_id"],17)
        self.assertEqual(result["observed"]["chosen_probe"]["id"],4000)
        self.assertNotIn("chosen",result["observed"])
        self.assertEqual(result["raw_logprob"],-6.-.02*17)
        self.assertNotEqual(result["raw_logprob"],result["observed"]["chosen_probe"]["logprob"])
        requests=[v for v in recorder.writer.rows if v["event"]=="request_attempt"]
        payload=m.restore_payload(requests[0],{"fragment_fixture":[10,17]})
        self.assertEqual(payload["prompt"],[10]);self.assertEqual(payload["n_probs"],64)
        self.assertEqual(payload["logit_bias"],[[4000,100]])

    def test_missing_target_increases_k_only_and_never_imputes_zero(self):
        session,recorder=self.fixture();recorder.row["teacher_ids"]=[10,3000]
        with self.assertRaisesRegex(ValueError,"absent from bounded"):
            m.force_target(session,recorder,[10,3000],1,cache_prompt=False,require_cold_prefix=True,target_piece=bytes([234]))
        attempts=[v for v in recorder.writer.rows if v["event"]=="probe_target_attempt"]
        self.assertEqual([v["requested_n_probs"] for v in attempts],[64,512,2048])
        self.assertTrue(all(v["target_logprob"] is None for v in attempts))

    def test_fragment_requires_cold_and_actual_probe_registry(self):
        session,recorder=self.fixture()
        with self.assertRaisesRegex(ValueError,"original cold"):
            m.force_target(session,recorder,[10,17],1,cache_prompt=True,target_piece=bytes([234]))
        del recorder.ascii_probes
        with self.assertRaisesRegex(ValueError,"registry"):
            m.force_target(session,recorder,[10,17],1,cache_prompt=False,require_cold_prefix=True,target_piece=bytes([234]))

    def test_reference_compare_preserves_different_actual_probe_identity(self):
        a=dict(target_id=17,raw_index=1,native_prefix_ids_sha256=m.object_sha([10]),raw_logprob=-2.,observed=dict(chosen_probe=dict(id=100,logprob=-10.),top=[dict(id=1,logprob=-.5),dict(id=2,logprob=-1.)]))
        b=copy.deepcopy(a);b["observed"]["chosen_probe"]["id"]=101
        self.assertTrue(m.compare_reference_scores(a,b)["passed"])
        b["raw_logprob"]-=1e-3
        with self.assertRaisesRegex(ValueError,"no cold fallback"):m.compare_reference_scores(a,b)

    def test_canary_preserves_original16_and_adds_failed_original34(self):
        rows=[dict(prepared_row_sha256=str(i),row_id=f"alm_{i:06d}") for i in range(1024)]
        chosen=m.canary_rows(rows)
        self.assertEqual(chosen[:16],rows[:16]);self.assertIs(chosen[-1],rows[34])
        self.assertEqual(len(chosen),17)

    def test_control_bias_subset_is_not_silently_replaced_by200(self):
        session,recorder=self.fixture()
        result=m.probe_target(session,recorder,[10,17],1,initial_bias=100,bias_values=(100,),k_values=(64,))
        self.assertEqual(result["bias"],100)
        with self.assertRaisesRegex(ValueError,"bias subset"):
            m.probe_target(session,recorder,[10,17],1,bias_values=(150,))


class StrictV7ActualContract(unittest.TestCase):
    def test_complete_target_cannot_accept_truncated_actual_response(self):
        recorder = recorder_fixture()
        recorder.row = dict(row_id="complete_fixture", teacher_ids=[20, 21, 90])
        session = NativeSession(recorder)
        def transport(route, payload, timeout):
            reply = native_reply(target=21,payload=payload)
            reply.update(truncated=True, timings=dict(cache_n=0))
            return reply
        session.transport = transport
        with self.assertRaises(ValueError):
            m.force_target(session, recorder, [20, 21, 90], 1,
                           cache_prompt=False, require_cold_prefix=True, target_piece="가".encode())

    def test_complete_target_actual_contract_errors_do_not_get_bias_retry(self):
        for mutate in ("prefix", "count", "raw", "mtp", "bytes", "top_positive", "top_order"):
            recorder = recorder_fixture()
            recorder.row = dict(row_id="complete_fixture", teacher_ids=[20, 21, 90])
            session = NativeSession(recorder)
            def transport(route, payload, timeout):
                session.calls.append((route, copy.deepcopy(payload)))
                reply = native_reply(target=21, payload=payload)
                if mutate == "prefix": reply["tokens_evaluated"] += 1
                elif mutate == "count": reply["tokens_predicted"] = 2
                elif mutate == "raw": reply["generation_settings"]["post_sampling_probs"] = True
                elif mutate == "mtp": reply["generation_settings"]["speculative.types"] = "draft-mtp"
                elif mutate == "bytes": reply["completion_probabilities"][0]["bytes"] = [65]
                elif mutate == "top_positive": reply["completion_probabilities"][0]["top_logprobs"][0]["logprob"] = 5e-7
                else: reply["completion_probabilities"][0]["top_logprobs"].reverse()
                return reply
            session.transport = transport
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                m.force_target(session, recorder, [20, 21, 90], 1, cache_prompt=False,
                               require_cold_prefix=True, target_piece="가".encode())
            self.assertEqual(len(session.calls), 1)
            self.assertEqual(recorder.writer.rows[-1]["event"], "request_succeeded")

    def probe_fixture(self, target=17):
        from scripts.p106b_alm_utf8_probability import ValidatedAsciiProbe
        recorder = recorder_fixture()
        recorder.row = dict(row_id="matrix_fixture", teacher_ids=[10, target])
        recorder.ascii_probes = [ValidatedAsciiProbe(4000, b"A", 4096, (4094, 4095)),
                                 ValidatedAsciiProbe(4001, b"B", 4096, (4094, 4095))]
        recorder.report["ascii_probe_registry"] = dict(vocab_size=4096,
            probes=[dict(token_id=p.token_id, piece_hex=p.piece_bytes.hex()) for p in recorder.ascii_probes])
        session = NativeSession(recorder)
        return session, recorder

    def control_reply(self, payload, *, target=17, actual_id=None, delta=0.0):
        from scripts.test_p106b_alm_utf8_probability import fixture_response
        reply = fixture_response(payload)
        wanted = payload["logit_bias"][0][0]
        actual_id = wanted if actual_id is None else actual_id
        top = reply["completion_probabilities"][0]["top_logprobs"]
        for entry in top:
            entry["logprob"] += delta
            if entry["id"] == target: entry.update(token="N", bytes=[78])
        if actual_id == target:
            logp, piece = -6. - .02 * target + delta, b"N"
        else:
            logp = min(-12., top[-1]["logprob"] - 1.)
            piece = b"A" if actual_id == 4000 else b"B"
        reply.update(tokens=[actual_id], content=piece.decode())
        reply["generation_settings"]["logit_bias"] = [dict(token=wanted, bias=payload["logit_bias"][0][1])]
        reply["completion_probabilities"][0].update(id=actual_id, token=piece.decode(), bytes=list(piece), logprob=logp)
        return reply

    def install_control_transport(self, session, *, target=17, delta_for=None):
        def transport(route, payload, timeout):
            ordinal = len(session.calls)
            session.calls.append((route, copy.deepcopy(payload)))
            delta = 0.0 if delta_for is None else delta_for(payload, ordinal)
            return self.control_reply(payload, target=target, delta=delta)
        session.transport = transport

    def completed_controls(self):
        session, recorder = self.probe_fixture()
        self.install_control_transport(session)
        m.probe_controls(session, recorder, [10, 17], 1, target_piece=b"N")
        return session, recorder

    def test_normal_controls_are_exact_same_k_two_by_two_and_cross_checked(self):
        session, recorder = self.completed_controls()
        controls = recorder.report["normal_forcing_probe_controls"]
        self.assertEqual(len(session.calls), 8)
        self.assertEqual({(c["probe_id"], c["bias"]) for c in controls},
                         {(4000, 100), (4000, 200), (4001, 100), (4001, 200)})
        self.assertEqual({c["k"] for c in controls}, {64})
        self.assertTrue(all(payload["prompt"] == [10] for _, payload in session.calls))
        matrix = m.validate_probe_controls(controls, recorder.report["ascii_probe_registry"])
        self.assertEqual(matrix, recorder.report["normal_forcing_probe_matrix"])
        self.assertEqual(matrix["native_prefix_ids_sha256"], m.object_sha([10]))

    def test_pairwise_matching_but_bias_dependent_values_are_rejected(self):
        session, recorder = self.probe_fixture()
        self.install_control_transport(session,
            delta_for=lambda payload, ordinal: -.1 if payload["logit_bias"][0][1] == 200 else 0.)
        with self.assertRaisesRegex(ValueError, "same-prefix"):
            m.probe_controls(session, recorder, [10, 17], 1, target_piece=b"N")
        self.assertEqual(len(session.calls), 4)
        self.assertTrue(all(c["comparison"]["passed"] for c in recorder.report["normal_forcing_probe_controls"]))
        self.assertNotIn("normal_forcing_probe_matrix", recorder.report)

    def test_pairwise_matching_but_probe_order_drift_is_rejected(self):
        session, recorder = self.probe_fixture()
        self.install_control_transport(session, delta_for=lambda payload, ordinal: -.1 if ordinal >= 4 else 0.)
        with self.assertRaisesRegex(ValueError, "same-prefix"):
            m.probe_controls(session, recorder, [10, 17], 1, target_piece=b"N")

    def test_missing_control_restarts_the_whole_matrix_at_next_k(self):
        session, recorder = self.probe_fixture(target=80)
        self.install_control_transport(session, target=80)
        m.probe_controls(session, recorder, [10, 80], 1, target_piece=b"N")
        self.assertEqual([p["n_probs"] for _, p in session.calls], [64, 64] + [512] * 8)
        self.assertEqual({c["k"] for c in recorder.report["normal_forcing_probe_controls"]}, {512})
        self.assertEqual(recorder.report["normal_forcing_probe_matrix"]["k"], 512)

    def test_control_closure_rejects_duplicates_k_prefix_and_cross_value_tampering(self):
        _, recorder = self.completed_controls()
        for mutate in ("duplicate", "k", "prefix", "cross_value"):
            controls = copy.deepcopy(recorder.report["normal_forcing_probe_controls"])
            if mutate == "duplicate": controls[-1] = copy.deepcopy(controls[0])
            elif mutate == "k": controls[-1]["k"] = 512
            elif mutate == "prefix": controls[-1]["probe_result"]["native_prefix_ids_sha256"] = "F" * 64
            else:
                controls[-1]["direct"]["raw_logprob"] -= .1
                controls[-1]["probe_result"]["raw_logprob"] -= .1
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                m.validate_probe_controls(controls, recorder.report["ascii_probe_registry"])

    def test_probe_retries_only_valid_other_selection_and_only_bias200(self):
        session, recorder = self.probe_fixture()
        def transport(route, payload, timeout):
            session.calls.append((route, copy.deepcopy(payload)))
            return self.control_reply(payload, actual_id=4001 if payload["logit_bias"][0][1] == 100 else 4000)
        session.transport = transport
        score = m.probe_target(session, recorder, [10, 17], 1, reference_piece=b"N")
        self.assertEqual(score["bias"], 200)
        self.assertEqual([p["logit_bias"][0][1] for _, p in session.calls], [100, 200])
        self.assertEqual([p["n_probs"] for _, p in session.calls], [64, 64])
        self.assertEqual([a["status"] for a in score["attempts"]], ["PROBE_NOT_FORCED", "FOUND"])

    def test_wrong_probe_plus_contract_error_is_not_a_retryable_choice(self):
        session, recorder = self.probe_fixture()
        def transport(route, payload, timeout):
            session.calls.append((route, copy.deepcopy(payload)))
            reply = self.control_reply(payload, actual_id=4001)
            reply["generation_settings"]["post_sampling_probs"] = True
            return reply
        session.transport = transport
        with self.assertRaises(ValueError):
            m.probe_target(session, recorder, [10, 17], 1, reference_piece=b"N")
        self.assertEqual(len(session.calls), 1)
        self.assertFalse(any(e["event"] == "probe_target_attempt" for e in recorder.writer.rows))

    def test_probe_not_forced_after_two_biases_does_not_escalate_k(self):
        from scripts.p106b_alm_utf8_probability import NativeNotForcedError
        session, recorder = self.probe_fixture()
        def transport(route, payload, timeout):
            session.calls.append((route, copy.deepcopy(payload)))
            return self.control_reply(payload, actual_id=4001)
        session.transport = transport
        with self.assertRaises(NativeNotForcedError):
            m.probe_target(session, recorder, [10, 17], 1, reference_piece=b"N")
        self.assertEqual(len(session.calls), 2)
        self.assertEqual({p["n_probs"] for _, p in session.calls}, {64})

    def test_fragment_reference_bytes_must_match_native_piece(self):
        session, recorder = self.probe_fixture()
        self.install_control_transport(session)
        with self.assertRaisesRegex(ValueError, "reference ID bytes"):
            m.probe_target(session, recorder, [10, 17], 1, reference_piece=bytes([234]))
        self.assertEqual(len(session.calls), 1)

    def test_fragment_cache_row_caller_keeps_original_prefix_and_same_k_repeat(self):
        from scripts.test_p106b_alm_utf8_probability import fixture_response
        row = NativeTemplateContract().fixture()
        prefix = NativeTemplateContract().prefix(row)
        session, recorder = self.probe_fixture()
        recorder.row = None
        def transport(route, payload, timeout):
            session.calls.append((route, copy.deepcopy(payload)))
            if route == "/apply-template": return dict(prompt=prefix)
            if route == "/tokenize":
                parts = [dict(id=20, piece=prefix), dict(id=17, piece=[234]),
                         dict(id=18, piece=[176, 128]), dict(id=90, piece="<|im_end|>"), dict(id=22, piece="\n")]
                return dict(tokens=parts if payload["with_pieces"] else [p["id"] for p in parts])
            reply = fixture_response(payload)
            reply["completion_probabilities"][0]["top_logprobs"][18].update(token="", bytes=[176, 128])
            return reply
        session.transport = transport
        result = m.cache_row(session, recorder, row, {90: "<|im_end|>"}, cache_prompt=False,
                             verify_all_cache=True, native_template=True, cold_replicate=True)
        requests = [p for route, p in session.calls if route == "/completion"]
        self.assertEqual([p["prompt"] for p in requests], [[20], [20, 17], [20], [20, 17]])
        self.assertTrue(all(p["n_probs"] == 64 and p["cache_prompt"] is False for p in requests))
        self.assertEqual([s["target_id"] for s in result["target_scores"]], [17, 18])
        self.assertTrue(all(s["observed"]["chosen_probe"]["id"] == 4000 for s in result["target_scores"]))
        self.assertEqual(len(result["cache_verifications"]), 2)
        self.assertEqual(result["cache_verification_scope"], "ALL_COLD_REPLICATES")
        self.assertAlmostEqual(sum(c["teacher_raw_logprob_sum"] for c in result["alignment"]["chunks"]), -12.7)
        self.assertTrue(result["eot_ce"])
        self.assertFalse(result["eot_kd"])

    def test_native_registry_binds_two_probe_bytes_and_header_vocab_without_model_io(self):
        session, recorder = self.probe_fixture()
        def transport(route, payload, timeout):
            session.calls.append((route, copy.deepcopy(payload)))
            literal = payload["content"]
            return dict(tokens=[dict(id=4000 if literal == "A" else 4001, piece=literal)])
        session.transport = transport
        header = dict(tensors={"token_embd.weight": dict(shape=[8, 4096]),
                               "output.weight": dict(shape=[8, 4096])})
        fake_path = SimpleNamespace(open=lambda *args, **kwargs: BytesIO(b"synthetic header"))
        with patch.object(m, "regular", return_value=fake_path), \
             patch("scripts.p106b_mtp_teacher.gguf_metadata", return_value=header):
            m.native_ascii_registry(session, recorder, {4094: "BOS", 4095: "EOT"})
        self.assertEqual(recorder.native_vocab_size, 4096)
        self.assertEqual([p.token_id for p in recorder.ascii_probes], [4000, 4001])
        self.assertEqual([p["parse_special"] for _, p in session.calls], [False, True, False, True])
        self.assertIn("NOT_A_GLOBAL_SPECIAL_REGISTRY", recorder.writer.rows[-1]["ordinary_token_evidence"])

    def test_native_registry_refuses_header_mismatch_before_probe_requests(self):
        session, recorder = self.probe_fixture()
        header = dict(tensors={"token_embd.weight": dict(shape=[8, 4096]),
                               "output.weight": dict(shape=[8, 4097])})
        fake_path = SimpleNamespace(open=lambda *args, **kwargs: BytesIO(b"synthetic header"))
        with patch.object(m, "regular", return_value=fake_path), \
             patch("scripts.p106b_mtp_teacher.gguf_metadata", return_value=header), \
             self.assertRaisesRegex(ValueError, "vocabulary proof"):
            m.native_ascii_registry(session, recorder, {})
        self.assertEqual(session.calls, [])


class FailedReferenceV7Contract(unittest.TestCase):
    def fixture(self):
        from scripts.p106b_alm_utf8_probability import TARGET_ORIGIN
        wanted = m.FAILED_TARGET_EXPECTATION
        score = dict(raw_index=1, shifted_index=0, target_id=wanted["target_id"], raw_logprob=-8., bias=100,
            native_prefix_ids_sha256=wanted["native_prefix_ids_sha256"], reference_piece_hex=wanted["piece_hex"],
            probability_origin=TARGET_ORIGIN,
            observed=dict(chosen_probe=dict(id=4000, logprob=-12.),
                reference_target=dict(id=wanted["target_id"], logprob=-8.),
                top=[dict(id=1, logprob=-1.), dict(id=2, logprob=-2.)]),
            probe=dict(status="FOUND", requested_n_probs=64, actual_n_probs=64, bias=100,
                reference_target_id=wanted["target_id"], target_probability_origin=TARGET_ORIGIN,
                target_logprob=-8., target_rank=19, probe_id=4000, chosen_probe=dict(id=4000, logprob=-12.),
                raw_target=dict(id=wanted["target_id"], logprob=-8., bytes=[236, 155])))
        row = dict(row_id="alm_000034", selection_index=34,
            teacher_ids=[7, wanted["target_id"], 8],
            teacher_pieces=[dict(id=7, piece="P"), dict(id=wanted["target_id"], piece=[236, 155]), dict(id=8, piece="X")],
            target_scores=[score], cache_verifications=[dict(raw_index=1, mode="COLD_COLD_REPLICATE",
                cold=copy.deepcopy(score), warm=copy.deepcopy(score), comparison=dict(passed=True))])
        registry = dict(vocab_size=40000, probes=[dict(token_id=4000, piece_hex="41"),
                                               dict(token_id=4001, piece_hex="42")])
        return row, registry

    def invoke(self, row, registry):
        # 원 prefix는 읽지 않는다. 여기서는 metadata predicate만 격리해 검사한다.
        with patch.object(m, "object_sha", return_value=m.FAILED_TARGET_EXPECTATION["native_prefix_ids_sha256"]):
            return m.failed_target_recovery([row], registry)

    def test_saved_reference_and_two_cold_events_have_exact_recovery_metadata(self):
        row, registry = self.fixture()
        result = self.invoke(row, registry)
        self.assertTrue(result["passed"])
        self.assertEqual(result["target_id"], 36054)
        self.assertEqual(result["piece_hex"], "ec9b")
        self.assertEqual(result["native_prefix_ids_sha256"], m.FAILED_TARGET_EXPECTATION["native_prefix_ids_sha256"])
        self.assertEqual([o["kind"] for o in result["observations"]], ["saved", "cold", "replicate"])
        self.assertFalse(result["quality_claim"])

    def test_original_prefix_is_recomputed_not_accepted_only_from_metadata(self):
        row, registry = self.fixture()
        with self.assertRaisesRegex(ValueError, "prefix identity"):
            m.failed_target_recovery([row], registry)

    def test_row_inclusion_without_failed_event_is_not_recovery(self):
        row, registry = self.fixture()
        row["target_scores"] = []
        with self.assertRaisesRegex(ValueError, "not actually recovered"):
            self.invoke(row, registry)

    def test_wrong_id_bytes_prefix_probe_origin_or_repeat_is_not_recovery(self):
        for mutate in ("id", "piece", "prefix", "selected_probe", "origin", "repeat", "different_k", "imputed_logp"):
            row, registry = self.fixture()
            score = row["target_scores"][0]
            if mutate == "id": score["target_id"] = 36055
            elif mutate == "piece": row["teacher_pieces"][1]["piece"] = [236, 156]
            elif mutate == "prefix": score["native_prefix_ids_sha256"] = "F" * 64
            elif mutate == "selected_probe": score["observed"]["chosen_probe"]["id"] = 36054
            elif mutate == "origin": score["probability_origin"] = "selected_probe"
            elif mutate == "repeat": row["cache_verifications"] = []
            elif mutate == "different_k": row["cache_verifications"][0]["warm"]["probe"]["requested_n_probs"] = 512
            else: score["probe"]["raw_target"]["logprob"] = -12.
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.invoke(row, registry)


class CanaryClosureV7Contract(unittest.TestCase):
    def fixture(self):
        _, recorder = StrictV7ActualContract().completed_controls()
        rows, identity, report = closed_fixture()
        extra = copy.deepcopy(rows[0])
        extra["prepared_row_sha256"] = "failed34-fixture"
        extra.pop("cache_row_sha256")
        extra["cache_row_sha256"] = m.object_sha(extra)
        rows.append(extra)
        identity["prepared_row_sha256"] = [r["prepared_row_sha256"] for r in rows]
        identity["expected_language_rows"] = dict(ko=9, en=8)
        report.update(status="ALM_CANARY_COMPLETE", rows_completed=17, language_totals=m.language_totals(rows),
                      cache_row_sha256=[r["cache_row_sha256"] for r in rows],
                      ascii_probe_registry=recorder.report["ascii_probe_registry"],
                      normal_forcing_probe_controls=recorder.report["normal_forcing_probe_controls"],
                      normal_forcing_probe_matrix=recorder.report["normal_forcing_probe_matrix"],
                      failed_target_recovery={"passed": True, "fixture": "isolated recovery predicate"})
        return rows, identity, report

    def invoke(self, rows, identity, report):
        with patch.object(m, "read_json", return_value=report), \
             patch("scripts.p106b_shards.verify"), \
             patch("scripts.p101a_sft_mtp_data.stream_rows", return_value=iter(rows)), \
             patch.object(m, "failed_target_recovery", return_value={"passed": True, "fixture": "isolated recovery predicate"}):
            return m.closed_batch(Path("unused-fixture"), identity, canary=True)

    def test_closure_recomputes_four_control_matrix(self):
        rows, identity, report = self.fixture()
        self.assertIs(self.invoke(rows, identity, report), report)

    def test_closure_rejects_duplicate_control_even_when_passed_and_count_four(self):
        rows, identity, report = self.fixture()
        report["normal_forcing_probe_controls"][-1] = copy.deepcopy(report["normal_forcing_probe_controls"][0])
        with self.assertRaisesRegex(ValueError, "combinations"):
            self.invoke(rows, identity, report)

    def test_closure_rejects_missing_or_falsely_stored_recovery_proof(self):
        rows, identity, report = self.fixture()
        report.pop("failed_target_recovery")
        with self.assertRaisesRegex(ValueError, "recovery metadata"):
            self.invoke(rows, identity, report)


if __name__ == "__main__":
    unittest.main()
