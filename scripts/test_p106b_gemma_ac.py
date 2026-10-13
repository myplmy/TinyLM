"""CPU source-slot/channel/parameter contracts; no original data/model IO."""
from __future__ import annotations
from pathlib import Path
import io
import json
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_gemma_ac as core
from scripts import diag_p106b_gemma_ac as driver
from scripts import p106b_gemma_teacher as teacher

def jobs():
    result=[]
    for language in ("ko","en"):
        for i in range(4):
            sha=("%064x"%(i+1+(10 if language=="en" else 0))).upper()
            result.append({"language":language,"source_group_id":sha,"original":{"messages":[
                {"role":"user","content":[{"type":"text","text":"fixture"}]},
                {"role":"assistant","content":[{"type":"text","text":"answer"}]}],
                "meta":{"source_id":language+str(i),"source_repo":"TinyLM/code-fixture","source_revision":"v1",
                    "source_sha256":sha,"source_license":"CC0-1.0","source_family":"code_authored_fixture","split":"train"}}})
    return result

class ACTests(unittest.TestCase):
    def test_factorial_has12_cells56_logical_requests_same8_sources(self):
        j=jobs();p=core.plan(j)
        self.assertEqual(len(p),12)
        self.assertEqual(sum(len(core.blocks(j,size)) for repeat,size,t in p),56)
        self.assertEqual(p[6:],[(1,s,t) for r,s,t in reversed(p[:6])])
        for repeat,size,t in p:
            keys=[x["source_group_id"] for b in core.blocks(j,size) for x in b]
            self.assertEqual(len(keys),8);self.assertEqual(set(keys),{x["source_group_id"] for x in j})

    def test_duplicate_source_is_not_filler(self):
        j=jobs();j[1]["source_group_id"]=j[0]["source_group_id"]
        with self.assertRaises(ValueError):core.plan(j)

    def test_card_sampler_and_fixed_context_budget_independent_of_batch(self):
        for size in core.SIZES:
            for t in core.THINKING:
                p=core.payload(jobs()[:size],t,17)
                for k,v in teacher.SAMPLER.items():self.assertEqual(p[k],v)
                self.assertEqual(p["max_tokens"],6144);self.assertEqual(p["thinking_budget_tokens"],t)
                self.assertFalse(p["cache_prompt"])

    def test_indexed_inline_four_slots_and_private_thought_separate(self):
        final="\n".join(f"QUESTION_{i}: Q{i}\nANSWER_{i}: A{i}" for i in range(1,5))+"\nNOTE:"
        r=core.parse({"choices":[{"finish_reason":"stop","message":{"content":final,"reasoning_content":"private thought"}}]},4)
        self.assertEqual(len(r["slots"]),4);self.assertEqual(r["thinking"],"private thought")
        self.assertNotIn("private thought",r["slots"][0]["answer"])

    def test_length_stop_is_never_accepted(self):
        r=core.parse({"choices":[{"finish_reason":"length","message":{"content":"QUESTION_1: Q\nANSWER_1: A\nNOTE:"}}]},1)
        self.assertEqual(r["status"],"INCOMPLETE");self.assertFalse(r["slots"])

    def test_canonical_source_split_and_reasoning_ref_not_target(self):
        row=core.canonical(jobs()[0],{"question":"Q","answer":"A"},"A"*64,"fixture","secret","raw:fixture")
        self.assertEqual(row["meta"]["parent_concept_id"],jobs()[0]["source_group_id"])
        self.assertFalse(row["meta"]["reasoning_is_student_target"])
        self.assertNotIn("secret",json.dumps(row["messages"]))

    def test_runtime_profile_restores_original_teacher_defaults(self):
        before=(teacher.CONTEXT,teacher.MAX_OUTPUT,teacher.THINKING)
        with self.assertRaises(ValueError),driver.profile(16384,6144,256):
            self.assertEqual(teacher.THINKING,256);raise ValueError("fixture")
        self.assertEqual((teacher.CONTEXT,teacher.MAX_OUTPUT,teacher.THINKING),before)

    def test_checkonly_cannot_read_jobs_tokenizer_assets_or_model(self):
        with patch.object(sys,"argv",["fixture","--mode","panel","--check-only"]), \
             patch.object(driver,"jobs_and_tokenizer",side_effect=AssertionError("private data")), \
             patch.object(driver.teacher,"assets",side_effect=AssertionError("model header")), \
             patch.object(driver,"panel",side_effect=AssertionError("GPU")),patch("sys.stdout",new=io.StringIO()):
            self.assertEqual(driver.main(),0)

    def test_partial_cell_set_is_not_a_speed_adoption(self):
        self.assertFalse(core.summarize([])["same_completed_source_sets"])

    def test_real_telemetry_enum_is_sampled_only_not_continuous_complete(self):
        proof={"measurement_coverage":"SAMPLED_ONLY","successful_queries":3,"fatal_calls":0}
        self.assertTrue(driver.sampled_resource_ok({"sampled_gpu_min_free_mib":2048},proof))
        for coverage in ("GAPPED","COMPLETE","UNKNOWN"):
            self.assertFalse(driver.sampled_resource_ok({"sampled_gpu_min_free_mib":4096},dict(proof,measurement_coverage=coverage)))
        for free in (2047,None,True):
            self.assertFalse(driver.sampled_resource_ok({"sampled_gpu_min_free_mib":free},proof))

    def test_generic_request_only_session_counts_actual_template_tokens(self):
        class Session:
            def __init__(self):self.calls=[]
            def request(self,path,payload):
                self.calls.append((path,payload))
                return {'prompt':'exact prompt'} if path=='/apply-template' else {'tokens':[1,2,3]}
        session=Session()
        info=driver.count_prompt(session,[{'role':'user','content':'fixture'}],8192,3072)
        self.assertEqual(info['prompt_tokens'],3)
        self.assertEqual([p for p,b in session.calls],['/apply-template','/tokenize'])
        self.assertTrue(session.calls[1][1]['parse_special'])

    def test_budget_rejects_overflow_and_bad_server_contract(self):
        from scripts.p106b_gate_runtime import GateNegative
        class Session:
            def request(self,path,payload):
                return {'prompt':'x'} if path=='/apply-template' else {'tokens':[1]*150}
        with self.assertRaises(GateNegative):driver.count_prompt(Session(),[],256,128)
        class Bad:
            def request(self,path,payload):return {'tokens':[True]}
        with self.assertRaises(ValueError):driver.count_prompt(Bad(),[],8192,3072)

    def test_attribute_error_is_tool9_not_resource8(self):
        rows=[{'context':c,'passed':False,'error_type':'AttributeError'} for c,m,t in core.CAPACITY]
        self.assertEqual(driver.capacity_verdict(rows),(False,'CAPACITY_PARTIAL_ERROR',9))
        rows=[{'context':core.CONTEXT,'passed':False}]
        self.assertEqual(driver.capacity_verdict(rows),(False,'CAPACITY_MEASURED',8))
        rows=[{'context':core.CONTEXT,'passed':True},{'context':32768,'passed':False,'error_type':'GateNegative'}]
        self.assertEqual(driver.capacity_verdict(rows),(True,'CAPACITY_MEASURED',0))

if __name__=="__main__":unittest.main(verbosity=2)
