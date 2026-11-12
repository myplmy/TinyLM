"""Prove typed repeated choices or redundant nonnumeric category tags."""
from collections import Counter,defaultdict
import hashlib
import re
from scripts import p106b_hold_resolution_policy_v31 as baseline
from scripts import p106b_hold_resolution_metadata_v4 as metadata
from scripts.p106b_hold_resolution_repeat_context_v1 import UI,QUOTED_CONTEXT

QUESTION=re.compile(r'(?P<number>[1-9][0-9]*)[.)][ \t]+(?P<text>\S.{12,}[?:])')
OPTION=re.compile(r'-[ \t]+(?P<text>\S.{3,220})')
ANSWER=re.compile(r'(?i:answers)[ \t]*:[ \t]*(?P<values>.+)')
EXTRA_CONTENT_HEADS={'운항노선','화물노선','갤러리','작품연보','기후','사진','방송일자'}


def sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest().upper()


def repeats(text):
    rows=defaultdict(list)
    for number,line in enumerate(baseline.plain_text(text).splitlines(),1):
        value=line.strip()
        if len(value)>=6 and baseline.v1.normalize_heading(value) not in baseline.v1.LABELS:
            rows[value].append(number)
    return {line:places for line,places in rows.items() if len(places)>1}


def has_content_stub(text):
    if metadata.empty_content_headings(text):
        return True
    return any(re.sub(r'\s+','',block.strip()) in EXTRA_CONTENT_HEADS
               for block in re.split(r'\n\s*\n',text))


def choice_proof(text,repeated):
    lines=[(n,value.strip()) for n,value in enumerate(text.splitlines(),1) if value.strip()]
    first=next((i for i,(_n,value) in enumerate(lines) if QUESTION.fullmatch(value)),None)
    if first is None or first==0:
        return None
    introduction=' '.join(value for _n,value in lines[:first])
    if len(introduction)>2000 or not re.search(r'[.!?]$',introduction):
        return None
    position=first
    questions=[]
    roles={}
    while position<len(lines):
        line_number,value=lines[position]
        match=QUESTION.fullmatch(value)
        if match is None or int(match['number'])!=len(questions)+1:
            break
        if position+4>=len(lines):
            return None
        options=[]
        for offset in range(1,5):
            option_line,option_text=lines[position+offset]
            option=OPTION.fullmatch(option_text)
            if option is None:
                return None
            options.append(option['text'])
            roles[option_line]=dict(question=int(match['number']),option=offset)
        if len(set(options))!=4:
            return None
        questions.append(dict(number=int(match['number']),question_sha256=sha(match['text']),
            source_line=line_number,option_sha256=[sha(value) for value in options]))
        position+=5
    if len(questions)<2 or position!=len(lines)-1:
        return None
    if len({row['question_sha256'] for row in questions})!=len(questions):
        return None
    answer=ANSWER.fullmatch(lines[position][1])
    if answer is None:
        return None
    pairs=re.findall(r'([1-9][0-9]*)[.)][ \t]*([A-D])',answer['values'])
    residue=re.sub(r'[1-9][0-9]*[.)][ \t]*[A-D]','',answer['values'])
    if residue.strip(' ,;\t') or [int(n) for n,_letter in pairs]!=list(range(1,len(questions)+1)):
        return None
    records=[]
    for value,places in repeated.items():
        if any(number not in roles for number in places):
            return None
        contexts=[dict(source_line=number,**roles[number]) for number in places]
        if len({item['question'] for item in contexts})!=len(contexts):
            return None
        records.append(dict(line_sha256=sha(value),role='CHOICE_IN_DIFFERENT_EXPLICIT_NUMBERED_QUESTION',contexts=contexts))
    return dict(candidate=text,changes=[],proof=dict(kind='COMPLETE_NUMBERED_FOUR_CHOICE_QUESTIONS',
        questions=questions,answer_keys=pairs,repeated_records=records,
        all_repeated_occurrences_typed=True,question_or_answer_factual_accuracy_claimed=False))


def metadata_proof(text,repeated):
    boundary=metadata.prove(text)
    if boundary is None:
        return None
    last=boundary['metadata_original']
    start=text.rfind(last)
    prefix=text[:start]
    prefix_lines={line.strip() for line in baseline.plain_text(prefix).splitlines()}
    values=[line.strip() for line in last.splitlines() if line.strip()]
    if any(value in prefix_lines or value not in values or re.search(r'\d',value) for value in repeated):
        return None
    counts=Counter(values)
    if any(counts[value]!=len(places) for value,places in repeated.items()):
        return None
    seen=set();kept=[];removed=[]
    for line in last.splitlines(keepends=True):
        value=line.strip()
        if value in repeated and value in seen:
            removed.append(value)
        else:
            kept.append(line)
        seen.add(value)
    if not removed:
        return None
    clean=boundary['candidate']
    assert clean.count(last)==1
    clean=clean.replace(last,''.join(kept),1)
    return dict(candidate=clean,changes=boundary['changes']+[dict(
        reason='EXACT_REDUNDANT_NONNUMERIC_TAG_IN_PROVED_METADATA_BLOCK',removed=removed,
        retained_first_occurrence=True,numeric_tags_deleted=0)],proof=dict(
        kind='REPEATED_NONNUMERIC_TAGS_ONLY_IN_PROVED_LITERAL_METADATA',
        metadata_boundary=boundary['proof'],removed=removed,metadata_sha256=sha(last),
        repeated_records=[dict(line_sha256=sha(value),source_lines=places,
                              retained_source_line=places[0],removed_source_lines=places[1:])
                          for value,places in repeated.items()],
        all_repeated_occurrences_typed=True,numeric_tags_deleted=0))


def prove(text):
    repeated=repeats(text)
    if not repeated or UI.search(text) or QUOTED_CONTEXT.search(text) or has_content_stub(text):
        return None
    if metadata.FORMAL_GAP.search(baseline.plain_text(text)):
        return None
    return choice_proof(text,repeated) or metadata_proof(text,repeated)
