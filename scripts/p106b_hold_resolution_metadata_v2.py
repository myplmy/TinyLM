"""Extend an existing metadata boundary proof only for typed ordinal categories."""
import hashlib
import re
from scripts import p106b_hold_resolution_policy_v25 as baseline

ORDINAL_FOOTBALL = re.compile(r"[1-9][0-9]?[.][ \t]+[^.!?。\r\n]{1,90}의[ _]+축구[ _]+선수")
FORBIDDEN = re.compile(r"[!?。《》\[\]<>`{}=\"'‘’“”]")
LIFE_BIRTH = re.compile(r"[12][0-9]{2,3}(?:년대|년)[ _]+출생")
LIFE_END = re.compile(r"[12][0-9]{2,3}년[ _]+사망|살아있는[ _]+사람")


def typed_ordinal_category(value):
    return (value.count('.') == 1 and ORDINAL_FOOTBALL.fullmatch(value) is not None
            and baseline.CATEGORY.fullmatch(value) is not None)


def prove(text):
    """Return a literal proof and candidate, never an admission decision."""
    if baseline.separate_metadata_suffix(text)[2] or baseline.intro(text) is None:
        return None
    if text.lstrip().startswith(('"', "'", '‘', '“', '>')):
        return None
    blocks = [match for match in baseline.BLOCK.finditer(text) if match[0].strip()]
    if len(blocks) < 2:
        return None
    last = blocks[-1]
    values = [line.strip() for line in last[0].splitlines() if line.strip()]
    if len(values) < 2 or any(len(v) > 100 or not re.search(r'[가-힣]', v) or FORBIDDEN.search(v) for v in values):
        return None
    dotted = [v for v in values if '.' in v]
    if not dotted or not all(typed_ordinal_category(v) for v in dotted):
        return None
    years = [v for v in values if baseline.YEAR.fullmatch(v)]
    categories = [v for v in values if baseline.CATEGORY.fullmatch(v)]
    life_pair = any(LIFE_BIRTH.fullmatch(v) for v in years) and any(LIFE_END.fullmatch(v) for v in years)
    if not life_pair and not (years and len(categories) >= 2):
        return None
    if not re.fullmatch(r'[ \t\r\n]+', text[blocks[-2].end():last.start()]):
        return None
    if baseline.QUOTE_CONTEXT.search(text[max(0, last.start() - 400):last.start()]):
        return None
    removable = baseline.v4.STRIPPABLE_APPENDICES | baseline.v17.EMPTY_LEAF_LABELS
    removed = []
    for block in reversed(blocks[:-1]):
        labels = [baseline.v1.normalize_heading(v) for v in block[0].splitlines() if v.strip()]
        if not labels or any(label not in removable for label in labels):
            break
        removed.append(block)
    clean, changes = text, []
    for block in removed:
        clean = clean[:block.start()] + clean[block.end():]
        changes.append(dict(reason='EMPTY_FOOTER_BEFORE_PROVEN_TYPED_ORDINAL_FOOTBALL_METADATA',
            original=block[0], prepared_candidate_characters=[block.start(), block.end()],
            metadata_values_deleted=0))
    if last[0] not in clean:
        raise ValueError('literal metadata block changed')
    return dict(candidate=clean, changes=changes, metadata_original=last[0],
        proof=dict(kind='EXPLICIT_YEAR_OR_LIFE_PAIR_WITH_TYPED_ORDINAL_FOOTBALL_CATEGORIES',
            dotted_category_values=dotted, literal_values=values,
            input_text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest().upper(),
            literal_metadata_sha256=hashlib.sha256(last[0].encode('utf-8')).hexdigest().upper(),
            values_deleted_or_reordered=0))
