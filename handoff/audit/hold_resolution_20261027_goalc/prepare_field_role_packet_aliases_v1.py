"""Copy pinned unchanged packets into the exact assigned role's read-only views."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

parser=argparse.ArgumentParser()
parser.add_argument('--role',choices=['context_hangul','context_latin','historical_review','legacy_review'],required=True)
role=parser.parse_args().role
source_path=inv.BASE/'remaining_field_title_readers_v1/complete.json'
source=inv.cache.read(source_path)
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
blocked_ids=set(contract['restricted_ids']);blocked_sha=set(contract['restricted_hashes'])
output=AUDIT/('FIELD_'+role.upper()+'_EXACT_PACKET_ALIASES_V1.json')
assert not output.exists()
for page in source['pages']:
    target=inv.BASE/'agents'/role/page['group']/'reading_packets_v1'
    assert not target.exists()
pages=[];all_sources=0;all_packets=0;total_bytes=0
for page in source['pages']:
    path=ROOT/page['path']
    assert inv.file_sha(path)==page['sha256']
    manifest=inv.cache.read(path)
    rows=[row for row in manifest['rows'] if row['role']==role]
    assert len(rows)==page['assignments'][role]
    assert not ({row['id'] for row in rows}&blocked_ids)
    assert not ({row['original']['sha256'] for row in rows}&blocked_sha)
    canonical=inv.BASE/page['group']/'reading_packets_v1'
    directory=inv.BASE/'agents'/role/page['group']
    target=directory/'reading_packets_v1'
    target.mkdir()
    aliases=[]
    for row in rows:
        parts=[]
        for pin in row['reading_parts']:
            original=ROOT/pin['path']
            assert not original.is_symlink() and original.resolve().is_relative_to(canonical.resolve())
            payload=original.read_bytes()
            assert inv.sha(payload.decode('utf-8'))==pin['sha256'] and 0<len(payload)<20_000_000
            view=target/original.name
            with view.open('xb') as stream:stream.write(payload)
            assert inv.file_sha(view)==pin['sha256']
            parts.append(dict(canonical=pin,alias=dict(path=str(view.relative_to(ROOT)),sha256=pin['sha256']),bytes=len(payload)))
            all_packets+=1;total_bytes+=len(payload)
        aliases.append(dict(id=row['id'],parts=parts))
    report=target/'alias_manifest_v1.json'
    inv.write_json(report,dict(status='EXACT_PINNED_READONLY_COPIES_NOT_NEW_SOURCE_DATA',role=role,
        page=page['page'],rows=aliases,source_manifest=page,goal_complete=False,training_authorized=False))
    assert report.stat().st_size<20_000_000
    lines=['# 自己担当 exact packet 사본 허가','',
        '총괄이 자기 역할에 이미 배정된 packet을 아래 새 자기폴더에 동일 바이트로 복사하고 source/사본 SHA를 실제 대조했다.',
        '이 폴더는 읽기 전용 입력이며 새 본문/리뷰/sidecar를 이 안에 쓰거나 덮지 않는다. 코드·registry·manifest JSON을 열 필요는 없다.',
        '기존 canonical 경로도 유효하다. 아래 사본만 추가 허용하고 다른 역할/다른source 경로를 추측하지 않는다.',
        '사본 읽기는 같은 한 문서의 판독이며 새고유자료나 두 독립검토자 판독이 아니다. 다른후보는모든frame을읽고 동일증명ID는원문전문/최종diff필수범위를읽는다.',
        '자기TASK의 원문/후보 전문 및 직접diff로 실제읽기를완료했다면 사본packet중복읽기는필수아니다. 출력잘림은완료로세지않는다.','']
    for row in aliases:
        lines+=['## '+row['id']]
        paths=[str(ROOT/part['alias']['path']) for part in row['parts']]
        for offset in range(0,len(paths),2):lines+=['cat '+' '.join(paths[offset:offset+2])]
    guide=directory/'ROOT_EXACT_PACKET_ALIASES_V1.md'
    payload=(chr(10).join(lines)+chr(10)).encode('utf-8');assert len(payload)<20_000_000
    with guide.open('xb') as stream:stream.write(payload)
    pages.append(dict(page=page['page'],sources=len(rows),manifest=dict(path=str(report.relative_to(ROOT)),sha256=inv.file_sha(report)),
        guide=dict(path=str(guide.relative_to(ROOT)),sha256=inv.file_sha(guide))))
    all_sources+=len(rows)
inv.write_json(output,dict(status='ALL_ROLE_FIELD_EXACT_PACKET_COPIES_VERIFIED_NOT_NEW_PROSE',role=role,
    sources=all_sources,packets=all_packets,bytes=total_bytes,pages=pages,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [source_path,Path(__file__)]},
    cleaned_prose_authored_by_root=0,source_or_candidate_changed=False,goal_complete=False,training_authorized=False))
print(json.dumps(dict(role=role,sources=all_sources,packets=all_packets,bytes=total_bytes,pages=len(pages))))
