"""Preserve exact executed P108 source bytes; never mutate a source/profile.

The pre-fix v1 bodies are reconstructed with the recorded narrow inverse patch
and MUST match their already sealed SHA. A guessed reconstruction is rejected.
"""
import hashlib
import json
from pathlib import Path

BASE=Path('handoff/audit/nov04_weight_space')
PROFILES=[Path('test_result/evidence')/tag/model/'profile.json' for tag,model in
    [('p108w_v1_20261104','new595-broad-q'),('p108w_v2_20261104','new595-broad-q'),
     ('p108w_v3_20261104','new595-broad-f')]]


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def earlier(name,data):
    text=data.decode('utf-8')
    if name=='scripts/p108_weight_space.py':
        old='''                if not bool(delta.ne(0).any()):
                    # Adding +0 can canonicalize ternary -0 bits. A no-op must
                    # preserve the exact original cache object and byte hash.
                    pass
                elif realization == 'latent':'''
        text=text.replace(old,"                if realization == 'latent':",1)
    elif name=='scripts/test_p108_weight_space.py':
        text=text.replace('''    with torch.no_grad():
        model.a.weight[1, 0] = -.1  # Quantizes to a genuine negative zero.
''','',1)
        text=text.replace("            delta = w.projection_delta(cache, torch.tensor([.6, .8]), [1], .5)",
                          "            delta = w.projection_delta(cache, torch.tensor([.6, .8]), [0], .5)",1)
        text=text.replace('                    cache_hash = w.tensor_sha(model.a._wq)'+chr(10),'',1)
        text=text.replace('                        self.assertEqual(w.tensor_sha(model.a._wq), cache_hash)'+chr(10),'',1)
    return text.encode('utf-8')


def main():
    collected={}
    manifests=[]
    for profile_path in PROFILES:
        raw=profile_path.read_bytes()
        profile=json.loads(raw)
        entries=[]
        for name,expected in profile['sources'].items():
            data=Path(name).read_bytes()
            mode='LIVE_EXACT'
            if sha(data)!=expected:
                data=earlier(name,data)
                mode='RECORDED_INVERSE_PATCH_SHA_VERIFIED'
            if sha(data)!=expected:
                raise ValueError('cannot reproduce sealed source: '+name)
            collected[expected]=data
            entries.append(dict(source=name,sha256=expected,bytes=len(data),mode=mode,
                                blob='source_blobs/'+expected+'.txt'))
        manifests.append(dict(profile=str(profile_path),profile_sha256=sha(raw),sources=entries))
    directory=BASE/'source_blobs'
    directory.mkdir(exist_ok=False)
    for digest,data in collected.items():
        with (directory/(digest+'.txt')).open('xb') as stream:
            stream.write(data)
    out=dict(schema='P108_SOURCE_ARCHIVE_V1',profiles=manifests,unique_blobs=len(collected),
             bytes=sum(map(len,collected.values())),original_source_writes=0,
             interpretation='EXACT_BYTES_SHA_VERIFIED_NOT_A_NEW_EXECUTABLE_ENVIRONMENT')
    with (BASE/'SOURCE_ARCHIVE_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(out,stream,ensure_ascii=False,indent=2)
        stream.write(chr(10))
    print(json.dumps(dict(blobs=out['unique_blobs'],bytes=out['bytes'],profiles=len(manifests))))


if __name__=='__main__':
    main()
