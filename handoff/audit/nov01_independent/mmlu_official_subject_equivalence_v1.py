"""허가된 공식 test/dev 원본만 취득해 all 재구성의 내용·순서 동등성을 검산한다."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
REVISION = 'c30699e8356da336a370243923dbaf21066bb9fe'
OUT = ROOT / 'data_cache/p106b_mmlu_official_subject_originals_v1_20261101'
PROOF = ROOT / 'test_result/evidence/p106b_mmlu_subject_originals_v1_20261101/report.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',',':'))


def normalize(rows, subject):
    result = []
    for row in rows:
        assert set(row) in ({'question','choices','answer'}, {'question','choices','answer','subject'})
        assert row.get('subject', subject) == subject
        assert type(row['answer']) is int and 0 <= row['answer'] < 4 and len(row['choices']) == 4
        result.append(dict(question=row['question'],choices=row['choices'],answer=row['answer'],subject=subject))
    return result


def main():
    import pyarrow.parquet as pq
    assert not OUT.exists() and not PROOF.exists()
    assert not OUT.parent.is_symlink()
    OUT.mkdir(parents=True)
    assets = json.loads((ROOT/'data_cache/p106b_mmlu_official_v1_20261101/assets.json').read_text())
    subjects = assets['subjects']
    assert len(subjects) == len(set(subjects)) == 57
    original_all, original_hashes = {}, {}
    for split in ('dev','test'):
        source = ROOT/'HF/datasets--cais--mmlu/snapshots'/REVISION/'all'/(split+'-00000-of-00001.parquet')
        raw = source.read_bytes()
        rows = pq.read_table(io.BytesIO(raw)).to_pylist()
        assert len(rows) == (285 if split == 'dev' else 14042)
        original_all[split] = {subject:normalize([r for r in rows if r['subject']==subject],subject) for subject in subjects}
        original_hashes[split] = dict(path=str(source.relative_to(ROOT)),sha256=digest(raw))
    def fetch(subject, split):
        relative = subject+'/'+split+'-00000-of-00001.parquet'
        url = 'https://huggingface.co/datasets/cais/mmlu/resolve/'+REVISION+'/'+relative
        started = time.monotonic()
        request = urllib.request.Request(url,headers={'User-Agent':'TinyLM-official-evaluation-audit/1.0'})
        with urllib.request.urlopen(request,timeout=30) as response:
            assert response.status == 200
            raw = response.read(1_000_001)
        assert 8 <= len(raw) <= 1_000_000 and raw[:4] == raw[-4:] == b'PAR1'
        path = OUT/relative
        path.parent.mkdir(exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        rows = normalize(pq.read_table(io.BytesIO(raw)).to_pylist(),subject)
        reference = original_all[split][subject]
        a,b = [canonical(r) for r in rows],[canonical(r) for r in reference]
        return dict(subject=subject,split=split,url=url,path=str(path.relative_to(ROOT)),
            sha256=digest(raw),bytes=len(raw),rows=len(rows),all_rows=len(reference),
            ordered_equal=a==b,multiset_equal=Counter(a)==Counter(b),
            original_order_sha256=digest(canonical(rows).encode()),all_order_sha256=digest(canonical(reference).encode()),
            seconds=time.monotonic()-started)
    records, errors = [], []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures={executor.submit(fetch,subject,split):(subject,split) for subject in subjects for split in ('dev','test')}
        for future in as_completed(futures):
            subject,split=futures[future]
            try:
                records.append(future.result())
            except Exception as exc:
                errors.append(dict(subject=subject,split=split,error_type=type(exc).__name__,message=str(exc)[:500]))
            if (len(records)+len(errors)) % 20 == 0:
                print(json.dumps(dict(completed=len(records),errors=len(errors))),flush=True)
    records.sort(key=lambda r:(r['subject'],r['split']))
    matches = len(records)==114 and not errors and all(r['ordered_equal'] for r in records)
    result=dict(schema='MMLU_OFFICIAL_SUBJECT_EQUIVALENCE_V1',
        status='ALL_57_SUBJECT_TEST_DEV_ORDER_EXACT' if matches else 'INCOMPLETE_OR_DIFFERENT',
        created_at=datetime.now(timezone.utc).isoformat(),revision=REVISION,authority_directives=[20,23,104],
        files=records,errors=errors,original_all=original_hashes,downloads=len(records),
        downloaded_bytes=sum(r['bytes'] for r in records),wall_seconds=time.monotonic()-started,
        evaluation_only=True,original_evaluation_inputs_changed=False,training=0,model_loads=0,
        source_sha256=digest(Path(__file__).read_bytes()))
    PROOF.parent.mkdir(parents=True,exist_ok=False)
    with PROOF.open('x') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
        stream.write(chr(10))
    assert PROOF.stat().st_size < 20_000_000
    print(json.dumps({k:result[k] for k in ('status','downloads','downloaded_bytes','wall_seconds','errors')}),flush=True)
    return 0 if matches else 8


if __name__ == '__main__':
    raise SystemExit(main())
