"""Belebele 독립 제어기의 합성 CPU 회귀. 실제 자료·모델·GPU·네트워크는 열지 않는다."""
from __future__ import annotations

import ast
from contextlib import contextmanager, redirect_stderr
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from scripts import diag_p106b_belebele as m
from scripts.p106b_shards import ShardWriter, verify


def fixture_documents(count=3):
    documents = {}
    for language in m.LANGUAGES:
        rows = []
        for index in range(count):
            doc = dict(link="https://example.invalid/article-" + str(index // 2),
                question_number=index % 2 + 1, flores_passage="passage" + str(index),
                question="  fixture question " + str(index) + "  ", correct_answer_num=str(index % 4 + 1),
                dialect=language, ds="2023-07-21" if language == "kor_Hang" else "2023-05-03")
            doc.update({"mc_answer" + str(number): "fixture answer " + str(number) for number in range(1, 5)})
            if count % 2 and index == count - 1:
                doc["question_number"] = 2  # q2만 있는 singleton도 허용한다.
            rows.append(doc)
        documents[language] = rows if language == "kor_Hang" else list(reversed(rows))
    return documents


class FixtureTask:
    def __init__(self, rows):
        self.eval_docs = rows
        self.config = SimpleNamespace(task="belebele_" + rows[0]["dialect"], repeats=1)

    def doc_to_text(self, doc):
        return (f"P: {doc['flores_passage']}\nQ: {doc['question'].strip()}\n"
                + "\n".join(letter + ": " + doc["mc_answer" + str(i)] for i, letter in enumerate("ABCD", 1))
                + "\nAnswer:")

    def doc_to_choice(self, doc):
        return list("ABCD")

    def doc_to_target(self, doc):
        return int(doc["correct_answer_num"]) - 1

    def fewshot_context(self, doc, **kwargs):
        if kwargs != dict(num_fewshot=0, apply_chat_template=False, fewshot_as_multiturn=False, system_instruction=None):
            raise AssertionError("0shot/chatOFF 원형이 다르다")
        return self.doc_to_text(doc)

    def construct_requests(self, doc, ctx, metadata, apply_chat_template):
        if apply_chat_template or metadata != (self.config.task, self.eval_docs.index(doc), 1):
            raise AssertionError("공식 요청 원형이 다르다")
        return [SimpleNamespace(request_type="loglikelihood", args=(ctx, " " + choice)) for choice in "ABCD"]

    def process_results(self, doc, responses):
        chosen = max(range(4), key=lambda i: responses[i][0])
        return dict(acc=int(chosen == self.doc_to_target(doc)), acc_norm=int(chosen == self.doc_to_target(doc)))

    def aggregation(self):
        return {name: lambda values: sum(values) / len(values) for name in ("acc", "acc_norm")}


class FixtureLM:
    prefix_token_id = 1
    core = SimpleNamespace(vocab_size=32)

    def __init__(self, *, long_marker=None, offset=0):
        self.long_marker, self.offset, self.scoring_calls = long_marker, offset, 0

    def _encode_pair(self, context, continuation):
        if self.long_marker is not None and self.long_marker in context:
            context += "x" * 1600
        return ([((ord(char) + self.offset) % 25) + 2 for char in context],
                [((ord(char) + self.offset) % 25) + 2 for char in continuation])

    def loglikelihood(self, requests, disable_tqdm=True):
        self.scoring_calls += 1
        return [(-float(index + 1), False) for index, _ in enumerate(requests)]


class WrongMetricTask(FixtureTask):
    def process_results(self, doc, responses):
        return dict(acc=1, acc_norm=0)


class WrongChoicesTask(FixtureTask):
    def doc_to_choice(self, doc):
        return [doc["mc_answer" + str(i)] for i in range(1, 5)]


class WrongDelimiterTask(FixtureTask):
    def construct_requests(self, *args, **kwargs):
        requests = super().construct_requests(*args, **kwargs)
        return [SimpleNamespace(request_type=request.request_type, args=(request.args[0], request.args[1].strip()))
                for request in requests]


class MissingResponseLM(FixtureLM):
    def loglikelihood(self, requests, disable_tqdm=True):
        return [(-1., False)]


class FakeHTTP(io.BytesIO):
    def __init__(self, raw, *, url=None, status=200, advertised=None):
        super().__init__(raw)
        self.url = url or m.SPECS["kor_Hang"]["url"]
        self.status = status
        self.headers = {} if advertised is None else {"Content-Length": str(advertised)}

    def geturl(self):
        return self.url


class BelebeleTests(unittest.TestCase):
    def task_yaml(self, language="kor_Hang"):
        return dict(task="belebele_" + language, dataset_path="facebook/belebele", dataset_name=language,
            output_type="multiple_choice", test_split="test", fewshot_split="test", fewshot_config=dict(sampler="first_n"),
            doc_to_text=m.PROMPT, doc_to_choice=list("ABCD"), doc_to_target=m.TARGET,
            metric_list=[dict(metric=name, aggregation="mean", higher_is_better=True) for name in ("acc", "acc_norm")],
            should_decontaminate=True, doc_to_decontamination_query="question", metadata=dict(version=1.0))

    def fixture_spec(self, raw=b"fixture source\n"):
        return dict(m.SPECS["kor_Hang"], bytes=len(raw),
                    git_blob_oid=hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest())

    def tasks(self, documents):
        return {language: FixtureTask(rows) for language, rows in documents.items()}

    def frozen_plans(self, tasks, lm=None):
        lm = FixtureLM() if lm is None else lm
        return {language: {i: [m.token_plan(lm, request) for request in m.requests_for(task, doc, i)]
                           for i, doc in enumerate(task.eval_docs)} for language, task in tasks.items()}

    def write(self, directory, rows, stem="fixture"):
        writer = ShardWriter(directory, stem, limit=10000)
        for row in rows:
            writer.append(row)
        return writer.close(lineage=dict(fixture=True))

    def record(self, task, index):
        doc = task.eval_docs[index]
        requests = m.requests_for(task, doc, index)
        responses, metrics = m.item_metrics(task, doc, FixtureLM().loglikelihood(requests))
        return dict(doc_id=index, language=doc["dialect"], key=list(m.key_for(doc)), doc=doc,
            arguments=[list(request.args) for request in requests], responses=[list(value) for value in responses],
            metrics=metrics, plans=[m.token_plan(FixtureLM(), request) for request in requests], common_untruncated=True)

    def cost(self):
        return dict(schema=m.SCHEMA, tag=m.TAG, model="falcon90m", mode="cost", returncode=0,
            status="BELEBELE_COST_COMPLETE", source_identity=dict(fixture=True), policy=m.policy("falcon90m"),
            canary_report_sha256="fixture-canary", prepare_report_sha256="fixture-prepare",
            sources_unchanged=True, inputs_unchanged=True, raw_independent_recount=True,
            actual_counts={language: 32 for language in m.LANGUAGES}, actual_rows=64, actual_choice_likelihoods=256,
            evaluation_seconds=dict(kor_Hang=4., eng_Latn=6.), wall_seconds=20.)

    def admission(self):
        return m.base.control.window(m.base.control.DEADLINE_ISO, 7200, "full", now=m.base.control.LATEST_DEADLINE - 10000)

    def admit(self, cost=None, **kwargs):
        return m.full_admission(self.cost() if cost is None else cost, dict(fixture=True), "falcon90m", self.admission(),
            "fixture-canary", "fixture-prepare", now=kwargs.get("now", m.base.control.LATEST_DEADLINE - 10000))

    def test_exact_original_revision_urls_bytes_blob_oids_and_license(self):
        self.assertEqual(m.REVISION, "7899cdfa4e1e0d733fd77c848e2c273cb1d32be2")
        self.assertEqual(m.LICENSE, "CC-BY-SA-4.0")
        self.assertEqual(m.SPECS["kor_Hang"]["bytes"], 1534047)
        self.assertEqual(m.SPECS["eng_Latn"]["git_blob_oid"], "a678517e601a401ba28a8c51287b7e186b161ef6")
        self.assertEqual(len(m.ALLOWED_URLS), 2)
        self.assertIn("_default_template_yaml", m.YAML_PINS)
        self.assertNotIn("_default_template_yaml.yaml", m.YAML_PINS)

    def test_git_blob_hash_includes_git_header_and_sha256_is_separate(self):
        raw = b"fixture source\n"; spec = self.fixture_spec(raw)
        proof = m.verify_blob(raw, spec)
        self.assertEqual(proof["sha256"], hashlib.sha256(raw).hexdigest().upper())
        for change in (dict(bytes=len(raw) + 1), dict(git_blob_oid=hashlib.sha1(raw).hexdigest())):
            with self.assertRaises(ValueError):
                m.verify_blob(raw, dict(spec, **change))

    def test_duplicate_json_keys_and_nonfinite_constants_are_rejected(self):
        self.assertEqual(m.decode('{"fixture":"한글"}'), dict(fixture="한글"))
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                m.decode(raw)

    def test_exact_asset_download_and_existing_byte_revalidation_without_network(self):
        raw = b"fixture source\n"; spec = self.fixture_spec(raw); calls = []
        def opener(request, timeout):
            calls.append((request.full_url, timeout))
            return FakeHTTP(raw, advertised=len(raw))
        with tempfile.TemporaryDirectory() as name:
            data, receipt = m.acquire_file(Path(name), spec, allow_download=True, opener=opener)
            self.assertEqual(data, raw)
            self.assertTrue(receipt["downloaded_in_this_phase"])
            self.assertEqual(receipt["git_blob_oid"], spec["git_blob_oid"])
            again, reused = m.acquire_file(Path(name), spec, opener=lambda *a, **k: self.fail("기존 파일은 취득하지 않는다"))
            self.assertEqual(again, raw)
            self.assertFalse(reused["downloaded_in_this_phase"])
            self.assertEqual(calls, [(spec["url"], 30)])

    def test_missing_asset_never_downloads_without_explicit_prepare_admission(self):
        with tempfile.TemporaryDirectory() as name, self.assertRaises(FileNotFoundError):
            m.acquire_file(Path(name), self.fixture_spec(), opener=lambda *a, **k: self.fail("네트워크 금지"))

    def test_bad_existing_asset_is_preserved_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); target = directory / "kor_Hang.jsonl"
            with target.open("xb") as stream:
                stream.write(b"bad prior artifact")
            with self.assertRaises(ValueError):
                m.acquire_file(directory, self.fixture_spec(), allow_download=True,
                               opener=lambda *a, **k: self.fail("기존 실패 파일 덮기 금지"))
            self.assertEqual(target.read_bytes(), b"bad prior artifact")

    def test_only_two_exact_urls_and_names_are_allowed(self):
        with tempfile.TemporaryDirectory() as name:
            for change in (dict(url="https://example.invalid/fixture"), dict(filename="../fixture.jsonl"),
                           dict(bytes=True), dict(bytes=m.base.control.LIMIT)):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    m.acquire_file(Path(name), dict(self.fixture_spec(), **change), allow_download=True,
                                   opener=lambda *a, **k: self.fail("허용목록 밖 URL 금지"))

    def test_http_status_redirect_and_advertised_length_are_checked_before_file_creation(self):
        raw = b"fixture source\n"
        for options in (dict(status=404), dict(url="http://huggingface.co/fixture"),
                        dict(url="https://example.invalid/fixture"), dict(url="https:///missing-host"),
                        dict(url="https://user@huggingface.co/fixture"), dict(advertised=1)):
            with tempfile.TemporaryDirectory() as name, self.subTest(options=options):
                with self.assertRaises(ValueError):
                    m.acquire_file(Path(name), self.fixture_spec(raw), allow_download=True,
                                   opener=lambda *a, **k: FakeHTTP(raw, **options))
                self.assertFalse((Path(name) / "kor_Hang.jsonl").exists())

    def test_bounded_http_preserves_short_and_overlong_partial_files(self):
        raw = b"fixture source\n"
        for body in (raw[:-1], raw + b"overlong"):
            with tempfile.TemporaryDirectory() as name, self.subTest(length=len(body)):
                with self.assertRaises(ValueError):
                    m.acquire_file(Path(name), self.fixture_spec(raw), allow_download=True,
                                   opener=lambda *a, **k: FakeHTTP(body))
                self.assertTrue((Path(name) / "kor_Hang.jsonl").exists())

    def test_redirect_destination_is_checked_before_next_network_request(self):
        request = m.Request(m.SPECS["kor_Hang"]["url"])
        handler = m.OfficialRedirect()
        for url in ("https://example.invalid/fixture", "file:///fixture", "http://huggingface.co/fixture"):
            with self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, "fixture", {}, url)
        redirected = handler.redirect_request(request, None, 302, "fixture", {}, "https://cas-bridge.xethub.hf.co/fixture")
        self.assertEqual(redirected.full_url, "https://cas-bridge.xethub.hf.co/fixture")

    def test_cache_and_asset_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); real = directory / "real"; real.mkdir()
            linked = directory / "linked"; linked.symlink_to(real, target_is_directory=True)
            with self.assertRaises(ValueError):
                m.acquire_file(linked, self.fixture_spec())
            (real / "kor_Hang.jsonl").symlink_to(directory / "missing")
            with self.assertRaises(ValueError):
                m.acquire_file(real, self.fixture_spec())

    def test_key_join_is_language_order_independent_ds_independent_and_allows_q2_singletons(self):
        docs = fixture_documents()
        audit = m.align_languages(docs, expected_rows=3, expected_links=2)
        self.assertEqual(audit["paired_keys"], 3)
        self.assertEqual(audit["paired_links"], 2)
        self.assertEqual(audit["gold_index_disagreements"], 0)
        self.assertEqual(audit["languages"]["kor_Hang"]["questions_per_link"], {"1": 1, "2": 1})
        self.assertNotEqual(docs["kor_Hang"][0]["link"], docs["eng_Latn"][0]["link"])

    def test_missing_join_key_wrong_gold_duplicate_key_and_wrong_link_count_are_rejected(self):
        for change in (lambda d: d["eng_Latn"][0].update(link="different-key"),
                       lambda d: d["eng_Latn"][0].update(correct_answer_num="4"),
                       lambda d: d["kor_Hang"][1].update(question_number=1),
                       lambda d: d["kor_Hang"].pop()):
            docs = fixture_documents(); change(docs)
            with self.assertRaises(ValueError):
                m.align_languages(docs, expected_rows=3, expected_links=2)
        with self.assertRaises(ValueError):
            m.align_languages(fixture_documents(), expected_rows=3, expected_links=3)

    def test_exact_schema_string_gold_language_and_integer_question_number_required(self):
        for field, value in (("correct_answer_num", 1), ("correct_answer_num", "0"), ("dialect", "other"),
                             ("question_number", True), ("question_number", 3), ("mc_answer1", "  ")):
            docs = fixture_documents(); docs["kor_Hang"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                m.align_languages(docs, expected_rows=3, expected_links=2)
        docs = fixture_documents(); docs["kor_Hang"][0]["extra"] = "not raw source"
        with self.assertRaises(ValueError):
            m.align_languages(docs, expected_rows=3, expected_links=2)

    def test_official_prompt_target_choices_and_metrics_are_deep_preserved(self):
        task_yaml = self.task_yaml(); before = m.validate_yaml(task_yaml, "kor_Hang")
        self.assertEqual(before["doc_to_choice"], list("ABCD"))
        task_yaml["metric_list"][0]["aggregation"] = "changed"
        self.assertEqual(before["metric_list"][0]["aggregation"], "mean")
        self.assertTrue(before["should_decontaminate"])

    def test_rewritten_choice_text_delimiter_target_language_or_metric_is_rejected(self):
        for key, value in (("doc_to_choice", ["answer1", "answer2", "answer3", "answer4"]),
                           ("doc_to_target", "{{correct_answer_num}}"), ("dataset_name", "eng_Latn"),
                           ("doc_to_text", "question"), ("metric_list", []), ("fewshot_config", dict(sampler="random"))):
            task_yaml = self.task_yaml(); task_yaml[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate_yaml(task_yaml, "kor_Hang")

    def test_fewshot_dataclass_normalization_does_not_compare_object_to_raw_dictionary(self):
        before = m.validate_yaml(self.task_yaml(), "kor_Hang")
        task = SimpleNamespace(config=SimpleNamespace(**{key: value for key, value in before.items() if key != "fewshot_config"}),
                               fewshot_cfg=SimpleNamespace(sampler="first_n"))
        task.config.num_fewshot, task.config.target_delimiter = 0, " "
        m.verify_task_fields(task, before)
        for field, value in (("num_fewshot", 1), ("target_delimiter", ""), ("test_split", "validation")):
            altered = copy.deepcopy(task); setattr(altered.config, field, value)
            with self.assertRaises(ValueError):
                m.verify_task_fields(altered, before)
        task.fewshot_cfg.sampler = "random"
        with self.assertRaises(ValueError):
            m.verify_task_fields(task, before)

    def test_official_requests_are_four_whole_leading_space_labels_not_answer_sentences(self):
        task = self.tasks(fixture_documents())["kor_Hang"]
        requests = m.requests_for(task, task.eval_docs[0], 0)
        self.assertEqual([request.args[1] for request in requests], [" A", " B", " C", " D"])
        self.assertIn("Q: fixture question 0\n", requests[0].args[0])
        self.assertEqual([m.token_plan(FixtureLM(), request)["continuation_tokens"] for request in requests], [2] * 4)

    def test_wrong_delimiter_or_answer_text_choice_requests_fail(self):
        docs = fixture_documents()["kor_Hang"]
        for task in (WrongDelimiterTask(docs), WrongChoicesTask(docs)):
            with self.assertRaises(ValueError):
                m.requests_for(task, docs[0], 0)

    def test_plan_uses_original_1025_boundary_and_keeps_all_continuation_subtokens(self):
        request = SimpleNamespace(args=("x" * 1023, " A"))
        edge = m.token_plan(FixtureLM(), request)
        self.assertEqual(edge["truncated_context_tokens"], 0)
        self.assertEqual(edge["input_tokens"], 1024)
        after = m.token_plan(FixtureLM(), SimpleNamespace(args=("x" * 1024, " A")))
        self.assertEqual(after["truncated_context_tokens"], 1)
        self.assertEqual(after["continuation_tokens"], 2)
        self.assertEqual(after["target_start"] + after["continuation_tokens"], 1024)

    def test_equal_token_lengths_do_not_hide_different_token_ids(self):
        request = SimpleNamespace(args=("fixture context", " A"))
        left, right = (m.token_plan(FixtureLM(offset=i), request) for i in (0, 1))
        for name in ("input_tokens", "continuation_tokens", "truncated_context_tokens"):
            self.assertEqual(left[name], right[name])
        self.assertNotEqual(left["encoded_context_sha256"], right["encoded_context_sha256"])
        self.assertNotEqual(left["encoded_continuation_sha256"], right["encoded_continuation_sha256"])
        with self.assertRaises(ValueError):
            m.token_plan(FixtureLM(), SimpleNamespace(args=("", " A")))

    def test_token_only_hf_inherits_encoder_and_sets_real_backend_without_model_constructor(self):
        calls = []
        class Template:
            def __init__(self):
                calls.append("template_init")
        class HFLM(Template):
            def __init__(self):
                raise AssertionError("모델 생성자 호출 금지")
            def tok_encode(self, text):
                return [3] * len(text)
            def _encode_pair(self, context, continuation):
                if self.backend != "causal":
                    raise AssertionError("공식 backend 속성 필요")
                return self.tok_encode(context), self.tok_encode(continuation)
        wrapper = m.token_only_hf_type(HFLM, Template)
        lm = wrapper(SimpleNamespace(bos_token_id=1), 32)
        self.assertIs(wrapper.tok_encode, HFLM.tok_encode)
        self.assertIs(wrapper._encode_pair, HFLM._encode_pair)
        self.assertEqual(m.token_plan(lm, SimpleNamespace(args=("ctx", " A")))["continuation_tokens"], 2)
        self.assertEqual(calls, ["template_init"])
        for action in (lambda: lm.loglikelihood([]), lambda: lm._model_call(None)):
            with self.assertRaises(RuntimeError):
                action()

    def freeze_fixture(self, directory, *, partial_report=None, check=lambda: None):
        docs = fixture_documents(); tasks = self.tasks(docs); instances = []
        @contextmanager
        def factory(model, pins):
            lm = FixtureLM(long_marker="passage1" if model == "m2" else None)
            instances.append(lm)
            yield lm, dict(model=model, model_instances=0, forward_calls=0)
        frozen = m.freeze_tokens(tasks, directory, {}, check, models=("m1", "m2"), factory=factory,
                                 partial_report=partial_report)
        return frozen, docs, instances

    def test_common_untruncated_freeze_is_intersection_of_all_models_languages_and_choices(self):
        with tempfile.TemporaryDirectory() as name:
            frozen, docs, instances = self.freeze_fixture(Path(name))
            self.assertEqual(frozen["token_manifest"]["rows"], 12)
            self.assertEqual(frozen["common_rows_per_language"], 2)
            self.assertEqual(frozen["model_instances"], 0)
            self.assertTrue(frozen["frozen_before_model_output"])
            self.assertTrue(all(lm.scoring_calls == 0 for lm in instances))
            selected, common = m.read_frozen(Path(name), frozen, docs, "m2", models=("m1", "m2"), expected_rows=3)
            self.assertEqual(len(selected["kor_Hang"]), 3)
            self.assertEqual(len(common), 2)
            self.assertGreater(selected["kor_Hang"][1][0]["truncated_context_tokens"], 0)

    def test_frozen_full_denominator_model_inventory_and_common_intersection_are_rechecked(self):
        with tempfile.TemporaryDirectory() as name:
            frozen, docs, _ = self.freeze_fixture(Path(name))
            for key, value in (("models", ["m1"]), ("frozen_before_model_output", False),
                               ("model_instances", 1), ("common_rows_per_language", 3), ("common_keys", [])):
                altered = copy.deepcopy(frozen); altered[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    m.read_frozen(Path(name), altered, docs, "m2", models=("m1", "m2"), expected_rows=3)
            with self.assertRaises(ValueError):
                m.read_frozen(Path(name), frozen, docs, "m2")

    def test_timeout_preserves_partial_token_shards_without_scores_or_forward(self):
        calls = []
        def check():
            calls.append(True)
            if len(calls) == 3:
                raise TimeoutError("fixture token-only timeout")
        with tempfile.TemporaryDirectory() as name:
            report = {}
            with self.assertRaisesRegex(TimeoutError, "fixture token-only timeout"):
                self.freeze_fixture(Path(name), partial_report=report, check=check)
            partial = report["partial_token_artifacts"]["partial_pair_manifest"]
            self.assertEqual(partial["rows"], 1)
            verify(Path(name), partial)

    def test_manifest_write_failure_preserves_closed_raw_metadata_and_original_exception(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); writer = ShardWriter(directory, "fixture")
            writer.append(dict(fixture=True))
            with writer.manifest_path.open("x") as stream:
                stream.write("existing fixture")
            report = {}
            with self.assertRaises(FileExistsError):
                m.close_writer(writer, {}, report, "fixture")
            failure = report["artifact_close_errors"]["fixture"]
            self.assertEqual(failure["rows"], 1)
            self.assertEqual(len(failure["shards"]), 1)
            self.assertEqual(writer.manifest_path.read_text(), "existing fixture")

    def test_official_acc_norm_equals_acc_with_label_character_lengths_and_earliest_tie(self):
        task = self.tasks(fixture_documents())["kor_Hang"]
        responses = [(-2., False)] * 4
        _, first = m.item_metrics(task, task.eval_docs[0], responses)
        _, second = m.item_metrics(task, task.eval_docs[1], responses)
        self.assertEqual(first, dict(acc=1, acc_norm=1))
        self.assertEqual(second, dict(acc=0, acc_norm=0))
        records = [dict(metrics=first), dict(metrics=second)]
        self.assertEqual(m.aggregate(task, records)["metrics"], dict(acc=.5, acc_norm=.5))

    def test_missing_labels_nonfinite_response_nonbool_and_wrong_metric_are_rejected(self):
        docs = fixture_documents()["kor_Hang"]; task = FixtureTask(docs)
        for responses in ([(-1., False)] * 3, [(-1., 0)] * 4, [(float("nan"), False)] * 4,
                          [(1., False)] * 4, [(True, False)] * 4):
            with self.assertRaises(ValueError):
                m.item_metrics(task, docs[0], responses)
        with self.assertRaises(ValueError):
            m.item_metrics(WrongMetricTask(docs), docs[0], [(-1., False)] * 4)

    def test_empty_common_subset_is_none_not_zero_accuracy(self):
        task = self.tasks(fixture_documents())["kor_Hang"]
        self.assertEqual(m.aggregate(task, [])["rows"], 0)
        self.assertIsNone(m.aggregate(task, [])["metrics"])

    def test_raw_recount_verifies_original_docs_requests_plans_metrics_and_common_keys(self):
        docs = fixture_documents(); task = self.tasks(docs)["kor_Hang"]
        rows = [self.record(task, i) for i in range(3)]
        plans = {row["doc_id"]: row["plans"] for row in rows}
        common = {m.key_for(doc) for doc in docs["kor_Hang"]}
        with tempfile.TemporaryDirectory() as name:
            manifest = self.write(Path(name), rows)
            result = m.recount_raw(task, docs["kor_Hang"], "kor_Hang", Path(name), manifest, 3, plans, common)
            self.assertEqual(result["rows"], 3)
            self.assertEqual(result["choice_likelihoods"], 12)
            self.assertEqual(result["auxiliary_common_untruncated"]["rows"], 3)
            self.assertTrue(result["raw_sha_verified"])

    def test_hash_valid_but_semantically_modified_raw_is_rejected(self):
        docs = fixture_documents(); task = self.tasks(docs)["kor_Hang"]
        original = [self.record(task, i) for i in range(3)]
        plans = {row["doc_id"]: row["plans"] for row in original}
        common = {m.key_for(doc) for doc in docs["kor_Hang"]}
        for change in (lambda r: r[0].update(doc_id=1), lambda r: r[0].update(language="eng_Latn"),
                       lambda r: r[0]["doc"].update(question="rewritten"),
                       lambda r: r[0]["arguments"][0].__setitem__(1, "A"),
                       lambda r: r[0]["plans"][0].update(continuation_tokens=1),
                       lambda r: r[0]["metrics"].update(acc=0),
                       lambda r: r[0].update(common_untruncated=False)):
            rows = copy.deepcopy(original); change(rows)
            with tempfile.TemporaryDirectory() as name:
                manifest = self.write(Path(name), rows)
                with self.assertRaises(ValueError):
                    m.recount_raw(task, docs["kor_Hang"], "kor_Hang", Path(name), manifest, 3, plans, common)

    def test_cost_runs_exact32_per_language_and256_full_label_likelihoods_without_full_claim(self):
        docs = fixture_documents(32); tasks = self.tasks(docs); plans = self.frozen_plans(tasks)
        common = {m.key_for(doc) for doc in docs["kor_Hang"][:4]}
        with tempfile.TemporaryDirectory() as name:
            report = {}
            m.evaluate(tasks, docs, FixtureLM(), "falcon90m", "cost", Path(name), report, lambda: None, plans, common)
            self.assertEqual(report["actual_rows"], 64)
            self.assertEqual(report["actual_choice_likelihoods"], 256)
            self.assertEqual(report["actual_counts"], dict(kor_Hang=32, eng_Latn=32))
            self.assertFalse(report["quality_claim"])
            self.assertEqual(report["confidence_intervals"], "NOT_RUN")
            self.assertEqual(report["independent_audits"]["kor_Hang"]["auxiliary_common_untruncated"]["rows"], 4)

    def test_synthetic_full_path_requires_exact1800_rows_and7200_choice_likelihoods(self):
        docs = fixture_documents(900); tasks = self.tasks(docs); plans = self.frozen_plans(tasks)
        common = {m.key_for(doc) for doc in docs["kor_Hang"]}
        with tempfile.TemporaryDirectory() as name:
            report = {}
            m.evaluate(tasks, docs, FixtureLM(), "falcon90m", "full", Path(name), report, lambda: None, plans, common)
            self.assertEqual(report["actual_rows"], 1800)
            self.assertEqual(report["actual_choice_likelihoods"], 7200)
            self.assertEqual(report["actual_counts"], dict(kor_Hang=900, eng_Latn=900))
            self.assertTrue(report["quality_claim"])  # 합성 제어분기 검사이며 실제 모델 품질 근거가 아니다.
            self.assertTrue(report["raw_independent_recount"])
            self.assertTrue(all(shard["bytes"] < 20_000_000 for manifest in report["sample_manifests"].values()
                                for shard in manifest["shards"]))

    def test_actual_runtime_equal_length_but_different_encoding_fails_before_scoring(self):
        docs = fixture_documents(32); tasks = self.tasks(docs); plans = self.frozen_plans(tasks)
        lm = FixtureLM(offset=1)
        with tempfile.TemporaryDirectory() as name, self.assertRaisesRegex(ValueError, "사전 동결"):
            m.evaluate(tasks, docs, lm, "falcon90m", "cost", Path(name), {}, lambda: None, plans, set())
        self.assertEqual(lm.scoring_calls, 0)

    def test_missing_response_and_timeout_do_not_become_complete_or_discard_partial_raw(self):
        docs = fixture_documents(32); tasks = self.tasks(docs); plans = self.frozen_plans(tasks)
        with tempfile.TemporaryDirectory() as name, self.assertRaises(ValueError):
            m.evaluate(tasks, docs, MissingResponseLM(), "falcon90m", "cost", Path(name), {}, lambda: None, plans, set())
        calls = []
        def check():
            calls.append(True)
            if len(calls) == 2:
                raise TimeoutError("fixture evaluation timeout")
        with tempfile.TemporaryDirectory() as name:
            report = {}
            with self.assertRaisesRegex(TimeoutError, "fixture evaluation timeout"):
                m.evaluate(tasks, docs, FixtureLM(), "falcon90m", "cost", Path(name), report, check, plans, set())
            manifest = report["partial_artifacts"]["kor_Hang"]["partial_pair_manifest"]
            self.assertEqual(manifest["rows"], 1)
            verify(Path(name), manifest)
            self.assertNotIn("quality_claim", report)

    def test_full_forecast_uses_both_language_real_cost_multiplier_overhead_and_cleanup(self):
        result = self.admit()
        self.assertEqual(result["forecast_multiplier"], 1.5)
        self.assertEqual(result["observed_non_eval_overhead_seconds"], 10.)
        self.assertAlmostEqual(result["forecast_seconds"], (900 / 32 * 10) * 1.5 + 10 + 120)
        self.assertEqual(result["hard_cap_seconds"], 7200)

    def test_old_partial_changed_source_model_canary_prepare_or_policy_cost_is_rejected(self):
        for key, value in (("source_identity", {}), ("model", "native595-f"), ("returncode", 9),
                           ("status", "OFFICIAL_CORE6_COST_COMPLETE"), ("canary_report_sha256", "other"),
                           ("prepare_report_sha256", "other"), ("policy", {}), ("sources_unchanged", False),
                           ("inputs_unchanged", False), ("raw_independent_recount", False), ("actual_rows", 63),
                           ("actual_choice_likelihoods", 255), ("actual_counts", dict(kor_Hang=31, eng_Latn=32))):
            cost = self.cost(); cost[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.admit(cost)

    def test_invalid_real_cost_timing_deadline_and_cap_are_rejected(self):
        for change in (lambda c: c["evaluation_seconds"].update(kor_Hang=0),
                       lambda c: c["evaluation_seconds"].update(eng_Latn=float("nan")),
                       lambda c: c.update(wall_seconds=5), lambda c: c.update(wall_seconds=True),
                       lambda c: c["evaluation_seconds"].update(eng_Latn=1000.)):
            cost = self.cost(); change(cost)
            with self.assertRaises(ValueError):
                self.admit(cost)
        with self.assertRaises(ValueError):
            self.admit(now=m.base.control.LATEST_DEADLINE - 100)
        for mode, cap in (("prepare", 601), ("canary", 601), ("cost", 601), ("full", 7201)):
            with self.assertRaises(ValueError):
                m.base.control.window(m.base.control.DEADLINE_ISO, cap, mode, now=m.base.control.LATEST_DEADLINE - 10000)

    def test_failure_finalization_keeps_primary_error_when_report_serialization_also_fails(self):
        with tempfile.TemporaryDirectory() as name:
            primary = TimeoutError("fixture original evaluation timeout")
            report = dict(returncode=9, status="BELEBELE_PARTIAL", error_type="TimeoutError", error=str(primary),
                          unserializable=object())
            result = m.base.finish_execution(report, Path(name), m.time.perf_counter(), {}, {"fixture": "pin"},
                primary_error=primary, identity_fn=lambda: {}, verify_fn=lambda pins: None)
            self.assertIs(result, report)
            saved = json.loads((Path(name) / "report.json").read_text())
            self.assertEqual(saved["original_error"], dict(type="TimeoutError", message=str(primary)))
            self.assertEqual(saved["report_closure_error"]["type"], "TypeError")
            self.assertEqual(saved["status"], "BELEBELE_PARTIAL")
            self.assertEqual(saved["returncode"], 9)
            self.assertEqual(report["error_type"], "TimeoutError")

    def test_runtime_cleanup_failure_does_not_replace_primary_evaluation_error(self):
        original = TimeoutError("fixture evaluation deadline")
        cleanup = RuntimeError("fixture runtime exit error")
        report = dict(quality_claim=True)
        primary = m.record_failure(report, cleanup, original)
        self.assertIs(primary, original)
        self.assertEqual(report["error_type"], "TimeoutError")
        self.assertEqual(report["error"], str(original))
        self.assertTrue(report["timed_out"])
        self.assertFalse(report["quality_claim"])
        self.assertEqual(report["secondary_runtime_errors"], [dict(type="RuntimeError", message=str(cleanup))])
        interrupted = {}
        m.record_failure(interrupted, KeyboardInterrupt("fixture interrupt"))
        self.assertEqual(interrupted["returncode"], 130)

    def test_execute_import_failure_guard_and_primary_error_connection_are_present(self):
        tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
        execute = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute")
        attempt = next(node for node in execute.body if isinstance(node, ast.Try))
        preceding = execute.body[:execute.body.index(attempt)]
        initialized = {node.id for stmt in preceding for node in ast.walk(stmt)
                       if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
        self.assertTrue({"torch", "require_idle_gpu", "primary_error"}.issubset(initialized))
        finish = next(node for stmt in attempt.finalbody for node in ast.walk(stmt)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "finish_execution")
        self.assertTrue(any(keyword.arg == "primary_error" and isinstance(keyword.value, ast.Name)
                            and keyword.value.id == "primary_error" for keyword in finish.keywords))

    def test_import_check_only_is_stdlib_and_frozen_helpers_only_without_data_or_gpu_calls(self):
        tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
        forbidden = {"torch", "tinylm", "transformers", "datasets", "lm_eval", "tokenizers"}
        for node in tree.body:
            if isinstance(node, ast.Import):
                self.assertFalse(any(alias.name.split(".")[0] in forbidden for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn((node.module or "").split(".")[0], forbidden)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                self.assertNotIn((node.func.value.id, node.func.attr), {("config", "get"), ("config", "update"),
                                                                      ("cfg", "get"), ("cfg", "update")})

    def test_cli_requires_explicit_source_and_prepare_is_all7_token_only(self):
        for argv in (("--prepare",), ("--prepare", "--mode", "cost", "--model", "falcon90m", "--source-sha256", "fixture"),
                     ("--prepare", "--model", "falcon90m", "--source-sha256", "fixture"),
                     ("--execute", "--mode", "cost", "--source-sha256", "fixture")):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                m.main(argv)
        selected = m.policy("gemma270")
        self.assertFalse(selected["cache"])
        self.assertFalse(selected["training"])
        self.assertEqual(selected["full_rows"], 1800)
        self.assertEqual(selected["full_choice_likelihoods"], 7200)
        self.assertEqual(selected["character_denominators"], [1, 1, 1, 1])
        self.assertEqual(len(m.MODELS), 7)
        self.assertEqual(selected["confidence_intervals"], "NOT_IMPLEMENTED_NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()
