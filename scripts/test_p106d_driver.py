"""No-model controller tests: guards, closed rubric and backend journal."""
from __future__ import annotations
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from urllib.error import HTTPError
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106d_views as driver
from scripts import p106d_teacher_views as wire


class ControllerTests(unittest.TestCase):
    def test_checkonly_never_calls_model_or_tokenizer(self):
        with patch.object(sys,"argv",["diag","--mode","teacher","--check-only"]), \
             patch.object(driver,"tokenizer",side_effect=AssertionError("private tokenizer read")), \
             patch.object(driver,"teacher",side_effect=AssertionError("model request")), \
             patch("sys.stdout",new=io.StringIO()):
            self.assertEqual(driver.main(),0)

    def test_source_output_symlink_and_tag_escape_refused(self):
        for name in ("../bad","bad/path","UPPER"):
            with self.assertRaises(ValueError): driver.paths(name,"prepare")

    def test_closed_only_rubric(self):
        self.assertTrue(driver.classify("+5","5")); self.assertTrue(driver.classify("TRUE","true"))
        self.assertTrue(driver.classify('{"answer":"5"}','{"answer":"5"}'))
        self.assertFalse(driver.classify("5 because arithmetic","5"))
        self.assertFalse(driver.classify("unsupported free answer","expected exact value"))

    def test_http_error_body_preserved_and_secret_redacted(self):
        class Session:
            key="fixture-secret"
            def request(self,*args,**kwargs):
                raise HTTPError("http://localhost/",500,"server failure",{},io.BytesIO(b"native backend fixture-secret mismatch"))
        records=[]
        with self.assertRaises(HTTPError): driver.request_with_evidence(Session(),{"safe":"request"},records.append,"g",timeout=1)
        self.assertEqual(records[0]["http_status"],500)
        self.assertIn("native backend",records[0]["error_body"])
        self.assertNotIn("fixture-secret",records[0]["error_body"])
        self.assertEqual(len(records[0]["captured_body_sha256"]),64)

    def test_second_single_view_paraphrases_same_source(self):
        case=wire.cases()[0]
        data={"choices":[{"finish_reason":"stop","message":{"content":"QUESTION_1:\n동일한 합을 계산하면?\nANSWER_1:\n5\nNOTE:\n"}}]}
        self.assertEqual(wire.parse(data,1,case,view_number=2)["status"],"QA_VIEWS_WIRE_COMPLETE")
        self.assertEqual(wire.parse(data,1,case,view_number=1)["status"],"PARSE_ERROR")

    def test_incomplete_report_does_not_load_student(self):
        args=SimpleNamespace(mode="fixed",tag="fixture",max_wall_sec=1800)
        with tempfile.TemporaryDirectory(prefix="p106d_guard_") as folder:
            corpus=Path(folder); driver.write(corpus/"report.json",{"ready":False,"train_rows":0})
            with patch.object(driver,"tokenizer",side_effect=AssertionError("tokenizer must not load")):
                with self.assertRaises(FileNotFoundError): driver.train(args,{"code_sha256":{}},corpus,corpus)

    def test_teacher_failure_preserves_raw_manifest_and_body(self):
        from scripts import p106b_gemma_teacher as gemma
        from scripts import p106b_gate_runtime as lifecycle
        class Session:
            key="fixture-secret"
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def request(self,*args,**kwargs):
                raise HTTPError("http://localhost/",500,"failure",{},io.BytesIO(b"native backend failure"))
        args=SimpleNamespace(seed=1337,max_wall_sec=10)
        with tempfile.TemporaryDirectory(prefix="p106d_partial_") as tmp, \
             patch.object(driver,"tokenizer",return_value=(None,{})), \
             patch.object(gemma,"assets",return_value={"model_sha256":"A"*64}), \
             patch.object(gemma,"GemmaSession",return_value=Session()), \
             patch.object(lifecycle,"idle_before_gpu"):
            folder=Path(tmp)
            with self.assertRaises(HTTPError): driver.teacher(args,{},folder)
            partial=json.loads((folder/"teacher_partial.json").read_text())
            self.assertEqual(partial["status"],"PRESERVED_PARTIAL_JOURNAL")
            self.assertEqual(partial["raw_manifest"]["rows"],1)
            part=partial["raw_manifest"]["shards"][0]["path"]
            raw=json.loads((folder/part).read_text())
            self.assertIn("native backend failure",raw["error_body"])

    def test_rates_count_retries_and_match_complete_source_set(self):
        def row(case,condition,status="QA_VIEWS_WIRE_COMPLETE"):
            return {"case":case,"condition":condition,"status":status,"attempts":2,
                    "request_sum_sec_including_retries":10,"candidate_x_tokens":20,"candidate_targets":5,
                    "completion_tokens_including_retries":100}
        rows=[row("a","single"),row("a","single"),row("a","paired"),
              row("b","single"),row("b","single","PARSE_ERROR"),row("b","paired")]
        r=driver.teacher_rates(rows)
        self.assertEqual(r["common_complete_sources"],["a"])
        self.assertEqual(r["single"]["all_sources"]["request_sum_sec"],40)
        self.assertEqual(r["single"]["same_completed_sources"]["request_sum_sec"],20)

    def test_successful_teacher_closes_all_raw_and_candidate_shards(self):
        from scripts import p106b_gemma_teacher as gemma
        from scripts import p106b_gate_runtime as lifecycle
        from scripts import p106d_views as views
        class Session:
            key="fixture-secret"
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def check(self): return None
            def request(self,path,data,**kwargs):
                source=json.loads(data["messages"][1]["content"])
                count=source["producer_control"]["qa_count"]
                fields=[]
                for i in range(1,count+1):
                    fields.extend((f"QUESTION_{i}:",source["SOURCE"]["learner_question"],f"ANSWER_{i}:","5"))
                fields.extend(("NOTE:","fixture only"))
                return {"choices":[{"finish_reason":"stop","message":{
                    "content":"\n".join(fields),"reasoning_content":"fixture thinking"}}],
                    "usage":{"completion_tokens":4,"prompt_tokens":2,"total_tokens":6}}
        args=SimpleNamespace(seed=1337,max_wall_sec=10)
        with tempfile.TemporaryDirectory(prefix="p106d_success_") as tmp, \
             patch.object(driver,"tokenizer",return_value=(None,{})), \
             patch.object(gemma,"assets",return_value={"model_sha256":"A"*64}), \
             patch.object(gemma,"GemmaSession",return_value=Session()), \
             patch.object(lifecycle,"idle_before_gpu"), \
             patch.object(views,"real_signature",return_value=(16,4)), \
             patch("sys.stdout",new=io.StringIO()):
            folder=Path(tmp)
            result,rc=driver.teacher(args,{},folder)
            self.assertEqual(rc,0)
            self.assertEqual(result["raw_manifest"]["rows"],24)
            self.assertEqual(result["candidate_manifest"]["rows"],32)
            partial=json.loads((folder/"teacher_partial.json").read_text())
            self.assertEqual(partial["raw_manifest"]["rows"],24)
            records=[]
            for part in partial["raw_manifest"]["shards"]:
                records.extend(json.loads(line) for line in (folder/part["path"]).read_text().splitlines())
            self.assertEqual(len(records),24)
            self.assertTrue(all(row["parsed"]["raw_thinking"]=="fixture thinking" for row in records))


if __name__=="__main__": unittest.main(verbosity=2)
