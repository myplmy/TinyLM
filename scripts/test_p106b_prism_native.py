"""C-compiler ABI layout and model-free raw-logit interface contracts."""
from __future__ import annotations
import ctypes as C,math,os,subprocess,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from scripts import p106b_prism_native as native

class PrismNativeContracts(unittest.TestCase):
    def test_every_ctypes_field_matches_compiled_pinned_C_declarations(self):
        path=Path(os.environ['PRISM_ABI_PROBE'])
        result=subprocess.run([str(path)],capture_output=True,text=True,check=True,timeout=5)
        parsed={}
        for line in result.stdout.splitlines():
            parts=line.split()
            if parts[0]=='STRUCT':parsed[parts[1]]=dict(size=int(parts[2]),alignment=int(parts[3]),fields={})
            elif parts[0]=='FIELD':parsed[parts[1]]['fields'][parts[2]]=int(parts[3])
            else:raise ValueError('unexpected ABI probe output')
        self.assertEqual(parsed,native.layout())
        self.assertEqual({k:v['size']for k,v in parsed.items()},{'model':80,'context':168,'batch':56})

    def test_bind_uses_fork_struct_returns_and_exact_native_pointer_types(self):
        library=native.bind(Mock())
        self.assertIs(library.llama_model_default_params.restype,native.ModelParams)
        self.assertIs(library.llama_context_default_params.restype,native.ContextParams)
        self.assertEqual(library.llama_model_load_from_file.argtypes,[C.c_char_p,native.ModelParams])
        self.assertEqual(library.llama_init_from_model.argtypes,[C.c_void_p,native.ContextParams])
        self.assertEqual(library.llama_memory_clear.argtypes,[C.c_void_p,C.c_bool])
        self.assertEqual(library.llama_decode.argtypes,[C.c_void_p,native.Batch])

    def test_raw_fp32_normalizer_matches_independent_scalar_fsum(self):
        logits=np.array([-100.,-.3,0.,15.,-300.],dtype=np.float32)
        actual=native.log_probabilities(logits)
        maximum=max(float(x)for x in logits)
        z=maximum+math.log(math.fsum(math.exp(float(x)-maximum)for x in logits))
        expected=np.array([float(x)-z for x in logits],dtype=np.float64)
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-12)
        self.assertAlmostEqual(math.fsum(math.exp(float(x))for x in actual),1.,places=13)

    def test_invalid_partial_dtype_and_nonfinite_logits_are_rejected(self):
        for values in (np.array([1.],dtype=np.float32),np.ones(2,dtype=np.float64),
                np.array([0.,np.nan],dtype=np.float32),np.array([0.,np.inf],dtype=np.float32),
                np.ones((2,2),dtype=np.float32)):
            with self.assertRaises(ValueError):native.log_probabilities(values)

    def test_tokenizer_receives_exact_utf8_bytes_and_native_special_policy(self):
        observed=[]
        def tokenizer(vocab,text,length,output,capacity,add_special,parse_special):
            observed.append((text,length,add_special,parse_special))
            output[0]=3;output[1]=7;return 2
        model=native.NativeModel('/not-opened','/not-opened')
        model.vocab=1;model.vocab_size=10
        model.api=SimpleNamespace(llama_tokenize=tokenizer)
        for special in (False,True):self.assertEqual(model.tokenize('수도 Paris',add_special=special),[3,7])
        self.assertEqual(observed,[(b'\xec\x88\x98\xeb\x8f\x84 Paris',12,False,True),
            (b'\xec\x88\x98\xeb\x8f\x84 Paris',12,True,True)])

    def test_full_prompt_clear_true_chunk_order_and_logits_ownership(self):
        api=Mock();events=[];rows=(C.c_float*4)(1.,2.,3.,4.)
        api.llama_get_memory.return_value=8
        api.llama_memory_clear.side_effect=lambda memory,data:events.append(('clear',memory,data))
        def batch(tokens,count):
            value=native.Batch();value.n_tokens=count;value.token=tokens;return value
        def decode(context,value):
            events.append(('ids',[int(value.token[i])for i in range(value.n_tokens)]));return 0
        api.llama_batch_get_one.side_effect=batch;api.llama_decode.side_effect=decode
        api.llama_get_logits_ith.return_value=C.cast(rows,C.POINTER(C.c_float))
        model=native.NativeModel('/not-opened','/not-opened',n_ctx=8)
        model.api=api;model.context=7;model.vocab_size=4;model.batch_limit=2
        result=model.logits([0,1,2])
        self.assertEqual(events,[('clear',8,True),('ids',[0,1]),('ids',[2])])
        rows[0]=99.
        self.assertEqual(result.tolist(),[1.,2.,3.,4.])
        self.assertEqual((model.calls,model.clears,model.processed_tokens),(1,1,3))
        with self.assertRaises(ValueError):model.logits([True])
        with self.assertRaises(ValueError):model.logits([0]*9)

    def test_constructor_never_opens_library_and_close_releases_owned_handles(self):
        with patch.object(C,'CDLL',side_effect=AssertionError('unexpected library open')):
            model=native.NativeModel('/not-opened','/not-opened')
        self.assertFalse(model.model_load_attempted);self.assertFalse(model.backend_was_initialized)
        api=Mock();model.api=api;model.context=1;model.model=2;model.vocab=3;model.backend=True
        model.close()
        api.llama_free.assert_called_once_with(1)
        api.llama_model_free.assert_called_once_with(2)
        api.llama_backend_free.assert_called_once_with()
        self.assertIsNone(model.context);self.assertIsNone(model.model);self.assertFalse(model.backend)

    def test_null_model_tracks_attempt_and_releases_initialized_backend(self):
        api=Mock();ggml=Mock();mp=native.ModelParams();cp=native.ContextParams();cp.n_threads=4
        api.llama_model_default_params.return_value=mp;api.llama_context_default_params.return_value=cp
        api.llama_model_load_from_file.return_value=None
        model=native.NativeModel('/not-opened','/not-opened')
        with patch.object(C,'CDLL',side_effect=[ggml,api]):
            with self.assertRaisesRegex(ValueError,'model load returned NULL'):model.__enter__()
        self.assertTrue(model.model_load_attempted);self.assertTrue(model.backend_was_initialized)
        self.assertFalse(model.backend);self.assertIsNone(model.model)
        api.llama_backend_free.assert_called_once_with()

if __name__=='__main__':unittest.main()

