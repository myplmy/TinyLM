"""Prove literal category tails from independent typed anchors, without value edits."""
import hashlib
import re
from scripts import p106b_hold_resolution_policy_v30 as baseline
from scripts.p106b_hold_resolution_metadata_v3 import FORMAL_GAP

CONTENT_HEADS = {baseline.v1.normalize_heading(v) for v in [
    '수상자','수상 목록','수상 내역','방영 목록','방송 목록','실험 결과','기록','출연',
    '등장인물','주제가','트랙 목록','목록','교육 기관','전투서열','전투 서열','역대 사령관',
    '사령관','연혁','역사','인구','행정 구역','역대 선거 결과','메달 집계','보유 항공기',
    '운행 차량','선수 명단','역대 선수','역대 감독','발매 목록','음반 목록']}
SECTION_HEADS = CONTENT_HEADS | {baseline.v1.normalize_heading(v) for v in [
    '교통','철도','도로','지리','개요','소개','같이 보기','외부 링크','각주','참고 문헌']}
FORBIDDEN = re.compile(r'[.!?。《》\[\]<>`{}=\"\'‘’“”]')
NAMED = re.compile(r'\A\s*(?P<name>[^\n]{2,160}?)(?:은|는|란|이란)\s+')
DEICTIC = re.compile(r'(?:이|그|해당|본)\s*(?:학교|대학|회사|기업|단체|기관|문서|문장|사람|것)')
LIFE_BIRTH = re.compile(r'[12][0-9]{2,3}(?:년대|년)[ _]+출생')
LIFE_END = re.compile(r'[12][0-9]{2,3}년[ _]+사망|살아있는[ _]+사람')


def empty_content_headings(text):
    """Conservative metadata flags, never deletion or a general parser claim."""
    blocks = [m for m in baseline.BLOCK.finditer(text) if m[0].strip()]
    findings = []
    for n, block in enumerate(blocks):
        values = [v.strip() for v in block[0].splitlines() if v.strip()]
        labels = [baseline.v1.normalize_heading(v) for v in values]
        if not labels or not all(v in CONTENT_HEADS for v in labels):
            continue
        if n+1 == len(blocks):
            findings.extend(values)
            continue
        after = [v.strip() for v in blocks[n+1][0].splitlines() if v.strip()]
        after_labels = [baseline.v1.normalize_heading(v) for v in after]
        next_is_heading = all(v in SECTION_HEADS for v in after_labels)
        next_is_metadata = bool(after and any(baseline.YEAR.fullmatch(v) for v in after)
            and any(baseline.CATEGORY.fullmatch(v) or re.fullmatch(r'.+의[ _]+[^.!?]+',v) for v in after)
            and all(len(v)<=100 and not FORBIDDEN.search(v) for v in after))
        if next_is_heading or next_is_metadata:
            findings.extend(values)
    return findings


def prove(text):
    if FORMAL_GAP.search(baseline.plain_text(text)) or empty_content_headings(text):
        return None
    introductory = baseline.intro(text)
    if introductory is None or text.lstrip().startswith(('"', "'", '‘', '“', '>')):
        return None
    named = NAMED.match(introductory)
    if named is None or DEICTIC.fullmatch(named['name'].strip()):
        return None
    blocks = [m for m in baseline.BLOCK.finditer(text) if m[0].strip()]
    if len(blocks)<2:
        return None
    last = blocks[-1]
    values = [v.strip() for v in last[0].splitlines() if v.strip()]
    if len(values)<2 or any(len(v)>100 or not re.search(r'[가-힣]',v) or FORBIDDEN.search(v) for v in values):
        return None
    categories = sorted({v for v in values if baseline.CATEGORY.fullmatch(v)})
    years = [v for v in values if baseline.YEAR.fullmatch(v)]
    life_pair = any(LIFE_BIRTH.fullmatch(v) for v in years) and any(LIFE_END.fullmatch(v) for v in years)
    if not (len(categories)>=2 or (life_pair and categories)):
        return None
    if baseline.QUOTE_CONTEXT.search(text[max(0,last.start()-400):last.start()]):
        return None
    if not re.fullmatch(r'[ \t\r\n]+',text[blocks[-2].end():last.start()]):
        return None
    removed = []
    for block in reversed(blocks[:-1]):
        labels = [baseline.v1.normalize_heading(v) for v in block[0].splitlines() if v.strip()]
        if not labels or any(v not in baseline.v4.STRIPPABLE_APPENDICES for v in labels):
            break
        removed.append(block)
    clean,changes = text,[]
    for block in removed:
        clean=clean[:block.start()]+clean[block.end():]
        changes.append(dict(reason='ISOLATED_EMPTY_FOOTER_BEFORE_MULTIPLE_TYPED_LITERAL_CATEGORY_ANCHORS',
            original=block[0],prepared_candidate_characters=[block.start(),block.end()],metadata_values_deleted=0))
    assert last[0] in clean
    return dict(candidate=clean,changes=changes,metadata_original=last[0],proof=dict(
        kind='NAMED_INTRO_MULTIPLE_TYPED_LITERAL_CATEGORY_ANCHORS',source_name=named['name'].strip(),
        typed_category_anchors=categories,literal_year_markers=years,literal_values=values,
        metadata_sha256=hashlib.sha256(last[0].encode()).hexdigest().upper(),
        values_deleted_or_reordered=0,existing_populated_references_preserved=True))
