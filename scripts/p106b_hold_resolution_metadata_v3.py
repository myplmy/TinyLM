"""Prove a separate literal metadata suffix using explicit start/end event dates."""
import hashlib
import re
from scripts import p106b_hold_resolution_policy_v28 as baseline

EVENT = re.compile(r'(?P<year>[12][0-9]{3})년[ _]+(?P<kind>설립|설치|폐지|해체)')
NAMED = re.compile(r'\A[ \t]*(?P<name>[^\n.!?(){}|<>]{2,100}?)(?:\([^()\n]*\))?[ \t]*(?:은|는|란|이란)[ \t]+')
FORBIDDEN = re.compile(r'[.!?。《》\[\]<>`{}=\"\'‘’“”]')
CATEGORY_END = re.compile(r'(?:학교|대학교|단체|정당|공화국|군|노총|노동조합|건축물|방송국|구단|팀|시설|철도|노선|왕조|대성당|교회당)$')
FORMAL_GAP = re.compile(r'(?:함수|군|공간|벡터|상수|변수|집합)[ \t]+(?:은|는|을|를|에|의)[ \t]+')


def prove(text):
    # A new metadata proof cannot silently clear an observed missing-symbol
    # phrase even when the older general scanner did not recognize it.
    if FORMAL_GAP.search(baseline.plain_text(text)):
        return None
    if baseline.separate_metadata_suffix(text)[2]:
        return None
    introductory = baseline.intro(text)
    if introductory is None or text.lstrip().startswith(('"', "'", '‘', '“', '>')):
        return None
    named = NAMED.match(introductory)
    if (named is None or not re.search(r'[가-힣A-Za-z]', named['name'])
            or re.match(r'[0-9]', named['name'].strip())
            or named['name'].strip() in {'이 학교', '이 대학', '이 단체', '본 단체'}):
        return None
    blocks = [m for m in baseline.BLOCK.finditer(text) if m[0].strip()]
    if len(blocks) < 2:
        return None
    last = blocks[-1]
    values = [line.strip() for line in last[0].splitlines() if line.strip()]
    if (len(values) < 3 or any(len(v) > 100 or not re.search(r'[가-힣]',v)
                              or FORBIDDEN.search(v) for v in values)):
        return None
    events = [(v, EVENT.fullmatch(v)) for v in values]
    starts = [int(m['year']) for _,m in events if m and m['kind'] in {'설립','설치'}]
    ends = [int(m['year']) for _,m in events if m and m['kind'] in {'폐지','해체'}]
    if not starts or not ends or max(starts) > min(ends):
        return None
    if not any(not EVENT.fullmatch(v) and (baseline.CATEGORY.fullmatch(v) or CATEGORY_END.search(v)) for v in values):
        return None
    if any(baseline.v1.normalize_heading(v) in baseline.v1.LABELS for v in values):
        return None
    if not re.fullmatch(r'[ \t\r\n]+', text[blocks[-2].end():last.start()]):
        return None
    if baseline.QUOTE_CONTEXT.search(text[max(0,last.start()-400):last.start()]):
        return None
    removable = baseline.v4.STRIPPABLE_APPENDICES
    unresolved_content_heads = {baseline.v1.normalize_heading(v) for v in
        ['수상자', '수상 목록', '방영 목록', '실험 결과', '기록', '출연', '등장인물', '주제가', '트랙 목록', '목록']}
    removed = []
    for block in reversed(blocks[:-1]):
        labels = [baseline.v1.normalize_heading(line) for line in block[0].splitlines() if line.strip()]
        if not labels or any(label not in removable for label in labels):
            if labels and all(label in unresolved_content_heads for label in labels):
                return None
            break
        removed.append(block)
    # This extension only edits actual isolated empty footers. It does not
    # release unchanged bodies merely because a date pair can be recognized.
    if not removed:
        return None
    clean, changes = text, []
    for block in removed:
        clean = clean[:block.start()] + clean[block.end():]
        changes.append(dict(reason='ISOLATED_EMPTY_FOOTER_BEFORE_EXPLICIT_START_END_EVENT_METADATA',
                            original=block[0], prepared_candidate_characters=[block.start(),block.end()],
                            metadata_values_deleted=0))
    assert last[0] in clean
    return dict(candidate=clean, changes=changes, metadata_original=last[0],
                proof=dict(kind='NAMED_INTRO_AND_LITERAL_START_END_EVENT_PAIR',
                           source_name=named['name'], literal_values=values,
                           events=[dict(literal=v,year=int(m['year']),kind=m['kind']) for v,m in events if m],
                           metadata_sha256=hashlib.sha256(last[0].encode()).hexdigest().upper(),
                           values_deleted_or_reordered=0))
