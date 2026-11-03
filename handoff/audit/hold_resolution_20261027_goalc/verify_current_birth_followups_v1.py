"""Verify only root-read, author-written corrections; never write corpus bodies."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read(path):
    return json.loads(path.read_bytes())


def pin(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))


def verify(item):
    path = ROOT / item['path']
    assert not path.is_symlink() and path.resolve().is_relative_to(BASE)
    data = path.read_bytes()
    assert sha(data) == item['sha256']
    return data.decode('utf-8')


def replace_once(text, old, new):
    assert text.count(old) == 1, 'expected exact source span is not unique'
    return text.replace(old, new, 1)


manifest_path = BASE / 'birth_root11_independent_v1/manifest.json'
snapshot_path = BASE / 'birth_root11_independent_v1_snapshots/v14/complete.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
manifest = {r['id']:r for r in read(manifest_path)['rows']}
snapshot = read(snapshot_path)
contract = read(contract_path)
assert not snapshot['errors'] and not snapshot['needs_root']
records = {}
for shard in snapshot['shards']:
    payload = (ROOT / shard['path']).read_bytes()
    assert sha(payload) == shard['sha256']
    records.update({r['id']:r for r in json.loads(payload)})
specifications = {
    'expanded_train:192706': [
        ('도자와 마사요시(1719년 ~ 1745년 9월 9일)', '도자와 마사요시(1745년 사망)'),
        ('교호 19년(1734년에', '교호 19년(1734년)에'),
        ('엔쿄 2년(1745년) 8월 14일에 27세', '엔쿄 2년(1745년)에 27세'),
        ('1719년 출생' + chr(10), '')],
    'expanded_train:194297': [
        ('도자와 마사노부(1720년 ~ 1765년 11월 3일)', '도자와 마사노부(1765년 11월 3일 사망)'),
        ('1720년 출생' + chr(10), '')],
    'expanded_train:136932': [
        ('|이름     = 아유르바르와다 부얀투 카안 |원래 이름 = ', '|이름     = 아유르바르와다 부얀투 카안'),
        ('|휘       = 아유르바르와다(, )', '|휘       = 아유르바르와다'),
        ('|칸호 = 부얀투 카안(, )', '|칸호 = 부얀투 카안'),
        ('|사망일   = 연우(延祐) 7년 1월 21일(1320년 3월 1일)', '|사망일   = 1320년'),
        ('1320년 3월 1일(음력 1월 21일)', '1320년'),
        ('부얀투 카안(, Буянт хаан, 普顏篤可汗, 巴顏圖可汗)', '부얀투 카안(Буянт хаан, 普顏篤可汗, 巴顏圖可汗)'),
        ("본명은 아유르바르와다'''(, )으로", '본명은 아유르바르와다로'),
        ('인종 아유르바르와다는 1285년 음력', '인종 아유르바르와다는 음력'),
        ('유아 시절인 1286년부터', '1286년부터'),
        ('인종 사후인 1316년에 완료', '1316년에 완료'),
        ('1320년 3월 21일 인종은', '1320년 인종은'),
        (chr(10) + '족보' + chr(10)*2 + '기년' + chr(10)*2 + '각주 ' + chr(10), '')]
}
results = []
for ident, changes in specifications.items():
    source, record = manifest[ident], records[ident]
    assert ident not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    original = verify(source['original'])
    candidate = verify(source['candidate'])
    body_pin = dict(path=record['body'], sha256=record['clean_text_sha256'])
    body = verify(body_pin)
    expected = candidate
    for old, new in changes:
        expected = replace_once(expected, old, new)
    removed_empty_rows = []
    if ident == 'expanded_train:136932':
        retained = []
        for line in expected.splitlines(keepends=True):
            if re.fullmatch(r'\|[^=\n]*=[ \t]*\n', line):
                removed_empty_rows.append(line)
            else:
                retained.append(line)
        expected = ''.join(retained)
        assert len(removed_empty_rows) == 16
        for value in ('아유르바르와다 부얀투 카안', 'Буянт хаан', '普顏篤可汗', '巴顏圖可汗',
                      '1316년에 완료', '인종 생전에는 반포되지 못한다', '1323년에 대원통제',
                      '몽골 황금사에 의하면 아유르바르와다는 1275년생이라 한다'):
            assert value in body
    expected = expected.rstrip(chr(10)) + chr(10)
    assert expected == body, 'change outside exact root-reviewed allowance'
    sidecar_name = ('hold_136932_task085_v3.md' if ident.endswith(':136932') else
                    'hold_' + ident.split(':')[1] + '_v3.md')
    sidecar_path = BASE / 'agents' / record['role'] / 'birth_root11_independent_v1' / sidecar_name
    sidecar_pin = pin(sidecar_path)
    sidecar = verify(sidecar_pin)
    assert all(term in sidecar for term in ({
        'expanded_train:192706': ['1719년', '1745년 9월 9일', '8월 14일'],
        'expanded_train:194297': ['1720년', '1765년 11월 3일'],
        'expanded_train:136932': ['1285년', '유아 시절인', '사후인', '족보', '기년', '각주']
    }[ident]))
    review_payload = (ROOT / record['review']['archive']).read_bytes()
    assert sha(review_payload) == record['review']['sha256']
    results.append(dict(id=ident, original=source['original'], candidate=source['candidate'],
        selected_body=body_pin, review=record['review'], sidecar=sidecar_pin,
        allowed_exact_replacements=len(changes), removed_empty_info_rows=len(removed_empty_rows),
        unchanged_bytes_outside_allowed_edits_verified=True,
        root_actual_read_scope=('original full; selected full; every candidate-to-selected diff hunk; sidecar full'
            if ident != 'expanded_train:136932' else
            'original full; every candidate-to-selected hunk and surrounding context; selected EOF; sidecar full'),
        root_actual_read_chunks=['ec9543', 'c6a3b0', 'e10418', 'bd2255', '832c27'],
        decision='KNOWN_FOLLOWUP_SCOPE_SATISFIED_NOT_YET_ROOT_OR_CACHE_ADOPTED'))
result = dict(status='THREE_ROOT_READ_AUTHOR_CORRECTIONS_AND_UNCHANGED_BYTES_VERIFIED', rows=results,
    pending_known_corrections_in_these_three=0,
    root_correction='Earlier procedural message called Enkyo2 Aug14 lunar without an explicit source label. '
                    'That assumption was withdrawn; both unqualified death dates are held without conversion.',
    reported_packet_discrepancy_160640=dict(source_original_characters=1777,candidate_characters=1761,
        reading_packets=1, original_jokbo_ginyeon_occurrences=0,candidate_jokbo_ginyeon_occurrences=0,
        actual_diff_matches_assigned_packet=True, root_check_chunk='49dc10',
        author_corrected_review='review_092_v3.md', producer_input_repair_needed=False),
    input_pins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
                (manifest_path,snapshot_path,contract_path,Path(__file__).resolve())},
    root_authored_corpus_bodies=0, root_or_cache_adoptions=0,
    protected_body_reads=0, whole_semantic_review_complete=False, goal_complete=False)
target = AUDIT / 'CURRENT_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json'
with target.open('x',encoding='utf-8') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'],rows=len(results),pending_known_in_this_scope=0,
                     root_or_cache_adoptions=0),ensure_ascii=False))
