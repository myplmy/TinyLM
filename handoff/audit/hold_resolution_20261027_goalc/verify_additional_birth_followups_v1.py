"""Check five author-written followups with frozen verification primitives."""
from pathlib import Path
import ast
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
frozen=AUDIT/'verify_current_birth_followups_v1.py'
tree=ast.parse(frozen.read_text(encoding='utf-8'))
names={'sha','read','pin','verify','replace_once'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert len(nodes)==len(names) and all(not n.decorator_list and not n.args.defaults for n in nodes)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(frozen),'exec'),globals())

manifest_path=BASE/'birth_root11_independent_v1/manifest.json'
snapshot_path=BASE/'birth_root11_independent_v1_snapshots/v17/complete.json'
contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
manifest={r['id']:r for r in read(manifest_path)['rows']}
contract=read(contract_path)
snapshot=read(snapshot_path)
assert not snapshot['errors'] and not snapshot['needs_root']
records={}
for shard in snapshot['shards']:
    payload=(ROOT/shard['path']).read_bytes()
    assert sha(payload)==shard['sha256']
    records.update({r['id']:r for r in json.loads(payload)})
specs={
 'expanded_train:151767':[
  ('이윤재(李允宰, 12월 25일~12월 8일)','이윤재(李允宰, 12월 25일생)'),
  ('숭덕학교 교원시절에','숭덕학교 교원 시절에'),
  ('1년 6개월간 수감생활을국했다. 대학 사학과를 1년 수료 33년·술·학리교 신해다 등에서',
   '1년 6개월간 수감 생활을 했다.'),
  ('12월 8일순국하였다.','12월 8일 순국하였다.'),
  ('특히 경신학교 교원 시절인 1933년과 1934년 사이에 제자들에게 다음과 같은 말을 주저 없이 하였다고 전해온다.',''),
  ('그러면서 그는 조선어','그는 조선어')],
 'expanded_train:175714':[
  ('본명은 미쓰시게이다.',"본명은 미쓰시게이다. 둘째 아들인 시게마사(誠政)는 쇼군 도쿠가와 이에미쓰의 '光'자를 피휘한 것으로 여겨지고 있다.")],
 'expanded_train:240050':[
  ('풍천인 임대원(任大原)의 딸.','풍천인 임대원(任大原)의 딸).')],
 'expanded_train:246989':[
  ('|즉위식=가경(嘉慶) 원년 1월 1일(1796년 2월 9일)','|즉위식=가경(嘉慶) 원년 1월 1일'),
  ('愛新覺羅顒琰, )','愛新覺羅顒琰)'),('仁宗, )','仁宗)'),
  ('睿皇帝, )','睿皇帝)'),('嘉慶, , )','嘉慶)'),
  ('1796년 음력 1월 1일(양력 2월 10일)','1796년 음력 1월 1일'),
  ("모친':","모친:"),
  ('2006년, , 331쪽','2006년, 331쪽'),
  ('청아출판사, 2006년, .','청아출판사, 2006년.'),
  ("The Great Qing''",'The Great Qing')],
 'expanded_train:265302':[
  ('이재명(李在明, 1964년 12월 22일~)','이재명(李在明, 1964년 12월 22일(호적상 출생일)~)')]
}
sidecars={
 'expanded_train:151767':['hold_151767_task090_v2.md'],
 'expanded_train:175714':['hold_175714_task097_v1.md'],
 'expanded_train:240050':[],
 'expanded_train:246989':['hold_246989_v1.md','hold_246989_v2.md'],
 'expanded_train:265302':['hold_265302_v1.md']}
reading={
 'expanded_train:151767':dict(scope='Original full; selected full; all diff hunks; sidecar full',chunks=['af3072','fe7d02','e48473']),
 'expanded_train:175714':dict(scope='Original full; selected full; all diff hunks; sidecar full',chunks=['af3072','fe7d02','e48473']),
 'expanded_train:240050':dict(scope='Original full; selected full; all diff hunks; no new omitted text',chunks=['1a8a23','6dd451']),
 'expanded_train:246989':dict(scope='Original full in two contiguous reads; all selected hunks/context/EOF; both sidecars full',chunks=['af3072','c09d64','96718c','64191c']),
 'expanded_train:265302':dict(scope='Exact source first context and explicit birth-registration paragraph; all selected hunks/context/EOF; sidecar full. Not original full reading by root.',chunks=['64191c','c23315'])}
rows=[]
for ident,changes in specs.items():
    source,record=manifest[ident],records[ident]
    assert ident not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    assert record['original']['sha256']==source['original']['sha256']
    original=verify(source['original'])
    candidate=verify(source['candidate'])
    selected=dict(path=record['body'],sha256=record['clean_text_sha256'])
    body=verify(selected)
    expected=candidate
    for old,new in changes:
        expected=replace_once(expected,old,new)
    empty_headers=[]
    if ident in {'expanded_train:246989','expanded_train:265302'}:
        start_marker=' 황후 ' if ident.endswith(':246989') else '역대 선거 결과'
        end_marker=' 참고 자료 ' if ident.endswith(':246989') else '외부 링크 '
        begin=expected.index(chr(10)+start_marker+chr(10))
        end=expected.index(chr(10)+end_marker+chr(10),begin)
        block=expected[begin:end]
        empty_headers=[s.strip() for s in block.splitlines() if s.strip()]
        assert empty_headers==(['황후','후궁','황귀비','측비','서비','황자','황녀','기년과 연호']
            if ident.endswith(':246989') else ['역대 선거 결과','소속 정당'])
        expected=replace_once(expected,block,'')
    exact_eof=expected==body
    assert exact_eof or expected.rstrip(chr(10))+chr(10)==body, 'unexpected text outside root-read edits'
    saved_sidecars=[]
    for name in sidecars[ident]:
        path=BASE/'agents'/record['role']/'birth_root11_independent_v1'/name
        saved=pin(path)
        verify(saved)
        saved_sidecars.append(saved)
    payload=(ROOT/record['review']['archive']).read_bytes()
    assert sha(payload)==record['review']['sha256']
    rows.append(dict(id=ident,original=source['original'],candidate=source['candidate'],
        selected=selected,review=record['review'],sidecars=saved_sidecars,
        exact_allowed_replacements=len(changes),removed_empty_headers=empty_headers,
        eof_normalization_only=not exact_eof,unchanged_bytes_outside_allowed_edits_verified=True,
        actual_root_reading=reading[ident],
        decision='KNOWN_FOLLOWUP_SCOPE_SATISFIED_NOT_YET_ROOT_OR_CACHE_ADOPTED'))
result=dict(status='FIVE_ADDITIONAL_ROOT_READ_AUTHOR_FOLLOWUPS_AND_UNCHANGED_BYTES_VERIFIED',rows=rows,
    known_pending_in_these_five=0,prior_three_verified_scope=pin(AUDIT/'CURRENT_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json'),
    input_pins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
                (manifest_path,snapshot_path,contract_path,frozen,Path(__file__).resolve())},
    expected_transforms_existed_only_in_memory_for_verification=True,
    root_authored_corpus_bodies=0,root_or_cache_adoptions=0,protected_body_reads=0,
    whole_semantic_review_complete=False,goal_complete=False)
target=AUDIT/'ADDITIONAL_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json'
with target.open('x',encoding='utf-8') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'],rows=len(rows),known_pending_in_this_scope=0,
                     root_or_cache_adoptions=0),ensure_ascii=False))
