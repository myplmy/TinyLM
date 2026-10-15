"""Lossless whole-message views for diagnostic inference, never training export."""
import copy
import hashlib


def sha(text):return hashlib.sha256(text.encode('utf-8')).hexdigest().upper()


def header(unit,language):
    if language=='ko':return f"[원문 메시지 {unit['id']} / {unit['role']}]\n"
    if language=='en':return f"[Original message {unit['id']} / {unit['role']}]\n"
    raise ValueError('known language only')


def view(row,variant):
    if variant not in ('full','selected','empty'):raise ValueError('declared diagnostic view required')
    if [m['role'] for m in row['messages']]!=['user','assistant']:raise ValueError('one outer QA required')
    if len(row['messages'][0]['content'])!=1 or row['messages'][0]['content'][0]['type']!='text':raise ValueError('text-only outer input required')
    full=row['messages'][0]['content'][0]['text'];meta=row['meta'];lang=meta['language']
    units=meta['source_reference_trace'];spans=meta['student_original_message_ranges']
    if not units or len(units)!=len(spans):raise ValueError('complete upstream message ranges required')
    for unit,span in zip(units,spans):
        text=full[span['start']:span['end']]
        if text!=unit['text'] or sha(text)!=span['sha256'] or span['source_message_index']!=unit['source_message_index']:
            raise ValueError('upstream complete-message bytes differ')
    first=header(units[0],lang);start=spans[0]['start']-len(first)
    if start<0 or full[start:spans[0]['start']]!=first:raise ValueError('known original header absent')
    prefix=full[:start];suffix=full[spans[-1]['end']:]
    marker='\n질문:\n' if lang=='ko' else '\nQuestion:\n'
    if not suffix.startswith(marker):raise ValueError('exact trailing question required')
    def build(chosen):return prefix+''.join(header(u,lang)+u['text']+'\n' for u in chosen)+suffix[1:]
    if build(units)!=full:raise ValueError('full lossless reconstruction differs')
    selected=meta['teacher_selected_reference_ids'];available={u['id'] for u in units}
    if (not selected or len(set(selected))!=len(selected) or any(type(v) is not int or v not in available for v in selected)):
        raise ValueError('recorded teacher IDs required; no word-based inference')
    chosen=units if variant=='full' else [u for u in units if u['id'] in selected] if variant=='selected' else []
    text=build(chosen);result=copy.deepcopy(row);result['messages'][0]['content'][0]['text']=text
    result['meta']=dict(language=lang,kind='public_qa',rubric=meta['rubric'],source='P106B_REFERENCE_VIEW_DIAGNOSTIC',
        source_family=meta.get('source_family'),source_id=meta.get('source_id'),source_license=meta.get('source_license'),
        semantic_truth='NOT_REVIEWED',student_training_allowed=False,source_split='DEVELOPMENT_EVAL_ONLY',
        reference_variant=variant,current_reference_ids=[u['id'] for u in chosen],
        full_prompt_sha256=sha(full),current_prompt_sha256=sha(text),upstream_meta=copy.deepcopy(meta),
        scope='stored whole-message selection only; not source-truth judgment, online filter or training export')
    return result
