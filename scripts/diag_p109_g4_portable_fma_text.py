"""Run the existing portable 32K G4 text path with hardware FMA and scalar INT8 lookup."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

import torch

from scripts import diag_p109_g4_portable_cpu as previous


base, text, codec = previous.base, previous.text, previous.codec
TAG = "p109_g4_portable_fma_text_v1_20261119"
OUT = previous.OUT.with_name(TAG)
LIMIT = 170
FLAGS = ("-mavx", "-mfma", "-mno-avx2", "-mno-f16c", "-fno-math-errno")
CODEGEN = previous.ROOT / "handoff/audit/research_20261118_01a1e647/P109_PORTABLE_FMA_CODEGEN_v1.json"


def build(directory):
    lookup, kernel, executable = (directory / name for name in ("lookup.o", "kernel.o", "g4_text"))
    cpp = (previous.ROOT / base.CPP).read_bytes()
    assert cpp.count(previous.tile.ORIGINAL) == 1
    source = cpp.replace(previous.tile.ORIGINAL, previous.tile.CHANGED, 1)
    commands = [
        (['/usr/bin/gcc', '-std=c11', '-O3', *previous.PORTABLE, '-c', base.C, '-o', str(lookup)], None),
        (['/usr/bin/g++', *previous.FLAGS, *FLAGS, '-Dmain=run_compact_g4', '-x', 'c++', '-c', '-', '-o', str(kernel)], source),
        (['/usr/bin/g++', *previous.FLAGS, *FLAGS, '-static', text.WRAPPER, str(kernel), str(lookup), '-o', str(executable)], None),
    ]
    for command, data in commands:
        subprocess.run(command, input=data, timeout=55, check=True, cwd=previous.ROOT)
    objdump = subprocess.check_output(['/usr/bin/objdump', '-d', str(kernel)], text=True, timeout=15)
    assert 'vfmadd' in objdump and 'vcvtph2ps' not in objdump and 'vcvtps2ph' not in objdump
    return executable, dict(commands=[cmd for cmd, _ in commands], sha256=base.SHA(executable),
                            source_bytes_sha256=sha256(source).hexdigest().upper(), fma=True)


@torch.inference_mode()
def main():
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    prior = base.READ(previous.OUT / 'profile.json')
    previous.verify(prior)
    codegen = base.READ(CODEGEN)
    for name in (base.C, base.CPP):
        path = Path(name)
        assert codegen['sources'][str(path)] == base.SHA(previous.ROOT / path), name
    plan = previous.PLAN.read_text(encoding='utf8').split('#### 4AK. ', 1)[1].split(chr(10) + '## 5.', 1)[0]
    assert TAG in plan
    OUT.mkdir()
    sealed_plan = OUT / 'plan_at_execution.md'
    sealed_plan.write_text('#### 4AK. ' + plan, encoding='utf8')
    archived = {language: previous.OUT / f'raw_{language}.json' for language in previous.CASES}
    pins = {str(path): base.SHA(path) for path in (Path(__file__), sealed_plan, CODEGEN, *archived.values())}
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    available = sorted(os.sched_getaffinity(0))
    assert len(available) >= 2 and min(available) >= 12
    cpus = dict(zip(archived, available[-2:], strict=True))
    payloads = codec.wire(json.loads(codec.TOK.read_bytes()))
    tok_ref = base.READ(codec.OUT / 'profile.json')
    assert [sha256(data).hexdigest().upper() for data in payloads] == [row['sha256'] for row in tok_ref['files']['split_model']]
    prompts = base.READ(codec.OUT / 'report.json')['runs']['split_model'][0]['outputs']
    with (TemporaryDirectory(prefix='p109_fma_text_') as temp, ExitStack() as stack,
          patch.multiple(previous, OUT=OUT, LIMIT=LIMIT)):
        previous.gate(LIMIT + 75)
        executable, binary = build(Path(temp))
        def fd(name):
            handle = base.memfile(name)
            stack.callback(os.close, handle)
            return handle
        model_fd, vocab, merges = (fd(name) for name in ('g4_fma_weights', 'g4_fma_vocab', 'g4_fma_merges'))
        model = base.prior.load_candidate(prior['candidate'])
        artifact = base.model_blob(model, model_fd, prior['candidate']['model_tensor_bytes'])
        del model
        assert artifact == prior['original_model']
        for handle, data in zip((vocab, merges), payloads, strict=True):
            text.store(handle, data)
            previous.edits.seal(handle)
        base.WRITE(OUT / 'profile.json', dict(tag=TAG, approval=177, binary=binary, pins=pins, cpus=cpus,
                                             original=artifact, request_deadline_seconds=LIMIT))
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(previous.full_request, str(executable), (model_fd, vocab, merges), lang,
                                prompts[lang]['decoded'].encode(), cpus[lang], base.READ(ref))
                    for lang, ref in archived.items()]
            results = [job.result() for job in jobs]
    previous.verify(prior)
    assert all(base.SHA(Path(path)) == sha for path, sha in pins.items()) and not torch.cuda.is_initialized()
    base.WRITE(OUT / 'report.json', dict(tag=TAG, artifact=artifact, cases=results, source_preserved=True,
                                        cuda_initialized=False, checkpoint_writes=0))
    print('P109_FMA_TEXT_COMPLETE', results, flush=True)


if __name__ == '__main__':
    main()
