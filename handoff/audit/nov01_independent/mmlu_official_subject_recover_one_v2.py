"""v1의 113원본을 재취득하지 않고 크기 한도에 걸린 공식 원본 1개만 회수한다."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'test_result/evidence/p106b_mmlu_subject_originals_v1_20261101/report.json'
OUT = ROOT/'data_cache/p106b_mmlu_official_subject_originals_v2_20261101'
PROOF = ROOT/'test_result/evidence/p106b_mmlu_subject_originals_v2_20261101/report.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def main():
    import pyarrow.parquet as pq
    prior=json.loads(BASE.read_text())
    assert prior['errors']==[dict(subject='professional_law',split='test',error_type='AssertionError',message='')]
    assert len(prior['files'])==113 and all(r['ordered_equal'] and r['multiset_equal'] for r in prior['files'])
    for record in prior['files']:
        assert sha((ROOT/record['path']).read_bytes())==record['sha256']
    assert not OUT.exists() and not PROOF.exists()
    OUT.mkdir(parents=True)
    revision=prior['revision'];subject='professional_law';split='test'
    relative=subject+'/'+split+'-00000-of-00001.parquet'
    url='https://huggingface.co/datasets/cais/mmlu/resolve/'+revision+'/'+relative
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TinyLM-official-evaluation-audit/1.0'}),timeout=30) as response:
        assert response.status==200
        raw=response.read(4_000_001)
    assert 8<=len(raw)<=4_000_000 and raw[:4]==raw[-4:]==b'PAR1', '원본 크기/Parquet 한도'
    path=OUT/relative;path.parent.mkdir()
    with path.open('xb') as stream:stream.write(raw)
    records=pq.read_table(io.BytesIO(raw)).to_pylist()
    def normalize(rows):
        out=[]
        for row in rows:
            assert set(row) in ({'question','choices','answer'},{'question','choices','answer','subject'})
            assert row.get('subject',subject)==subject
            out.append(dict(question=row['question'],choices=row['choices'],answer=row['answer'],subject=subject))
        return out
    rows=normalize(records)
    all_source=ROOT/prior['original_all']['test']['path']
    assert sha(all_source.read_bytes())==prior['original_all']['test']['sha256']
    reference=normalize([r for r in pq.read_table(all_source).to_pylist() if r['subject']==subject])
    assert len(rows)==len(reference)==1534
    a,b=[canonical(r) for r in rows],[canonical(r) for r in reference]
    record=dict(subject=subject,split=split,url=url,path=str(path.relative_to(ROOT)),sha256=sha(raw),bytes=len(raw),
        rows=len(rows),all_rows=len(reference),ordered_equal=a==b,multiset_equal=Counter(a)==Counter(b),
        original_order_sha256=sha(canonical(rows).encode()),all_order_sha256=sha(canonical(reference).encode()))
    files=sorted(prior['files']+[record],key=lambda r:(r['subject'],r['split']))
    assert len(files)==114 and len({(r['subject'],r['split']) for r in files})==114
    assert all(r['ordered_equal'] and r['multiset_equal'] for r in files)
    result=dict(schema='MMLU_OFFICIAL_SUBJECT_EQUIVALENCE_V2',status='ALL_57_SUBJECT_TEST_DEV_ORDER_EXACT',
        created_at=datetime.now(timezone.utc).isoformat(),revision=revision,authority_directives=[20,23,104],
        previous_report_sha256=sha(BASE.read_bytes()),reused_files=113,new_files=1,
        accepted_original_files=114,accepted_original_bytes=sum(r['bytes'] for r in files),
        previous_failed_read='1MB safety cap retained; v2 allows4MB only for professional_law test; old failure preserved',
        dev_first_five_order_equal_subjects=57,test_order_equal_subjects=57,files=files,
        original_all=prior['original_all'],evaluation_inputs_changed=False,training=0,model_loads=0,
        source_sha256=sha(Path(__file__).read_bytes()),errors=[])
    PROOF.parent.mkdir(parents=True)
    with PROOF.open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    print(json.dumps({key:result[key] for key in ('status','accepted_original_files','accepted_original_bytes',
        'reused_files','new_files','dev_first_five_order_equal_subjects','test_order_equal_subjects')}),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
