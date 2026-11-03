"""Bind actual whole-source root readings to reviewed HOLD, never unread renaming."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
group = inv.BASE / 'remaining_literal_full_counter_v1'
manifest_path = group / 'manifest.json'
sources = {row['id']: row for row in inv.cache.read(manifest_path)['rows']}
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
findings = {
    'expanded_train:213255': ('ROOT_SCRAP_COLLAGE_BOUNDARIES_V1.md', None, '서로무관한R/SEO/악성코드/공항/영화주제파편이문장중간에서교차하고원래독립본문경계를신뢰할수없다.'),
    'expanded_train:229534': ('ROOT_SCRAP_COLLAGE_BOUNDARIES_V1.md', None, '여러언어·도구의API검색문구와업체문자열치환이교차해정상원래대상과문장경계를확정할수없다.'),
    'expanded_train:550829': ('ROOT_MIXED_SNIPPET_ADJUDICATIONS_V1.md', None, 'VB검색발췌/광고/포럼/페이지번호가섞이고실제연도·버전·문장끝이사라져본래하나의글로복원할수없다.'),
    'expanded_train:455473': ('ROOT_MIXED_SNIPPET_ADJUDICATIONS_V1.md', None, 'SQL도구/역사/인물/문서플랫폼의검색발췌가섞여귀속을확정할수없다. 주제자체가제외근거는아니다.'),
    'expanded_train:739077': (None, '5b2e85', 't분포/정규분포/Excel·Sheets/미적분발췌가잘린문장으로교차하고함수자리도도메인문자열로치환돼원래귀속과단일본문을복구할수없다.'),
    'expanded_train:744720': (None, 'd7ca84', 'R보험청구/Matlab GEV/별도미적분문제가문장마다교차하며목표·식·수치·시각조건의본래귀속을분리할수없다.'),
    'expanded_train:770057': (None, '9b9da5', '첫단락부터assertion/JVM예외/license가삽입되고후속은여러언어API·포럼·검색문장이잘려교차한다. 제안했던첫단락의연속본문경계도성립하지않는다.'),
}
rows = []
for ident, (evidence_name, chunk, reason) in findings.items():
    source = sources[ident]
    assert ident not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
    assert inv.file_sha(ROOT / source['original']['path']) == source['original']['sha256']
    evidence = None
    if evidence_name:
        path = group / evidence_name
        assert ident.split(':')[1] in path.read_text(encoding='utf-8')
        evidence = {'path': str(path.relative_to(ROOT)), 'sha256': inv.file_sha(path)}
    rows.append({'id': ident, 'role': source['role'], 'original': source['original'],
        'source_ids': source['source_ids'], 'source_ids_sha256': source['source_ids_sha256'],
        'occurrences': source['occurrences'], 'reviewer': 'root', 'full_original_actually_read': True,
        'observation_tool_chunk': chunk, 'prior_direct_read_evidence': evidence,
        'decision': 'HOLD', 'reviewed_disposition': 'INDIVIDUALLY_REVIEWED_UNRECOVERABLE_MIXED_CONTEXT',
        'reason': reason, 'raw_original_preserved': True, 'unread_bulk_disposition': False,
        'new_prose_authored_by_root': False, 'root_approved_nonadmission': True, 'cache_admitted': False})
inv.write_json(AUDIT / 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V1.json', {
    'status': 'SEVEN_INDIVIDUAL_FULL_SOURCE_READINGS_NOT_UNREAD_HOLD_RENAMING', 'rows': rows,
    'unique_sources': len(rows), 'positions': sum(row['occurrences'] for row in rows),
    'input_pins': {str(path.relative_to(ROOT)): inv.file_sha(path) for path in (manifest_path, Path(__file__))},
    'current_roster_or_cache_changed': False, 'whole_corpus_processing_complete': False,
    'goal_complete': False, 'training_authorized': False})
print('individual whole-source reviewed nonadmissions:', len(rows))
