"""Keep six actual reads and separate a reviewed fix from unchanged old cache."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
prior_path=AUDIT/'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V2.json'
prior=inv.cache.read(prior_path)
source_path=AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
records={row['id']:row for row in inv.cache.read(source_path)['records']}
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
rows=list(prior['rows'])
findings={
 'expanded_train:1021004': '원문/기존선택문전부및별도전체diff를읽었다. 기존추상알고리즘의완결의사코드까지삭제됐고복잡도의난수가정·추측/미증명한정이사라진채속도주장은남는다. 실제원문한정과완결의사코드의보완을원래context_latin역할에위임했다. 새로운g/n정의·수식·증명을추정하지않는다.',
 'expanded_train:1023734': '원문/기존선택문전부및전체diff를읽었다. 로드스터최고속도의실제282km/h가다른단위빈슬롯과함께삭제됐다. 같은실제값·단위를원래최고속도문맥에보존하도록원래historical_review역할에위임했다. 미상중량/출력/토크나현재차량사실을복원하지않는다.',
}
for ident,finding in findings.items():
    row=records[ident]
    assert ident not in contract['restricted_ids'] and row['original_text_sha256'] not in contract['restricted_hashes']
    assert inv.file_sha(ROOT/row['original_comparison_source'])==row['original_text_sha256']
    assert inv.file_sha(ROOT/row['body'])==row['clean_text_sha256']
    rows.append({'id':ident,'original':{'path':row['original_comparison_source'],'sha256':row['original_text_sha256']},
        'body':{'path':row['body'],'sha256':row['clean_text_sha256']},'reviewer':'root',
        'full_original_and_selected_body_read':True,'full_diff_read':True,
        'observation_tool_chunks':['72f53a','edd473'] if ident.endswith(':1021004') else ['72f53a'],
        'finding':finding,'decision':'CORRECTION_REQUIRED_BEFORE_SEMANTIC_CLOSURE','source_fact_verification':False})
assert len({row['id'] for row in rows})==len(rows)==6
directory=inv.BASE/'agents/context_latin/root11_ordered_corrections_v1'
fixed=directory/'reviewed_1018113_root11_v2.txt'
guide=AUDIT/'ROOT11_1018113_CORRECTION_INPUTS_V1.json'
assert 'Cartesian Product'+chr(10)+'In this situation' in fixed.read_text(encoding='utf-8')
review=directory/'review_001_v2.md';sidecar=directory/'hold_1018113_root11_v2.md'
for path in (fixed,review,sidecar):assert path.is_file() and 0<path.stat().st_size<20_000_000
inv.write_json(AUDIT/'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V3.json',{
    'status':'SIX_ACTUAL_READS_ONE_CORRECTED_BODY_REVIEWED_NOT_YET_IN_SELECTION_OR_CACHE',
    'ordered_flag_sources':585,'actually_reviewed_sources':6,'remaining_unreviewed_flag_sources':579,
    'old_root11_acceptable_sources':3,'old_root11_sources_requiring_replacement':3,
    'corrected_semantic_reviewed_sources':1,'corrections_still_pending':2,'rows':rows,
    'corrected_1018113':{'id':'expanded_train:1018113','body':{'path':str(fixed.relative_to(ROOT)),'sha256':inv.file_sha(fixed)},
        'review':{'path':str(review.relative_to(ROOT)),'sha256':inv.file_sha(review)},
        'sidecar':{'path':str(sidecar.relative_to(ROOT)),'sha256':inv.file_sha(sidecar)},
        'root_full_v1_read_tool_chunk':'6707c6','heading_move_full_diff_tool_chunk':'93fc76',
        'root_rechecked_full_v2':True,'decision':'REVIEWED_CORRECTED_MEANING_WITH_ORIGINAL_LIMITS',
        'in_new_root_selection':False,'in_cache3':False},
    'prior':{'path':str(prior_path.relative_to(ROOT)),'sha256':inv.file_sha(prior_path)},
    'input_pins':{str(path.relative_to(ROOT)):inv.file_sha(path) for path in (source_path,guide,Path(__file__))},
    'detector_flag_automatically_waived':False,'old_cache_or_source_changed':False,
    'birth_independent_whole_second_reading':'NOT_COMPLETED','whole_corpus_semantic_completion':False,
    'goal_complete':False,'training_authorized':False})
print('six actual source/body reviews; one replacement reviewed; two fixes and579 other flag reads remain')
