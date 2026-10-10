"""CPU responses/transport fixtures only; no Gemma session or dataset IO."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106d_teacher_views as views


def reply(case,count=2):
    text="\n".join(f"QUESTION_{i}:\n{case['question']}\nANSWER_{i}:\n5" for i in range(1,count+1))+"\nNOTE:\n"
    return {"choices":[{"finish_reason":"stop","message":{"content":text,"reasoning_content":"fixture sidecar"}}]}


class TeacherViewTests(unittest.TestCase):
    def test_one_and_two_pairs_and_reasoning_separation(self):
        case=views.cases()[0]
        for count in (1,2):
            got=views.parse(reply(case,count),count,case)
            self.assertEqual(got["status"],"QA_VIEWS_WIRE_COMPLETE")
            self.assertEqual(len(got["pairs"]),count)
            self.assertEqual(got["raw_thinking"],"fixture sidecar")
            self.assertEqual(got["semantic_truth"],"NOT_REVIEWED")

    def test_unique_answer_duplicates_not_rejected(self):
        case=views.cases()[0]; got=views.parse(reply(case),2,case)
        self.assertEqual(got["pairs"][0]["answer"],got["pairs"][1]["answer"])

    def test_wrong_label_order_missing_and_duplicate_rejected(self):
        case=views.cases()[0]
        for suffix in ("\nQUESTION_1:\nx","\nANSWER_3:\nx"):
            data=reply(case); data["choices"][0]["message"]["content"]+=suffix
            self.assertEqual(views.parse(data,2,case)["status"],"PARSE_ERROR")
        data=reply(case); data["choices"][0]["message"]["content"]=data["choices"][0]["message"]["content"].replace("QUESTION_2:","ANSWER_2:")
        self.assertEqual(views.parse(data,2,case)["status"],"PARSE_ERROR")

    def test_truncated_completion_not_rescued(self):
        case=views.cases()[0]; data=reply(case); data["choices"][0]["finish_reason"]="length"
        self.assertEqual(views.parse(data,2,case)["status"],"INCOMPLETE")

    def test_literal_question_transport_preserved(self):
        case=views.cases()[0]; data=reply(case)
        data["choices"][0]["message"]["content"]=data["choices"][0]["message"]["content"].replace(case["question"],"changed",1)
        self.assertEqual(views.parse(data,2,case)["reason"],"producer_fixed_question_literal_changed")

    def test_wrapper_keeps_source_anchor_and_no_thinking_target(self):
        case=views.cases()[0]; parsed=views.parse(reply(case),2,case)
        rows=[views.wrap(case,p,group_id="g",view_id=str(i),teacher_sha="A"*64) for i,p in enumerate(parsed["pairs"])]
        self.assertEqual(rows[0]["messages"][0],rows[1]["messages"][0])
        self.assertTrue(all(r["meta"]["semantic_truth"]=="NOT_REVIEWED" for r in rows))
        self.assertNotIn("fixture sidecar",str(rows))

    def test_card_controls_and_single_completion_not_api_n2(self):
        p=views.payload(views.cases()[0],2,1337)
        self.assertEqual((p["temperature"],p["top_p"],p["top_k"],p["min_p"]),(1.0,.95,64,0.0))
        self.assertNotIn("n",p); self.assertFalse(p["cache_prompt"])

    def test_observed_inline_labels_are_valid_fields(self):
        case=views.cases()[0]
        data=reply(case,1)
        data["choices"][0]["message"]["content"]=("QUESTION_1: "+case["question"]+"\nANSWER_1: 5\nNOTE: 2 + 3 = 5")
        got=views.parse(data,1,case)
        self.assertEqual(got["status"],"QA_VIEWS_WIRE_COMPLETE")
        self.assertEqual(got["pairs"],[{"question":case["question"],"answer":"5"}])

    def test_inline_and_multiline_fields_mix_without_changing_content(self):
        case=views.cases()[0]; data=reply(case)
        data["choices"][0]["message"]["content"]=("QUESTION_1: "+case["question"]+"\nANSWER_1:\n5\nQUESTION_2:\n동일한 덧셈의 결과는?\nANSWER_2: 5\nNOTE:")
        self.assertEqual(views.parse(data,2,case)["status"],"QA_VIEWS_WIRE_COMPLETE")

    def test_fenced_literal_labels_are_content_not_additional_fields(self):
        case=views.cases()[0]; data=reply(case,1)
        data["choices"][0]["message"]["content"]=("QUESTION_1: "+case["question"]+"\nANSWER_1: ```text\nQUESTION_2: literal\n```\nNOTE:")
        got=views.parse(data,1,case)
        self.assertEqual(got["status"],"QA_VIEWS_WIRE_COMPLETE")
        self.assertIn("QUESTION_2: literal",got["pairs"][0]["answer"])
        data["choices"][0]["message"]["content"]=data["choices"][0]["message"]["content"].replace("\n```\nNOTE:","\nNOTE:")
        self.assertEqual(views.parse(data,1,case)["status"],"PARSE_ERROR")

    def test_inline_duplicate_outside_preface_empty_answer_still_rejected(self):
        case=views.cases()[0]; good="QUESTION_1: "+case["question"]+"\nANSWER_1: 5\nNOTE:"
        for text in ("preface\n"+good,good+"\nANSWER_1: 6",good.replace("ANSWER_1: 5","ANSWER_1:"),good.replace("ANSWER_1: 5","OTHER: 5")):
            data=reply(case,1); data["choices"][0]["message"]["content"]=text
            self.assertEqual(views.parse(data,1,case)["status"],"PARSE_ERROR")

    def test_context_reaches_learner_and_paraphrase_retry_is_not_literal(self):
        case=views.cases()[3]; pair={"question":case["question"],"answer":"개수를 합하기 때문입니다."}
        row=views.wrap(case,pair,group_id="g",view_id="1",teacher_sha="A"*64)
        self.assertIn(case["context"],str(row["messages"]))
        instruction=views.feedback(case,1,view_number=2,reason="field_boundaries")
        self.assertIn("paraphrase",instruction)
        self.assertNotIn("copy QUESTION_1 exactly",instruction)


if __name__=="__main__": unittest.main(verbosity=2)
