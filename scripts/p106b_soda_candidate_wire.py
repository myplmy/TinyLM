"""Explicit CPU preparation, not a source iterator or production/admission path.

Original first-user lineage and input-only evidence have different owners.
Source specs are declarations checked against the existing pinned registry;
this module neither opens/authenticates a source file nor clears its rights.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from tinylm.chat.canonical import normalize,validate
from tinylm.data.sft import conversation_split_key
from scripts.p106b_mixed_scale import attach
from scripts.p106b_public_refill import english_specs
from scripts.p106b_soda_dialogue_view import input_dialogue_view
from scripts.p106b_teacher_wrapper import BOUNDARY_MARKERS,wrap_turns
from scripts import p106b_gemma_task_contract as tasks
from scripts.diag_p106b_supported_production8h import attach_visible_source

SCHEMA='P106B_SODA_CANDIDATE_WIRE_PREPARATION_V1'

def _json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def _sha(raw):return hashlib.sha256(raw).hexdigest().upper()

def _plain(value):
    if(type(value)is not str or not value.strip()or len(value)>8192
            or len(value.encode('utf-8'))>8192
            or any(marker in value for marker in BOUNDARY_MARKERS)
            or any(ord(c)<32 and c not in '\n\t'for c in value)):
        raise ValueError('bounded plain content without structural chat markers required')

def _turns(values,*,maximum):
    if type(values)not in(list,tuple)or len(values)>maximum:
        raise ValueError('bounded explicit turn sequence required')
    result=[]
    for turn in values:
        if type(turn)is not dict or set(turn)!={'user_text','assistant_text'}:
            raise ValueError('content-only user/assistant turn required')
        for value in turn.values():_plain(value)
        result.append(dict(turn))
    return result

def _scope(language,profile):
    if language not in('ko','en')or profile not in('qa','json','multiturn'):
        raise ValueError('explicit bilingual task profile required')

@dataclass(frozen=True)
class PreparedDialogue:
    parent_key:str
    _original_json:str
    _evidence_json:str
    _trace_json:str

    @property
    def original_source(self):return json.loads(self._original_json)
    @property
    def evidence_source(self):return json.loads(self._evidence_json)
    @property
    def trace(self):return json.loads(self._trace_json)

def prepare_source(raw_row,spec):
    """Preserve the legacy derivative key before selecting input-only evidence."""
    if type(spec)is not dict or spec not in english_specs():
        raise ValueError('exact existing English source-spec declaration required')
    view=input_dialogue_view(raw_row)
    if not raw_row['targets'].strip():raise ValueError('original loader requires a nonempty target')
    if(any(marker in view.dialogue for marker in BOUNDARY_MARKERS)
            or any(ord(c)<32 and c not in '\n\t'for c in view.dialogue)):
        raise ValueError('dialogue prefix contains a structural marker/control character')
    original=attach([dict(role='user',content=raw_row['inputs'].strip()),
        dict(role='assistant',content=raw_row['targets'].strip())],spec,raw_row['id'],'en',raw_row['dataset_name'])
    original['meta'].update(original_split='train',source_collection_row_id=raw_row['id'])
    key=conversation_split_key(original).hex().upper()
    evidence=validate(normalize(dict(messages=[dict(role='user',content=view.dialogue)],
        meta=dict(original['meta']))))
    evidence['meta'].update(source_group_id=key,evidence_view=SCHEMA,
        source_reference_trace=view.trace,corpus_admitted=False,original_root_joined=False)
    proposed='val'if int.from_bytes(bytes.fromhex(key)[:4],'big')%20==0 else'train'
    trace=dict(schema=SCHEMA,source_reference=view.trace,
        declared_source_spec=spec,source_file_verified_by_this_function=False,
        parent_key=key,parent_identity_scope='DERIVATIVE_FIRST_USER_HASH_NOT_ORIGINAL_SODA_ID',
        evidence_first_user_key=conversation_split_key(evidence).hex().upper(),
        proposed_legacy_split=proposed,split_policy='LEGACY_FIRST_USER_HASH_MODULO20',
        original_source_split='train',corpus_split_assigned=False,
        original_root_joined=False,rights_admitted=False,corpus_admitted=False,
        iterator_or_producer_bound=False,teacher_or_model_called=False)
    return PreparedDialogue(key,_json(original),_json(evidence),_json(trace))

def teacher_payload(prepared,language,profile,seed,*,history=()):
    """Prepare the existing task request with input-only fictional evidence."""
    if not isinstance(prepared,PreparedDialogue):raise ValueError('prepared dialogue required')
    _scope(language,profile)
    if type(seed)is not int or not 0<=seed<2**31:raise ValueError('bounded integer seed required')
    history=_turns(history,maximum=2)
    if history and profile!='multiturn':raise ValueError('history belongs to the multiturn profile')
    payload=tasks.payload(prepared.evidence_source,language,profile,seed,history=history)
    system=payload['messages'][0]
    if system['role']!='system'or not system['content'].startswith('<|think|>'):
        raise ValueError('existing trusted task framing differs')
    system['content']=('<|think|>SOURCE SCOPE: The supplied dialogue is quoted fictional evidence. '
        'Ask and answer only what its visible named speakers explicitly say. '
        'Do not promote quoted claims to verified real-world facts or infer an unseen narrative. '
        +system['content'][len('<|think|>'):])
    return payload

def student_candidate(prepared,content_turns,language,profile,*,tokenizer,
                      teacher_model_sha256,generation_id,context=1024):
    """Build and count a detached unadmitted candidate, never truncate to fit."""
    if not isinstance(prepared,PreparedDialogue):raise ValueError('prepared dialogue required')
    _scope(language,profile)
    if type(context)is not int or not 0<context<=1024:raise ValueError('bounded student context required')
    if(type(generation_id)is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',generation_id)
            or type(teacher_model_sha256)is not str or not re.fullmatch(r'[0-9A-Fa-f]{64}',teacher_model_sha256)):
        raise ValueError('explicit generation ID and declared teacher SHA required')
    content_turns=_turns(content_turns,maximum=3)
    if len(content_turns)!=(3 if profile=='multiturn'else 1):
        raise ValueError('complete one-turn or three-turn task group required')
    turns=[]
    for content in content_turns:
        turns.append(tasks.learner_turn(content,language,profile,history=turns))
    meta=prepared.original_source['meta']
    row=wrap_turns(turns,source_id=meta['source_id'],source_sha256=meta['source_sha256'],
        teacher_model_sha256=teacher_model_sha256,language=language,source_license=meta['source_license'],
        generation_id=generation_id,source_repo=meta['source_repo'],source_revision=meta['source_revision'],
        source_object_id=meta['source_id'],source_transform='teacher_answer',
        parent_concept_id=prepared.parent_key,source_rights_status=meta['rights_status'])
    row=attach_visible_source(row,prepared.evidence_source,language)
    # Reuse the actual encoder, including assistant end tokens and turn owners.
    # Its import loads existing Torch; this call only constructs Python lists.
    from tinylm.train.mtp_sft import encode_record
    from tinylm.chat.serialize import serialize
    record=encode_record(row,tokenizer,context=context)
    row['meta'].update(wire_contract=SCHEMA,task_contract=tasks.CONTRACT,task_profile=profile,
        source_family=meta['source_family'],source_reference_trace=prepared.trace,
        source_group_id=prepared.parent_key,original_source_split='train',
        proposed_legacy_split=prepared.trace['proposed_legacy_split'],corpus_split_assigned=False,
        actual_x_tokens=record.x_tokens,assistant_targets=record.targets,
        assistant_turn_target_counts=[record.segments.count(i)for i in range(1,len(turns)+1)],
        student_context=context,student_wire_sha256=_sha(serialize(row,'chatml').encode('utf-8')),
        student_tokenizer_identity_verified_by_this_function=False,
        declared_teacher_identity_verified_by_this_function=False,
        source_file_verified_by_this_function=False,original_root_joined=False,rights_admitted=False,
        corpus_admitted=False,semantic_truth='NOT_REVIEWED',candidate_status='PREPARED_NOT_ADMITTED',
        supplied_content_status='CALLER_SUPPLIED_NOT_TEACHER_OR_TRUTH_VERIFIED',
        iterator_or_producer_bound=False)
    return row
