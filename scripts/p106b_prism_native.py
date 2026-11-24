"""Exact pinned Prism adfffbe C declarations; import never opens a library.

Primary ABI: PrismML-Eng/llama.cpp@adfffbe41b2cabcd51fff326ab045662265062bb,
include/llama.h blob deb1e12828c6cead2a6c7a1793f4c4396b5121d2.
The matching fork includes DSpark/load-mode/context fields absent from stock
bindings. No stock llama.cpp structure is substituted.
"""
from __future__ import annotations
import ctypes as C
from pathlib import Path
import numpy as np

COMMIT='adfffbe41b2cabcd51fff326ab045662265062bb'
HEADER_BLOB='deb1e12828c6cead2a6c7a1793f4c4396b5121d2'
class ModelParams(C.Structure):
    _fields_=[
        ('dspark_head_source',C.c_void_p),('devices',C.c_void_p),('tensor_buft_overrides',C.c_void_p),
        ('n_gpu_layers',C.c_int32),('split_mode',C.c_int),('load_mode',C.c_int),('main_gpu',C.c_int32),
        ('tensor_split',C.c_void_p),('progress_callback',C.c_void_p),('progress_callback_user_data',C.c_void_p),
        ('kv_overrides',C.c_void_p),('vocab_only',C.c_bool),('check_tensors',C.c_bool),
        ('use_extra_bufts',C.c_bool),('no_host',C.c_bool),('no_alloc',C.c_bool),('load_mtp',C.c_bool)]
class ContextParams(C.Structure):
    _fields_=[
        ('n_ctx',C.c_uint32),('n_batch',C.c_uint32),('n_ubatch',C.c_uint32),('n_seq_max',C.c_uint32),
        ('n_rs_seq',C.c_uint32),('n_outputs_max',C.c_uint32),('n_outputs_max_per_seq',C.c_uint32),
        ('n_threads',C.c_int32),('n_threads_batch',C.c_int32),('ctx_type',C.c_int),
        ('rope_scaling_type',C.c_int),('pooling_type',C.c_int),('attention_type',C.c_int),('flash_attn_type',C.c_int),
        ('rope_freq_base',C.c_float),('rope_freq_scale',C.c_float),('yarn_ext_factor',C.c_float),
        ('yarn_attn_factor',C.c_float),('yarn_beta_fast',C.c_float),('yarn_beta_slow',C.c_float),
        ('yarn_orig_ctx',C.c_uint32),('defrag_thold',C.c_float),('cb_eval',C.c_void_p),
        ('cb_eval_user_data',C.c_void_p),('type_k',C.c_int),('type_v',C.c_int),
        ('path_kv_mean_center',C.c_void_p),('abort_callback',C.c_void_p),('abort_callback_data',C.c_void_p),
        ('embeddings',C.c_bool),('offload_kqv',C.c_bool),('no_perf',C.c_bool),('op_offload',C.c_bool),
        ('swa_full',C.c_bool),('kv_unified',C.c_bool),('samplers',C.c_void_p),
        ('n_samplers',C.c_size_t),('ctx_other',C.c_void_p)]
class Batch(C.Structure):
    _fields_=[('n_tokens',C.c_int32),('token',C.POINTER(C.c_int32)),('embd',C.POINTER(C.c_float)),
        ('pos',C.POINTER(C.c_int32)),('n_seq_id',C.POINTER(C.c_int32)),
        ('seq_id',C.POINTER(C.POINTER(C.c_int32))),('logits',C.POINTER(C.c_int8))]

STRUCTS={'model':ModelParams,'context':ContextParams,'batch':Batch}

def layout():
    return {name:dict(size=C.sizeof(cls),alignment=C.alignment(cls),
        fields={field:getattr(cls,field).offset for field,_ in cls._fields_})for name,cls in STRUCTS.items()}

def bind(library):
    pointer=C.c_void_p;i32=C.c_int32;token_pointer=C.POINTER(i32)
    declarations={
        'llama_model_default_params':([],ModelParams),'llama_context_default_params':([],ContextParams),
        'llama_backend_init':([],None),'llama_backend_free':([],None),
        'llama_model_load_from_file':([C.c_char_p,ModelParams],pointer),
        'llama_model_free':([pointer],None),'llama_init_from_model':([pointer,ContextParams],pointer),
        'llama_free':([pointer],None),'llama_model_get_vocab':([pointer],pointer),
        'llama_vocab_n_tokens':([pointer],i32),'llama_get_memory':([pointer],pointer),
        'llama_memory_clear':([pointer,C.c_bool],None),'llama_synchronize':([pointer],None),
        'llama_n_ctx':([pointer],C.c_uint32),'llama_n_batch':([pointer],C.c_uint32),
        'llama_tokenize':([pointer,C.c_char_p,i32,token_pointer,i32,C.c_bool,C.c_bool],i32),
        'llama_token_to_piece':([pointer,i32,C.c_void_p,i32,i32,C.c_bool],i32),
        'llama_batch_get_one':([token_pointer,i32],Batch),'llama_decode':([pointer,Batch],i32),
        'llama_get_logits_ith':([pointer,i32],C.POINTER(C.c_float))}
    for name,(args,result)in declarations.items():
        function=getattr(library,name);function.argtypes=args;function.restype=result
    return library

def log_probabilities(logits):
    if not isinstance(logits,np.ndarray) or logits.dtype!=np.float32 or logits.ndim!=1 or not 2<=len(logits)<=300000:
        raise ValueError('complete bounded FP32 native logits required')
    if not np.isfinite(logits).all():raise ValueError('native logits must all be finite')
    values=logits.astype(np.float64);maximum=float(values.max())
    normalizer=maximum+float(np.log(np.exp(values-maximum).sum(dtype=np.float64)))
    return values-normalizer

class NativeModel:
    """Explicit existing-library/model context, no sampler or text template."""
    def __init__(self,bundle,model_path,*,vocab_size=248320,n_ctx=1024,check=None):
        self.bundle=Path(bundle);self.path=Path(model_path);self.expected_vocab=vocab_size
        self.context_limit=n_ctx;self.check=check or (lambda:None)
        self.api=self.ggml=None;self.model=self.context=self.vocab=None
        self.backend=False;self.clears=self.calls=self.processed_tokens=0
        self.model_load_attempted=False;self.backend_was_initialized=False

    def __enter__(self):
        self.check()
        self.ggml=C.CDLL(str(self.bundle/'libggml.so.0.21.0'),mode=C.RTLD_GLOBAL)
        self.ggml.ggml_backend_load_all_from_path.argtypes=[C.c_char_p]
        self.ggml.ggml_backend_load_all_from_path.restype=None
        self.api=bind(C.CDLL(str(self.bundle/'libllama.so.0.2.0'),mode=C.RTLD_GLOBAL))
        try:
            mp=self.api.llama_model_default_params();cp=self.api.llama_context_default_params()
            if (mp.dspark_head_source or mp.devices or mp.tensor_buft_overrides or mp.kv_overrides
                    or mp.vocab_only or mp.no_alloc or mp.load_mtp
                    or not -1<=mp.split_mode<=3 or not -1<=mp.load_mode<=4
                    or not 1<=cp.n_threads<=4096 or not 0<=cp.ctx_type<=1
                    or cp.ctx_other or cp.samplers or cp.n_samplers):
                raise ValueError('pinned binary default parameter fields differ')
            self.defaults=dict(model_layers=mp.n_gpu_layers,model_split=mp.split_mode,model_load_mode=mp.load_mode,
                n_ctx=cp.n_ctx,n_batch=cp.n_batch,n_ubatch=cp.n_ubatch,n_threads=cp.n_threads,
                context_type=cp.ctx_type,key_cache_type=cp.type_k,value_cache_type=cp.type_v)
            self.ggml.ggml_backend_load_all_from_path(str(self.bundle).encode())
            self.api.llama_backend_init();self.backend=True;self.backend_was_initialized=True
            mp.n_gpu_layers=-1;mp.split_mode=0;mp.load_mode=1;mp.main_gpu=0;mp.progress_callback=None
            mp.no_host=False;mp.no_alloc=False;mp.load_mtp=False;mp.check_tensors=True
            self.model_load_attempted=True
            self.model=self.api.llama_model_load_from_file(str(self.path).encode(),mp)
            if not self.model:raise ValueError('existing Prism model load returned NULL')
            self.vocab=self.api.llama_model_get_vocab(self.model)
            if not self.vocab:raise ValueError('native vocabulary returned NULL')
            self.vocab_size=int(self.api.llama_vocab_n_tokens(self.vocab))
            if self.vocab_size!=self.expected_vocab:raise ValueError('exact native vocabulary differs')
            cp.n_ctx=self.context_limit;cp.n_batch=512;cp.n_ubatch=512;cp.n_seq_max=1;cp.n_rs_seq=0
            cp.n_threads=4;cp.n_threads_batch=4;cp.ctx_type=0;cp.flash_attn_type=0
            cp.path_kv_mean_center=None;cp.cb_eval=None;cp.cb_eval_user_data=None
            cp.abort_callback=None;cp.abort_callback_data=None;cp.embeddings=False
            cp.offload_kqv=True;cp.op_offload=True;cp.no_perf=True;cp.samplers=None;cp.n_samplers=0;cp.ctx_other=None
            self.context=self.api.llama_init_from_model(self.model,cp)
            if not self.context:raise ValueError('existing Prism context returned NULL')
            if int(self.api.llama_n_ctx(self.context))!=self.context_limit:
                raise ValueError('native context length differs')
            self.batch_limit=int(self.api.llama_n_batch(self.context))
            if not 1<=self.batch_limit<=512:raise ValueError('native batch cap differs')
            return self
        except BaseException:
            self.close();raise

    def tokenize(self,text,*,add_special):
        if not isinstance(text,str) or not text or type(add_special)is not bool:
            raise ValueError('nonempty text and explicit native special policy required')
        raw=text.encode('utf-8')
        if len(raw)>1_000_000:raise ValueError('native text cap')
        capacity=min(max(len(raw)*2+16,32),4096)
        tokens=(C.c_int32*capacity)()
        n=int(self.api.llama_tokenize(self.vocab,raw,len(raw),tokens,capacity,add_special,True))
        if n<0 or not 1<=n<=capacity:raise ValueError('native tokenization failed or overflowed')
        result=[int(tokens[i])for i in range(n)]
        if any(not 0<=i<self.vocab_size for i in result):raise ValueError('native token ID outside vocabulary')
        return result

    def piece(self,token):
        if type(token)is not int or not 0<=token<self.vocab_size:raise ValueError('native piece ID invalid')
        buffer=C.create_string_buffer(8192)
        n=int(self.api.llama_token_to_piece(self.vocab,token,buffer,len(buffer),0,True))
        if n<0 or n>len(buffer):raise ValueError('native piece byte cap')
        return bytes(buffer.raw[:n])

    def logits(self,ids):
        ids=list(ids)
        if not 1<=len(ids)<=self.context_limit or any(type(i)is not int or not 0<=i<self.vocab_size for i in ids):
            raise ValueError('full untruncated bounded native IDs required')
        self.check();memory=self.api.llama_get_memory(self.context)
        if not memory:raise ValueError('native memory handle required for isolation')
        self.api.llama_memory_clear(memory,True);self.api.llama_synchronize(self.context);self.clears+=1
        for begin in range(0,len(ids),self.batch_limit):
            self.check();part=ids[begin:begin+self.batch_limit];tokens=(C.c_int32*len(part))(*part)
            batch=self.api.llama_batch_get_one(tokens,len(part))
            code=int(self.api.llama_decode(self.context,batch))
            if code!=0:raise ValueError('full native decode failed: '+str(code))
            self.api.llama_synchronize(self.context)
        pointer=self.api.llama_get_logits_ith(self.context,-1)
        if not pointer:raise ValueError('last raw logits returned NULL')
        result=np.ctypeslib.as_array(pointer,shape=(self.vocab_size,)).copy()
        if result.dtype!=np.float32 or not np.isfinite(result).all():raise ValueError('complete finite native logits required')
        self.calls+=1;self.processed_tokens+=len(ids)
        return result

    def close(self):
        if self.api is not None:
            if self.context:self.api.llama_free(self.context);self.context=None
            if self.model:self.api.llama_model_free(self.model);self.model=None
            if self.backend:self.api.llama_backend_free();self.backend=False
        self.vocab=None

    def __exit__(self,*args):
        self.close()

