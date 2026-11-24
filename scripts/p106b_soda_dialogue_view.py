"""Qualified input-prefix view only; no model, file access or corpus admission.

Visible ASCII labels are lexical text, not recovered original speaker identities.
The caller owns file provenance, original-root/split/rights and token budgets.
Original rows/targets remain untouched; old targets are excluded from evidence.
"""
from dataclasses import asdict,dataclass
import hashlib
import json
import re

SCHEMA='P106B_SODA_NAMED_INPUT_DIALOGUE_VIEW_V1'
SUFFIX='What do you think the narrative of the conversation above is?'
BOUNDARY='\n\n\n'+SUFFIX
FIELDS={'id','inputs','targets','dataset_name','sub_dataset_name','task_type','template_id','language','script','split'}
PROFILE=dict(dataset_name='SODA-inst',sub_dataset_name='-',task_type='dialogue',
    template_id=1,language='eng',script='Latn',split='train')
RESERVED={'system','developer','user','assistant','tool'}
LABEL=re.compile(r"[A-Za-z][A-Za-z' -]*")


def _sha(raw):return hashlib.sha256(raw).hexdigest().upper()
def _canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)


@dataclass(frozen=True)
class ViewLimits:
    row_bytes:int=131072
    input_bytes:int=65536
    evidence_bytes:int=32768
    turns:int=128
    labels:int=16
    label_chars:int=64

    def __post_init__(self):
        hard=dict(row_bytes=131072,input_bytes=65536,evidence_bytes=32768,turns=128,labels=16,label_chars=64)
        if any(type(value)is not int or not 0<value<=hard[key]for key,value in asdict(self).items()):
            raise ValueError('positive bounded integer view limits required')
        if not self.evidence_bytes<=self.input_bytes<=self.row_bytes or min(self.turns,self.labels)<2:
            raise ValueError('view byte/turn/label limits are inconsistent')


@dataclass(frozen=True)
class DialogueView:
    dialogue:str
    visible_labels:tuple
    turns:int
    _trace_json:str

    @property
    def trace(self):return json.loads(self._trace_json)

    def as_reference(self):
        return dict(schema=SCHEMA,kind='QUOTED_SOURCE_RELATIVE_DIALOGUE',text=self.dialogue,trace=self.trace)


def input_dialogue_view(row,*,limits=None):
    limits=ViewLimits()if limits is None else limits
    if not isinstance(limits,ViewLimits)or not isinstance(row,dict)or set(row)!=FIELDS:
        raise ValueError('exact flat row and explicit view limits required')
    if(type(row['id'])is not int or not 0<row['id']<2**63 or type(row['template_id'])is not int
            or any(row.get(key)!=value for key,value in PROFILE.items())):
        raise ValueError('unsupported SODA named-input profile')
    if(any(type(row[key])is not str for key in FIELDS-{'id','template_id'})
            or not row['inputs']or not row['targets']
            or len(row['inputs'])>limits.input_bytes or len(row['targets'])>limits.row_bytes):
        raise ValueError('bounded literal source strings required')
    text=row['inputs'];encoded=text.encode('utf-8')
    if len(encoded)>limits.input_bytes or '\r'in text:
        raise ValueError('bounded LF input profile required')
    raw_row=_canonical(row).encode('utf-8')
    if len(raw_row)>limits.row_bytes:
        raise ValueError('serialized source row byte budget exceeded')
    if not text.endswith(BOUNDARY)or text.count(SUFFIX)!=1:
        raise ValueError('one exact final management suffix required')
    stop=len(text)-len(BOUNDARY);dialogue=text[:stop]
    raw=dialogue.encode('utf-8')
    if not raw or len(raw)>limits.evidence_bytes:
        raise ValueError('bounded nonempty dialogue prefix required')
    blocks=dialogue.split('\n\n')
    if not 2<=len(blocks)<=limits.turns:
        raise ValueError('qualified visible turn count required')
    labels=[]
    for block in blocks:
        name,separator,content=block.partition(': ')
        if(not separator or name!=name.strip()or not LABEL.fullmatch(name)or len(name)>limits.label_chars
                or name.casefold()in RESERVED or not content.strip()or '\n'in block):
            raise ValueError('qualified single-line visible label/utterance required')
        if name not in labels:labels.append(name)
    if not 2<=len(labels)<=limits.labels:
        raise ValueError('at least two bounded distinct visible labels required')
    trace=dict(schema=SCHEMA,view_scope='INPUT_PREFIX_ONLY_NOT_COMPLETE_ORIGINAL_MESSAGE',
        source_raw_row_sha256=_sha(raw_row),source_input_sha256=_sha(encoded),
        source_row_id=row['id'],original_source_split=row['split'],source_role='user',
        input_char_range=[0,stop],input_utf8_byte_range=[0,len(raw)],evidence_sha256=_sha(raw),
        excluded_original_target_from_evidence=True,visible_labels=labels,visible_turns=len(blocks),
        label_scope='LEXICAL_VISIBLE_LABELS_NOT_ORIGINAL_SPEAKER_ARRAY',
        source_relative_fiction_only=True,source_file_verified_by_this_function=False,
        original_root_joined=False,corpus_admitted=False,token_budget='NOT_COUNTED',limits=asdict(limits))
    return DialogueView(dialogue,tuple(labels),len(blocks),_canonical(trace))
