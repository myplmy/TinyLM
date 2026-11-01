"""Bounded CPU profiling of the unchanged full-root verifier; fresh output only."""
from datetime import datetime,timezone
import faulthandler
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).parent
os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
    OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',
    HF_DATASETS_OFFLINE='1',TRANSFORMERS_OFFLINE='1',USE_HUB_KERNELS='0')

def main():
    stack=AUDIT/'GSM8K_ROOT_LATENCY_STACK_v2.log'
    report_path=AUDIT/'GSM8K_ROOT_LATENCY_PROBE_v2.json'
    assert not stack.exists() and not report_path.exists()
    started=time.monotonic();observed={};code=9
    def timeout(*_):raise TimeoutError('90-second CPU diagnosis limit')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(90)
    with stack.open('x') as trace:
        faulthandler.dump_traceback_later(20,repeat=True,file=trace)
        try:
            print('IMPORT_START',flush=True)
            source=AUDIT/'gsm8k_root_readback_v1.py'
            spec=importlib.util.spec_from_file_location('profiled_completed_gsm8k',source)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            print('IMPORT_FINISHED',time.monotonic()-started,flush=True)
            module.READBACK=module.driver.OUTPUT/'readback_latency_v2'
            module.READBACK.mkdir(exist_ok=False)
            tok=module.manual.local_tokenizer(module.manual.verify_manifest())
            tick=time.perf_counter()
            for _ in range(100):assert tok.get_vocab_size()==32768
            elapsed=time.perf_counter()-tick
            observed['get_vocab_size_100_calls_seconds']=elapsed
            observed['extrapolation_for337664_calls_seconds']=elapsed/100*337664
            print(json.dumps(observed),flush=True)
            def instrument(obj,name,label):
                original=getattr(obj,name)
                def timed(*args,**kwargs):
                    tick=time.monotonic();print('ENTER',label,flush=True)
                    try:return original(*args,**kwargs)
                    finally:print('LEAVE',label,time.monotonic()-tick,flush=True)
                setattr(obj,name,timed)
            for obj,name,label in [
                (module.driver,'identity','SOURCE_HASH'),
                (module.data,'load_task','OFFICIAL_TASK'),
                (module.manual,'verify_manifest','MODEL_METADATA'),
                (module.manual,'local_tokenizer','TOKENIZER'),
                (module,'shards','SHARDS')]:
                instrument(obj,name,label)
            print('FULL_ROOT_START',flush=True)
            module.one('native')
            code=0
        except TimeoutError as exc:
            observed.update(error_type=type(exc).__name__,error=str(exc));code=8
        except Exception as exc:
            observed.update(error_type=type(exc).__name__,error=str(exc));code=9
        finally:
            faulthandler.cancel_dump_traceback_later();signal.alarm(0)
    observed.update(actual_exit=code,seconds=time.monotonic()-started,
        original_verifier_source_sha256=hashlib.sha256((AUDIT/'gsm8k_root_readback_v1.py').read_bytes()).hexdigest().upper(),
        local_timing_proxies_only=True,only_output_namespace_changed=True,
        model_runs=0,gpu_runs=0,original_gpu_report_or_scores_modified=False,
        created_at=datetime.now(timezone.utc).isoformat())
    with report_path.open('x') as stream:json.dump(observed,stream,indent=2)
    print(json.dumps(observed),flush=True)
    return code

if __name__=='__main__':raise SystemExit(main())
