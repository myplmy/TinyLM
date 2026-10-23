"""합성 BabyLM 원함수/독립 oracle 회귀. 모델·평가 자료·GPU를 사용하지 않는다."""
from __future__ import annotations

import ast
from collections import defaultdict
import copy
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import p106b_babylm_causal as m

SOURCE = Path(__file__).resolve().parents[1] / "data_cache/p106b_official_eval_tools" / ("babylm_eval_"+m.COMMIT+"_minimal_blimp/source/strict/evaluation_pipeline/sentence_zero_shot")


class OfficialCausalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        cls.torch=torch

    def setUp(self):
        self.ns,self.proof=m.load_official(SOURCE,self.torch,device="cpu")
        self.args=SimpleNamespace(task="blimp",save_predictions=True,images_path=None)

    def item(self,values,uid="A",mask=None):
        torch=self.torch;processed={};sentences=[]
        for j,tokens in enumerate(values):
            name="sentence_"+str(j);sentences.append("candidate-"+str(j))
            processed[name+"_tokens"]=torch.tensor(tokens)
            processed[name+"_attn_mask"]=torch.ones(len(tokens),dtype=torch.long)
            processed[name+"_phrase_mask"]=torch.tensor(mask[j] if mask else [1]*len(tokens))
            processed[name+"_image"]=None
        raw=dict(sentences=sentences,completions=sentences)
        return raw,processed,0,dict(field="toy",UID=uid,linguistics_term="toy"),uid

    def test_import_does_not_import_torch_or_read_files(self):
        path=Path(m.__file__)
        spec=importlib.util.spec_from_file_location("pure_babylm_import",path)
        module=importlib.util.module_from_spec(spec)
        with patch.object(Path,"read_text",side_effect=AssertionError("실자료 읽기 금지")),patch.object(Path,"open",side_effect=AssertionError("자산 열기 금지")):
            spec.loader.exec_module(module)
        tree=ast.parse(path.read_text(encoding="utf-8"))
        top=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertFalse(any((getattr(n,"module","") or "").startswith("torch") for n in top))

    def test_original_hashes_and_ast_nodes_are_pinned(self):
        self.assertEqual(self.proof["commit"],m.COMMIT)
        self.assertFalse(self.proof["official_cli"])
        for name,receipt in self.proof["files"].items():
            self.assertEqual(m.file_sha(SOURCE/name),receipt["sha256"])
            tree=ast.parse((SOURCE/name).read_text())
            for node_name,value in receipt["nodes"].items():
                node=m.selected_node(tree,node_name)
                self.assertEqual(node.lineno,value["start_line"])
        self.assertEqual(self.ns["get_causal_collate_fn"](9).__closure__[0].cell_contents,9)

    def test_hash_mismatch_is_rejected_before_exec(self):
        with patch.object(Path,"read_bytes",return_value=b"wrong-source"),self.assertRaises(ValueError):
            m.load_official(SOURCE,self.torch)

    def test_decode_main_and_supplement(self):
        decode=self.ns["decode_blimp"]
        raw=dict(sentence_good="A is here.",sentence_bad="A are here.",field="syntax_semantics",UID="root",linguistics_term="agreement")
        value=decode(raw,Path("other.jsonl"))
        self.assertEqual(value["field"],"syntax/semantics")
        self.assertEqual(value["sentences"],[raw["sentence_good"],raw["sentence_bad"]])
        supplement=decode({k:v for k,v in raw.items() if k.startswith("sentence_")},Path("toy_suffix.jsonl"))
        self.assertEqual(supplement["UID"],"toy_suffix")
        self.assertEqual(supplement["label"],0)

    def test_official_shift_right_pad_and_candidate_width(self):
        batch=[self.item(([1,2,3],[1,2])),self.item(([1,4],[1,2,4,3])),self.item(([1,3,2],[1,2,3]))]
        _,values,labels,_,_,_=self.ns["get_causal_collate_fn"](0)(batch)
        self.assertEqual(values["sentence_0_inputs"].tolist(),[[1,2],[1,4],[1,3]])
        self.assertEqual(values["sentence_0_targets"].tolist(),[[2,3],[4,0],[3,2]])
        self.assertEqual(values["sentence_0_phrase_mask"].tolist(),[[1,1],[1,0],[1,1]])
        self.assertEqual(tuple(values["sentence_1_inputs"].shape),(3,3))
        self.assertEqual(labels,[0,0,0])

    def test_original_causal_logits_match_independent_lse_with_mask_hole(self):
        torch=self.torch
        batch=[self.item(([1,2,3,4],[1,3,2,4]),mask=([0,1,0,1],[0,1,1,0]))]
        collated=self.ns["get_causal_collate_fn"](0)(batch)
        logits=torch.tensor([[[0.,1.,2.,3.,4.],[4.,3.,2.,1.,0.],[0.,0.,0.,0.,0.]]])
        model=lambda **kw:dict(logits=logits)
        scores=[]
        original=self.ns["rank_and_evaluate"]
        def observe(*args):
            scores.extend([float(v[0]) for v in args[2][1.0]])
            return original(*args)
        self.ns["rank_and_evaluate"]=observe
        with torch.no_grad():self.ns["compute_causal_results"](self.args,model,[collated],[1.0])
        for j in range(2):
            values=collated[1]
            expected=m.scalar_oracle(logits[0].tolist(),values[f"sentence_{j}_targets"][0].tolist(),values[f"sentence_{j}_phrase_mask"][0].tolist())
            self.assertAlmostEqual(scores[j],expected,places=5)

    def test_rank_rng_counter_predictions_and_macro_not_micro(self):
        torch=self.torch;torch.manual_seed(1337)
        stats={1.0:{}};pred={1.0:defaultdict(list)}
        raw=[dict(sentences=["good","bad"],completions=["good","bad"])]*3
        metas=[dict(field="toy",UID=uid,linguistics_term="toy") for uid in ("A","A","B")]
        self.ns["update_subset_to_stats"](stats,metas)
        with m.RankAudit(self.ns,torch) as audit:
            self.ns["rank_and_evaluate"](self.args,stats,{1.0:[torch.tensor([-1.,-3.,-1.]),torch.tensor([-2.,-1.,-2.])]},raw,[0]*3,metas,["A","A","B"],pred)
        _,average=self.ns["process_results"](self.args,stats)
        value=audit.summary(average[1.0])
        self.assertEqual(value["uid_macro_percent"],75.)
        self.assertAlmostEqual(value["pair_micro_percent"],200/3)
        self.assertEqual(list(pred[1.0]),["A","B"])

    def test_exact_tie_replays_official_cpu_rng_and_restores_wrapper(self):
        torch=self.torch;torch.manual_seed(99)
        original=self.ns["rank_and_evaluate"]
        batches=[self.ns["get_causal_collate_fn"](0)([self.item(([1,2],[1,2]))])]
        model=lambda **kw:dict(logits=torch.zeros((1,1,5)))
        captured=[]
        with m.RankAudit(self.ns,torch,sink=captured.append) as audit,torch.no_grad():
            stats,_=self.ns["compute_causal_results"](self.args,model,batches,[1.0])
        self.assertIs(self.ns["rank_and_evaluate"],original)
        self.assertEqual(audit.ties,1)
        self.assertTrue(captured[0]["exact_tie"])
        self.assertIn(captured[0]["chosen"],(0,1))

    def test_nonfinite_score_is_error_not_silent_random(self):
        torch=self.torch
        stats={1.0:{}};meta=[dict(field="toy",UID="A",linguistics_term="toy")]
        self.ns["update_subset_to_stats"](stats,meta)
        with m.RankAudit(self.ns,torch),self.assertRaises(ValueError):
            self.ns["rank_and_evaluate"](self.args,stats,{1.0:[torch.tensor([float("nan")]),torch.tensor([-2.])]},[dict(sentences=["a","b"],completions=["a","b"])],[0],meta,["A"],{1.0:defaultdict(list)})

    def test_raw_bos_eos_offsets_and_mask_are_not_reencoded(self):
        calls=[]
        class Tokenizer:
            def encode(self,text,add_special_tokens):
                calls.append((text,add_special_tokens))
                return SimpleNamespace(ids=[9,1,2,8],offsets=[(0,0),(0,1),(1,len(text)),(0,0)],attention_mask=[1]*4,overflowing=[])
        processor=m.TextProcessor(Tokenizer(),native=True,vocab=10)
        item=m.processed_pair(self.ns,processor,dict(sentence_good="ab",sentence_bad="ac"),"toy.jsonl")
        self.assertEqual(len(calls),2)
        self.assertTrue(all(v[1] for v in calls))
        self.assertEqual(item[1]["sentence_0_phrase_mask"].tolist(),[0,1,1,0])

    def test_single_token_rejected_without_invented_bos(self):
        tokenizer=SimpleNamespace(encode=lambda *args,**kw:SimpleNamespace(ids=[1],offsets=[(0,1)],attention_mask=[1],overflowing=[]))
        with self.assertRaises(ValueError):m.TextProcessor(tokenizer,native=True,vocab=10)(text="a",return_offsets_mapping=True)

    def test_context_overflow_rejected_without_truncation(self):
        tokenizer=SimpleNamespace(encode=lambda *args,**kw:SimpleNamespace(ids=[1]*1026,offsets=[(0,1)]*1026,attention_mask=[1]*1026,overflowing=[]))
        with self.assertRaises(ValueError):m.TextProcessor(tokenizer,native=True,vocab=10)(text="a",return_offsets_mapping=True)

    def test_exact_1024_input_boundary_is_supported(self):
        tokenizer=SimpleNamespace(encode=lambda *args,**kw:SimpleNamespace(ids=[1]*1025,offsets=[(0,1)]*1025,attention_mask=[1]*1025,overflowing=[]))
        value=m.TextProcessor(tokenizer,native=True,vocab=10)(text="a",return_offsets_mapping=True)
        self.assertEqual(len(value["input_ids"])-1,1024)

    def test_all_wrong_uid_zero_counter_and_length_tie_disclosed(self):
        torch=self.torch
        raw=[dict(sentences=["good","poor"],completions=["good","poor"])]*3
        meta=[dict(field="toy",UID=uid,linguistics_term="toy") for uid in ("B","A","B")]
        stats={1.0:{}};pred={1.0:defaultdict(list)}
        self.ns["update_subset_to_stats"](stats,meta)
        with m.RankAudit(self.ns,torch) as audit:
            self.ns["rank_and_evaluate"](self.args,stats,{1.0:[torch.tensor([-2.,-2.,-2.]),torch.tensor([-1.,-1.,-1.])]},raw,[0]*3,meta,["B","A","B"],pred)
        _,average=self.ns["process_results"](self.args,stats)
        summary=audit.summary(average[1.0])
        self.assertEqual(summary["correct"],0)
        self.assertEqual(summary["equal_character_length_pairs"],3)
        self.assertEqual(summary["shortest_random_tie_expected_correct"],1.5)
        self.assertEqual(list(pred[1.0]),["B","A"])

    def test_sink_failure_restores_original_rank_and_rng_after_original(self):
        torch=self.torch;torch.manual_seed(222)
        original=self.ns["rank_and_evaluate"]
        collated=self.ns["get_causal_collate_fn"](0)([self.item(([1,2],[1,2]))])
        before=torch.get_rng_state().clone()
        torch.randint(2,(1,));expected=torch.get_rng_state().clone();torch.set_rng_state(before)
        def sink(event):raise RuntimeError("합성 저장 실패")
        with self.assertRaises(RuntimeError),m.RankAudit(self.ns,torch,sink=sink),torch.no_grad():
            self.ns["compute_causal_results"](self.args,lambda **kw:dict(logits=torch.zeros((1,1,5))),[collated],[1.0])
        self.assertIs(self.ns["rank_and_evaluate"],original)
        self.assertTrue(torch.equal(torch.get_rng_state(),expected))

    def test_native_existing_truncation_padding_overflow_and_actual_mask_rejected(self):
        for key,value in (("truncation",{}),("padding",{})):
            tokenizer=SimpleNamespace(**{key:value},encode=lambda *a,**k:(_ for _ in ()).throw(AssertionError("변경된 원 설정을 실행하면 안 됨")))
            with self.subTest(key=key),self.assertRaises(ValueError):m.TextProcessor(tokenizer,native=True,vocab=10)(text="ab",return_offsets_mapping=True)
        for mask,overflow in (([0,1],[]),([1,1],["tail"])):
            tokenizer=SimpleNamespace(encode=lambda *a,**k:SimpleNamespace(ids=[1,2],offsets=[(0,1),(1,2)],attention_mask=mask,overflowing=overflow))
            with self.subTest(mask=mask,overflow=overflow),self.assertRaises(ValueError):m.TextProcessor(tokenizer,native=True,vocab=10)(text="ab",return_offsets_mapping=True)

    def test_wrong_task_or_prediction_flag_rejected_before_original(self):
        torch=self.torch
        for changes in (dict(task="global_piqa_parallel"),dict(save_predictions=False),dict(images_path="images")):
            args=copy.copy(self.args)
            for key,value in changes.items():setattr(args,key,value)
            with m.RankAudit(self.ns,torch) as audit,patch.object(audit,"original",side_effect=AssertionError("원 rank 호출 금지")),self.assertRaises(ValueError):
                audit.call(args,{}, {},[],[],[],[],{})

    def test_extra_prediction_is_rejected_and_prior_prefix_is_rechecked_at_close(self):
        torch=self.torch;meta=[dict(field="toy",UID="A",linguistics_term="toy")]
        raw=[dict(sentences=["a","b"],completions=["a","b"])];stats={1.0:{}};pred={1.0:defaultdict(list)}
        self.ns["update_subset_to_stats"](stats,meta)
        with m.RankAudit(self.ns,torch) as audit:
            audit.call(self.args,stats,{1.0:[torch.tensor([-1.]),torch.tensor([-2.])]},raw,[0],meta,["A"],pred)
            pred[1.0]["A"][0]["pred"]="mutated"
            with self.assertRaises(ValueError):audit.summary(100.)
        stats={1.0:{}};pred={1.0:defaultdict(list)};self.ns["update_subset_to_stats"](stats,meta)
        original=self.ns["rank_and_evaluate"]
        def duplicate(*args):
            original(*args);args[-1][1.0]["A"].append(dict(id="A_1",pred="extra"))
        self.ns["rank_and_evaluate"]=duplicate
        with m.RankAudit(self.ns,torch) as audit,self.assertRaises(ValueError):
            audit.call(self.args,stats,{1.0:[torch.tensor([-1.]),torch.tensor([-2.])]},raw,[0],meta,["A"],pred)

    def test_observation_sink_preserves_original_text(self):
        torch=self.torch;events=[]
        item=self.item(([1,2],[1,3]))
        collate=self.ns["get_causal_collate_fn"](0)
        before=copy.deepcopy(item[0])
        with m.RankAudit(self.ns,torch,sink=events.append),torch.no_grad():
            self.ns["compute_causal_results"](self.args,lambda **kw:dict(logits=torch.zeros((1,1,5))),[collate([item])],[1.0])
        self.assertEqual(events[0]["raw_sentences"],before)
        self.assertEqual(item[0],before)


if __name__=="__main__":unittest.main()
