"""Exact seven historical checkpoint headers and byte hashes; no forward."""
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import time
os.environ['CUDA_VISIBLE_DEVICES']=''
import torch

ROOT=Path(__file__).resolve().parents[3]
TARGETS=('mC_wsd','mC_g16','mC_d36','mC_r20','mC_r20_nokd','mC_r30_nokd','mC_r20in_nokd')
OUT=ROOT/'handoff/audit/oct27_independent/recurrent_checkpoint_headers_v1.json'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest().upper()

def main():
    assert not OUT.exists()
    began=time.monotonic();rows=[]
    for tag in TARGETS:
        matches=list((ROOT/'runs/logs').glob('*_'+tag+'.json'));assert len(matches)==1
        log=matches[0];checkpoint=ROOT/'runs/ckpt'/(log.stem+'.pt');assert checkpoint.is_file() and not checkpoint.is_symlink()
        before=checkpoint.stat();sha=digest(checkpoint)
        with checkpoint.open('rb') as stream:payload=torch.load(stream,map_location='meta',weights_only=True)
        assert isinstance(payload,dict) and isinstance(payload['cfg'],dict) and isinstance(payload['model'],dict)
        assert all(v.device.type=='meta' for v in payload['model'].values() if isinstance(v,torch.Tensor))
        cfg=payload['cfg'];after=checkpoint.stat()
        assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
        rows.append(dict(tag=tag,checkpoint=str(checkpoint.relative_to(ROOT)),checkpoint_sha256=sha,bytes=after.st_size,
            log=str(log.relative_to(ROOT)),log_sha256=digest(log),step=payload.get('step'),cfg=cfg,
            serialized_model_tensor_reference_dtypes=dict(Counter(str(v.dtype) for v in payload['model'].values() if isinstance(v,torch.Tensor))),
            optimizer_top_keys=list(payload.get('opt',{})) if isinstance(payload.get('opt'),dict) else 'UNKNOWN',
            physical_layers=cfg['n_prelude']+cfg['n_middle']+cfg['n_coda'],
            unique_middle_MLPs=cfg['n_middle']//cfg['mlp_group'],
            tensor_allocation_device='META_ONLY_NOT_RUNTIME_STORAGE',historical_code_commit='NOT_IN_HEADER',
            tokenizer_file_sha256='NOT_IN_HEADER'))
        del payload
        print(json.dumps(dict(tag=tag,checkpoint_bytes=after.st_size,sha256=sha)),flush=True)
    assert not torch.cuda.is_initialized()
    OUT.write_text(json.dumps(dict(started_scope='SEVEN_EXACT_OLD_CPS; FULL_BYTE_HASH_PLUS_WEIGHTS_ONLY_META_HEADERS',
        generated_at=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-began,rows=rows,
        model_instantiations=0,forward_calls=0,training_updates=0,checkpoint_writes=0,cuda_initialized=False),ensure_ascii=False,indent=2)+chr(10))
    return 0

if __name__=='__main__':raise SystemExit(main())
