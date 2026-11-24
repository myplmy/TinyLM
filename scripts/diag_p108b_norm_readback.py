"""Recount closed amplitudes, freeze DEV choice, and prepare readable raw QA."""
import json
from pathlib import Path
from scripts import diag_p108b_norm_sweep as study
from scripts import diag_p108b_policy as io
from scripts import p108b_norm_sweep as selection
from scripts import p108b_policy as devmetrics
from scripts import p108_weight_space as metrics
from scripts.diag_p108b_review_pack import signature
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as library

ROOT=study.ROOT
AUDIT=ROOT/'handoff/audit/nov16_pm_p108b'
READABLE=ROOT/'review_request/20261116_PM_P108B_수정량_원답_v1'


def run():
    report=study.read(study.OUT/'report.json')
    if (report['status']!='NORM_SWEEP_COMPLETE_ROOT_REVIEW_PENDING' or not report['original_core_restored'] or
            report['cuda_allocated_after_bytes'] or report['cuda_reserved_after_bytes']):
        raise ValueError('successful closed native sweep required')
    if READABLE.exists():raise FileExistsError('preserve previous reading pack')
    profile=study.read(study.PROFILE)
    if report['source_profile_sha256']!=manual.file_sha(study.PROFILE):raise ValueError('report/profile binding changed')
    for path,sha in dict(profile['sources'],**profile['references']).items():
        if manual.file_sha(ROOT/path)!=sha:raise ValueError('source input changed')
    data=study.read(study.SOURCE/'data.json');dev=study.read(study.SOURCE/'select_dev.json')['rows']
    originals=io.read_answers(study.SOURCE/'geometry',study.read(study.SOURCE/'geometry/report.json')['baseline']['answers_manifest'])
    required={r['id']for r in originals if r['split']!='select_dev'and r['protected']and r['exact']}
    original=dict(name='original',lost_original_protected_ids=[],physical=dict(net_norm=0.),
                  dev=devmetrics.dev_summary([r for r in originals if r['split']=='select_dev']),
                  edited_core_sha256=profile['origin']['core_sha256'],source='geometry baseline',packet=None)
    candidates=[original];known={}
    for dirname in ('20261116_P108B_답전체범위_원답_v1','20261116_P108B_정상경로보호_원답_v1'):
        folder=ROOT/'review_request'/dirname
        review=study.read(folder/'ROOT_REVIEW_v1.json')
        sha=manual.file_sha(folder/'SOURCE_ROWS_v1.json')
        if review['source_sha256']!=sha:raise ValueError('old reviewed original rows differ')
        for row in study.read(folder/'SOURCE_ROWS_v1.json')['rows']:
            known[signature(row)]=dict(source=str((folder/'SOURCE_ROWS_v1.json').relative_to(ROOT)),source_sha256=sha,review_id=row['review_id'])
    for mode in profile['modes']:
        directory,parent=study.old_candidate(mode)
        candidates.append(dict(parent,source=str((directory/'report.json').relative_to(ROOT)),
                               source_sha256=manual.file_sha(directory/'report.json')))
    unique={};models={};pins={};total=0
    expected={r['id']:r['question']for r in data['rows']+dev}
    for arm in report['arms']:
        directory=study.OUT/arm['name'];path=directory/'report.json'
        if study.read(path)!=arm:raise ValueError('root/arm actual report differs')
        pins[str(path.relative_to(ROOT))]=manual.file_sha(path)
        rows=io.read_answers(directory,arm['answers_manifest'])
        if len(rows)!=164 or {r['id']:r['question']for r in rows}!=expected:raise ValueError('same164 actual inputs required')
        for row in rows:
            if row['exact']!=(None if row['expected']is None else metrics.exact_answer(row['answer'],row['expected'])):
                raise ValueError('raw strict answer differs from owner rule')
        fit=metrics.summarize([r for r in rows if r['split']=='fit'])
        development=devmetrics.dev_summary([r for r in rows if r['split']=='select_dev'])
        kept={r['id']for r in rows if r['split']!='select_dev'and r['protected']and r['exact']}
        if fit!=arm['fit']or development!=arm['dev']or sorted(required-kept)!=arm['lost_original_protected_ids']:
            raise ValueError('actual summary/old-seven transitions disagree')
        candidates.append(dict(arm,source=str(path.relative_to(ROOT)),source_sha256=manual.file_sha(path)))
        models[arm['name']]={k:arm[k]for k in ('fit','dev','physical','physical_delivery','relative_weight_change',
            'predicted_gain','actual_gain','lost_original_protected_ids','kept_original_protected_ids')}
        for row in rows:
            key=signature(row)
            if key not in unique:
                unique[key]=dict(row,review_id='N'+str(len(unique)).zfill(4),qa_signature=key,
                                 previous_root_read=known.get(key),occurrences=[])
            unique[key]['occurrences'].append(dict(model=arm['name'],id=row['id']))
        total+=len(rows)
    winner=min(candidates,key=selection.selection_key)
    frozen=dict(schema='P108B_NORM_DEV_FROZEN_CHOICE_V1',selection_rule=profile['selection_rule'],
        source_profile_sha256=manual.file_sha(study.PROFILE),source_report_sha256=manual.file_sha(study.OUT/'report.json'),
        name=winner['name'],source=winner['source'],source_sha256=winner.get('source_sha256'),
        edited_core_sha256=winner['edited_core_sha256'],packet=winner.get('packet'),
        selection_key=list(selection.selection_key(winner)),
        candidates=[dict(name=r['name'],key=list(selection.selection_key(r)),source=r['source'])for r in candidates],
        final_or_official_answers_used=False,root_language_read_used_for_selection=False)
    library.write_new(study.BASE/'norm_selection_v1.json',frozen)
    rows=list(unique.values());READABLE.mkdir();parts=[]
    for start in range(0,len(rows),25):
        group=rows[start:start+25];path=READABLE/f'answers_{start//25+1:03d}.txt'
        lines=['보호 경로를 유지한 수정량 대조: 실제 질문과 답','정답성/관련성/문장성/반복·나열은 별도로 읽습니다.','']
        for row in group:
            lines.extend([row['review_id']+' / '+row['language']+' / '+row['family'],
                '대응> '+', '.join(r['model']+':'+r['id']for r in row['occurrences']),
                '질문> '+row['question'],'답변> '+row['answer'],
                '기준> '+str(row['expected'])+' / 엄격 정답> '+str(row['exact']),
                '이전 동일 문맥 판독> '+str(row['previous_root_read']),''])
        with path.open('x',encoding='utf-8')as stream:stream.write('\n'.join(lines)+'\n')
        parts.append(dict(path=str(path.relative_to(ROOT)),sha256=manual.file_sha(path),ids=[r['review_id']for r in group]))
    library.write_new(READABLE/'SOURCE_ROWS_v1.json',dict(rows=rows))
    library.write_new(READABLE/'READING_MANIFEST_v1.json',dict(source_report_sha256=frozen['source_report_sha256'],
        actual_answers=total,unique_full_contexts=len(rows),previous_same_qa_read=sum(bool(r['previous_root_read'])for r in rows),
        new_unique=len([r for r in rows if not r['previous_root_read']]),parts=parts,root_status='NEW_UNIQUE_ROOT_REVIEW_PENDING'))
    library.write_new(AUDIT/'NORM_READBACK_v1.json',dict(schema='P108B_NORM_RAW_READBACK_V1',models=models,
        raw_answer_references=total,unique_full_contexts=len(rows),source_reports=pins,
        frozen_selection=frozen['name'],selection_sha256=manual.file_sha(study.BASE/'norm_selection_v1.json'),
        new_model_calls=0,final_or_official_inputs=False))
    print(json.dumps(dict(frozen=winner['name'],selection_key=frozen['selection_key'],raw_answers=total,
        unique=len(rows),previous=sum(bool(r['previous_root_read'])for r in rows),parts=len(parts)),ensure_ascii=False))


if __name__=='__main__':run()
