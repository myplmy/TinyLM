"""Original reading AST, native token traces and scalar-only cache contracts."""
import sys,math,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
import torch
from scripts import p106b_babylm_reading as core

class ToyTokenizer:
    chars={'x':1,'y':2,'a':3,'b':4,' ':5,'c':6,'z':7}
    def encode(self,text,*,add_special_tokens):
        return SimpleNamespace(ids=([0]if add_special_tokens else[])+[self.chars[c]for c in text])
    def decode(self,ids,*,skip_special_tokens):
        return ''.join(next(c for c,n in self.chars.items()if n==i)for i in ids)

class ToyBase:
    def __init__(self):self.calls=0;self.inputs=[]
    def __call__(self,**inputs):
        ids=inputs['input_ids'];self.calls+=1;self.inputs.append(ids[0].tolist())
        values=((torch.arange(8)+int(ids.sum()))%7).float()*.13
        return {'logits':values.reshape(1,1,8).expand(1,ids.shape[1],8)}

class ReadingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.official,cls.proof=core.load_official(torch,device='cpu')
        if torch.cuda.is_initialized():raise ValueError('CPU contracts CUDA forbidden')
    def objects(self):
        base=ToyBase();forward=core.ReadingForward(base)
        tokenizer=core.TokenizerBridge(ToyTokenizer(),torch,native=True,vocab=8)
        return base,forward,tokenizer
    def test_single_and_multi_target_original_probabilities_match_independent_CE(self):
        for word in ('a','ab'):
            base,forward,tokenizer=self.objects();forward.capture=True
            result=core.evaluate(self.official,forward,tokenizer,'xy',word)
            oracle=core.CE_oracle(result,forward,torch)
            self.assertTrue(oracle['passed'])
            self.assertEqual(len(result['trace']),len(word));self.assertEqual(result['multi'],int(len(word)>1))
            expected_ids=[[0,1,2],[0,1,2,3]][:len(word)]
            self.assertEqual(base.inputs,expected_ids)
            self.assertEqual([r['target_id']for r in result['trace']],[3,4][:len(word)])
    def test_full_target_encoding_and_native_attention_mask_are_retained(self):
        base,forward,tokenizer=self.objects()
        result=core.evaluate(self.official,forward,tokenizer,'xy','ab')
        self.assertEqual(result['trace'][0]['target_ids'],[3,4])
        self.assertEqual(result['trace'][1]['target_ids'],[4])
        self.assertEqual(result['native_positions'],3+4)
        batch=tokenizer('xy',return_tensors='pt').to('cpu')
        self.assertTrue(torch.equal(batch['attention_mask'],torch.ones((1,3),dtype=torch.long)))
    def test_cache_cannot_cross_models_or_mutate_the_stored_trace(self):
        base,forward,tokenizer=self.objects();cache=core.ExactPairCache('model-a')
        calculate=lambda:core.evaluate(self.official,forward,tokenizer,'xy','ab')
        first,hit=cache.get('model-a','xy','ab',calculate);self.assertFalse(hit)
        first['trace'][0]['prefix_ids'][0]=99
        again,hit=cache.get('model-a','xy','ab',calculate);self.assertTrue(hit)
        self.assertEqual(again['trace'][0]['prefix_ids'],[0,1,2])
        self.assertEqual(base.calls,2);self.assertEqual((cache.hits,cache.misses),(1,1))
        with self.assertRaises(ValueError):cache.get('model-b','xy','ab',calculate)
    def test_context_limit_and_native_ID_range_never_crop_or_alias(self):
        tok=core.TokenizerBridge(ToyTokenizer(),torch,native=True,vocab=8,limit=2)
        with self.assertRaises(core.ReadingHold):tok('xy',return_tensors='pt')
        tok=core.TokenizerBridge(ToyTokenizer(),torch,native=True,vocab=3)
        with self.assertRaises(core.ReadingHold):tok('a',add_special_tokens=False)
    def test_single_piece_replacement_is_loud_hold(self):
        base,forward,tokenizer=self.objects()
        with patch.object(tokenizer.tokenizer,'decode',return_value='\ufffd'):
            with self.assertRaisesRegex(core.ReadingHold,'replacement'):
                core.evaluate(self.official,forward,tokenizer,'xy','ab')
    def test_original_zero_probability_is_not_floored_or_removed(self):
        base,forward,tokenizer=self.objects()
        def underflow(**inputs):
            values=torch.zeros((1,inputs['input_ids'].shape[1],8));values[:,:,3]=-1000
            return {'logits':values}
        forward.base=underflow
        with self.assertRaisesRegex(core.ReadingHold,'underflow'):
            core.evaluate(self.official,forward,tokenizer,'xy','a')
    def test_source_drift_refuses_loading_the_original_nodes(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);path=root/'source/strict/evaluation_pipeline/reading/evaluation_functions.py'
            path.parent.mkdir(parents=True);path.write_text('def get_p(): return 0\n')
            with patch.object(core,'ARCHIVE',root):
                with self.assertRaisesRegex(ValueError,'blob differs'):core.load_official(torch,device='cpu')
    def test_original_full_data_and_original_AST_boundaries(self):
        rows=core.rows()
        self.assertEqual(len(rows),1726);self.assertEqual([r['index']for r in rows],list(range(1726)))
        self.assertGreater(sum(r['previous']is not None for r in rows),0)
        self.assertEqual(set(self.proof['functions']['reading']),{'get_p','get_p2'})
        self.assertFalse(self.proof['source_imported_as_package'])
        self.assertFalse(self.proof['original_model_loader_executed'])

if __name__=='__main__':unittest.main()

