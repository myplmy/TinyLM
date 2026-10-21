"""Synthetic user-menu/runtime contracts. Never load real checkpoints or GPU."""
from __future__ import annotations
import contextlib
import copy
import io
import importlib
import json
import os
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from scripts import interactive_infer as ui
from tinylm.infer import dialogue as d
from tinylm.infer.catalog import discover_models,resolve_selection
GENERATE=importlib.import_module("tinylm.infer.generate")


class FakeTokenizer:
    def get_vocab_size(self):return 32768
    def token_to_id(self,name):return {"<|im_start|>":3,"<|im_end|>":4}.get(name)
    def encode(self,text):return NS(ids=[ord(c)%8192+20 for c in text])
    def decode(self,ids,skip_special_tokens=True):return "answer" if ids in ([91,4],[91]) else "decoded"


def fixture_record(root,name="m100s10_ko-en_night_fixture",stamp=1):
    path=root/(name+".pt");path.write_bytes(b"not an actual checkpoint");os.utime(path,(stamp,stamp))
    return NS(checkpoint=path,stem=name,selector=name,data="ko-en",arch=None,
        display_val=None,log_path=None,modified_ns=path.stat().st_mtime_ns,pool_tokens=None)


class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="tinylm-dialogue-");self.root=Path(self.tmp.name)
        self.record=fixture_record(self.root);self.legacy=self.root/"tok-ko-en-32768.json"
        self.chat=self.root/"tok-ko-en-32768-chat32.json"
        self.legacy.write_text("legacy");self.chat.write_text("chat")
        self.meta=dict(cfg=dict(vocab_size=32768,tie_mlp=False),
            tokenizer_sha256=d.file_sha(self.chat),chat_family="chat32")
    def tearDown(self):self.tmp.cleanup()

    def test_saved_config_not_filename_owns_selected_architecture(self):
        value=d.selected_metadata(dict(cfg=dict(vocab_size=32768,tie_mlp=False),step=640,epoch=4))
        self.assertEqual(value["arch"],"dense");self.assertEqual(value["epoch"],4)
        for state in ({},dict(cfg={}),dict(cfg=dict(vocab_size=32768))):
            with self.assertRaises(ValueError):d.selected_metadata(state)

    def test_checkpoint_sha_finds_chat32_even_without_classic_log(self):
        route=d.resolve_tokenizer(self.record,self.meta,self.root)
        self.assertEqual(route.path,self.chat);self.assertTrue(route.verified)

    def test_sha_is_case_insensitive_and_explicit_wrong_file_never_falls_back(self):
        self.meta["tokenizer_sha256"]=self.meta["tokenizer_sha256"].lower()
        self.assertTrue(d.resolve_tokenizer(self.record,self.meta,self.root).verified)
        with self.assertRaises(ValueError):d.resolve_tokenizer(self.record,self.meta,self.root,self.legacy)

    def test_malformed_or_missing_saved_identity_refused(self):
        for identity in ("bad","A"*64,[],True):
            with self.assertRaises(ValueError):d.resolve_tokenizer(self.record,dict(self.meta,tokenizer_sha256=identity),self.root)

    def test_no_saved_sha_is_labelled_unverified(self):
        value=dict(self.meta,tokenizer_sha256=None,chat_family=None)
        route=d.resolve_tokenizer(self.record,value,self.root)
        self.assertEqual(route.path,self.legacy);self.assertFalse(route.verified)
        self.record.stem+="_chat32"
        with self.assertRaises(ValueError):d.resolve_tokenizer(self.record,value,self.root)
        self.assertFalse(d.resolve_tokenizer(self.record,value,self.root,self.chat).verified)

    def test_invalid_data_component_and_missing_local_file_refused(self):
        self.record.data="../elsewhere"
        with self.assertRaises(ValueError):d.resolve_tokenizer(self.record,self.meta,self.root)
        with self.assertRaises(ValueError):d.resolve_tokenizer(self.record,self.meta,self.root,self.root/"absent.json")

    def test_auto_mode_uses_actual_tokenizer_not_checkpoint_name(self):
        self.assertEqual(d.resolve_mode(FakeTokenizer(),self.meta["cfg"]),("chatml",[4]))
        self.assertEqual(d.resolve_mode(FakeTokenizer(),self.meta["cfg"],"plain"),("plain",[]))
        with self.assertRaises(ValueError):d.resolve_mode(FakeTokenizer(),dict(vocab_size=123))
        class NoMarkers(FakeTokenizer):
            def token_to_id(self,name):return None
        self.assertEqual(d.resolve_mode(NoMarkers(),self.meta["cfg"]),("plain",[]))
        with self.assertRaises(ValueError):d.resolve_mode(NoMarkers(),self.meta["cfg"],"chatml")

    def test_prompt_is_canonical_and_single_turn_unless_history_given(self):
        prompt=d.make_prompt("1+1은?","chatml")
        self.assertIn("<|im_start|>user\n1+1은?<|im_end|>",prompt)
        self.assertTrue(prompt.endswith("<|im_start|>assistant\n"))
        self.assertEqual(d.make_prompt("plain prefix","plain"),"plain prefix")

    def test_history_keeps_actual_answer_and_reset_can_be_empty(self):
        original=[];history=d.add_turn(original,"1+1은?","노무현")
        self.assertEqual(original,[]);before=copy.deepcopy(history)
        self.assertIn("노무현",d.make_prompt("다시 답해","chatml",history))
        self.assertEqual(before,history)
        with self.assertRaises(ValueError):d.make_prompt("x","plain",history)
        with self.assertRaises(ValueError):d.make_prompt(" ","chatml")

    def test_answer_extraction_uses_actual_ids_not_decoded_string_prefix(self):
        self.assertEqual(d.answer_from_ids(FakeTokenizer(),[7,8],[7,8,91,4],2),"answer")
        for ids,count in (([8,7,91,4],2),([7,8,91,4],1),(None,2)):
            with self.assertRaises(ValueError):d.answer_from_ids(FakeTokenizer(),[7,8],ids,count)


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="tinylm-menu-");self.root=Path(self.tmp.name)
        self.record=fixture_record(self.root)
    def tearDown(self):self.tmp.cleanup()

    def run_main(self,args,*,tty=False,inputs=()):
        out=io.StringIO();fake=dict(device="cpu",mode="chatml")
        with patch.object(ui,"discover_models",return_value=[self.record]),\
             patch.object(ui,"_load_runtime",return_value=fake) as load,\
             patch.object(ui,"_metadata"),patch.object(ui,"_emit",return_value=("노무현",dict(finish_reason="STOP_SEQUENCE",generated_tokens=3))) as emit,\
             patch("sys.stdin.isatty",return_value=tty),patch("builtins.input",side_effect=list(inputs)),\
             contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
            result=ui.main(args)
        return result,out.getvalue(),load,emit

    def test_list_does_not_load_any_checkpoint_and_shows_full_name(self):
        result,text,load,emit=self.run_main(["--list"])
        self.assertEqual(result,0);load.assert_not_called();emit.assert_not_called()
        self.assertIn(self.record.selector,text)

    def test_noninteractive_menu_fails_before_model_load(self):
        with patch.object(ui,"discover_models",return_value=[self.record]),patch.object(ui,"_load_runtime") as load,\
             patch("sys.stdin.isatty",return_value=False),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:ui.main([])
            self.assertEqual(raised.exception.code,2);load.assert_not_called()

    def test_explicit_noninteractive_prompt_preserves_wrong_answer_without_retry(self):
        result,text,load,emit=self.run_main(["--model","1","--prompt","1+1은?"])
        self.assertEqual(result,0);self.assertIn("노무현",text);self.assertIn("정답 판정이 아닙니다",text)
        self.assertEqual(emit.call_count,1);self.assertEqual(load.call_count,1)

    def test_same_model_stays_loaded_and_questions_independent_by_default(self):
        result,_,load,emit=self.run_main(["--model","1"],tty=True,inputs=["1+1은?","2+2는?",":q"])
        self.assertEqual(result,0);self.assertEqual(load.call_count,1);self.assertEqual(emit.call_count,2)
        self.assertEqual(emit.call_args_list[0].args[3],());self.assertEqual(emit.call_args_list[1].args[3],())

    def test_history_is_opt_in_and_reset_drops_old_turns(self):
        result,_,_,emit=self.run_main(["--model","1","--history"],tty=True,inputs=["first","second",":reset","third",":q"])
        self.assertEqual(result,0)
        self.assertEqual(len(emit.call_args_list[1].args[3]),2)
        self.assertEqual(emit.call_args_list[1].args[3][1]["content"][0]["text"],"노무현")
        self.assertEqual(emit.call_args_list[2].args[3],[])

    def test_recent_sort_is_not_validation_loss_sort(self):
        newer=fixture_record(self.root,"new",stamp=2)
        self.assertIs(ui._ordered([self.record,newer],"recent")[0],newer)
        self.assertIs(ui._ordered([newer,self.record],"name")[0],self.record)

    def test_cfg_and_tokenizer_checked_before_loading_selected_model(self):
        import torch
        cache=self.root/"cache";cache.mkdir();path=cache/"tok-ko-en-32768-chat32.json";path.write_text("fixture")
        metadata=dict(cfg=dict(vocab_size=32768,tie_mlp=False),tokenizer_sha256=d.file_sha(path),step=640,epoch=4)
        args=NS(tokenizer=None,mode="auto",precision="fp32-math",device="cpu",history=False)
        with patch.object(torch,"load",return_value=metadata),patch.object(ui.paths,"DATA_CACHE",cache),\
             patch("tokenizers.Tokenizer.from_file",return_value=FakeTokenizer()),\
             patch.object(GENERATE,"load_model",return_value=(object(),NS(vocab_size=32768),"cpu")) as load:
            result=ui._load_runtime(self.record,args)
            self.assertEqual(result["mode"],"chatml");self.assertTrue(result["route"].verified)
            self.assertEqual(load.call_args.args[0],"dense")

    def test_identity_failure_prevents_actual_model_loading(self):
        import torch
        metadata=dict(cfg=dict(vocab_size=32768,tie_mlp=False),tokenizer_sha256="A"*64)
        args=NS(tokenizer=None,mode="auto",precision="fp32-math",device="cpu",history=False)
        with patch.object(torch,"load",return_value=metadata),patch.object(ui.paths,"DATA_CACHE",self.root),\
             patch.object(GENERATE,"load_model") as load:
            with self.assertRaises(ValueError):ui._load_runtime(self.record,args)
            load.assert_not_called()

    def test_cli_tied_label_does_not_imply_mlp_tying(self):
        import torch
        cache=self.root/"cache";cache.mkdir();path=cache/"tok-ko-en-32768-chat32.json";path.write_text("fixture")
        metadata=dict(cfg=dict(vocab_size=32768,tie_mlp=False),tokenizer_sha256=d.file_sha(path))
        args=NS(tokenizer=None,mode="auto",precision="fp32-math",device="cpu",history=False)
        self.record.arch="tied"
        with patch.object(torch,"load",return_value=metadata),patch.object(ui.paths,"DATA_CACHE",cache),\
             patch("tokenizers.Tokenizer.from_file",return_value=FakeTokenizer()),\
             patch.object(GENERATE,"load_model",return_value=(object(),NS(vocab_size=32768),"cpu")) as load:
            runtime=ui._load_runtime(self.record,args)
            self.assertEqual(runtime["metadata"]["cfg"]["tie_mlp"],False)
            self.assertEqual(load.call_count,1)

    def test_emit_has_exact_stop_and_does_not_silently_truncate(self):
        args=NS(max_new=128,temperature=0.,top_k=1);tok=FakeTokenizer()
        runtime=dict(model=object(),cfg=NS(max_seq_len=1024),device="cpu",mode="chatml",tokenizer=tok,stop_ids=[4])
        def fake_sample(model,cfg,captured,prompt,**kwargs):
            ids=tok.encode(prompt).ids
            captured.decode(ids+[91,4])
            return "not a decoded prompt prefix",dict(generated_tokens=2,finish_reason="STOP_SEQUENCE")
        with patch.object(GENERATE,"sample",side_effect=fake_sample) as call:
            answer,meta=ui._emit(runtime,"question",args)
            self.assertEqual(answer,"answer");self.assertEqual(call.call_args.kwargs["stop_token_sequences"],[[4]])
            runtime["cfg"].max_seq_len=8
            with self.assertRaises(ValueError):ui._emit(runtime,"question",args)
            self.assertEqual(call.call_count,1)

    def test_chat32_val_does_not_guess_or_read_another_cache(self):
        runtime=dict(mode="chatml",route=NS(verified=True,path=Path("tok-ko-en-32768-chat32.json")))
        with patch("tinylm.infer.text_probe.select_cache") as select,contextlib.redirect_stdout(io.StringIO()):
            ui._validation_probe(self.record,runtime,None);select.assert_not_called()

    def test_real_discovery_supports_night_names_without_guessing_architecture(self):
        ckpt=self.root/"ckpt";logs=self.root/"logs";ckpt.mkdir();logs.mkdir()
        name="m100s10_ko-en_night_p106b_night_prompt_v1_s1337_prompt01"
        (ckpt/(name+".pt")).write_bytes(b"")
        (logs/(name+".json")).write_text("[]")
        rows=discover_models(ckpt,logs)
        self.assertEqual(rows[0].data,"ko-en");self.assertEqual(rows[0].tokens,"?")
        self.assertIsNone(rows[0].arch)
        self.assertIs(resolve_selection(rows,name+".pt"),rows[0])

    def test_malformed_numeric_log_does_not_break_the_whole_menu(self):
        ckpt=self.root/"ckpt";logs=self.root/"logs";ckpt.mkdir();logs.mkdir()
        stem="m100s10_ko-en_300M_bad"
        (ckpt/(stem+".pt")).write_bytes(b"")
        (logs/(stem+".json")).write_text(json.dumps(dict(steps=[],seed=True,pool_tokens="inf",final=[])))
        row=discover_models(ckpt,logs)[0]
        self.assertIsNone(row.steps);self.assertIsNone(row.pool_tokens);self.assertIsNone(row.seed)

    def test_legacy_cache_must_prove_same_tokenizer_before_memmap(self):
        import numpy as np
        cache=self.root/"cache";cache.mkdir();(cache/"meta.json").write_text(json.dumps(dict(tokenizer_sha256="B"*64)))
        runtime=dict(mode="plain",route=NS(verified=True,path=Path("legacy.json"),sha256="A"*64))
        with patch("tinylm.infer.text_probe.select_cache",return_value=cache),patch.object(np,"memmap") as memory,\
             contextlib.redirect_stdout(io.StringIO()):
            ui._validation_probe(self.record,runtime,None);memory.assert_not_called()


if __name__=="__main__":unittest.main()
