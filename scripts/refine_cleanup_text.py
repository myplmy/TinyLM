#!/usr/bin/env python3
"""Refine the saved TinyLM text using verified boundaries from the previous pass."""

import json
import mmap
import os
import re
import struct
import sys
import zlib
from base64 import b64decode, b64encode
from collections import Counter
from datetime import datetime
from hashlib import blake2b, sha256
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, 'scripts')
from next_cleanup_batch import (BREAK, CONTEXT_MARKUP, DOCUMENT_POSITION, INTRO_LIFE_DATES,
                                Document, empty_footer, format_category_footer, lock,
                                normalize_heading, stamp)

base=Path('data_cache')
v1=base/'20261120_정제데이터셋v1.txt'
work=base/'p106b_hold_resolution_v1_20261027_goalc'
audit=Path('handoff/audit/hold_resolution_20261027_goalc')
guard_path=audit/'GUARDED_SOURCE_METADATA_CONTRACT_V6.json'
guard=json.loads(guard_path.read_bytes())
restricted=set(guard['restricted_ids'])|set(guard['trusted_metadata'])
part=base/'.20261120_정제데이터셋v1.1.txt.part'
meta=base/'20261120_정제데이터셋v1.1.txt.work'
result=base/'20261120_정제데이터셋v1.1.txt'
position=struct.Struct('<III')
slot_bytes=4096
reserved=2*slot_bytes
cleanup_timezone=ZoneInfo('Asia/Seoul')
deadline=datetime.fromisoformat(os.environ.get('TINYLM_CLEANUP_DEADLINE','2026-11-20T17:00:00+09:00'))
if deadline.tzinfo is None:
    deadline=deadline.replace(tzinfo=cleanup_timezone)
deadline=deadline.astimezone(cleanup_timezone)
scope=json.loads((work/'scope.json').read_bytes())
starts={}
offset=0
for row in scope['inputs']:
    starts[row['name']]=offset
    offset+=row['intervals']
def ordinal(ident):
    source,index=ident.split(':')
    return starts[source]+int(index)+1


def legacy_receipts():
    with (work/'hold_first_pass.txt.work').open('rb') as fp:
        rows = (json.loads(line) for line in fp if line.startswith(b'{"type":"legacy_'))
        return {row['type']: row for row in rows}

LABELS = {
    '각주': 'note', '내용주': 'note', '참조주': 'note', 'footnotes': 'note',
    '참고 문헌': 'references', '참고문헌': 'references', 'references': 'references',
    'bibliography': 'references', '외부 링크': 'links', '외부링크': 'links',
    '외부 자료': 'materials', '외부자료': 'materials', 'external links': 'links',
    '분류': 'categories', 'categories': 'categories', '같이 보기': 'see_also',
    'see also': 'see_also', '인접역': 'adjacent_station', '인접한 역': 'adjacent_station',
    '관련 사이트': 'links', '관련사이트': 'links', '참고 자료': 'references',
    '참고자료': 'references', '주해와 각주': 'note', '주석': 'note', '사진': 'photo',
}
LABEL_BYTES = re.compile(
    rb'(?im)^[ \t]*(?:={2,6}[ \t]*)?(?:' +
    b'|'.join(re.escape(k.encode()) for k in LABELS) +
    rb')(?:[ \t]*={2,6})?[ \t]*\r?$'
)
LIFE_MARKERS = tuple(value.encode() for value in ('년 출생','년 사망','년_출생','년_사망'))
LIFE_ALIAS_PREFIX = re.compile(rb'\A[ \t]*[^()\r\n]{2,210}\([ \t]*(?:,|\xef\xbc\x8c)[ \t]*[12][0-9]{3}')
LIFE_ALIAS_GAP = re.compile(r'\A[ \t]*[^()\r\n]{2,100}\((?P<empty>[ \t]*[,，][ \t]*)(?=[12][0-9]{3}년)')
INLINE_EMPTY = re.compile(r'<ref[ \t]*/>|<ref[ \t]*>[ \t]*</ref[ \t]*>', re.I)
ORPHAN_REF_CLOSE = re.compile(r'(?<=[.!?。])[ \t]*</ref[ \t]*>',re.I)
NAV_LINK = re.compile(
    r'(?:https?://[^\s<>"\']+|'
    r'공식 (?:웹사이트|홈페이지|사이트)(?:\s*[-–—:]\s*[\w .·\-]{1,65})?|'
    r'official (?:web\s*site|home\s*page)(?:\s*[-–—:]\s*[\w .·\-]{1,65})?|'
    r'위키미디어 공용)\.?', re.I
)
FOOTNOTE = re.compile(r'^\[(\d{1,3})\][ \t]+(.{6,450})$')
RELEASE_STUB = re.compile(
    r'\A(?P<lead>《[^》\n]{1,150}》[은는][ \t][^\n]{20,330})\n'
    r'(?:[ \t]*\n){1,6}각주[ \t]*\n(?:[ \t]*\n){1,4}'
    r'(?P<year>[12][0-9]{3})년 (?P<kind>EP|싱글|음반)[ \t]*(?:\n[ \t]*)*\Z'
)
WEB_SKIP = re.compile(
    rb'\A[ \t]*Skip to (?:main )?content[ \t]*\r?\n'
    rb'(?:[ \t]*Skip to navigation menu[ \t]*\r?\n)?',re.I
)
WEB_REPLY = re.compile(
    rb'\n[ \t]*Leave a Reply[.!]?[ \t]*\r?\n(?:[ \t]*\r?\n){0,3}'
    rb'[ \t]*You must be logged in to post a comment\.?[ \t]*(?:\r?\n[ \t]*)*\Z',re.I
)
WEB_COMMENT_END = re.compile(
    rb'\n[ \t]*Leave a (?:Reply|Comment(?: on this page| below)?)[.!]?[ \t]*'
    rb'(?:\r?\n[ \t]*)+\Z',re.I
)
CATHOLIC_PROMOTION = b'The Catholic Encyclopedia is the most comprehensive resource on Catholic teaching'
CATHOLIC_PROMOTION_BYTES = 1469
CATHOLIC_PROMOTION_SHA = '7b249765fbf4d210d53dc0d398ed5e6be2bcdabb6d2d987dc2b88fa98c469a17'
CATHOLIC_CREDIT = 'Copyright © Catholic Encyclopedia.'.encode()
WEB_FOOTER_BLOCKS = (
    (430,b"Subscribe now to read the rest of thi",bytes.fromhex('cb1b6ef3cba674fd9fbdcbfb565b58bf')),
    (287,b"Subscribe to Practical Homeschooling ",bytes.fromhex('f884afd6cf262ed62e52ce4c82faa8c9')),
    (710,b"Sign up for our free newsletter and w",bytes.fromhex('f7bf99697856c93b55dc2d7be0ed4850')),
    (469,b"Log in with your social accounts:",bytes.fromhex('09341eb8b176eadb5eee9e1564b2718b')),
    (307,b"Log in using your username and passwo",bytes.fromhex('724d1b04be2198e8bd06614fac51d3cf')),
    (426,b"Subscribe to free FactDr newsletters.",bytes.fromhex('5a71adf26864f33a44392c2ca7daef69')),
    (544,b"Sign up with Google",bytes.fromhex('e7dfd1494d806008c913b8191abea90c')),
    (1131,b"Newsletter [Click here]",bytes.fromhex('2778dbf8fc65baacff355078ba3781cb')),
    (895,b"Sign up for daily news updates from C",bytes.fromhex('1d188dbf4b98bd92820ea5f57acec41c')),
    (315,b"MORE FROM SPIEGEL INTERNATIONAL",bytes.fromhex('db0ad1c8522c75350a6c7d143b6a8b4f')),
)
HTML_LINK = re.compile(
    rb'''<a[ \t]+href=(?P<quote>["'])https?://[^\s"'<>]+(?P=quote)'''
    rb'''(?:[ \t]+(?:target|rel|class|title)=(?P<attr_quote>["'])[^"'<>\r\n]*(?P=attr_quote))*[ \t]*>'''
    rb'''(?P<visible>[^<>\r\n]{2,500})</a[ \t]*>''',re.I
)
HTML_LINK_EXAMPLE = re.compile(
    r'HTML[^\r\n]{0,45}(?:태그|요소|속성|마크업|tag|element|attribute|markup)|'
    r'(?:anchor tag|링크 태그|코드 예제|태그 사용법)',re.I
)
CITATION_FORM = re.compile(r'[《『][^》』\n]+[》』]|ISBN\b|doi\.org/|\b[A-Z][a-z]+ University Press\b')
SHORT_PAGE_CITATION = re.compile(
    r"[A-Z][A-Za-z.'’ -]{1,85}[ \t]+(?:\([12][0-9]{3}\)|[12][0-9]{3})[ \t]*[:;,][ \t]*"
    r'(?:pp?\.?[ \t]*)?[0-9]{1,5}(?:[-–][0-9]{1,5})?\.?'
)
SHORT_CATEGORY = re.compile(r'[\w가-힣][\w가-힣 .&·()’/–-]{1,86}')
CATEGORY_YEAR = re.compile(
    r'(?:[0-9]{1,4}(?:년대|년|세기) (?:출생|사망|설립|개교|개업(?:한 철도역)?|설치|'
    r'폐지|폐교|신설|개관|개항|개통|완공(?:된 (?:건축물|스포츠 시설))?|(?:한국 )?사람)|생년 미상|'
    r'몰년 미상|생몰년 미상|살아[ ]?있는 사람)'
)
CATEGORY_ROLE = re.compile(
    r'(?:[\w·() ]{2,62}(?: 출신| 동문|의 회원|상 수상자| 메달 수상자|'
    r' 합격자| 역|의 (?:도시|학교|철도역|전철역|지하철역|전문대학|'
    r'(?:(?:공립|사립|일반계) )?(?:고등학교|중학교|초등학교)))|'
    r'(?:일반계|공립|사립) (?:고등학교|중학교|초등학교))'
)
TYPED_CATEGORY_YEAR = re.compile(
    r'([0-9]{4})년 (개통한 철도 노선|설립된 기업|개교한 학교|결성된 음악 그룹)'
)
SPORTS_CATEGORY = re.compile(
    r'[0-9]{4}년 (?:(?:하계|동계) 올림픽|아시안 게임)(?: [가-힣 ]{2,24})? (?:참가 선수|메달리스트)'
)
TYPED_EVENT = {
    '개통한 철도 노선': ('철도 노선','개통'), '설립된 기업': ('기업','설립'),
    '개교한 학교': ('학교','개교'), '결성된 음악 그룹': ('그룹','결성'),
}
OFFICIAL_LABEL = re.compile(
    r'[가-힣A-Za-z][가-힣A-Za-z0-9 .·()\-]{1,56}(?:\s+\(공식\)| 공식\s*(?:웹사이트|홈페이지|사이트))'
)
FOOTER_LABELS = {'note', 'references', 'links', 'materials', 'see_also'}
NAV_TITLE = re.compile(
    r'(?:공식|프로필|홈페이지|웹사이트|공용|인터넷 영화 데이터베이스|'
    r'(?:기록|정보) (?:보기|페이지)|(?:official|homepage|website|profile|IMDb|Wikimedia)\b)', re.I
)
PLAIN_PREDICATE = re.compile(r'(?:이다|였다|했다|된다|되었다|있다|없다|한다|않다|같다|라고 한다)[.!?。]?$')
TOPIC_NAME = re.compile(r'\A[ \t]*([가-힣][가-힣A-Za-z0-9 ·ㆍ「」《》\-]{1,54}?)(?=\(|[은는][ \t])')
PERSON_FACT = re.compile(
    r'(?:과학자|물리학자|화학자|수학자|생물학자|천문학자|철학자|화가|배우|가수|시인|작가|작곡가|'
    r'연주자|선수|감독|교수|정치인|목회자|저술가|국왕|군주|기업인|의사|전문의|'
    r'법조인|대법관|판사|변호사|건축가)'
)
PERSON_CATEGORY = re.compile(
    r'(?:[가-힣A-Za-z· \-]{2,35}의 )?(?:(?:영화|텔레비전|야구|축구|농구|배구|수영|테니스|'
    r'육상|피아노|바이올린|남자|여자) )?' + PERSON_FACT.pattern
)
PLACE_CATEGORY = re.compile(
    r'[가-힣A-Za-z· \-]{2,45}의 (?:섬|해협|반도|하천|산|산맥|행정 구역|교량|항만|기차역|공항|'
    r'공원|경기장|도서관|미술관|박물관|기념물|건축물)'
)
NOUN_CATEGORY = re.compile(
    r'[가-힣A-Za-z0-9][가-힣A-Za-z0-9 ·–-]{1,52}의 '
    r'[가-힣 ·]{1,32}(?:역|버스|터미널|교통|지리|역사|반도|도시|시|군|구|섬|도서관|박물관|'
    r'문화유산|정치|문화|음악|미술|작품|축구|선수|교수|학자|인물|민족|계통|종교|소설|산맥|공원|채널)'
)
LINK_TITLE_FORM = re.compile(r'''[\w가-힣][\w가-힣 '&’"“”·:/()「」《》,[\]_–—.!\-+]{1,116}''')
LINK_SOURCE_CUE = re.compile(
    r'(?:[0-9]{4}(?:년|[./-][0-9])|(?:pp?|vol|No|권|쪽|ISBN|DOI)[. ]+[0-9]|'
    r'[.?!。][ \t]|[ ](?:출간|논문|조사|보도|인용|발행|발표|폐지|개업|설립|개교))', re.I
)
NAMED_LINK_SOURCE = re.compile(
    r'^(?:[\w가-힣 .·]{2,34}(?:신문|일보|학회|출판사|대학교 출판부|Journal|Press)\s*[-–—:]\s*\S'
    r'|.*(?:저서[ \t]+[《『]|history of the editions of )).{0,140}$',re.I
)
PROFILE_LINK_LABELS = {'홈페이지','공식 홈페이지','공식 웹사이트','미니홈피 - 싸이월드','네이트 인물검색'}
FILM_LEAD = re.compile(r'^[ \t]*[《"“]([^》"”\n]{2,100})[》"”](?:\([^()\n]{0,85}\))?'
                       r'[은는][ \t]+[^.\n]{2,230}영화(?:이|다|로)')
FILM_LINK = re.compile(r'(.{2,117}?) - (다음영화|무비스트|KMDb|IMDb|씨네21|한국영화 ?데이터베이스|네이버 영화)')
INLINE_CITATION = re.compile(r'([.!?。])([ \t]*)<ref>([^<>\r\n]{12,415})</ref[ \t]*>', re.I)
WIKI_CATEGORY_LINE = re.compile(r'[ \t]*\[\[(?:분류|Category):[ \t]*([^\][|\r\n]{2,85})(?:\|[^\][\r\n]{0,85})?\]\][ \t]*',re.I)
WIKI_CATEGORY_LITERAL = re.compile(r'마크업|위키텍스트|문법|코드[ \t]*예제|태그[ \t]*사용법|namespace|wikitext')
OTHER_CATEGORY = re.compile(
    r'(?:[0-9]{3,4}년 (?:알파인 스키|프리스타일스키|(?:(?:동계|하계) )?올림픽[^.!?]{1,25}|'
    r'기재된[ ]+[가-힣]{2,15})|[가-힣 .·]{2,50} (?:선수단|분류군|폐교된 (?:초등학교|중학교|고등학교))|'
    r'[가-힣A-Za-z ·-]{3,45}의 [가-힣 ·]{2,25})'
)
QUOTED_BIBLIOGRAPHY = re.compile(
    r'(?P<author>[가-힣A-Za-z][가-힣A-Za-z .,\-·]{1,65}?)'
    r'(?:[ ,]*\([0-9]{4}[^()]{0,14}\)[., ]*|[, ]+)'
    r'[《「『“"](?P<title>[^》」』”"\n]{6,120})[》」』”"](?P<record>[.\s,].{3,230})'
)
TITLED_CITATION = re.compile(r'논문|저서|출처|인용|출판|간행|기록|자료|수록|(?:journal|cited|published|wrote)\b', re.I)
EXPLICIT_YEAR = re.compile(r'([0-9]{3,4})년 (설립|설치|개교|폐교|개관|개업(?:한 철도역)?|출생|사망|폐지|완공)')
YEAR_PARTICLE = {
    '설립': '설립되었다', '설치': '설치되었다', '개교': '문을 열었다',
    '개관': '문을 열었다', '개업': '영업을 시작했다', '개업한 철도역': '영업을 시작했다',
    '폐지': '폐지되었다', '폐교': '폐교되었다', '완공': '완공되었다',
}
YEAR_EVIDENCE = {
    '설립': r'설립|창립', '설치': r'설치|(?:시|군|구)(?:로|로의)?[ \t]*승격',
    '개교': r'개교|문을 열', '개관': r'개관|문을 열', '개업': r'개업|영업 개시|영업을 시작',
    '개업한 철도역': r'개업|영업 개시|영업을 시작', '폐지': r'폐지', '폐교': r'폐교', '완공': r'완공|준공',
    '출생': r'출생|태어났', '사망': r'사망|별세|타계|죽었',
}


def topic_particle(name):
    last = ord(name[-1])
    return '은' if 0xAC00 <= last <= 0xD7A3 and (last-0xAC00) % 28 else '는'


def same_person_role(category, clause):
    def normalized(value):
        value=re.sub(r'(?<!\S)여성(?=\s)','여자',value)
        return re.sub(r'(?<!\S)남성(?=\s)','남자',value)
    return bool(re.match(re.escape(normalized(category))+r'(?:이다|이었다|였다|이자|이며|이고)(?=$|[ \t,])',
                         normalized(clause.strip())))


def present_category(value, body, topic, lead, *, explicit=False):
    typed = TYPED_CATEGORY_YEAR.fullmatch(value)
    if typed:
        moment, kind = typed.groups()
        entity, event = TYPED_EVENT[kind]
        if entity in lead and (value in lead or re.search(
                rf'(?m)^[ \t]*{moment}년(?: [0-9]{{1,2}}월(?: [0-9]{{1,2}}일)?)?'
                rf'[ \t]*[:：][ \t]*{event}\.?[ \t]*$',body)):
            return ''
        return None
    year = EXPLICIT_YEAR.fullmatch(value)
    if year:
        moment, event = year.groups()
        evidence = r'(?<!\d)'+moment+r'년[^\n.!?]{0,65}(?:'+YEAR_EVIDENCE[event]+')'
        if re.search(evidence, body):
            return ''
        if event in ('출생', '사망'):
            life = re.search(r'\((?:[^(),，\n]{1,60}[,，][ \t]*)?'
                             r'([0-9]{3,4})년[^()\n~∼–]*[~∼–][ \t]*([0-9]{3,4})?년?', lead)
            if life and life[1 if event == '출생' else 2] == moment:
                return ''
            if (explicit and PERSON_FACT.search(lead) and life is None
                    and not re.search(r'[0-9]{3,4}년[^\n.!?]{0,65}(?:'+YEAR_EVIDENCE[event]+')',body)
                    and not re.search(r'생년 미상|몰년 미상|생몰년 미상',lead)):
                verb = '태어났다' if event=='출생' else '사망했다'
                return f'{topic}{topic_particle(topic)} {moment}년에 {verb}.'
            return None
        event_near_year = r'(?<!\d)[0-9]{3,4}년[^\n.!?]{0,65}(?:'+YEAR_EVIDENCE[event]+')'
        if re.search(event_near_year, body):
            return None
        return f'{topic}{topic_particle(topic)} {moment}년에 {YEAR_PARTICLE[event]}.'
    if CATEGORY_ROLE.fullmatch(value) and not value.endswith(' 역'):
        if value in lead:
            return ''
        if explicit:
            named_lines = re.findall(r'(?:^|[.!?。][ \t\n]+)'+re.escape(topic)
                                     +r'[은는이가][ \t]+[^.!?。\n]+',body,re.M)
            related = ' '.join([lead]+named_lines)
            if value in related:
                return ''
            entity, _, status = value.rpartition(' ')
            action = {'출신':r'출신|태어났', '동문':r'동문|졸업|수료',
                      '합격자':r'합격|급제', '수상자':r'수상|받았'}.get(status)
            if entity and action and re.search(re.escape(entity)+r'[^.!?。\n]{0,45}(?:'+action+')',body):
                return ''
        area, sep, kind = value.rpartition('의 ')
        explicit_area = area in lead or all(len(word)>1 and word in lead for word in area.split())
        explicit_kind = (kind in lead or (kind == '도시' and '시다.' in lead)
                         or (kind == '전철역' and '도시철도' in lead and '환승역' in lead))
        if sep and explicit_area and explicit_kind:
            return ''
        return f'{topic}{topic_particle(topic)} {value}이다.'
    if explicit and PERSON_CATEGORY.fullmatch(value):
        subject=re.match(re.escape(topic)+r'(?:\([^()\r\n]{0,135}\))?[은는][ \t]+',lead.lstrip())
        if subject:
            clause=re.split(r'[.!?。]',lead.lstrip()[subject.end():],maxsplit=1)[0]
            if same_person_role(value,clause):
                return ''
        return None
    if explicit and PLACE_CATEGORY.fullmatch(value) and value.rsplit(' ',1)[1] in lead:
        area, sep, kind = value.rpartition('의 ')
        if value in lead or (sep and area in lead and (kind in lead or (kind=='의사' and '전문의' in lead))):
            return ''
        return f'{topic}{topic_particle(topic)} {value}이다.'
    return None


def navigation_title(value):
    if NAMED_LINK_SOURCE.fullmatch(value):
        return False
    if NAV_LINK.fullmatch(value) or OFFICIAL_LABEL.fullmatch(value):
        return True
    return (len(value) <= 105 and bool(NAV_TITLE.search(value))
            and not PLAIN_PREDICATE.search(value) and not re.search(r'[.!?。][ \t]|[0-9]{4}년', value))


def appendices_link_list(lines, start, stop):
    """A visible list finishes at the first flush-left paragraph."""
    items = []
    for i in range(start+1, stop):
        line = lines[i]
        text = line.strip()
        if not text:
            continue
        if not line[0].isspace():
            if items and i>start+2 and not lines[i-1].strip():
                break
            return []
        value = text.lstrip('*').strip()
        if value.isdecimal() or NAMED_LINK_SOURCE.fullmatch(value) or not (navigation_title(value) or
                (LINK_TITLE_FORM.fullmatch(value) and not LINK_SOURCE_CUE.search(value)
                 and not PLAIN_PREDICATE.search(value) and not value.endswith(('.', '。', '?', '!')))):
            return []
        items.append(i)
    return items


def preserve_film_title(lines, start, entries, counts):
    first=next((i for i in range(start) if lines[i].strip()),None)
    original=FILM_LEAD.match(lines[first]) if first is not None else None
    if original is None:
        return False
    catalogs={}
    for i in entries:
        record=FILM_LINK.fullmatch(lines[i].strip().lstrip('*').strip())
        if record:
            title=record[1].strip('《》“”"')
            site=record[2].replace('한국영화데이터베이스','한국영화 데이터베이스')
            catalogs.setdefault(title,set()).add(site)
    primary=''.join(c.casefold() for c in original[1] if c.isalnum())
    alternatives=[(title,sites) for title,sites in catalogs.items() if len(sites)>=2
                  and ''.join(c.casefold() for c in title if c.isalnum())!=primary
                  and all(title not in line for line in lines[:start])]
    if not alternatives:
        return False
    title,sites=alternatives[0]
    if len(alternatives)>1 or re.findall(r'\d+',title)!=re.findall(r'\d+',original[1]):
        counts['unresolved_film_titles']+=1
        return True
    if not lines[first].rstrip().endswith(('.', '。', '!', '?')):
        return True
    sources=' 및 '.join(sorted(sites))
    lines[first]=lines[first].rstrip('\r\n')+f' {sources} 자료에는 제목이 《{title}》로 표기되어 있다.\n'
    counts['film_titles_in_prose']+=1
    return False


def blank_footer_followed_by_metadata(lines, section, before, values, strong, body, kind):
    if section != before or lines[section+1].strip():
        return False
    if not re.search(r'[.!?。]',body[:1200]) or re.search(r'<ref\b|\[\d{1,3}\]',body,re.I):
        return False
    cues = 0
    for value in values:
        ordinary = (value in strong or OTHER_CATEGORY.fullmatch(value)
                    or TYPED_CATEGORY_YEAR.fullmatch(value) or SPORTS_CATEGORY.fullmatch(value))
        if LINK_SOURCE_CUE.search(value) and not ordinary:
            return False
        words = [word.removesuffix('의') for word in value.split()]
        related = value in body or (len(words)>=2 and all(len(word)>1 and word in body[:3500] for word in words))
        cues += bool(ordinary or related)
    if kind != 'note' and not any(CATEGORY_YEAR.fullmatch(v) or CATEGORY_ROLE.fullmatch(v)
                                  or TYPED_CATEGORY_YEAR.fullmatch(v) or SPORTS_CATEGORY.fullmatch(v) for v in values):
        return False
    return cues >= max(1, (len(values)+1)//2)


def label(line):
    normal = normalize_heading(line)
    if normal.startswith('==') and normal.endswith('=='):
        normal = normal.strip('=').strip()
    return LABELS.get(normal)


def remove_empty_before_categories(lines, counts):
    from scripts.p106b_hold_resolution_policy_v16 import CATEGORY, YEAR

    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    if len(nonempty) < 4:
        return lines
    stop = nonempty[-1]+1
    start = stop-1
    while start and lines[start-1].strip() and label(lines[start-1]) is None:
        start -= 1
        if stop-start > 30:
            return lines
    if not start or not 1 <= stop-start <= 30:
        return lines
    before = next((i for i in reversed(nonempty) if i < start), None)
    if before is None:
        return lines
    section = before
    while section >= 0 and (not lines[section].strip()
                            or (lines[section][0].isspace() and navigation_title(lines[section].strip()))):
        section -= 1
    if section < 1 or label(lines[section]) not in FOOTER_LABELS | {'categories'}:
        return lines
    if lines[section-1].strip():
        return lines
    values = [line.strip() for line in lines[start:stop]]
    if not all(SHORT_CATEGORY.fullmatch(value) and not value.endswith('.') for value in values):
        return lines
    strong = [value for value in values if (CATEGORY_YEAR.fullmatch(value)
                                           or CATEGORY_ROLE.fullmatch(value)
                                           or NOUN_CATEGORY.fullmatch(value)
                                           or CATEGORY.fullmatch(value) or YEAR.fullmatch(value))]
    kind = label(lines[section])
    body = ''.join(lines[:section])
    all_flush_left = all(not row[0].isspace() for row in lines[start:stop])
    known_note = (kind in ('note','references','links','materials') and all_flush_left
                  and blank_footer_followed_by_metadata(lines,section,before,values,strong,body,kind))
    explicit_family = (kind == 'categories' and section == before and all_flush_left and
                       any(CATEGORY_ROLE.fullmatch(value) or CATEGORY_YEAR.fullmatch(value)
                           or TYPED_CATEGORY_YEAR.fullmatch(value)
                           or PERSON_CATEGORY.fullmatch(value) or PLACE_CATEGORY.fullmatch(value)
                           for value in values))
    if len(values) == 1 and not (known_note or explicit_family):
        return lines
    min_strong = max(2, (len(values)+1)//2)
    if kind == 'note' and not lines[start-1].strip() and any(CATEGORY_YEAR.fullmatch(value) for value in values):
        min_strong = 2
    if len(strong) < min_strong and not (known_note or explicit_family):
        return lines
    tightly_set = (all_flush_left and len(strong) >= (2 if kind == 'note' else 3)
                   and not lines[start-1].strip() and not any(LINK_SOURCE_CUE.search(value)
                            for value in values if value not in strong))
    if len(body.strip()) < 40 or (not (known_note or explicit_family or tightly_set)
                                 and any(value not in strong and value not in body for value in values)):
        return lines
    headings = []
    if kind in FOOTER_LABELS and (section == before or kind in ('links', 'materials')):
        headings.append(section)
        if section < before:
            counts['navigation_headings'] += 1
            counts['navigation_lines'] += sum(bool(line.strip()) for line in lines[section+1:before+1])
        else:
            counts['empty_before_categories'] += 1
    for pos in reversed(nonempty):
        if pos >= section:
            continue
        if label(lines[pos]) not in FOOTER_LABELS or pos == 0 or lines[pos-1].strip():
            break
        counts['empty_before_categories'] += 1
        headings.append(pos)
    remove = set(headings)
    if section in remove:
        remove.update(range(section+1, before+1))
    name = TOPIC_NAME.match(body)
    if name and all_flush_left and not PLAIN_PREDICATE.search(values[-1]):
        topic = name[1].strip()
        first = next(i for i, line in enumerate(lines[:section]) if line.strip())
        lead = lines[first][:1200]
        if re.search(r'(?:[은는][ \t]).{1,180}[.!?。]', lead):
            added = []
            for i, value in enumerate(values, start):
                sentence = present_category(value,body,topic,lead,explicit=explicit_family)
                if (sentence is None and explicit_family and len(value)>=5 and value in lead
                        and (CATEGORY.fullmatch(value) or value.endswith(('병원','대학교','학교','박물관')))):
                    sentence = ''
                if sentence is None:
                    continue
                remove.add(i)
                if sentence:
                    added.append(sentence)
                    counts['category_prose'] += 1
                else:
                    counts['category_duplicates'] += 1
            if all(i in remove for i in range(start, stop)) and kind == 'categories':
                remove.add(section)
                counts['category_headings'] += 1
            if added:
                lines[first] = lines[first].rstrip('\r\n')+' '+' '.join(added)+'\n'
    return [line for i, line in enumerate(lines) if i not in remove]


def bind_titled_bibliography(lines, counts):
    for number in range(len(lines)-1,-1,-1):
        if label(lines[number]) not in ('references','links','materials') or number == 0 or lines[number-1].strip():
            continue
        end = next((i for i in range(number+1,len(lines)) if label(lines[i])),len(lines))
        selected = []
        for i in range(number+1,end):
            entry = lines[i].strip()
            citation = QUOTED_BIBLIOGRAPHY.fullmatch(entry)
            if citation is None:
                continue
            author = citation['author'].strip(' ,.')
            title = citation['title']
            matches = [j for j,line in enumerate(lines[:number])
                       if title in line and author in line and TITLED_CITATION.search(line)
                       and line.rstrip().endswith(('.', '。'))]
            if len(matches)!=1:
                continue
            source = lines[matches[0]]
            if entry.rstrip('.') not in source:
                prefix = ' 이 자료의 출처는 ' if re.search(r'[가-힣]',source) else ' The cited source is '
                ending = '이다.' if prefix.startswith(' 이') else '.'
                lines[matches[0]] = source.rstrip('\r\n') + prefix + entry.rstrip('.') + ending + '\n'
            selected.append(i)
        if selected:
            counts['anchored_citations'] += len(selected)
            if all(not lines[i].strip() or i in selected for i in range(number+1,end)):
                selected.append(number)
                counts['citation_headings'] += 1
            for i in sorted(selected,reverse=True):
                del lines[i]
    return lines


def unfold_explicit_wiki_categories(lines, counts):
    end = next((i+1 for i in range(len(lines)-1,-1,-1) if lines[i].strip()),0)
    values = []
    start = end
    while start:
        match = WIKI_CATEGORY_LINE.fullmatch(lines[start-1].rstrip('\r\n'))
        if match is None:
            break
        values.append(match[1])
        start -= 1
    if not values or not start or lines[start-1].strip():
        return lines
    if WIKI_CATEGORY_LITERAL.search(''.join(lines[:start])):
        return lines
    folded = lines[:start] + ['분류\n'] + [value+'\n' for value in reversed(values)] + lines[end:]
    changes = Counter()
    result = remove_empty_before_categories(folded,changes)
    if not changes['category_headings']:
        return lines
    counts.update(changes)
    counts['explicit_category_markup'] += len(values)
    return result


def format_life_roles(value, counts):
    lead=value.split('\n',1)[0]
    topic=TOPIC_NAME.match(lead)
    dates=INTRO_LIFE_DATES.match(lead)
    if not topic or not dates:
        return value
    clause=re.split(r'[.!?。]',lead[dates.end():],maxsplit=1)[0]
    if not PERSON_FACT.search(clause) or re.search(r'아니|였지만|였으나|(?<!\S)않',clause):
        return value
    head,separator,tail=value.rstrip('\r\n').rpartition('\n\n')
    entries=tail.splitlines()
    if not separator or not 1<=len(entries)<=24 or not all(SHORT_CATEGORY.fullmatch(line.strip()) for line in entries):
        return value
    name=topic[1].strip()
    deceased=bool(dates[2])
    keep=[]
    prose=[]
    concepts={'출신':r'태어났|출생|출신','동문':r'졸업|수학|동문','수상자':r'수상|받았'}
    for line in entries:
        category=line.strip()
        durable=category.endswith((' 출신',' 동문','상 수상자',' 메달 수상자'))
        if PERSON_CATEGORY.fullmatch(category) and same_person_role(category,clause):
            counts['category_duplicates']+=1
        elif not (durable and CATEGORY_ROLE.fullmatch(category)):
            keep.append(line)
        elif same_person_role(category,clause):
            counts['category_duplicates']+=1
        else:
            subject,status=category.rsplit(' ',1)
            if status in concepts and re.search(re.escape(subject)+r'[^.!?。\n]{0,110}(?:'+concepts[status]+')',lead):
                keep.append(line)
                continue
            ending='이다.'
            if deceased:
                ending='이었다.' if topic_particle(category)=='은' else '였다.'
            prose.append(f'{name}{topic_particle(name)} {category}{ending}')
    if len(keep)==len(entries):
        return value
    counts['life_role_documents']+=1
    counts['category_prose']+=len(prose)
    if prose:
        head=head[:len(lead)]+' '+' '.join(prose)+head[len(lead):]
    return head+('\n\n'+'\n'.join(keep) if keep else '')


def transform(data, counts):
    promotion=data.find(CATHOLIC_PROMOTION)
    if promotion>0 and data[promotion-1:promotion]==b'\n':
        after=promotion+CATHOLIC_PROMOTION_BYTES
        if (data.startswith(CATHOLIC_CREDIT,after)
                and sha256(data[promotion:after]).hexdigest()==CATHOLIC_PROMOTION_SHA
                and not CONTEXT_MARKUP.search(data.decode('utf-8'))):
            data=data[:promotion]+data[after:]
            counts['encyclopedia_promotional_footers']+=1
    footer=data[-1150:].rstrip(b'\r\n')
    for width,prefix,digest in WEB_FOOTER_BLOCKS:
        start=len(footer)-width
        if (start>0 and footer[start-1:start]==b'\n' and footer.startswith(prefix,start)
                and blake2b(footer[start:],digest_size=16).digest()==digest
                and not CONTEXT_MARKUP.search(data.decode('utf-8'))):
            stop=len(data)-len(data[-1150:])+start
            if stop>=120:
                data=data[:stop].rstrip(b'\r\n')+BREAK
                counts['web_footer_block_documents']+=1
            break
    web_start=WEB_SKIP.match(data)
    web_tail=data[-320:]
    lower_tail=web_tail.lower()
    web_end=WEB_REPLY.search(web_tail) if b'logged in to post a comment' in lower_tail else None
    controls=2 if web_end else 0
    if web_end is None and b'leave a ' in lower_tail:
        web_end=WEB_COMMENT_END.search(web_tail)
        if web_end and not data[:len(data)-len(web_tail)+web_end.start()].rstrip().endswith((b':',b'=')):
            controls=1
        else:
            web_end=None
    if (web_start or web_end) and data.endswith(BREAK) and not CONTEXT_MARKUP.search(data.decode('utf-8')):
        first=web_start.end() if web_start else 0
        last=len(data)-len(web_tail)+web_end.start() if web_end else len(data)-len(BREAK)
        body=data[first:last].strip(b'\r\n')
        if len(body.strip())>=50:
            data=body+BREAK
            counts['web_ui_documents']+=1
            if web_start:
                counts['web_skip_labels']+=len(web_start[0].splitlines())
            if web_end:
                counts['web_comment_controls']+=controls
    if (b'<a ' in data or b'<A ' in data) and (b'</a' in data or b'</A' in data):
        value=data.decode('utf-8')
        if not (CONTEXT_MARKUP.search(value) or HTML_LINK_EXAMPLE.search(value)):
            def visible_text(match):
                start=data.rfind(b'\n',0,match.start())+1
                prefix=data[start:match.start()].strip()
                if len(prefix)<18 or b'<ref' in prefix.lower():
                    return match[0]
                counts['inline_html_link_tags']+=1
                return match['visible']
            plain=HTML_LINK.sub(visible_text,data)
            if plain!=data:
                data=plain
                counts['inline_html_documents']+=1
    life_metadata=any(marker in data for marker in LIFE_MARKERS)
    dated_alias=LIFE_ALIAS_PREFIX.match(data[:235])
    if not life_metadata and not dated_alias and not LABEL_BYTES.search(data) and b'[[' not in data:
        lower=data.lower()
        if b'<ref' not in lower and b'</ref' not in lower:
            return data
    if not data.endswith(BREAK):
        raise ValueError('document separator changed')
    value = data[:-len(BREAK)].decode('utf-8')
    if CONTEXT_MARKUP.search(value):
        counts['literal_or_table'] += 1
        return data
    release = RELEASE_STUB.fullmatch(value)
    if release is not None:
        lead, year, kind = release['lead'], release['year'], release['kind']
        issued = re.search(r'(?<![0-9])'+year+r'년[^.!?。]{0,45}발매된[^.!?。]{0,85}음반이다\.',lead)
        if issued is not None and lead.count('음반이다.')==1:
            if kind!='음반' and not re.search(r'\b'+kind+r'(?=[ \t]|다\.|이다\.)',issued[0]):
                lead = lead.replace('음반이다.',kind+' 음반이다.')
                counts['release_categories_in_prose']+=1
            counts['release_stubs']+=1
            counts['empty_headings']+=1
            counts['edited_documents']+=1
            return lead.encode()+BREAK
    original = value
    if dated_alias:
        alias=LIFE_ALIAS_GAP.match(value)
        if alias is not None:
            lo,hi=alias.span('empty')
            proposed=value[:lo]+value[hi:]
            first=proposed.split('\n',1)[0].replace('\xa0',' ')
            dates=INTRO_LIFE_DATES.match(first)
            if dates is not None and PERSON_FACT.search(first[dates.end():].split('.',1)[0]):
                value=proposed
                counts['empty_dated_aliases']+=1
    if life_metadata and INTRO_LIFE_DATES.match(value):
        value, life_changes = format_category_footer(value)
        if life_changes:
            counts['life_category_documents']+=1
            if any(change.startswith('첫 문장의 생몰 연도') for change in life_changes):
                value=format_life_roles(value,counts)
    value, removed = empty_footer(Document(0, 0, 0, value))
    counts['empty_headings'] += len(removed)
    lines = value.splitlines(keepends=True)
    if '[[' in value:
        lines = unfold_explicit_wiki_categories(lines,counts)
    lines = remove_empty_before_categories(lines,counts)
    active = [i for i,line in enumerate(lines) if line.strip()]
    remove = set()
    if len(active)>1 and label(lines[active[-1]]) in FOOTER_LABELS | {'photo'}:
        previous=lines[active[-2]].rstrip()
        if (not lines[active[-1]-1].strip()
                or (len(previous)>30 and PLAIN_PREDICATE.search(previous) and label(previous) is None)):
            remove.add(active[-1])
    for a,b in zip(active,active[1:]):
        kind=label(lines[a])
        if (a and kind and label(lines[b]) and not lines[a-1].strip()
                and (b>a+1 or kind in FOOTER_LABELS)):
            remove.add(a)
    if remove:
        counts['empty_headings'] += len(remove)
        lines = [line for i,line in enumerate(lines) if i not in remove]
    headings = [i for i,line in enumerate(lines) if label(line)]
    drop = set()
    for index,stop in zip(headings,headings[1:]+[len(lines)]):
        kind=label(lines[index])
        if kind not in ('links','materials','references','see_also') or index==0 or lines[index-1].strip():
            continue
        separated=appendices_link_list(lines,index,stop) if kind!='materials' else []
        if kind == 'see_also':
            prior=''.join(lines[:index])
            titles=[lines[i].strip().lstrip('*').strip() for i in separated]
            if titles and all(len(title)>=4 and title in prior for title in titles):
                drop.add(index)
                drop.update(separated)
                counts['repeated_see_also_sections']+=1
                counts['repeated_see_also_titles']+=len(titles)
            continue
        if kind == 'references':
            topic=TOPIC_NAME.match(value)
            if not separated or topic is None:
                continue
            prefix=topic[1].strip()+' '
            if all(lines[i].strip().startswith(prefix) and lines[i].strip()[len(prefix):] in PROFILE_LINK_LABELS
                   for i in separated):
                drop.add(index)
                drop.update(separated)
                counts['navigation_headings']+=1
                counts['navigation_lines']+=len(separated)
            continue
        if kind=='links' and separated and preserve_film_title(lines,index,separated,counts):
            continue
        tail=[line.strip().lstrip('*').strip() for line in lines[index+1:stop] if line.strip()]
        if 0 < len(tail) <= 8 and all(navigation_title(x) for x in tail):
            drop.update(range(index,stop))
            counts['navigation_headings'] += 1
            counts['navigation_lines'] += len(tail)
        elif separated:
            drop.add(index)
            drop.update(separated)
            counts['navigation_headings'] += 1
            counts['navigation_lines'] += len(separated)
    if drop:
        lines = [line for i,line in enumerate(lines) if i not in drop]
    for number in range(len(lines)-1,-1,-1):
        if label(lines[number]) != 'note' or number==0 or lines[number-1].strip():
            continue
        following = next((i for i in range(number+1,len(lines)) if label(lines[i])),len(lines))
        notes = [FOOTNOTE.fullmatch(line.strip()) for line in lines[number+1:following] if line.strip()]
        if not notes or not all(m and CITATION_FORM.search(m[2]) for m in notes):
            continue
        changes = []
        if len({m[1] for m in notes}) != len(notes):
            continue
        for m in notes:
            marker = '['+m[1]+']'
            matches = [i for i,line in enumerate(lines[:number]) if marker in line]
            if len(matches)!=1 or lines[matches[0]].count(marker)!=1:
                break
            j=matches[0]
            sentence=lines[j].rstrip()
            if not re.search(re.escape(marker)+r'[.!?。]?$',sentence) or len(sentence)<25:
                break
            changes.append((j,marker,f' 이 대목의 출처는 {m[2].rstrip(".")}이다.'))
        else:
            if len({j for j,_,_ in changes}) != len(changes):
                continue
            for j,marker,source in changes:
                line=lines[j]
                main=line.rstrip().replace(marker,'')
                if not main.endswith(('.', '。', '!', '?')):
                    main+='.'
                lines[j]=main+source+('\n' if line.endswith('\n') else '')
            del lines[number:following]
            counts['anchored_citations'] += len(changes)
            counts['citation_headings'] += 1
    value = ''.join(bind_titled_bibliography(lines,counts))
    if re.search(r'(?im)^[ \t]*<ref[ \t]*',value):
        pieces = value.splitlines(keepends=True)
        clean = [line for line in pieces if not INLINE_EMPTY.fullmatch(line.strip())]
        counts['empty_ref_lines'] += len(pieces)-len(clean)
        value = ''.join(clean)
    def cite(match):
        reference = match[3].strip()
        if not (CITATION_FORM.search(reference) or SHORT_PAGE_CITATION.fullmatch(reference)):
            return match[0]
        counts['anchored_citations'] += 1
        if re.search(r'[가-힣]',value[max(0,match.start()-120):match.start()]):
            return match[1]+' 이 대목의 출처는 '+reference.rstrip('.')+'이다.'
        return match[1]+' The source for this passage is '+reference.rstrip('.')+'.'
    value = INLINE_CITATION.sub(cite,value)
    value, empty_inline = INLINE_EMPTY.subn('',value)
    if empty_inline:
        counts['empty_inline_refs'] += empty_inline
    if '</ref' in value.lower() and not re.search(r'<ref\b',original,re.I):
        value, orphan_closes=ORPHAN_REF_CLOSE.subn('',value)
        if orphan_closes:
            counts['orphan_ref_closes']+=orphan_closes
    if value.rstrip('\r\n') == original.rstrip('\r\n') or not value.strip():
        return data
    out=value.rstrip('\r\n').encode()+BREAK
    counts['edited_documents'] += 1
    return out


def write_prefix():
    prefix=legacy_receipts()['legacy_prefix_span']
    with v1.open('rb') as source:
        before=stamp(source)
        block=source.read(prefix['end'])
        if sha256(block).hexdigest()!=prefix['sha256'] or prefix['start']!=0:
            raise ValueError('existing prefix receipt does not match v1')
        expected=0
        for ident,start,end,split,evidence in prefix['rows']:
            if start!=expected or end<=start or block[end-2:end]!=BREAK or ident in restricted:
                raise ValueError('unverified or restricted prefix metadata')
            expected=end
        if expected!=len(block):
            raise ValueError('prefix has unindexed bytes')
        counts=Counter()
        if part.exists() or meta.exists():
            raise ValueError('existing v1.1 staging paths')
        with part.open('xb', buffering=1<<20) as out, meta.open('x+b',buffering=1<<20) as idx:
            idx.seek(reserved)
            for ident,start,end,split,evidence in prefix['rows']:
                data=transform(block[start:end],counts)
                out.write(data)
                idx.write(position.pack(ordinal(ident),end-start,len(data)))
            out.flush()
            os.fsync(out.fileno())
            idx.flush()
            os.fsync(idx.fileno())
            if stamp(source)!=before:
                raise ValueError('v1 changed during prefix processing')
            entry={'version':'1.1','revision':1,'stage':'prefix_saved','input':str(v1.resolve()),
                   'input_stamp':before,'cursor':expected,'output_bytes':out.tell(),'rows':len(prefix['rows']),
                   'counts':counts,'index_offset':reserved,'index_format':'<III'}
            raw=json.dumps(entry,ensure_ascii=False,separators=(',',':')).encode()
            idx.seek(0)
            idx.write((sha256(raw).hexdigest().encode()+b'\n'+raw).ljust(reserved//2,b'\0'))
            idx.flush()
            os.fsync(idx.fileno())
            print(json.dumps(entry,ensure_ascii=False))


LEGACY_ID = re.compile(rb'"id":"([a-z_]+:[0-9]+)"')
LEGACY_SHA = re.compile(rb'"clean_text_sha256":"([0-9A-Fa-f]{64})"')


def latest_slot(fp):
    versions = []
    fp.seek(0)
    for _ in range(2):
        checksum, _, raw = fp.read(slot_bytes).rstrip(bytes(1)).partition(b'\n')
        if sha256(raw).hexdigest().encode() == checksum:
            try:
                header = json.loads(raw)
                if isinstance(header,dict) and 'zlib_json' in header:
                    header = json.loads(zlib.decompress(b64decode(header['zlib_json'],validate=True)))
                if isinstance(header,dict) and type(header.get('revision')) is int:
                    versions.append(header)
            except (TypeError, ValueError, zlib.error):
                continue
    if not versions:
        raise ValueError('작업 위치를 읽을 수 없습니다.')
    return max(versions, key=lambda row: row['revision'])


def load_position(fp):
    state = latest_slot(fp)
    if state['version'] != '1.1' or state['index_format'] != position.format or state['index_offset'] != reserved:
        raise ValueError('v1.1 작업 위치 형식이 달라졌습니다.')
    return state


def position_header(state):
    raw = json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode()
    if len(raw)+65>slot_bytes:
        encoded=b64encode(zlib.compress(raw)).decode('ascii')
        raw=json.dumps({'zlib_json':encoded},separators=(',',':')).encode()
    body = sha256(raw).hexdigest().encode() + b'\n' + raw
    if len(body) > slot_bytes:
        raise ValueError('작업 위치 저장 한도를 넘었습니다.')
    return body.ljust(slot_bytes, bytes(1))


def checkpoint(output, index, state):
    output.flush()
    os.fsync(output.fileno())
    index.flush()
    end = index.tell()
    if end != reserved + state['rows'] * position.size:
        raise ValueError('문서 위치 수와 인덱스 크기가 다릅니다.')
    state['output_bytes'] = output.tell()
    state['revision'] += 1
    body = position_header(state)
    index.seek(((state['revision'] - 1) % 2) * slot_bytes)
    index.write(body)
    index.flush()
    os.fsync(index.fileno())
    index.seek(end)


def resume_pair(source, output, index):
    lock(output)
    lock(index)
    state = load_position(index)
    if stamp(source) != state['input_stamp']:
        raise ValueError('v1이 작업 착수 뒤 바뀌었습니다.')
    output_end = state['output_bytes']
    index_end = reserved + state['rows'] * position.size
    if state['stage']=='binding_gap':
        raise ValueError('중단된 위치 연결 묶음을 먼저 이어서 저장하세요.')
    proof = read_source_binding_proof(index,state)
    if stamp(output)[2] < output_end or stamp(index)[2] < index_end:
        raise ValueError('v1.1 파일이 마지막 저장 위치보다 짧습니다.')
    output.seek(output_end)
    output.truncate()
    index.seek(index_end)
    index.truncate(index_end+len(proof))
    return state


SOURCE_BINDING = struct.Struct('<IIB')
SOURCE_EMPTY_FORMATTING = re.compile(rb'[ \t\r\n]+|\([ \t]*\)')
SOURCE_ARTICLE_HEADER = re.compile(
    rb'\n\n([^\r\n]{8,180}\nBy [^\r\n]{3,100}\n'
    rb'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    rb' [0-9]{1,2}, [0-9]{4})[ \t\r\n]*\Z'
)
NEW_GAP_ROW = (1<<32)-1


def read_source_binding_proof(index,state):
    record=state.get('source_binding_proof')
    if record is None:
        return b''
    if record['offset']!=reserved+state['rows']*position.size:
        raise ValueError('원문 연결 근거의 시작 위치가 다릅니다.')
    index.seek(record['offset'])
    raw=index.read(record['rows']*SOURCE_BINDING.size)
    if len(raw)!=record['rows']*SOURCE_BINDING.size or sha256(raw).hexdigest()!=record['sha256']:
        raise ValueError('원문 연결 근거 기록이 바뀌었습니다.')
    return raw


def legacy_setup():
    sys.path.insert(0, str(audit.resolve()))
    import active_guard_v6_preflight_v1 as active_guard

    active_guard.activate()
    receipts = legacy_receipts()
    span = receipts['legacy_cache_span']
    cache = work/'cache_reviewed_partial_v18'
    built = (cache/'built.json').read_bytes()
    if (span['skipped'] or Path(span['cache']) != cache.resolve()
            or sha256(built).hexdigest() != span['built_sha256']):
        raise ValueError('v1의 기존 문서 위치 증거와 캐시가 다릅니다.')
    manifest = json.loads(built)['manifests']
    protected = {f'expanded_train:{n-1}' for n in receipts['legacy_admission_hold']['documents']}
    proof = json.loads((cache/'prior_safe_derivative_reuse_verified.json').read_bytes())
    if protected != {row['id'] for row in proof['bodies']} or not protected.issubset(restricted):
        raise ValueError('기존 보호 위치 목록이 일치하지 않습니다.')
    lengths = {row['id']: (Path(row['body']['path']).stat().st_size + len(BREAK),
                           row['body']['sha256']) for row in proof['bodies']}
    shards = [(split, cache/'text'/split, spec) for split in ('train', 'val')
              for spec in manifest['text_' + split]['shards']]
    active_guard.assert_no_protected_opens()
    return span, lengths, shards, active_guard


def edit_legacy_shard(entries, source, output, index, state, protected, split, counts):
    rows = cursor = 0
    end = len(entries)
    address = state['cursor']
    while cursor < end:
        line_end = entries.find(b'\n', cursor)
        if line_end < 0:
            raise ValueError('기존 위치 자료의 행 경계가 끊겼습니다.')
        prefix_end = min(cursor+1600, line_end)
        name = LEGACY_ID.search(entries, cursor, prefix_end)
        if name is None:
            raise ValueError('문서 본문 앞의 ID 필드를 확인하지 못했습니다.')
        ident = name[1].decode('ascii')
        doc_number = ordinal(ident)
        if ident in restricted:
            pin = protected.get(ident)
            digest = LEGACY_SHA.search(entries, cursor, name.start())
            if pin is None or digest is None or digest[1].decode().upper() != pin[1]:
                raise ValueError(f'승인된 위치 증거가 없는 보호 문서입니다. {ident}')
            width = pin[0]
            data = b''
            counts['carried_admission_hold'] += 1
            counts['carried_admission_hold_bytes'] += width
        else:
            row = json.loads(entries[cursor:line_end])
            if row['id'] != ident or row['split'] != split or row['decision'] not in ('KEEP', 'EDIT'):
                raise ValueError(f'문서 위치와 분할이 다릅니다. {ident}')
            original = row['text'].encode() + BREAK
            width = len(original)
            if original != source[address:address + width]:
                raise ValueError(f'v1 문서 경계가 이전 증거와 다릅니다. {ident}, {address}')
            data = transform(original, counts)
        output.write(data)
        index.write(position.pack(doc_number, width, len(data)))
        address += width
        cursor = line_end + 1
        rows += 1
    state['cursor'] = address
    state['rows'] += rows
    return rows


def write_legacy():
    span, protected, shards, active_guard = legacy_setup()
    with (v1.open('rb') as original, mmap.mmap(original.fileno(), 0, access=mmap.ACCESS_READ) as source,
          part.open('r+b', buffering=1<<20) as output, meta.open('r+b', buffering=1<<20) as index):
        state = resume_pair(original, output, index)
        if state['stage'] not in ('prefix_saved', 'legacy'):
            raise ValueError('v1.1 앞부분부터 저장하거나 확인된 이어받기 위치를 쓰세요.')
        if state['stage'] == 'prefix_saved' and state['cursor'] != span['start']:
            raise ValueError('앞부분과 기존 확정 위치의 경계가 다릅니다.')
        counts = Counter(state['counts'])
        initial_rows = state['rows'] - state.get('legacy_rows', 0)
        for shard in range(state.get('next_shard', 0), len(shards)):
            if datetime.now(deadline.tzinfo) >= deadline:
                break
            split, directory, spec = shards[shard]
            path = directory/spec['path']
            if path.is_symlink() or path.stat().st_size != spec['bytes']:
                raise ValueError('증거 파일 크기가 바뀌었습니다.')
            with path.open('rb') as fp, mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ) as entries:
                written = edit_legacy_shard(entries, source, output, index, state, protected, split, counts)
            if written != spec['rows']:
                raise ValueError('기존 위치 자료의 문서 수가 다릅니다.')
            state.update(stage='legacy', counts=counts, next_shard=shard+1, legacy_rows=state['rows']-initial_rows)
            if (shard+1)%16 == 0:
                checkpoint(output, index, state)
                print(f"{state['legacy_rows']:,}문서 처리, 누적 수정 {counts['edited_documents']:,}문서", flush=True)
        if state.get('next_shard', 0) == len(shards):
            if (state['cursor'] != span['end'] or state['legacy_rows'] != span['counts']['train']+span['counts']['val']
                    or counts['carried_admission_hold'] != len(protected)):
                raise ValueError('기존 문서 위치의 끝이나 보호 문서 수가 다릅니다.')
            state['stage'] = 'legacy_saved'
        if stamp(original) != state['input_stamp']:
            raise ValueError('v1이 정제 중 바뀌었습니다.')
        active_guard.assert_no_protected_opens()
        checkpoint(output, index, state)
        print(json.dumps(state, ensure_ascii=False))


QUARK_APPENDIX = (
    "외부 자료 \n"
    " 쿼크란 무엇인가? - 입자물리학자 이강영 교수. YTN 사이언스. 2014년 7월 2일.\n"
    " CosmicVoyage 초은하단에서 쿼크까지. 2015년 7월 2일.\n"
    " 빛의 물리학 6부 빛과 끈 #003 쿼크와 랩톤 그리고 끈이론. 2015년 6월 10일.\n"
    "\n"
    "분류\n"
    "기본 입자\n"
    "페르미 입자\n"
    "양자색역학\n"
    "피네간의 경야\n"
    "\n"
)
HEISENBERG_CATEGORIES = """분류
1901년 출생
1976년 사망
독일의 물리학자
독일의 대학 교수
양자역학
과학철학자
이론물리학자
뷔르츠부르크 출신
뮌헨 대학교 동문
괴팅겐 대학교 동문
베를린 훔볼트 대학교 교수
노벨 물리학상 수상자
독일의 노벨상 수상자
프로이센 과학 아카데미의 회원
교황청 과학원의 회원
푸르 르 메리트 민사훈장 수훈자
대연방공로십자성현장 수훈자
20세기의 자유군단 관련자
신장암으로 죽은 사람
양자물리학자
20세기 물리학자
왕립학회 외국인 회원
막스 플랑크 메달 수상자
유체역학자

"""
HEISENBERG_MEMBER = '린체이 아카데미(로마) 및 미국 과학 아카데미의 회원'
HEISENBERG_PRINCIPLE = '그는 1927년에 발표한 불확정성 원리로 유명하다.'
HEISENBERG_PAPER = (' Heisenberg, W. (1927). "Über den anschaulichen Inhalt der quantentheoretischen '
                    'Kinematik und Mechanik". Z. Phys. 43 (3–4): 172–198.\n')
REVIEWED_GAP_POSITIONS = {
    161: (4684565946, 4684569590, 1),
    218: (4684600481, 4684663417, 4),
}
REVIEWED_BODY_SHA = {
    76428: '0ece4fb9a6284b0169c48f90d4c2f84a3c700a1ad3245f96ebfcab8146375f0c',
    26677: '5e49640683452e865def7923588a2a9c96e2edadb09c5e8e7c2153b04cca11ed',
    112601: '18f11e3bcef02bfd7767654e203c5669138b7c72d3c5e626a050843c46e759f2',
    78501: '80ee0d1a5e5aaf2f59e98543f6e635793e47b51f510c2bc37e777d4addfb69ed',
    60675: 'ab583a5246165cb72e46a34ba5f13996d50e75d24a35aae3151564e5fe5e1eac',
    95793: 'da31e7ab4ba63d44eb24b0528fa5e932f9cb7af6873990db582193c8cd3e6b71',
    35558: '78394ca2e976e63646f0d7a8eef4edf93f954a37551dba8fbbac165edf1bc824',
    85027: 'b9c66ed328905a4e0803a3e1fa36963b47f4566a99d8415959a93112a2355392',
    65: 'e457836a2c932291d4fd26918e9674322aa5717e4f7a53384efaff58dbc930f7',
    161: 'eb10eda21bd9280b694f425bdfd224a0d9007f4af62a19c50310e5fb54260f8d',
    118577: 'f4ecfe1f60e07e2e4633cf95f15ae72417c6be79feac04bd7b4445ece387ec75',
    24738: '9cb90bd72b988f4d749aef9d1cf18094010f8a351190b1d4473b632d644b9d9e',
    188644: 'ee6773517b23078663ba75005ca2efe83c93a7eb6ef120996eba9e7dfbfb653a',
    205231: 'c05adab2f16f2032ccccbe8c94565e836074c31ab2a41bee0af79fca64d9452e',
    72197: '10ed6fb1481162aad36fef6e8e7cd518968cc5b38c688ef0b0546cd4ca98aee0',
    163473: '9550a2f521c482b1ba21d16dfe86a0478ffd4c1e857f35e6d33f0b1615794efc',
    177246: '08b9ca2df09dac57b4cbcc7ca3c854d28d1f6ae5c28eaf57ccd99cf11c80716d',
    78273: 'c8dfe53019e2eb4833a659655f5995724bd2db8a33555d9ec0d38bc14551b63e',
    # 한 원문만 남은 구간에서 수치와 양쪽 문맥 또는 본문 토큰 배열을 대조했다.
    3213: '883b3ca64b279bc4cfd105c46ac953c117143521db1470c45b1b4b5e800c63c3',
    3247: 'de48ed197027c3fdc991b00bb8ad567892a0978251967c0c55d08669aaacec29',
    108420: 'e9d4e5e701d871ab9ac02e6b761a51213612bbf4eb613c4d032cdc598f4802a9',
    153475: '87cd8da0029e637fbac591ce4e79b3c5df450edc5f7aa65c4ca2745200f03f22',
    184261: 'a1feb30121bee227b58d6db36aeb85a3a268720b591758c05bb7217cc11dbc6a',
    # 단일 미연결 원문은 제목과 원문 순서가 같은 다섯 줄 이상 및 마지막 구간을 대조했다.
    3002: '8da6d6f4370acfe7f65dfeb7b082fc6b2d54df7c97d0a4a0f3ad5fe610373137',
    9603: '52e715420def3de0061781907d6c699c1753efe25684a1ffad5778fedc7ac3f6',
    19810: 'dc72a799211fc09934ac0cdd07fd621801a63d9e9480e16c3407cd907a00a986',
    20035: 'ce13ebedcbc0a39fa4fa3dc3e58cd7252ac64123fd050edbc53d6b7ae29a0450',
    21861: '560f3db65f52c3b3b326917f4a1349a448f95c4358537bc66355fe21c8fecf6c',
    21993: '8075085c6947b7ff75bc305591475f446a831dc083c0475f5f9c8ae51350ca95',
    27348: '912a59c0eaa91f1e04700d50e10d9f94f2a4f105f57467076d9b2ef74b581582',
    34544: '4cf8226950cf724759f22e6f254050a78cb60300d4e915386e1f8f1f48ca8bd5',
    37178: '18d48299e7775dde493da6bfd0b29838f13387a8495857312eafeaeba78a1b7f',
    47439: 'afb6c25824323623d9f23e52277f71f974ef42bc546b04209f81044ddfb14d0f',
    47712: '61a1296f38a9f6f3752b81a09abc687e5bd5880146542697147f7ad75f6cefc8',
    48459: 'c742da03fb789d697ade87c1a9f57127046099697a10dd47d0e6556c5fbdbcc8',
    49427: '310c9c244f76a0db8994352087275b0f107873a317282e37babaf3175bce2921',
    49673: '2dca86cd9e65cbc3b4fae433c5f4b48606225a6bef1937c25a27ac21dee06223',
    51508: '0101cc817bd9375472f9464dc2cdfa3e0c0f52ddbeb41c79094fe38f0c1c7f2a',
    52496: '182362db8a0858614b71c32a0470b0a5295e3adc9ab7ad042fcb57f3764b3299',
    53069: 'ffc0017886317178ef697b69f7ad70cc2a4aa4e1d687199c91ea837def79ab4d',
    58884: '52514fb0787b9f41ce5fae33cc3c047309b3816445f747cf95c283854c61f6c7',
    69579: 'cd38e994920125e24541b0650eeaf83dfe971d7d4b8fa35b9cfcbe8f8821f7ed',
    72061: '2cdf8a02b6652470db045cae2d8beb4c505608d59f95df125959a0f597ce1d00',
    82966: '3aa7a893f0ebc449b4e698a2e16f669ee38fe89d43d8f9d2b353024090a46397',
    83737: '61b425af2d128fd4e01986971409024dbf7445cf1166dfb30466cf77bfcb1f65',
    86303: '0946e281c6783767517e620446f188df31fb83530c4e82dbf9019b0eb72e6296',
    89178: '81dcd7397b3117b764eacace36cdc282e6397ca6e1a13ef0add4fc513711c07f',
    89274: '6a90e1d89abb842623e4fba5187675f488b5e7e5c85b3d54ccedc5ceeda8c64e',
    90788: '837be1227c1fedaeead79cf0092d028356bca3f5bb30a246a7b125fc56666733',
    107595: 'c50cd939e3c32bd38d27ac32c3519e3a681e7168bdf58783251dc8ecb5f81c9d',
    107888: 'f5927ebcec37dfdecbc1bdf8432b69284094992af88e991607b9b65d2865a413',
    118475: '9bf2066feb17be7df6719fb873145bad5cb92d69992fdabf46ca42c03347c368',
    137433: 'a3a2ffd26699bbeb99edb50821e293f1e50f2334e5eb5618a042ee4bb7b724c4',
    137814: 'ce7ea2c889398d07a09baa1cf428e8f1627282d5c242777274b0d8d6fd2ff457',
    138812: 'f6dd848f5ffdadfbcf026a5c8e44e37427c564e36c98e07e00ef3b077be321f7',
    172024: 'cf29af60fa56dce338a742add850d2cedc4d88a2d38ef4124f76004be35046fc',
    182574: '2b43f126e8f26688b098cc753275839ed6c3dcc6bd389949bd50b639b18a0a51',
}
REVIEWED_TRAILING_FRAGMENT = {
    65: (4684502780,'c3cf90ccfce7cb14a2bd66c7f76e5feb355f86c5438c031031b89a1890b0ed4e'),
}
REVIEWED_ADJACENT_BODY_SHA = {
    # 앞뒤 원문 경계와 본문 토큰 순서가 함께 확인된 세 구간.
    7387: '0bdd70474d6bc1617e425c5d6ab51cefe75782253dd8b7f1c9519e074d6d0cda',
    47329: '3550eeba5c31c6e712560fdf73ed2092bd97f91f23c15aca4102724b9b514cc2',
    181344: 'd6302e2fd3102d5f0552f7f785985b428d768c93b3c36701642a52ad5cb3eb30',
}
REVIEWED_UNORDERED_BODY_SHA = {
    # 양끝의 원문 단어 배열과 본문을 함께 확인한 위치.
    5009: '38b50645ccd65caf06d293fba10b914a75ebd4b8bd9adf6c57e8d3f106231ce4',
    5561: 'ea07590cd0332af427d4371afc2a6cec52ced5f164628e7dc88c822facba5145',
    6319: '868d087b342040fea4abd7ce5faa240239d8cc1a4b00cff68d88fd1de9094802',
    7083: '66ec19fbe604d3e40e37324a58edec763345fefb33cc770676632c18b6629443',
    7147: 'efdf36249780a9dbe40bc3520399691f2aa1843b496bd68e079aedb86d7cee53',
    15700: '872b7eb761ce0904e82c651e26973948795af4c3ad63927acdca1c9077d5509d',
    15712: '80791f8f8e80541def2d466c07a705814da4a5adf2b7a5f61f53b29ce931a544',
    25785: 'a67f75c1688cf07186eb7700b5a368ec3bda1a574b8ee7db6ce711c26f4a3d3c',
    26205: '2d63fa2e3b2213c927e77611d06f94ac28aff993d31935bb1288b54a6b84a2ed',
    26845: '4102b86723a501eeedb2641e59bf8cd691de0c2ff663c29430aaccba556808ae',
    27965: 'c2c59ba242628c7b316213630f82284f1a7def4bbd5095cf688f58a2ce8d8b43',
    34268: 'dd0dda5f37ac15dd2ed28372fb87b549acb54fa23fbe3d51bda5ed59e735df76',
    34281: '99ee9ae0cda1963761b1b46817a7194cadac4e001dcc1b9d69e949bd82a4853f',
    34958: 'e252ebc47a001b1862a7209eb098e1bee4a4eae57a8a20dc53451e51fa402852',
    37661: '0686bbb6d9db9065f4a3b1d41806a63e87f0340f72ed4ecdbc2137c199948f6d',
    37672: '09d3b3af5c07e878ab2ef4987ea65a1eba3d4a247d57e3502a3fb0bf54115697',
    38761: '195582c13bbb0323d8cb9a270afcfdae727e8146622d9eab4eb7ee21d28c82f6',
    40537: '22499c35d022e2ba4b6d737f02fd587427aa5beecad510bf67e36cc3eaf82924',
    40619: '02bebbb1a09bb833d8366d71c356367532273bc3bd6faa60dde4a796f8634a1e',
    41342: 'b4eb7e3566968461c08428c177f151a647a4f3415562d59ed1c59d89e31ba224',
    41476: 'e7037788a9dea915b619191a9d960169bc81e9114b632b971522ffb001848bb2',
    42111: '98d2bd64ba8a8251a2d972f61c462a480db43d82d6901196156c8b3960c42007',
    43528: '9e9372a542bcd856c824b33219b906ffcde96eff6117d52b505b75b18a475c4a',
    44382: '0175ef5ec9ff3fb78a6a67a6dad5b5477e8ba3d5c0cc2f0c236c1264ce840c1b',
    49008: '3470a34759290abaa699ad14baed59e7cf1c4e15fd52bf9c5832eadb5eb5012b',
    54642: '1fba7ed724e6358fad9e55ba0fa71bd96703335930bd1a91b415b0280ab0d6c5',
    55297: '921551076545b90aec925fbb58372368094b1dcf2333e7319248c9b3a5424cf9',
    55636: '5cf52d32a4ff6c5af2d9e480932f09306d52e7c07e82845270bc4420bd5cb740',
    55876: '7145333f3838e202259c21aae35bf31804392c02459c39870babd0e7c484466e',
    58471: '8a936197758ca9b346cdce7c3280c3aeaed6f756ee99257de3b8e26172d99513',
    78300: '0d1011df1574d28cb8e5019ecb5a3a1d878ac1e7f5ffe5b14942a7319eb9f9ed',
    82618: '77d294b0c5ea9bc00387a0804a41a6246485ba1d16b1e55ee109dee4c68266cb',
    104761: 'e1cd5d0231601058b7b4eb35175c996e7b3227219549cdfeb50091b9feb2ce06',
    136903: '42bf02c1f1ca5d2c9f164bfffad121379e3ed361c6dee15f54d845a3d762c30b',
    136909: '9f1bbd725a152ac6a20d5e407afdb29dd8cea3fdf014a9b271df429d1c81dfcd',
    140146: '5f8590b54f29ded78d19a8c4a958dd543f2e36a7c274cd9a70cabd0262be1caa',
    140151: '34f044c4eaf53574ef267f5bf3d9c46eee2efa2851c46dcac4dcade5d05840b9',
    143004: 'e7becb2c0739fec1df76fb81235d3fa949c2f0a2f423e66fc169eaf1ea511d3c',
    146388: 'cd63e4fc95db081091ba31f95a1c7d976f81bc11e25e2197844946e389855e9f',
    152250: 'f0b4446628b843657452105fd62ebfb2802ae2d03673b318df216320baa5144b',
    158719: '45859ddf3bd6162fcbc8b4040e2f139d106c536bc370185550604a0b542fe2dd',
    165473: '59e394f22a0804a793f11a477c21563e18f5c303352f31546df6a5106d6657aa',
    166161: 'beb51bf15576224020eed5ac295a931855b84308076d7f7a7e7be60f85dfd964',
    167478: '1f3c2779c51a3ec1e45ac0799cbad53c8fd352e40e1c68d2ea66b7318b33ed07',
    182744: '2f24f75b05b05e1b18748e4313c69b9a99e33e68765c6e29c594c65506ba76b0',
    200284: '19faa316a006a73b1131da96c6000c911cdcfc01d3b75deaf9088b5dc665853c',
    207141: '58262932805c467a43ae16959cd0b9b6cba1687e65e4204e6322c81d75d3338f',
    207372: '234facd459972034c64b292ecbcec3563ed43b06884a313298f0d672427c5af4',
}
OLYMPIC_APPENDIX = (
    "경기장\n"
    "\n"
    "경기 결과\n"
    "\n"
    "메달리스트\n"
    "\n"
    "참고 문헌 \n"
    " 국제 올림픽 위원회 - 1904년 하계 올림픽 기계 체조 경기 결과 \n"
    "  George Seymour Lyon - 1904년 올림픽 금메달리스트\n"
    "  \n"
    "  \n"
    "  \n"
    "\n"
    "남자 복합\n"
)
OYANO_BIBLIOGRAPHY = ('참고 문헌 \n 슈텐의 기리시탄 분카소오란(文化綜覧) '
                      '(아마쿠사 문화 출판사, 1983년, 쓰루타 분시(鶴田文史)/편저)')
FAMILY_REGISTER_BIBLIOGRAPHY = (
    "참고 문헌 \n"
    " 정현수, \"호적의 신편제 방안에 관한 연구 :호주제도의 폐지와 관련하여\", 동국대학교 법학과 박사학위논문, 1998 Available at RISS: http://www.riss4u.net/link?id=U9570230_002\n"
    " 류세형, \"호주제 폐지와 새로운 신분등록방안에 대한 고찰\", 호남대학교 법학과 석사학위논문, 2005 Available at RISS: http://www.riss4u.net/link?id=U10459626_002\n"
    " 조상호, \"호주제도에 대한 연구 :호주제도 폐지론을 중심으로\", 전북대학교 교육대학원 석사학위논문, 1982 Available at RISS: http://www.riss4u.net/link?id=U863716_002\n"
    " 전국사회교사모임, 우리 사회를 움직인 판결, 휴머니스트, 2007."
)
FAMILY_REGISTER_SOURCES = (
    '호주제 폐지와 등록 제도에 관한 연구로는 정현수의 「호적의 신편제 방안에 관한 연구: '
    '호주제도의 폐지와 관련하여」(동국대학교 법학과 박사학위논문, 1998년, RISS U9570230_002), '
    '류세형의 「호주제 폐지와 새로운 신분등록방안에 대한 고찰」(호남대학교 법학과 석사학위논문, '
    '2005년, RISS U10459626_002), 조상호의 「호주제도에 대한 연구: 호주제도 폐지론을 중심으로」'
    '(전북대학교 교육대학원 석사학위논문, 1982년, RISS U863716_002)가 있다. '
    '관련 판결을 살펴볼 수 있는 자료로는 전국사회교사모임의 《우리 사회를 움직인 판결》'
    '(휴머니스트, 2007년)이 있다.'
)
KOMATSU_APPENDIX = (
    "외부 링크 \n"
    "  공식 홈페이지 - KOMATSU20.COM\n"
    "\n"
    "1959년 출생\n"
    "살아있는 사람\n"
    "일본의 야구 선수\n"
    "일본 프로 야구 투수\n"
    "주니치 드래건스 선수\n"
    "일본의 야구 해설가\n"
    "이시카와현 출신\n"
    "사와무라 에이지상 수상자\n"
)


def copy_segment(source, output, start, end):
    for offset in range(start, end, 8<<20):
        output.write(source[offset:min(offset+(8<<20),end)])


def gap_edits(source, start, end):
    edits = []
    changes = [
        (4684569235, 4684569235+len(QUARK_APPENDIX.encode()), QUARK_APPENDIX, ''),
        (4684600780, 4684601050, HEISENBERG_PRINCIPLE,
         '그는 1927년에 발표한 불확정성 원리로 유명하다. 이 원리를 다룬 논문 '
         '「Über den anschaulichen Inhalt der quantentheoretischen Kinematik und Mechanik」는 '
         '《Zeitschrift für Physik》 제43권 3–4호 172–198쪽에 실렸다.'),
        (4684652300, 4684653500, HEISENBERG_MEMBER,
         HEISENBERG_MEMBER + '\n 그는 교황청 과학원의 회원이기도 했다.'),
        (4684660945, 4684661083, HEISENBERG_PAPER, ''),
        (4684662766, 4684662766+len(HEISENBERG_CATEGORIES.encode()), HEISENBERG_CATEGORIES, ''),
    ]
    for low, high, old, new in changes:
        before = old.encode()
        if high <= start or low >= end:
            continue
        if not start <= low < high <= end:
            raise ValueError('문맥을 확인한 수정 위치가 예상 범위를 벗어났습니다.')
        address = source.find(before, low, high)
        if address == -1 or source.find(before, address+1, high) != -1:
            raise ValueError(f'확정된 문맥 앵커가 달라졌습니다. {low}')
        edits.append((address, address+len(before), new.encode()))
    return edits


def rewrite_bound_body(source, start, end, number, counts):
    if number not in REVIEWED_GAP_POSITIONS:
        return rewrite_known_tail(source[start:end],number,counts)
    first,last,edit_count = REVIEWED_GAP_POSITIONS[number]
    edits = gap_edits(source,start,end)
    if (start,end,len(edits)) != (first,last,edit_count):
        raise ValueError(f'직접 정제한 원문 위치가 달라졌습니다. {number}')
    pieces = []
    for lo,hi,replacement in edits:
        pieces.extend((source[start:lo],replacement))
        start=hi
    pieces.append(source[start:end])
    counts['manual_documents'] += 1
    counts['manual_changed_spans'] += edit_count
    return b''.join(pieces)


def write_gap(source, output, index, state, end, counts):
    start = state['cursor']
    last = start
    out_start = output.tell()
    edits = gap_edits(source, start, end)
    for lo, hi, revised in edits:
        copy_segment(source, output, last, lo)
        output.write(revised)
        last = hi
    copy_segment(source, output, last, end)
    index.write(position.pack(0, end-start, output.tell()-out_start))
    state.update(cursor=end, rows=state['rows']+1, unlinked_input_bytes=end-start,
                 unlinked_output_bytes=output.tell()-out_start)
    counts['manual_documents'] += 2
    counts['manual_changed_spans'] += len(edits)


# Exclusions confirmed in both the complete saved body and the original-text SHA.
EXACT_REPEATS = {
    1442267: 1092, 1443680: 2505, 1444423: 3248, 1444635: 3460,
    1444758: 3583, 1445707: 4532, 1446120: 4945, 1446889: 5714,
    1448235: 7060, 1448890: 7715, 1450520: 9345, 1451488: 10313,
    1451517: 10342, 1453731: 12556, 1454465: 13290, 1454485: 13310,
    1454920: 13745, 1456262: 15087,
    1444118: 2943, 1446968: 5793, 1450819: 9644, 1454457: 13282,
}
# 원문 전체를 비교해 댓글 조작 안내만 다른 중복을 연결한다.
ARTICLE_UI_REPEATS = {417724: 1058922, 224383: 54142, 1110393: 469774}
REGISTRY_REPEATS = {526386:526382, 526387:526382, 526392:526382, 526393:526382, 526394:526382, 560022:526382, 794526:526382, 1165240:526382}
# 같은 학습 분할에서 양쪽 TXT의 본문 전체가 같고 경계의 줄바꿈만 다른 문서다.
BOUNDARY_REPEATS = {
    1444324: 3149, 1444325: 3150, 1444379: 3204, 1444411: 3236,
    1444425: 3250, 1444430: 3255, 1444465: 3290, 1445007: 3832,
    1445536: 4361, 1445579: 4404, 1449883: 8708, 1450500: 9325,
    1453440: 12265, 910123: 249980,
}
CONTENT_ADMISSION_HOLD = {819293, 2153229}
VALIDATION_OVERLAP = ((264386,2152996,1349), (1316468,2152903,2054))
VALIDATION_WORD_OVERLAP = (
    (1420712,2154450,3382,3431,3390),
    (1160842,2152500,673,679,689),
    (882064,2152893,307,349,309),
    (884830,2154117,614,619,696),
    (1368700,2152468,210,286,216),
    (1436404,2154899,859,1340,1115),
)

SOYEON_SOURCE_SHA = '6171f013a0edfed564de30c14278c6100e07126f091b8d5d7edbe9311f292cee'
SOYEON_PROSE = (
    "소연(전소연, 1998년 8월 26일~)은 대한민국의 가수, 래퍼, 작사가, 작곡가, 음악 프로듀서다. 걸 그룹 (여자)아이들의 리더이자 메인 래퍼다.\n\n"
    "서울특별시 강남구 개포동에서 전병화(田炳和)와 주혜경(朱惠卿)의 딸로 태어났다. 본관은 담양이다. 동생은 전소희(田素熹)다. 서울구룡초등학교와 대치중학교, 중앙대학교 사범대학 부속고등학교를 졸업했다.\n\n"
    "중학생 때부터 여러 기획사의 오디션을 보고 스트리트 댄서로 활동했다. 예술고등학교 입시에 응시했으나 불합격했다. 2014년 1월 큐브 엔터테인먼트의 연습생 선발 오디션에 랩으로 지원해 합격했다. 입사 전부터 춤과 랩, 프로듀싱을 연습했다.\n\n"
    "2016년 1월 큐브 엔터테인먼트 연습생으로 《프로듀스 101》 첫 번째 시즌에 출연했다. 5회에서 10위를 기록했으며 마지막 회에서는 20위를 차지해 I.O.I에 합류하지 못했다. 같은 해 7월 《언프리티 랩스타 3》에 참가해 최종 2위를 기록했고 마지막 컴필레이션 음반에 실린 세 곡에 참여했다. 2016년 12월 29일 큐브 엔터테인먼트와 전속 계약을 체결했다. 2017년 11월 5일 솔로로 데뷔했으며, 디지털 싱글로 〈Jelly〉와 〈Idle Song〉을 발표했다.\n\n"
    "2018년 1월 11일, 큐브 엔터테인먼트는 전소연이 (여자)아이들의 리더이자 메인 래퍼로 활동할 예정이라고 발표했다. 그는 그룹의 데뷔곡 〈라타타〉와 컴백곡 〈한〉의 작사, 작곡, 편곡에 참여했다. 두 곡은 호평을 받았고, 그는 그룹의 데뷔 EP 《I Am》의 다섯 곡을 작곡하는 데 기여했다.\n\n"
    "2018년 8월 8일 전소연의 SM STATION X 0 걸 그룹 프로젝트 참여가 발표됐다. 스테이션 영은 같은 해 9월 28일 첫 곡 〈Wow Thing〉을 발표했다. 이 곡에는 전소연과 슬기(레드벨벳), 청하, 신비(여자친구)가 참여했다. 라이엇 게임즈는 전소연과 같은 그룹 멤버 미연에게 연락했고, 두 사람은 매디슨 비어와 자이라 번스와 함께 《리그 오브 레전드》의 가상 그룹 K/DA에 참여했다. K/DA는 11월 3일 2018 리그 오브 레전드 월드 챔피언십에서 〈POP/STARS〉로 데뷔했다. 곡의 뮤직비디오는 같은 날 공개됐으며 닷새 만에 유튜브 조회수 3,000만 회를 넘었다. 이 곡은 빌보드 월드 디지털 송 차트에서 1위를 기록했다. K/DA의 아칼리는 팬아트와 코스프레의 소재가 됐다.\n\n"
    "2019년 전소연은 CLC의 곡 〈No〉를 작곡했다. 이 곡은 블라인드 테스트를 거쳐 리드 싱글로 선정됐다. 2019년 3월 그는 작곡을 배우던 시기에 음악 제작 프로그램 콘탁트의 불법 복제본을 사용한 일에 대해 온라인 팬 커뮤니티에서 사과했다. 본격적으로 작곡을 시작한 뒤에는 공인된 프로그램만 사용했다고 밝혔다. 소속사도 EP 《I Made》 준비 영상을 내리고 사과했다.\n\n"
    "전소연은 《리그 오브 레전드》의 가상 힙합 그룹 트루 데미지에서 아칼리 역을 맡았다. 〈Giants〉는 2019년 11월 10일 애니메이션 뮤직비디오와 함께 싱글로 발매됐다. 곡은 주로 영어로 불리며 스페인어와 한국어 구절이 있다. 트루 데미지는 같은 날 프랑스 파리에서 열린 2019 리그 오브 레전드 월드 챔피언십 결승전에서 공연했다. 전소연은 이로써 대회 결승전 개막식에서 2년 연속 공연했다. 〈Giants〉는 빌보드의 랩 차트와 R&B·힙합 디지털 송스 세일즈 차트에 각각 15위와 19위로 진입했다.\n\n"
    "2020년 전소연은 Mnet의 힙합 프로그램에 출연했다. 2월 28일 일슨과 Nuck과 함께 올드 & 영 협업 무대에서 〈2020 라이온 리믹스〉를 공연했다. (여자)아이들은 같은 해 4월 세 번째 EP 《I Trust》를 발매했다. 전소연은 DJ 효의 〈Desert〉 작사와 작곡에 참여했다. 8월 27일 K/DA의 〈The Baddest〉에서 아칼리 역을 맡았고 〈More〉에도 참여했다. 에이핑크 김남주의 솔로 데뷔곡 〈Bird〉의 제작에도 참여했다. 이 곡은 9월 7일 발매됐다.\n\n"
    "2021년 1월 전소연은 연예인의 일상을 휴대전화로 보여 주는 예능 프로그램에 출연했다. 프로그램은 1월 25일부터 3주 동안 매주 월요일 방송됐다. 그는 작곡 과정, (여자)아이들 멤버들과의 일상, 데모곡 1,600곡에 관한 내용과 《I Burn》 준비부터 컴백 당일까지의 영상을 공개했다. 5월 21일 솔로 음반을 낼 예정이라고 보도됐고, 6월 16일 큐브 엔터테인먼트는 첫 솔로 EP 《Windy》를 7월 5일 발매한다고 발표했다. 전소연은 7월 13일 SBS MTV 《더 쇼》에서 국내 음악 프로그램 첫 1위를 기록했다.\n\n"
    "전소연은 2020년 4월 홀트아동복지회를 통해 손 세정제 3만 개를 기부했다. 2021년 6월 2일 자신의 인스타그램에 사진과 팔의 문신을 공개했다. 그는 V LIVE에서 심전도 모양과 ‘장기기증 동의’ 문구가 장기 기증 의사를 표현한다고 밝혔다. 장기 기증을 기다리다 숨지는 사람이 있다는 기사를 읽고 자신이 할 수 있는 일을 고민한 결과라고 말했다. 2022년 1월 18일에는 ‘사랑의 연탄 나눔’ 캠페인에 연탄 2만 장을 기부했다.\n\n"
    "전소연은 작곡과 편곡, 안무, 랩, 춤, 노래에 두루 참여하는 음악가로 소개됐다. 전 라니아 멤버 유주이는 그를 작곡가이자 아이돌로 높이 평가했다. 쿠키뉴스는 그가 선배 그룹 CLC의 곡 제작에 참여한 점을 소개했다. 박은해 기자는 다양한 콘셉트를 시도하는 점과 독특한 위상을 들어 그를 ‘한국의 레이디 가가’라고 평했다.\n\n"
    "전소연은 그룹 멤버들에게서 작곡의 영감을 얻으며, 고등학교 때 만난 랩 선생님에게서 가사를 쓰고 생각을 표현하는 법을 배웠다고 했다. CL, 브리트니 스피어스, 에이브릴 라빈을 본보기로 꼽았다. 브리트니 스피어스와 에이브릴 라빈은 《I Never Die》의 콘셉트와 의상에도 영향을 주었다.\n\n"
    "〈Idle Song〉은 《스폰지밥 네모바지》의 주제가에서, 〈라타타〉는 KBS2 《개그콘서트》에서 송준근이 사용한 ‘아라타라타라타’라는 말에서 영감을 받았다. 〈한(혼자)〉의 영감은 김소월의 시 〈진달래꽃〉에서, 〈세노리타〉의 영감은 2017년 곡 〈Despacito〉에서 얻었다. 〈Uh-Oh〉는 미국에서 《투 네버랜드》를 촬영할 때 스태프가 쓴 표현과 말투에 영향을 받았다. 〈Luv U〉의 안무에는 《슈가슈가룬》의 ‘하트 핑거 V’ 장면이 참고가 됐고, 〈덤디덤디〉에는 2016년 디즈니 애니메이션 《주토피아》가 영감을 주었다.\n\n"
    "전소연은 《I Never Die》를 《원피스》의 마린포드 전쟁에 빗대어 시련을 겪은 뒤 성장한 멤버들의 모습을 담은 음반이라고 설명했다. 〈Tomboy〉에는 영화 《크루엘라》, 〈LION〉에는 실사 영화 《라이온 킹》이 영감을 주었다. 그는 연습생 때 작곡 수업을 받았고, 곡이 부족해 데뷔가 늦어지자 그룹의 타이틀곡을 쓰기 시작했다고 회고했다. 서효인 시인은 전소연이 작사와 작곡, 랩과 콘셉트 설정을 맡으면서 다른 멤버의 장점을 살린다고 평했다.\n\n"
    "전소연은 여성 프로듀서가 더 많이 활동하기를 바랐다. 음악과 공연, 게임 같은 예술에는 경계가 없으며 곡을 쓸 때 성별에 구애받지 않는다고 말했다.\n\n"
    "2016년 《프로듀스 101》 참여 음원으로 〈Pick Me〉, 화려 강산의 〈Don't Matter〉, 〈벚꽃이 지면〉이 있다. 같은 해 《언프리티 랩스타 3》의 1번 트랙 〈She's Coming〉은 프라이머리가, 3번 트랙 〈무서워〉는 KUSH가 제작했다. 1차 공연곡 〈어린이의 하루〉에는 슈퍼비가 피처링했고, 1차 공연과 세미파이널의 〈웃어〉에는 다비(DAVII)가 참여했다.\n\n"
    "전소연은 2022년 멜론 뮤직 어워즈에서 송라이터상을 받았다."
)

REVIEWED_WHOLE_PASSAGES = {
    55301: (
        'ec9dfb4f9d107997df7e0b9b6e7885c8bd806dd307dbc2dee10a14ebcf83046a',
        "새뮤얼 무어 ‘샘’ 월턴(1918년 3월 29일~1992년 4월)은 월마트를 설립한 미국 기업인이다. 오클라호마주 킹피셔에서 태어나 1923년까지 그곳에서 살았다. 보이 스카우트에서 이글 스카우트 상을 받았다.\n\n고등학교 졸업 후 경제학을 공부했으며, 1940년 대학을 졸업한 뒤 군에 입대했다. 1943년 2월 14일 헬린 월턴과 결혼했고 1945년에 제대했다. 그는 26세 때 아칸소주 뉴포트에 벤 프랭클린 상점을 열었다. 1962년 아칸소주, 미주리주, 캔자스주 등에서 체인점 16개를 운영했고 같은 해 7월 아칸소주 로저스에 첫 월마트 매장을 열었다.\n\n월턴은 대통령 자유 훈장을 받았다. 1992년 4월 아칸소주 리틀록에서 혈액암으로 사망했다.",
    ),
    60675: (
        'ab583a5246165cb72e46a34ba5f13996d50e75d24a35aae3151564e5fe5e1eac',
        "232(이백삼십이)는 231보다 크고 233보다 작은 자연수다. 232는 합성수이며, 양의 약수는 1, 2, 4, 8, 29, 58, 116, 232다. 약수의 합은 450으로 232의 두 배인 464보다 작으므로 232는 부족수다.\n\n연도를 나타낼 때는 서기 232년과 기원전 232년이 있다. 대한민국의 시·군·구를 232개로 집계한 사례에서는 인구 50만 명 이상 도시의 일반구를 제외했다. 1987년 5월 16일 롯데와의 경기는 연장 15회까지 이어졌으며 선동열은 투구 232개를 기록했다. 대한민국에는 232라는 이름으로 활동하는 만화가도 있다.",
    ),
    78501: (
        '80ee0d1a5e5aaf2f59e98543f6e635793e47b51f510c2bc37e777d4addfb69ed',
        "하기야마역은 일본 도쿄도 히가시무라야마시에 있는 세이부 철도의 역이다. 하이지마선과 다마코선 열차가 정차한다. 역은 1928년 4월 6일에 개업했고 1958년 9월 16일에 현재 위치로 옮겼다. 남쪽 출입구(南口)와 북쪽 출입구(北口)가 있다. 남쪽 출입구 쪽에는 도쿄 도립 하기야마 실무학교가 있다.",
    ),
    85027: (
        'b9c66ed328905a4e0803a3e1fa36963b47f4566a99d8415959a93112a2355392',
        "히가시오지마역은 일본 도쿄도 고토구와 에도가와구에 걸쳐 있는 도쿄도 교통국 도에이 지하철 신주쿠선의 역이다. 역의 주소는 사무소가 있는 고토구 쪽이다. 상대식 승강장 두 면과 선로 두 개를 갖췄으며 1978년 12월 21일에 영업을 시작했다. 역 건물은 구 나카가와강 위에 있으며 주변에 아라카와강이 있다.",
    ),
    695566: (SOYEON_SOURCE_SHA, SOYEON_PROSE),
    639046: (
        '08aa4b293c119ff9a8a44a67cb7dd82edb6535628d5f9b5d66bbe0d9f51d104c',
        '《애마 섹시 월드》는 1998년 대한민국 영화다. 한국어로 제작되었으며 독고영재, 진주희, 소비아가 출연했다.',
    ),
    639049: (
        '013007c07ea3ad2bf3ea90b5f4cad0cde671d0a96000fe0b4f62b7c4dc1a7163',
        '《애마 섹시 월드2》는 1998년 영화다. 독고영재의 출연작 목록에는 《애마 섹시 월드》와 별도로 이 영화가 올라 있다. '
        '다음영화와 무비스트의 항목에도 제목이 《애마 섹시 월드2》로 표시된다.',
    ),
    170561: (
        '7882413e6a2d08d5c3c37d8e176b847e4405e988eeb3778c6b0ffab183e3b36d',
        '미적분학에서 평균값 정리(平均-定理)는 적절한 연속성과 미분 가능성 조건을 만족하면 함수의 순간 변화율이 구간의 평균 변화율과 같은 점이 구간 내부에 존재한다고 말한다. '
        '기하학적으로는 그 점의 접선이 곡선의 양 끝점을 잇는 직선에 평행하다는 뜻이다. 이 정리는 롤의 정리로부터 유도된다. '
        '미적분학의 기본 정리를 증명하는 데 쓰이고 극값, 고계 도함수, 볼록 함수, 역함수를 다루는 데도 응용된다. 테일러 정리 등 여러 확장이 있다.\n\n'
        '코시 평균값 정리는 확장된 평균값 정리라고도 불린다. 제1 적분 평균값 정리는 각각의 조건 아래 함수의 평균값과 가중 평균값이 그 함수의 치역에 속한다는 결과를 준다. '
        '복소해석학에서 가우스의 평균값 정리는 코시의 적분공식에서 적분 경로를 원으로 택해 유도된다. 실수부를 취하면 조화함수에 대한 형태를 얻는다.\n\n'
        '인도의 Vatasseri Parameshvara가 최초 입안자로 기록되어 있으며, 오귀스탱 루이 코시가 이를 처음 공식화한 인물로 알려져 있다.',
    ),
}

RESUMED_PASSAGES = {
    26677: (
        ("러시아의 표트르 1세부터 알렉산드르 3세까지의 황제가 매장되어 있다.",
         "표트르 1세와 알렉산드르 3세를 비롯한 러시아의 황제들이 이곳에 매장되어 있다."),
        ("미디어 \n KBS 1TV : 《걸어서 세계속으로》\n\n외부 링크 \n  공식 홈페이지\n\n \n\n\n",
         "KBS 1TV의 《걸어서 세계속으로》에서도 이 요새를 소개했다.\n\n"),
    ),
    76428: (
        ("대한민국에서는 ‘시카고 현대 미술관’ 또는 시카고 미술 연구소이라고도 불린다.",
         "시카고 미술 연구소라고도 불린다."),
        ("시카고 미술관의 공식 웹사이트와 소장품 목록, Terra Foundation for American Art, School of the Art Institute of Chicago를 관련 자료로 제시한다.\n\n",
         ""),
    ),
    112601: (
        ("별하늘 찾기 운동과 관련된 단체로 International Dark-Sky Association, Campaign for Dark Skies(영국), National Dark Sky Week(미국), CieloBuio(이탈리아)가 열거되어 있다. 외부 자료로 International Dark-Sky Association과 전 세계 별하늘 관측 지점을 포함한 Google Earth 파일(Outdoor Lighting Regulations and Ordinances)이 제시되어 있다.",
         "영국의 Campaign for Dark Skies, 미국의 National Dark Sky Week, 이탈리아의 CieloBuio도 별하늘 찾기 운동과 관련이 있다. 《Outdoor Lighting Regulations and Ordinances》라는 Google Earth 파일에는 세계 여러 곳의 별하늘 관측 지점이 담겨 있다."),
    ),
    95793: (
        ('2005년 7회 수상자를 낸 이후에 다시 시행되지 않고 있다.',
         '2005년에 제7회 수상자를 낸 뒤 개최가 중단되었다.'),
    ),
    35558: (
        ('다른 도시와 연결되는 주요 도로가 있는 대규모 도시.\n\n기후\n\n\n',
         '하르게이사는 주요 도로를 통해 다른 도시와 연결되는 대규모 도시다.\n\n'),
    ),
    52494: (
        ("<ref>\"reason, ground, origin\", \"wonder, marvel\", tíva rök \"the life and doings of the gods\"\", þjóða rök \"origin, creation of mankind\", í aldar rök \"at the end of the worl\" (Zoega 1910); Proto-Germanic *rakō.(Bjordvand Lindeman 2007, pp. 856–857)</ref>",
         " Zoega의 1910년 자료에는 ‘이유·근거·기원’과 ‘경이’에 해당하는 뜻이 실려 있다. 이 자료는 tíva rök를 ‘신들의 삶과 행적’, þjóða rök를 ‘인류의 기원 또는 창조’, í aldar rök를 ‘세상의 끝’이라는 용례로 제시한다. Bjordvand와 Lindeman은 2007년 자료의 856–857쪽에서 게르만조어 형태 *rakō를 제시한다."),
    ),
    56704: (
        ("<ref name=\"yuncy\">윤치영 (尹致暎), 나의 이력서 (55) 悲運의 두 사람 : 북괴의 김일성은 가짜...진짜 김일성은 일육사 나와 (한국일보 1981年 9月 25日字 6면) 《동산회고록(東山回顧錄) : 윤치영(尹致映)의 20세기(世紀)》 (삼성출판사, 1991년 3월)</ref>",
         " 윤치영은 1981년 9월 25일자 《한국일보》 6면의 연재 「나의 이력서」 제55회 「悲運의 두 사람」에서 이 주장을 폈다. 이 글은 삼성출판사가 1991년 3월에 펴낸 《동산회고록: 윤치영의 20세기》에 수록되었다."),
    ),
    124377: (
        ("박서보(朴栖甫, , 1931년",
         "박서보(朴栖甫, 1931년"),
        ("<ref.>박서보, \"현대미술과 나 II\", <미술세계> 1989년 11월호, 106-108쪽.</ref>",
         " 박서보는 《미술세계》 1989년 11월호 106–108쪽에 실린 「현대미술과 나 II」에서 이 전시 체제를 다뤘다."),
    ),
    270413: (
        ("1994년에 스티븐 핑커가 자신의 저서인 《언어 본능》에 언급하기도 했다.<ref>Pinker, Steven. ''The Language Instinct: How the Mind Creates Language</i>. William Morrow and Company, Inc., New York, 1994. p. 210</ref>",
         "스티븐 핑커도 《언어 본능》(The Language Instinct: How the Mind Creates Language, 뉴욕 William Morrow and Company, 1994) 210쪽에서 이 예문을 다뤘다."),
    ),
    281503: (
        ("<ref>History of Armenia composed by abbot Chamchian, Mikayel. Պատմութիւն Հայոց (History of Armenia). Venice, 1786, p. 131.</ref>.",
         " 이 용례는 미카옐 참치안의 《Պատմութիւն Հայոց》(History of Armenia, 베네치아, 1786) 131쪽에 나온다."),
        ("의 형식으로 사용된다..",
         "의 형식으로 사용된다."),
    ),
    664577: (
        ("2015.04 – BBC ‘The Making of Me’ 시리즈의 첫 화 에피소드 등장 및 뉴스 기사 보도 ‘From homework to a global business’<ref>\"How doing homework for friends inspired a global company\".</cite></ref>",
         "2015년 4월 BBC 시리즈 《The Making of Me》의 첫 회에서 플리토를 소개했다. 이와 관련한 보도 자료에 「From homework to a global business」와 「How doing homework for friends inspired a global company」라는 제목이 쓰였다."),
    ),
    739654: (
        ("<ref>Andrée Giselle Simard, The Manuscript Torino J.II.9: A Late Medieval Perspective on Musical Life and Culture at the Court of the Lusignan Kings at Nicosia\", pp.35-36, December 2005, retrieved on 15 June 2009</ref>",
         " 이 표현은 Andrée Giselle Simard의 「The Manuscript Torino J.II.9: A Late Medieval Perspective on Musical Life and Culture at the Court of the Lusignan Kings at Nicosia」(2005년 12월) 35–36쪽에 나온다. 이 자료의 열람일은 2009년 6월 15일이다."),
    ),
    753514: (
        ("<ref name=grove>Ashbrook, William. \"Marino Faliero\", The New Grove Dictionary of Opera''', Oxford Music Online, accessed 17 June 2012 </ref>",
         " 윌리엄 애슈브룩은 Oxford Music Online에서 열람할 수 있는 《The New Grove Dictionary of Opera》의 「Marino Faliero」 항목에서 이 오페라를 다룬다. 해당 항목의 열람일은 2012년 6월 17일이다."),
    ),
    796119: (
        ("<ref>레닌그라드 사본의 모음 부호 및 문자 형태에 대해서는 다음을 참고할 것 : Israel Yeivin, The Aleppo Codex of the Bible: A Study of its Vocalization and Accentuation (Jerusalem: Magnes, 1968) pp. 357-359 (히브리어).</ref>, 수정 부분",
         " 레닌그라드 사본의 모음 부호와 문자 형태는 Israel Yeivin의 《The Aleppo Codex of the Bible: A Study of its Vocalization and Accentuation》(예루살렘 Magnes, 1968) 357–359쪽에서 다루며, 이 자료는 히브리어로 씌었다. 수정 부분"),
    ),
    796364: (
        ("<ref>J. G. Nichols, ed., Diary of Henry Machyn, Camden Society (1848), p. 401; Letters & Papers, vol. 2 (1864), no. 4282</ref>",
         " 이 일화의 출처는 J. G. Nichols가 편집한 《Diary of Henry Machyn》(Camden Society, 1848) 401쪽과 《Letters & Papers》 제2권(1864) 제4282호다."),
    ),
    944492: (
        ("<ref name=\"telegraph2\">(2011) Lives Remembered. The Daily Telegraph, London, 10 February 2010. Accessed on 2010-02-22. Also on web.archive.org</ref>",
         " 《The Daily Telegraph》의 「Lives Remembered」에서 이 사망 소식을 다뤘다. 서지에 적힌 기사 날짜는 2010년 2월 10일이고 열람일은 같은 해 2월 22일이다."),
    ),
    1026048: (
        (" [? 마르쿠스] 셈프로니우스 푸스쿠스 - 78/79년<ref>달리 언급되지 않는 한, 78/79년부터 136/137년까지 총독들 목록은 다음에서 출처로 한다: 베르너 에크, \"Jahres- und Provinzialfasten der senatorischen Statthalter von 69/70 bis 138/139\", Chiron, 12 (1982), pp. 281–362; 13 (1983), pp. 147–237.</ref>",
         "달리 표시하지 않은 78/79년부터 136/137년까지의 총독 명단은 베르너 에크의 「Jahres- und Provinzialfasten der senatorischen Statthalter von 69/70 bis 138/139」에 근거한다. 이 논문은 《Chiron》 12권(1982) 281–362쪽과 13권(1983) 147–237쪽에 실렸다.\n [? 마르쿠스] 셈프로니우스 푸스쿠스 - 78/79년"),
    ),
    1153182: (
        ("<ref>Michaud, Jean (April 2006). </cite></ref>。",
         " 이 견해는 Jean Michaud의 2006년 4월 자료에 실려 있다."),
    ),
    1162715: (
        ("<ref name=\"Zhang\">[https://books.google.com/books?id=R9QNAAAAQAAJ&pg=PA57 The Ceramics of China: the Yangshao culture, the Song dynasty By Gen Yang, Xiqiu Zhang, Wengu Shao, p.57]</ref>",
         " 이 설명의 출처는 Gen Yang, Xiqiu Zhang, Wengu Shao의 《The Ceramics of China: The Yangshao Culture, the Song Dynasty》 57쪽이다."),
    ),
    1442095: (
        ("<ref>Rose, J.D. 2003. A Critique of the paper: \"Do fish have nociceptors: Evidence for the evolution of a vertebrate sensory system\" </</ref>",
         " J. D. Rose는 2003년의 「A Critique of the Paper: ‘Do Fish Have Nociceptors: Evidence for the Evolution of a Vertebrate Sensory System’」에서 이 실험의 해석을 비판했다."),
    ),
    1450379: (
        ("<ref>Hinshaw, G.; et al. (2009). \"Five-year Wilkinson microwave anisotropy probe (WMAP) observations: Data processing, sky maps, and basic results\". The Astrophysical Journal Supplement. 180 (2): 225–245. arXiv:0803.0732.</ref name=AP2015>Ade, P.A.R.; et al. (2016). \"Planck 2015 results. XIII. Cosmological parameters\". Astron. Astrophys. 594 (13): A13. arXiv:1502.01589.</ref>",
         " G. Hinshaw 등은 WMAP 5년 관측을 다룬 「Five-year Wilkinson microwave anisotropy probe (WMAP) observations: Data processing, sky maps, and basic results」를 《The Astrophysical Journal Supplement》 180권 2호(2009) 225–245쪽에 실었다(arXiv:0803.0732). P. A. R. Ade 등은 「Planck 2015 results. XIII. Cosmological parameters」를 《Astronomy & Astrophysics》 594권 A13(2016)에 실었다(arXiv:1502.01589)."),
    ),
    5552: (
        ("외부 링크 \n\n  부산 강서구청 (공식)\n\n\n",
         "\n"),
    ),
    6714: (
        ("외부 링크 \n  중원구청 (공식)\n\n\n\n",
         "\n"),
    ),
    6731: (
        ("외부 링크 \n \n  안산시청 (공식) \n\n \n\n\n",
         "\n"),
    ),
    23793: (
        ("외부 링크 \n\n  산청군청 (공식)\n\n\n\n",
         "\n"),
    ),
    23953: (
        ("외부 링크 \n\n  영암군청 (공식)\n\n \n\n\n",
         "\n"),
    ),
    27841: (
        ("가시에 싸인 견과인 밤이 열린다.",
         "가시에 싸인 견과인 밤이 열린다. 밤은 식용 견과다."),
        ("외부 링크 \nhttps://bamkkot8.com/ \n\n https://web.archive.org/web/20051107233722/http://www.chestnut.or.kr/\n\n \n식용 씨앗과 견과류\n\n",
         "\n"),
    ),
    59576: (
        ("외부 링크 \n간쑤인민방송 공식 홈페이지\n\n중화인민공화국의 라디오\n\n",
         "\n"),
    ),
    59577: (
        ("허베이성의 성급 방송국이다.",
         "허베이성의 성급 라디오 방송국이다."),
        ("외부 링크 \n허베이인민방송 공식 홈페이지 \n\n중화인민공화국의 라디오\n\n",
         "\n"),
    ),
    76807: (
        ("외부 링크 \n중국망 한국어 공식 홈페이지\n\n중화인민공화국의 대중 매체\n\n",
         "\n"),
    ),
    76994: (
        ("외부 링크 \n중화인민공화국 수리부 공식 홈페이지\n\n수리부\n\n",
         "\n"),
    ),
    82045: (
        ("는 도치기현 우쓰노미야시 출신 사이타마현에서 자란 일본의 여자 성우, 가수다.",
         "치하라 미노리는 1980년에 태어난 일본의 성우이자 가수다. 도치기현 우쓰노미야시 출신으로 사이타마현에서 자랐다."),
        ("외부 링크 \n 공식 홈페이지\n 구(旧) 공식 홈페이지\n 공식 블로그「minorhythm（미노리듬）」\n 치하라 미노리의 radio minorhythm（란티스 웹라디오 방송중인 인터넷 라디오）\n\n1980년 출생\n살아있는 사람\n일본의 여자 성우\n우쓰노미야시 출신\n도치기현의 가수\n\n",
         "공식 블로그의 이름은 「minorhythm(미노리듬)」이다. 《치하라 미노리의 radio minorhythm》은 란티스 웹라디오에서 방송되었다.\n\n"),
    ),
    97466: (
        ("외부 링크 \n\n공식 사이트\n\n",
         ""),
    ),
    104755: (
        ("외부 링크 \n지능일렉콤 공식 홈페이지\n\n사운드 카드\n\n",
         "\n"),
    ),
    219513: (
        ("외부 링크 \n 룬드 대학교 - 공식사이트\n 룬드 공대 - 공식사이트\n 룬드 경제경영 학교 - 공식 사이트\n\n \n",
         ""),
    ),
    278972: (
        ("수도 산호세를 연고지로 한다.",
         "수도 산호세를 연고지로 한다. 이 구단은 1935년에 창단되었다."),
        ("외부 링크\n- 데포르티보 사프리사 공식 홈페이지\n\n코스타리카의 축구단\n1935년 설립된 축구단\n\n\n",
         "\n"),
    ),
    320685: (
        ("SHUFFLE! 시리즈 여섯 번째 작품이다.",
         "SHUFFLE! 시리즈 여섯 번째 작품이다. 윈도우용 미소녀 연애 어드벤처 게임이다."),
        ("외부 링크 \n  네이블 공식 웹사이트 (성인 권장)\n  네이블의 SHUFFLE! Love Rainbow 공식 웹사이트 (성인 권장)\n\n네이블\n윈도우 게임\n미소녀 게임\n연애 어드벤처 게임\n2011년 비디오 게임\n\n",
         "\n"),
    ),
    325977: (
        ("외부 링크\n지바 도시 모노레일 공식 웹사이트\n\n",
         ""),
    ),
    721411: (
        ("외부 링크 \n 김과장 공식사이트\n\n\n",
         "\n"),
    ),
    1100724: (
        ("외부 링크 \n LFP 세군다 디비시온 공식 웹사이트\n\n\n",
         "\n"),
    ),
    160647: (
        ('직업을 구했다.<ref>[http://www.telegraph.co.uk/arts/main.jhtml?xml=/arts/2006/02/19/svanna19.xml 멜리사 휘트워스, "신데렐라 소프라노". "텔레그래프, 2006년 2월 19일}}.]</ref>.',
         '직업을 구했다. 멜리사 휘트워스는 2006년 2월 19일 《텔레그래프》에 실린 「신데렐라 소프라노」에서 이 이력을 소개했다.'),
    ),
    372486: (
        ('레나르트<ref>Philipp Lenard: Ideelle Kontinentalsperre, München 1940.</ref>와 슈타르크는',
         '이 대목에서는 필리프 레나르트의 《Ideelle Kontinentalsperre》(뮌헨, 1940)를 인용했다. 레나르트와 슈타르크는'),
    ),
    21383: (
        ('너비이다.<ref name=Stuff>How New York Works, How Stuff Works, accessed 2009년 6월 30일.</ref>',
         '너비이다. 섬의 크기를 설명하는 이 대목은 How Stuff Works의 「How New York Works」에 근거하며, 이 자료의 열람일은 2009년 6월 30일이다.'),
    ),
    177405: (
        ('이 주장에 대한 반박이 곧바로 제기되었고,<ref name="bbcTriNotToro">, Bowdler, Neil(1 March 2012).Triceratops and Torosaurus dinosaurs \'two species, not one\'\'\'. Retrieved July 29, 2013 from http://www.bbc.co.uk/news/science-environment-17192624</ref>',
         '이 주장에는 곧바로 반박이 제기되었다. 닐 보들러는 2012년 3월 1일 BBC 기사 「Triceratops and Torosaurus dinosaurs ‘two species, not one’」에서 이 논쟁을 다뤘다. 이 기사의 열람일은 2013년 7월 29일이다.'),
    ),
    525932: (
        ('가수이다.<ref>http://www.discogs.com/artist/412087-Molly-Smitten-Downes, 2014년 3월 16일 discogs.com에서 확인</ref>',
         '가수이다. 이 약력에는 2014년 3월 16일에 열람한 Discogs의 아티스트 기록(항목 412087)이 인용되었다.'),
    ),
    692524: (
        ('<ref>Heikki Eskelinen: Itsenäisyytemme vuosikymmenet, s. 61. Helsinki: Yhtyneet Kuvalehdet, 1966.</ref>',
         ' 이 대목은 헤이키 에스켈리넨의 《Itsenäisyytemme vuosikymmenet》(헬싱키, Yhtyneet Kuvalehdet, 1966) 61쪽을 인용한다.'),
    ),
    930872: (
        ('322년경 오늘날의 중국: 등자.<ref name="autogenerated2">[https://web.archive.org/web/20071013231319/http://findarticles.com/p/articles/mi_m1310/is_1988_Oct/ai_6955868 "The stirrup – history of Chinese science." UNESCO Courier, October, 1988]</ref> 중국 전체로 널리 퍼진 것은 477년 이전.',
         '322년경 오늘날의 중국에 등자가 있었다. 이 기록에는 《UNESCO Courier》 1988년 10월호의 「The stirrup – history of Chinese science」가 인용되어 있다. 등자는 477년 이전에 중국 전체에 널리 퍼졌다.'),
    ),
    1066563: (
        ('[[파일:Syrischer Maler von 1354 001.jpg|섬네일|An illustration from a 1354 Syrian edition of the Panchatantra, an ancient Indian collection of animal fables. '
         'The original work is believed to be composed around the 3rd century BCE, based on older oral traditions, including "animal fables that are as old as we are able to imagine".'
         '<ref name="i-c-r.org.uk">Doris Lessing, Problems, Myths and Stories] , London: Institute for Cultural Research Monograph Series No. 36, 1999, p 13</ref>]',
         'An illustration appears in a 1354 Syrian edition of the Panchatantra. The Panchatantra is an ancient Indian collection of animal fables. '
         'The original work is believed to have been composed around the third century BCE, drawing on older oral traditions, including “animal fables that are as old as we are able to imagine.” '
         'This account cites page 13 of Doris Lessing’s Problems, Myths and Stories, published in London in 1999 as No. 36 in the Institute for Cultural Research Monograph Series.'),
    ),
    1166157: (
        ('가 있다.<ref name=Research>Lewis MK, Marshall I (2011). \'LGBT Psychology: Research Perspectives and People of African Descent\'\', Springer Science & Business Media, p. 25, .</ref>',
         '가 있다. 이 사례에 관한 출처는 M. K. Lewis와 I. Marshall의 《LGBT Psychology: Research Perspectives and People of African Descent》(Springer Science & Business Media, 2011) 25쪽이다.'),
    ),
    1187038: (
        ("<ref>Wiseman, T.P., Satyrs in Rome? The background to Horace's Ars Poetica, The Journal of Roman Studies, 1988, 78, p. 7, note 52}}</ref>",
         ' 이 대목의 출처는 T. P. Wiseman의 「Satyrs in Rome? The background to Horace’s Ars Poetica」(《The Journal of Roman Studies》 78권, 1988) 7쪽의 주 52다.'),
    ),
    656444: (
        ("권영수(1957년 3월 7일(음력 2월 6일) ~ )는 2021년 11월 1일 현재 LG에너지솔루션의 대표이사 부회장으로 임명된 KAIST 출신 기업인이다.<ref>권영수 네이버 인물정보</ref>\n",
         "권영수는 1957년 3월 7일(음력 2월 6일)에 태어난 KAIST 출신 기업인이다. 2021년 11월 1일 기준 LG에너지솔루션 대표이사 부회장이었다. 그의 이력은 네이버 인물정보에 실려 있다.\n"),
    ),
    739054: (
        ("올림피아스(, 기원전 375년 - 기원전 316년)는 에피로스의 국왕 네오프톨레모스 1세의 딸이자, 마케도니아 왕국의 필리포스 2세의 네 번째 아내이자, 알렉산더 3세 (대왕)의 어머니이다. 광란적인 뱀 숭배를 하는 디오니소스 신앙의 열렬한 신자이며, 1세기 전기작가 플루타르코스는 올림피아스가 뱀과 함께 잠을 잤었던 가능성을 시사하고 있다.<ref>뱀에 대한 헛소리는 플루타르코스의 Life of Alexander (2.6)에서 나왔으며, Robin Lane Fox의, Alexander the Great 1973:26 p. 504에 따르면; 팍스는 뱀손잡이가 유스티누스가 9.5.9에서 언급한 'stuprum이었다고 주장한다.</ref>\n",
         "올림피아스(기원전 375년~기원전 316년)는 에피로스 국왕 네오프톨레모스 1세의 딸이자 마케도니아 국왕 필리포스 2세의 네 번째 아내이며, 알렉산더 3세의 어머니다. 뱀을 숭배하는 의식과 관련된 디오니소스 신앙의 신자였다. 1세기 전기 작가 플루타르코스는 《알렉산더 전기》 2.6에서 올림피아스가 뱀과 함께 잠을 잤을 가능성을 시사했다. 로빈 레인 폭스는 《Alexander the Great》(1973, 504쪽)에서 뱀을 다루는 행위가 유스티누스가 9.5.9에서 언급한 ‘stuprum’에 해당한다고 해석했다.\n"),
    ),
    926557: (
        ("2019년 8월 16일 유희열의 스케치북(어쩌다 신인 특집)<ref>심민경 기자 (2019년 8월 17일). [유희열의 스케치북] 가창력 수준급! 대형 신인 HYNN(흰) ♬ 시든 꽃에 물을 주듯. KBS미디어. 2020년 6월 18일 확인.</ref>\n",
         "2019년 8월 16일 《유희열의 스케치북》의 ‘어쩌다 신인’ 특집에 출연했다. 심민경은 2019년 8월 17일 KBS미디어에 「[유희열의 스케치북] 가창력 수준급! 대형 신인 HYNN(흰) ♬ 시든 꽃에 물을 주듯」이라는 기사를 실었다. 이 기사의 열람일은 2020년 6월 18일이다.\n"),
    ),
    526382: (
        ("지정 목록\n\n제1호 ~ 제100호\n\n제101호 ~ 제200호\n\n제201호 ~ 제300호\n\n제301호 ~ 제400호\n\n제401호 ~ 제500호\n\n제501호 ~ 제600호\n\n제601호 ~ 제700호\n\n제701호 ~ 제800호\n\n제801호 ~ 제900호\n\n\n외부 링크 \n 문화재청 국가등록문화재 검색\n\n 00\n",
         ""),
    ),
    20457: (
        ("길안초등학교 길송분교 인근에 있는 소태나무이다.",
         "길안초등학교 길송분교 인근에 있는 소태나무다. 소태나무과에 속한다."),
        ("현지 안내문\n\n같이 보기 \n 길안초등학교 길송분교\n\n각주\n\n참고 자료 \n \n\n경상북도의 천연기념물\n송사동 소태나무\n소태나무과\n",
         ""),
    ),
    26180: (
        ("참고 문헌 \n Elmasri, Navathe:Fundamentals of database systems, Addision Wesley.\n\n외부 링크 \n SourceForge의 데이터베이스 관련 프로그램\n\n데이터베이스 관리 시스템\n",
         "데이터베이스 시스템의 구조와 원리를 다루는 교재로 Elmasri와 Navathe의 《Fundamentals of Database Systems》가 있다. Addison Wesley에서 출판했다.\n"),
    ),
    180660: (
        ("같이 보기 \n 빨래\n 의류 건조기\n\n각주\n\n참고 자료 \n\n세탁\n생활용품\n가전제품\n원심분리기\n미국의 발명품\n19세기 발명품\n",
         ""),
    ),
    454619: (
        ("같이 보기 \n 부석사\n 부석사 조사당\n\n참고 자료 \n \n\n경상북도의 국보\n조사당 벽화\n고려의 그림\n14세기 회화 작품\n1377년 작품\n",
         ""),
    ),
    1231274: (
        ("베를린 리히텐베르크역역은",
         "베를린 리히텐베르크역은"),
        ("경계상에 인접한 철도역이다.",
         "경계상에 인접한 철도역이다. 베를린 S반과 지하철 U5호선이 정차한다."),
        ("참고 문헌 \n \n Bernd Kuhlmann: Berliner Verkehrsknoten: Berlin-Lichtenberg. In: Verkehrsgeschichtliche Blätter, 37. Jg., Heft 5 (September/Oktober 2010), S. 117–129.\n\n외부 링크 \n\n Umgebungsplan des Bahnhofs\n Bahnhof Berlin-Lichtenberg auf stadtschnellbahn-berlin.de\n\n베를린 지하철역\n베를린 S반역\n베를린의 철도역\n1881년 개업한 철도역\n1930년 개업한 철도역\n베를린 지하철 5호선\n",
         "Bernd Kuhlmann은 리히텐베르크역을 다룬 「Berliner Verkehrsknoten: Berlin-Lichtenberg」를 《Verkehrsgeschichtliche Blätter》 제37권 제5호(2010년 9~10월) 117–129쪽에 실었다.\n"),
    ),
    1232314: (
        ("참고 문헌\n\n추가 자료 \n\n Davis, C. E. et al. (2016).  Re-investigating Tilaurakot’s Ancient Fortifications: A Preliminary Report of Excavations Through the Northern Rampart of Tilaurakot. Ancient Nepal 190, 30-46\n Coningham, R.A.E.; Acharya, K.P.; Manuel, M.J. and Davis, C.E.; Kunwar, R.B.; Simpson, I.A.; Strickland, K.M.; Smaghur, E.; Tremblay, J.; Lafortune-Bernard, A. (2018). Archaeological investigations at Tilaurakot-Kapilavastu, 2014-2016, Ancient Nepal 197-198, 5-59\n\n네팔의 마을\n유네스코 잠정 유산\n",
         "C. E. Davis 등은 틸라우라콧 북쪽 성벽의 발굴을 다룬 「Re-investigating Tilaurakot’s Ancient Fortifications: A Preliminary Report of Excavations Through the Northern Rampart of Tilaurakot」을 2016년 《Ancient Nepal》 제190호 30–46쪽에 실었다. R. A. E. Coningham, K. P. Acharya, M. J. Manuel, C. E. Davis, R. B. Kunwar, I. A. Simpson, K. M. Strickland, E. Smaghur, J. Tremblay, A. Lafortune-Bernard가 쓴 「Archaeological investigations at Tilaurakot-Kapilavastu, 2014-2016」은 2018년 같은 학술지 제197–198호 5–59쪽에 실렸다.\n"),
    ),
    1247536: (
        ("역사\n\n출신 선수\n\n참고 문헌 \n \n 약속의 땅 통영 제59회 춘계대학축구연맹전 출전 선수 명단\n\n같이 보기 \n 중앙대학교\n\n외부 링크 \n 중앙대학교 웹사이트\n 한국대학축구연맹\n\n경기도의 대학 축구부\n1953년 설립된 축구단\n안성시의 축구단\n대한민국의 대학 축구단\n중앙대학교\nU리그1 구단\n",
         "중앙대학교 축구부는 U리그1에 참가한다.\n"),
    ),
    248246: (
        ("2008년 Rosebleu의 창사에 참여하고 현재 소속 중이다.",
         "2008년 Rosebleu의 창사에 참여해 그곳에서 활동했다."),
        ("각주 \n [부고] 아고바리아 선생님 - MF문고\n 「용사와 마왕이 전격 동맹! 」저자의 아고바리아 씨, 사망 ITmedia 2016년 3월 31일\n\n일본의 작가\n생년 미상\n2016년 사망\n",
         "아고바리아는 2016년에 사망했다. MF문고에 부고가 실렸고, ITmedia는 2016년 3월 31일에 그의 사망 소식을 보도했다. 출생 연도는 알려져 있지 않다.\n"),
    ),
    88188: (
        ("손로원 작사로 손인호가 부른 노래이다.",
         "손로원 작사로 손인호가 부른 1953년 한국어 트로트 곡이다."),
        ("각주 \n\n트로트 노래\n대한민국의 노래\n한국어 노래\n1953년 노래\n비를 소재로 한 노래\n",
         ""),
    ),
    78199: (
        ("외부 링크 \n 광주문화예술회관 - 공식 웹사이트\n광주시립극단 갑질 사태 총정리\n\n1991년 설립\n대한민국의 예술 회관\n광주광역시의 예술 시설\n광주 북구 소재의 관공서\n문화예술회관\n",
         ""),
    ),
    228334: (
        ("경기장 \n2008년 하계 올림픽 레슬링 남자 그레코로만형 74kg급 경기는 개최 도시인 베이징에 있는 중국 농업대학 체유관에서 경기가 열렸다.\n\n경기 일정 \n경기 시간은 중국 표준시 (UTC+8) 기준이다.\n\n경기 결과\n\n본선 (1)\n\n본선 (2)\n\n패자부활전\n\n결승전\n\n메달리스트\n\n각주 \n Competition format\n\n남자 그레코로만형 74kg급\n",
         "경기 시각은 중국 표준시(UTC+8)를 기준으로 했다.\n"),
    ),
    279613: (
        ("같이 보기 \n 소셜 네트워크 서비스\n 댓글\n 악성 댓글\n 제한적 본인 확인제\n 라이브리\n\n각주 \n\n의사소통\n인터넷 용어\n인터넷 문화\n",
         ""),
    ),
    492682: (
        ("외부 링크 \n  (마이스페이스)\n 10 Years of Mellow Gold Documentary (retrospective documentary done for anniversary of the Beck's first album, features interviews with Rothrock)\n\n미국의 음악 프로듀서\n미국의 작곡가\n살아있는 사람\n",
         "벡의 첫 음반 10주년을 기념해 제작된 다큐멘터리 《10 Years of Mellow Gold Documentary》에는 로스록의 인터뷰가 실렸다.\n"),
    ),
    679401: (
        ("각주\n\n참고 사항 \n 고현정과 조인성은 SBS 주말드라마 《봄날》 이후로 12개월만에 재회한다.\n\n외부 링크 \n \n \n\n2016년 드라마\n2010년대 대한민국의 텔레비전 프로그램\n노희경 시나리오 작품\n스튜디오 드래곤 텔레비전 프로그램\n2016년에 시작한 대한민국 TV 프로그램\n2016년에 종료한 대한민국 TV 프로그램\ntvN 금토드라마\n백상예술대상 TV부문 작품상\n",
         "노희경이 극본을 쓴 스튜디오 드래곤의 텔레비전 작품이다. 고현정과 조인성은 SBS 드라마 《봄날》 이후 이 작품에 다시 함께 출연했다.\n"),
    ),
    1131931: (
        ("같이 보기 \n 2022년 동계 올림픽\n 2022년 동계 올림픽 컬링\n 2022년 동계 올림픽 컬링 남자\n 2022년 동계 올림픽 컬링 믹스더블\n\n\n외부 링크 \n \n\n2022년 동계 올림픽 컬링\n2022년 동계 올림픽 여자 종목\n",
         ""),
    ),
    599480: (
        ("<ref>[http://www.sportske.net/vest/domaci-fudbal/milivojevic-hvala-jankovicu-bicu-jos-bolji-52438.html Milivojević: \"Hvala Jankoviću, biću još bolji]  at Sportske.net</ref>",
         " Sportske.net은 이 내용을 「Milivojević: ‘Hvala Jankoviću, biću još bolji’」라는 제목으로 다뤘다."),
    ),
    10077: (
        ("<ref>Amidu, A. A. (1995). 'Kiswahili, a continental language: how possible is it? Part I.' Nordic Journal of African Studies, 4(2), p. 61.</ref>",
         " 이 설명은 A. A. Amidu의 「Kiswahili, a continental language: how possible is it? Part I.」(《Nordic Journal of African Studies》 제4권 제2호, 1995, 61쪽)에 근거한다."),
    ),
    1451252: (
        ("<ref>Amidu, A. A. (1995). 'Kiswahili, a continental language: how possible is it? Part I.' Nordic Journal of African Studies, 4(2), p. 61.</ref>",
         " 이 설명은 A. A. Amidu의 「Kiswahili, a continental language: how possible is it? Part I.」(《Nordic Journal of African Studies》 제4권 제2호, 1995, 61쪽)에 근거한다."),
    ),
    474431: (
        ("<ref>Quasten et al. 1970:6.</ref>",
         " 이 설명은 Quasten 외의 1970년 문헌 6쪽에 근거한다."),
    ),
    504052: (
        ("에이블 테스페이(, 1990년 2월 16일 ~ )는 위켄드()라는",
         "에이블 테스페이(1990년 2월 16일 ~ )는 위켄드라는"),
        ("<ref>Ritchie, Kevin (25 July 2011). The Weeknd’s perfect premiere .NOW Toronto\". Retrieved 28 March 2012</ref>",
         " Kevin Ritchie는 2011년 7월 25일 《NOW Toronto》에 이 공연을 다룬 「The Weeknd’s perfect premiere」를 실었다. 해당 기사의 열람일은 2012년 3월 28일이다."),
    ),
    401272: (
        ("머리사 토메이(, 1964년 12월 4일 ~ )는",
         "머리사 토메이(1964년 12월 4일 ~ )는"),
        (" 1986: Daughters - Cetta 역 (오프브로드웨이)<ref>[http://www.lortel.org/Archives/Production/1849 Daughters\"] lortel.org, retrieved March 20, 2017</ref>\n",
         "1986년 오프브로드웨이 공연 《Daughters》에서 Cetta 역을 맡았다. 공연 기록은 lortel.org에 있으며 열람일은 2017년 3월 20일이다.\n"),
    ),
    596794: (
        (" 1989년 3월 1일 동계분교장<ref>개교 1943.09.15총 졸업생 수 40회, 1,679명</ref> 편입\n",
         "1989년 3월 1일 동계분교장이 편입되었다. 동계분교장은 1943년 9월 15일에 문을 열었으며, 40회에 걸쳐 1,679명이 졸업했다.\n"),
        (" 1994년 3월 1일 계곡분교장<ref>개교 1947.10.05총 졸업생 수 42회, 1,492명</ref>, 동인분교장<ref>개교 1969.03.01총 졸업생 수 25회, 716명</ref> 편입\n",
         "1994년 3월 1일 계곡분교장과 동인분교장이 편입되었다. 계곡분교장은 1947년 10월 5일에 문을 열었고 42회에 걸쳐 1,492명이 졸업했다. 동인분교장은 1969년 3월 1일에 문을 열었고 25회에 걸쳐 716명이 졸업했다.\n"),
        (" 1999년 9월 1일 삼계분교장<ref>개교 1957.04.01총 졸업생 수 25회, 1,924명</ref>, 예안초등학교 부포분교장 본교 편입\n",
         "1999년 9월 1일 삼계분교장과 예안초등학교 부포분교장이 본교에 편입되었다. 삼계분교장은 1957년 4월 1일에 문을 열었고 25회에 걸쳐 1,924명이 졸업했다.\n"),
    ),
    48778: (
        ("참고 자료 \n 《클래식 명곡이야기》 (아름출판사 1993. 3. 25 출판)\n\n외부 링크 \n \n\n1943년\n관현악곡\n벨러 버르토크의 작품\n",
         "이 작품의 참고 자료로는 아름출판사가 1993년 3월 25일에 출판한 《클래식 명곡이야기》가 있다.\n"),
    ),
    67919: (
        ("참고 자료 \n\n Cunnington, Susan. The story of arithmetic, a short history of its origin and development. Swan Sonnenschein, London, 1904.\n Dickson, Leonard Eugene. History of the theory of numbers. Three volumes. Reprints: Carnegie Institute of Washington, Washington, 1932. Chelsea, New York, 1952, 1966.\n Leonhard Euler, Elements of Algebra Tarquin Press, 2007\n Fine, Henry Burchard (1858-1928). The number system of algebra treated theoretically and historically. Leach, Shewell & Sanborn, Boston, 1891.\n Karpinski, Louis Charles (1878-1956). The history of arithmetic. Rand McNally, Chicago, 1925. Reprint: Russell & Russell, New York, 1965.\n Ore, Øystein. Number theory and its history. McGraw-Hill, New York, 1948.\n Weil, Andre. Number theory: an approach through history. Birkhauser, Boston, 1984. Reviewed: Math. Rev. 85c:01004.\n",
         "Susan Cunnington은 산술의 기원과 발전을 다룬 《The Story of Arithmetic》을 1904년 런던의 Swan Sonnenschein에서 출판했다. Louis Charles Karpinski의 《The History of Arithmetic》은 1925년 시카고의 Rand McNally에서 출판되었고, 1965년 뉴욕의 Russell & Russell에서 재간되었다.\n\n수 체계를 다룬 책으로 Henry Burchard Fine의 《The Number System of Algebra Treated Theoretically and Historically》(보스턴, Leach, Shewell & Sanborn, 1891)가 있다. Leonhard Euler의 《Elements of Algebra》는 2007년 Tarquin Press에서 출판되었다. 정수론의 역사를 다룬 책에는 Leonard Eugene Dickson의 3권짜리 《History of the Theory of Numbers》, Øystein Ore의 《Number Theory and Its History》(뉴욕, McGraw-Hill, 1948), Andre Weil의 《Number Theory: An Approach Through History》(보스턴, Birkhauser, 1984)가 있다. Dickson의 책은 1932년 워싱턴의 Carnegie Institute of Washington과 1952년 및 1966년 뉴욕의 Chelsea에서 재간되었다.\n"),
        ("외부 링크 \n\n What is arithmetic?\n MathWorld article about arithmetic\n The New Student's Reference Work/Arithmetic\n 네이버 캐스트-사칙연산 왜 곱셈을 먼저 할까?\n\n산술\n수학 교육\n",
         ""),
    ),
    77658: (
        ("키부츠 (kibbutz ( 또는 ); 복수형: kibbutzim ( 또는 ))는 이스라엘의 집단 농업 공동체이다.",
         "키부츠(kibbutz, 복수형 kibbutzim)는 이스라엘의 집단 농업 공동체이자 농업협동조합의 한 형태다."),
        ("외부 링크 \n\n \n \n\n이스라엘의 문화\n이스라엘의 농업\n농업협동조합\n",
         ""),
    ),
    341016: (
        ("각주\n\n외부 링크 \n \n\n함평군의 행정 구역\n전라남도의 읍·면\n",
         ""),
    ),
    535080: (
        ("외부 링크 \n MBC 트라이앵글 공식사이트\n",
         ""),
    ),
    912616: (
        ("《인서울 - 내가 독립하는 유일한 방법》은 2019년 7월 29일부터 V라이브, 네이버 TV에서 공개되었으며, 2019년 8월 4일(8월 5일)부터 2019년 9월 29일(9월 30일) JTBC에서 방영된 드라마로 편성하였다.\n",
         "《인서울 - 내가 독립하는 유일한 방법》은 대한민국의 웹드라마다. 2019년 7월 29일부터 V라이브와 네이버 TV에서 공개되었고, 2019년 8월 4일(8월 5일)부터 2019년 9월 29일(9월 30일)까지 JTBC에서 방영되었다.\n"),
        ("각주\n\n외부 링크 \n 인서울 - 내가 독립하는 유일한 방법 홈페이지\n\n대한민국의 웹드라마\n2019년 드라마\nJTBC 웹드라마\n",
         ""),
    ),
    83848: (
        ("사진술에 있어서 뷰파인더(Viewfinder)란 사진사가 사진을 찍기 위해 혹은 초점을 맞추기 위해 들여다 보는 기구로 대한민국에서는 국립국어원이 보기창으로 다듬었다.\n",
         "뷰파인더(Viewfinder)는 사진사가 사진을 촬영하거나 초점을 맞출 때 들여다보는 기구다. 국립국어원은 뷰파인더를 ‘보기창’으로 다듬었다.\n"),
        ("같이 보기 \n 전자식 뷰파인더\n 웨이스트-레벨 파인더\n\n각주 \n\n사진 장비\n사진기의 기능\n광학\n",
         ""),
    ),
    85974: (
        ("같이 보기 \n 전자 음악\n MIDI\n 컴퓨터 음악\n 음악 게임\n 칩튠\n 하드코어 테크노\n 비디오 게임\n 효과음\n\n외부 링크 \n CVGM - an interactive game music radio\n\n비디오 게임 개발\n",
         ""),
    ),
    96917: (
        ("분류 \n 주로 불리는 층에 따라: 대중가요 (일반 대중), 군가 (군인), 동요 (어린이), 국가 (국민)\n 격식 있는 자리에서 불리는 노래: 교가, 국가, 군가.\n 전승 기간에 따라: 민요, 대중가요\n\n같이 보기 \n\n 음악\n\n노래\n예술\n",
         "노래는 주로 부르는 사람에 따라 대중가요, 군가, 동요, 국가로 분류할 수 있다. 대중가요는 일반 대중이, 군가는 군인이, 동요는 어린이가, 국가는 국민이 주로 부른다. 격식 있는 자리에서 불리는 노래에는 교가·국가·군가가 있다. 전승 기간에 따라 민요와 대중가요를 나누기도 한다.\n"),
    ),
    104817: (
        ("분류 \n토속민요는 기능에 따라 다음과 같이 크게 3가지로 분류할 수 있다.\n\n 노동요\n 의례요(儀禮謠) 또는 의식요(儀式謠)\n 유흥요(遊興謠) 또는 유희요(遊戱謠)\n\n각주 \n\n민요\n",
         "토속민요는 기능에 따라 노동요, 의례요(儀禮謠) 또는 의식요(儀式謠), 유흥요(遊興謠) 또는 유희요(遊戱謠)로 나뉜다.\n"),
    ),
    114859: (
        ("분류 \n이와나미 신서는 적색판, 청색판, 황색판, 신적색판의 4종류로 분류된다.\n\n참고 문헌 \n 이와나미 쇼텐 편집부 편, 《이와나미 신서의 50년》(岩波新書の50년 ), 이와나미 쇼텐, 1988년.\n\n\n외부 링크 \n이와나미 신서 홈페이지\n\n1938년 창간\n이와나미 쇼텐\n일본의 책\n",
         "이와나미 신서는 적색판, 청색판, 황색판, 신적색판의 네 종류로 나뉜다. 이와나미 쇼텐 편집부가 엮은 《이와나미 신서의 50년》은 1988년 이와나미 쇼텐에서 출판되었다.\n"),
    ),
    177121: (
        ("일본의 가수이자, 배우, 인권 운동가이며, 본명은 오시마 히사시이다.",
         "일본의 록 가수, 배우, 방송인, 인권 운동가였다. 본명은 오시마 히사시이다."),
        ("분류\n1941년 출생\n1985년 사망\n20세기 일본 사람\n일본의 남자 가수\n일본의 록 가수\n일본의 남자 영화 배우\n일본의 남자 뮤지컬 배우\n일본의 탤런트\n일본의 텔레비전 진행자\n일본의 인권 운동가\n일본의 자선가\nNHK 홍백가합전 출연자\n가와사키시 출신\n일본항공 123편 추락 사고로 죽은 사람\n",
         "영화와 뮤지컬에 출연했고 텔레비전 프로그램을 진행했다. 자선 활동을 했으며 NHK 홍백가합전에도 출연했다.\n"),
    ),
    225327: (
        ("노형돈은 대한민국의 가수 겸 작곡가·작사가, 즉 싱어송라이터다.\n",
         "노형돈은 인천광역시 출신의 대한민국 싱어송라이터다. 곡과 가사를 쓰고 한국어로 노래한다.\n"),
        ("분류\n살아있는 사람\n2010년대 가수\n한국어 가수\n대한민국의 남자 싱어송라이터\n대한민국의 남자 가수\n대한민국의 작곡가\n대한민국의 작사가\n인천광역시 출신\n2020년대 가수\n",
         ""),
    ),
    257446: (
        ("갤러리\n\n비잔틴 양식",
         "비잔틴 양식"),
        ("분류\n모스크바의 대성당\n러시아의 세계유산\n모스크바의 관광지\n러시아의 러시아 정교회 대성당\n붉은 광장\n1561년 완공된 건축물\n",
         "대성당은 모스크바의 관광지이기도 하다.\n"),
    ),
    286829: (
        ("유명인(有名人, )은",
         "유명인(有名人)은"),
        ("공인(公人, )으로",
         "공인(公人)으로"),
        ("분류\n\n인터넷 방송인\n\n연예인\n\n인플루언서\n\n운동선수\n\n범죄자\n",
         "대중의 주목을 받는 사람에는 인터넷 방송인, 연예인, 인플루언서, 운동선수뿐 아니라 범죄 등으로 알려진 사람도 있을 수 있다.\n"),
    ),
    387773: (
        ("분류 \n\n프랑스계 아르헨티나인\n",
         ""),
    ),
    84805: (
        ("연예인(演藝人, )은",
         "연예인(演藝人)은"),
        ("분류\n\n탤런트\n\n배우\n\n코미디언\n\nMC\n\n가수\n\n래퍼\n\n댄서\n\n아이돌\n",
         "연예인의 활동 유형으로는 탤런트, 배우, 코미디언, MC, 가수, 래퍼, 댄서, 아이돌 등이 있다.\n"),
    ),
    373248: (
        ("분류 \n도약의 분류 방법은 발의 움직임과 관련이 있다. 이 분류 체계에서는 다섯 가지의 기본 도약 형태로 구별한다:\n 두 발로 도약한 뒤 두 발로 착지\n 한 발로 도약한 뒤 같은 발로 착지\n 한 발로 도약한 뒤 다른 쪽 발로 착지\n 한 발로 도약한 뒤 두 발로 착지\n 두 발로 도약한 뒤 한 발로 착지\n\n참조 \n\n인간의 재주\n스포츠 과학\n",
         "도약은 뛰어오를 때와 착지할 때 어느 발을 쓰는지에 따라 구분할 수 있다. 두 발로 도약한 뒤에는 두 발 또는 한 발로 착지한다. 한 발로 도약한 뒤에는 같은 발, 다른 발 또는 두 발로 착지한다.\n"),
    ),
    387101: (
        ("아이스링크((氷上館))는",
         "아이스링크(氷上館)는"),
        ("분류 \n 아이스하키장 (:en:Ice hockey rink)\n 스피드 스케이트장 (:en:Speed skating rink)\n\n외부 링크 \n\n The Ice Rink – A Brief History\n",
         "빙상 경기의 종목에 따라 아이스하키장이나 스피드스케이트장을 사용한다. 「The Ice Rink – A Brief History」는 아이스링크의 역사를 다룬 자료다.\n"),
    ),
    605062: (
        ("분류 \n아래의 분지도는 라이언 외의 2012년 연구를 따른 것이다:\n\n\n참고 문헌 \n \n\n백악기 후기 북아메리카의 공룡\n켄트로사우루스아과\n2012년 기재된 화석 분류군\n",
         "제노케라톱스는 2012년에 기재된 북아메리카의 화석 분류군이다.\n"),
    ),
    926470: (
        ("[[분류:21세기 대한민국 사람]]\n\n\n1956년 출생\n2011년 사망\n대한민국의 남자 축구 선수\n경주 한국수력원자력 축구단의 축구 선수\n대한민국의 축구 감독\n내셔널리그의 축구 감독\n경주 한국수력원자력 축구단의 축구 코치\n경주 한국수력원자력 축구단의 축구 감독\n함양군 출신\n진주고등학교 동문\n서울시립대학교 동문\n신장암으로 죽은 사람\n20세기 대한민국 사람\n",
         "배종우는 서울시립대학교 동문이다.\n"),
    ),
    1158977: (
        ("대한민국의 테크노 음악 프로듀서, 패션 디렉터로 활동 중이다.",
         "대한민국의 가수이자 테크노 음악 프로듀서, 패션 디렉터다."),
        ("분류 \n 1세대 네이버 패션 인플루언서 (2010~현재)\n",
         "김은비는 2010년부터 1세대 네이버 패션 인플루언서로 활동했다.\n"),
        ("대한민국의 가수\n1989년 출생\n살아있는 사람\n대한민국의 프로듀서\n20세기 대한민국 사람\n",
         ""),
    ),
    21396: (
        (' 상징은 ‘’이다.', ''),
        ('세드나(임시 지정번호 )는', '세드나는'),
        ('데이비드 L. 라비노비츠(예일)가 발견했다.',
         '데이비드 L. 라비노비츠(예일)가 발견했다. 발견 당시 사진은 NASA의 세드나 자료에 실려 있다.'),
        ('몇몇 다른 천체들(e.g. )을', '몇몇 다른 천체를'),
        ('밝은 것은 에리스 정도로 밝을 것(-1.0 등급)이라는 결과를 나타냈다.',
         '밝은 것은 에리스 정도로 밝을 것(-1.0 등급)이라는 결과를 나타냈다. 「How Sedna and family were captured in a close encounter with a solar sibling」(2015년 6월 9일)에서는 세드나와 유사한 천체의 기원에 관한 시나리오를 다룬다.'),
        ('같이 보기 \n 태양계\n 해왕성 바깥 천체\n 세드나족\n 분리천체\n\n각주 \n 내용주\n\n 참조주\n\n외부 링크 \n\n How Sedna and family were captured in a close encounter with a solar sibling (9 Jun 2015)\n NASA\'s Sedna page  (Discovery Photos)\n Mike Brown\'s Sedna page\n\n해왕성 바깥 천체\n2003년 발견한 천체\n왜행성 후보\n세드나족\n',
         ''),
    ),
    35444: (
        ("J. 코흐 (Koch)의 알고리즘을 더하여 4색 정리를 증명하는 데에 성공하였다.",
         "J. 코흐 (Koch)의 알고리즘을 더하여 4색 정리를 증명하는 데에 성공하였다. 케네스 아펠, 볼프강 하켄, 존 코흐는 1977년 12월 《Illinois Journal of Mathematics》 제21권 439–567쪽에 「Every Planar Map Is Four Colorable」을 실었다. 아펠과 하켄의 「Solution of the Four Color Map Problem」은 같은 해 10월 《Scientific American》 제237권 제4호 108–121쪽에 실렸다. 미국 수학회는 1989년 두 사람의 《Every Planar Map Is Four-Colorable》을 출판했다."),
        ("같이 보기 \n\n 그래프 색칠 문제\n 그래프 이론\n 위상수학\n\n참고 문헌 \n\n Appel, Kenneth & Haken, Wolfgang & Koch, John, Every Planar map is Four Colorable, Illinois: Journal of Mathematics: vol.21: pp.439-567, December 1977.\n Appel, Kenneth & Haken, Wolfgang, Solution of the Four Color Map Problem, Scientific American, vol.237 no.4: pp.108-121, October 1977.\n Appel, Kenneth & Haken, Wolfgang, Every Planar Map is Four-Colorable. Providence, RI: American Mathematical Society, 1989.\n Gonthier, Georges, A computer-checked proof of the Four Colour Theorem, unpublished.\n O'Connor and Robertson, The Four Colour Theorem , at the MacTutor archive, 1996.\n Robertson, Neil; Sanders, Daniel; Paul, Seymour; and Thomas, Robin, Efficiently four-coloring planar graphs, New York: ACM Press, 1996.\n Saaty and Kainen, The Four Color Problem: Assaults and Conquest\n Thomas, Robin, Four Colors Suffice, London: Penguin Books Ltd, 2002.\n Thomas, Robin, An Update on the Four-Color Theorem (PDF File), Notices of the American Mathematical Society, Volume 45, number 7 (August 1998)\n Thomas, Robin, The Four Color Theorem, http://www.math.gatech.edu/~thomas/FC/fourcolor.html \n Ringel, G. and Youngs, J. W. T. \"Solution of the Heawood Map-Coloring Problem.\" Proc. Nat. Acad. Sci. USA 60, 438-445, 1968.\n\n분류\n위상수학\n그래프 이론 정리\n명수 4\n평면 그래프\n그래프 색칠\n",
         "4색 정리에 관한 후속 문헌으로는 Neil Robertson, Daniel Sanders, Paul Seymour, Robin Thomas의 「Efficiently four-coloring planar graphs」(ACM Press, 1996)와 Georges Gonthier의 「A computer-checked proof of the Four Colour Theorem」이 있다. O'Connor와 Robertson의 「The Four Colour Theorem」은 1996년 MacTutor 자료실에 실렸다. Saaty와 Kainen의 저서에는 《The Four Color Problem: Assaults and Conquest》가 있다.\n\nRobin Thomas의 「An Update on the Four-Color Theorem」은 1998년 8월 《Notices of the American Mathematical Society》 제45권 제7호에 실렸다. 《Four Colors Suffice》는 2002년 런던의 Penguin Books에서 출판되었다. Thomas의 「The Four Color Theorem」은 조지아 공과대학교 웹 자료에도 실렸다. 히우드 지도 색칠 문제는 G. Ringel과 J. W. T. Youngs의 「Solution of the Heawood Map-Coloring Problem」(《Proceedings of the National Academy of Sciences》 제60권, 438–445쪽, 1968)에서 별도로 다룬다.\n"),
    ),
    59571: (
        ('같이 보기 \n 막명악기\n 드럼셋\n 큰북\n 작은북\n 가온북\n\n\n외부 링크\n\n참고 자료 \n \n\n \n막울림악기\n',
         '북의 종류에는 큰북, 작은북, 가온북 등이 있다.\n'),
    ),
    148641: (
        ('미술의 역사는 지역별, 시대별, 장르별로 세분화하여 전세계 예술 분야를 연구하는 학문이다.\n\n분류 \n 동양 미술사\n 서양 미술사\n\n같이 보기 \n 미술사 연표\n 미술\n 미학\n 역사학\n\n참고 자료 \n\n 한정희 외, 《동양미술사》\n 에른스트 H. 곰브리치 《서양미술사》\n 김원룡, 안휘준 《한국미술의 역사》\n',
         '미술사는 세계 각지의 예술을 지역별, 시대별, 장르별로 연구한다. 지역에 따른 구분으로는 동양 미술사와 서양 미술사가 있다.\n\n한정희 등의 《동양미술사》는 동양 미술사를, 에른스트 H. 곰브리치의 《서양미술사》는 서양 미술사를 다룬다. 김원룡과 안휘준은 《한국미술의 역사》를 썼다.\n'),
    ),
    161181: (
        ('본관은 서산(瑞山).', '본관은 서산(瑞山)이다. 오늘날의 충청남도 지역 출신이다.'),
        ('분류 \n\n서산 류씨\n조선의 학자\n1388년 출생\n1443년 사망\n충청남도 출신\n', ''),
    ),
    224173: (
        ('가나가와현 출신. 쟈니즈 사무소 소속.', '가나가와현 출신이며 쟈니즈 사무소 소속이다.'),
        ('분류\n1990년 출생\n살아있는 사람\n가나가와현 출신\n일본의 남자 배우\n일본의 남자 가수\n일본의 아이돌\n자니즈\nHey! Say! JUMP\n호리코시 고등학교 동문\n', ''),
    ),
    260681: (
        ('이를 원작으로 한 텔레비전 드라마이다\n', '이를 원작으로 한 텔레비전 드라마이다.\n'),
        ('2002년에는 후지 TV에서 TV 드라마로도 방영되었다.', '이 만화를 원작으로 한 가족 드라마는 2002년 일본의 후지 TV에서 방영되었다.'),
        ('외부 링크 \n 모닝 | 연재 만화의 방\n\n분류\n일본의 만화\n2002년 드라마\n일본의 텔레비전 드라마\n일본의 만화의 텔레비전 드라마화 작품\n가족 드라마\n', ''),
    ),
    1441832: (
        ('뫼비우스(, 1790년', '뫼비우스(1790년'),
        ('요한 하인리히 뫼비우스()였으며', '요한 하인리히 뫼비우스였으며'),
        ('1813년 괴팅겐 대학교의 카를 프리드리히 가우스를 만나서 공부했다.', '1813년 괴팅겐 대학교의 카를 프리드리히 가우스를 만나서 공부했다. 그는 할레 대학교 동문이기도 하다.'),
        ('외부 링크 \n\n \n \n\n1790년 출생\n1868년 사망\n독일의 수학자\n독일의 천문학자\n19세기 수학자\n기하학자\n19세기 천문학자\n괴팅겐 대학교 동문\n라이프치히 대학교 동문\n[[분류:할레 대학교 동문]]\n', ''),
    ),
    44482: (
        ('18세기까지 존재하였다.\n', '18세기까지 존재하였다. 크림 고트어는 동게르만어군에 속하는 유럽의 사어다.\n'),
        ('예를 들어,  (알)이라는 단어는 고트어의 게르만어적인 특징을 잘 나타내고 있다.',
         '알을 뜻하는 단어는 고트어의 게르만어적 특징을 보여 주는 사례로 언급된다.'),
        ('외부 링크 \n 고트어 어휘\n 고트어 문법\n\n동게르만어군\n유럽의 사어\n크림반도의 역사\n', ''),
    ),
    86190: (
        ("《명탐정 코난: 탐정들의 진혼가》()은",
         "《명탐정 코난: 탐정들의 진혼가》는"),
        ("성우 - 오사와 아리마사<ref>나오키상 수상 작가. 오사와는 이 해인 2006년 5월 20일에 토크쇼 자리에서 이 작품에 참가한 일에 대해 언급했다. \"처음 (출연했던 것은) 2채널에서 화제가 되었다\" \"예전에 성우를 목표로 했었기 때문에 그만큼 이번 일에는 전력을 기울였다\" \"그림이 완성되지 않아서 후시 녹음에는 고생했다\" 등의 내용을 이야기했다</ref>",
         "나오키상을 받은 작가 오사와 아리마사가 경관의 목소리를 맡았다. 그는 2006년 5월 20일 토크쇼에서 첫 출연이 2채널에서 화제가 됐고, 예전에 성우를 목표로 했던 만큼 전력을 기울였다고 말했다. 그림이 완성되지 않아 후시 녹음에서 고생했다고도 회고했다."),
    ),
    174420: (
        ("대성(, 1989년 4월 26일 ~ )은",
         "대성(1989년 4월 26일 ~ )은"),
        ("<ref>Mo, Shin-Jeong. 빅뱅 대성, 트로트 싱글 '날 봐 귀순' 공개 (Big Bang's Daesung Reveals Trot Single \"Nalbwa Gwisun\")] . The Korea Times. June 16, 2008. Retrieved October 27, 2009.</ref>",
         " Mo, Shin-Jeong은 2008년 6월 16일 《The Korea Times》에 「빅뱅 대성, 트로트 싱글 ‘날 봐 귀순’ 공개」 기사를 실었다. 이 기사의 열람일은 2009년 10월 27일이다."),
    ),
    180446: (
        ("<ref>André Darmon Israel Magazine July 2007 Interview with Bat Ye'or Bat Ye'or</ref>",
         " 2007년 7월 《Israel Magazine》에는 앙드레 다르몽(André Darmon)의 밧 예올 인터뷰가 실렸다."),
    ),
    105184: (
        ('《광주여 영원히!()》는', '《광주여 영원히!》는'),
        ('외부 링크 \n 5.18 항쟁의 형상화에 사용된 음악표현양식 - 광주여 영원히!의 분석이 있다.\n\n',
         '5.18 항쟁을 형상화한 음악 표현 양식을 다룬 자료에서 《광주여 영원히!》를 분석한다.\n\n'),
    ),
    20182: (
        ("참고 문헌 \n 박영준 외, 《우리말의 수수께끼》, 김영사, 2002년, \n 정연종, 《한글은 단군이 만들었다》, 죠이정 인터내셔날, 1996년\n\n",
         ""),
    ),
    20183: (
        ("참고 문헌 \n\n 박영준 외, 《우리말의 수수께끼》, 김영사, 2002, \n 세계문자연구회, 《세계의 문자》, 범우사, 1997\n\n",
         ""),
    ),
    21818: (
        ("참고 문헌 \n 김필영, 『소비에트 중앙아시아 고려인 문학사 (1937~1991)』, 강남대학교 출판부, 2004\n 곽충구·김수현, 『중앙아시아 이주 한민족의 언어와 생활 - 카자흐스탄 알마티』, 태학사, 2008\n 곽충구, 『중앙아시아 이주 한민족의 언어와 생활 - 우즈베키스탄 타슈켄트』, 태학사, 2009\n\n",
         "중앙아시아 한민족의 언어와 생활을 다룬 책으로는 곽충구·김수현의 《중앙아시아 이주 한민족의 언어와 생활 - 카자흐스탄 알마티》(태학사, 2008)와 곽충구의 《중앙아시아 이주 한민족의 언어와 생활 - 우즈베키스탄 타슈켄트》(태학사, 2009)가 있다. 이 지역의 고려인 문학사는 김필영의 《소비에트 중앙아시아 고려인 문학사 (1937~1991)》(강남대학교 출판부, 2004)에서 다룬다.\n\n"),
    ),
    23046: (
        ("참고 문헌 \n 임동권, 《한국세시풍속연구》, 집문당, 1993\n 김광언, 《동아시아의 놀이》, 민속원, 2004\n\n\n",
         "한국의 세시풍속을 다룬 책으로 임동권의 《한국세시풍속연구》(집문당, 1993)가 있으며, 동아시아 놀이 문화에 관한 책으로 김광언의 《동아시아의 놀이》(민속원, 2004)가 있다.\n\n"),
    ),
    121326: (
        ("참고 문헌 \n 문중양, 《우리역사 과학기행》, 서울: 동아시아, 2006년\n 한영우·안휘준·배우성, 《우리 옛지도와 그 아름다움》, 서울: 효형출판, 2003년\n",
         "한국 고지도와 과학사의 배경 자료로 한영우·안휘준·배우성의 《우리 옛지도와 그 아름다움》(서울 효형출판, 2003)과 문중양의 《우리역사 과학기행》(서울 동아시아, 2006)이 있다.\n\n"),
        ("우리역사넷> 한국문화사 >  >  > 제4장 땅의 표현과 기술 > 2. 세계 지도, 세계관의 표상\n",
         "우리역사넷의 《한국문화사》 제4장 「땅의 표현과 기술」에는 ‘세계 지도, 세계관의 표상’ 절이 있다.\n"),
    ),
    170556: (
        ("참고 문헌 \n 고석구, 『복소해석학개론(2판)』, 경문사, 2005\n 강승필, 『해설 복소함수론』, 경문사, 2007\n\n",
         "복소해석학을 다룬 교재로 고석구의 《복소해석학개론》 제2판(경문사, 2005)과 강승필의 《해설 복소함수론》(경문사, 2007)이 있다.\n\n"),
    ),
    235075: (
        ("참고 문헌 \n 혼마 야스코, 『덕혜옹주 - 대한제국 마지막 황녀』, 역사공간, 2008년. \n 정범준, 『제국의 후예들 - 대한제국 후예들의 삶으로 읽는 한반도 백년사』, 황소자리, 2006년. \n\n",
         "덕혜옹주의 생애는 혼마 야스코의 《덕혜옹주 - 대한제국 마지막 황녀》(역사공간, 2008)의 주제이다. 정범준은 《제국의 후예들 - 대한제국 후예들의 삶으로 읽는 한반도 백년사》(황소자리, 2006)에서 대한제국 후예의 삶을 다룬다.\n\n"),
    ),
    290168: (
        ("참고 문헌 \n 김영애, 《태국사》, 한국외국어대학교 출판부, 2001.\n 김우조 외, 《아시아 아프리카 문학》, 김우조, 2003.\n\n",
         ""),
    ),
    302477: (
        ("참고 문헌 \n 간인 스루히토, 《일본사상의 비록》, 일본민주협회, 1968년\n 다카시 후지타니, 《훌륭한 왕조 : 현대 일본의 권력과 화려한 왕실 행사》, 캘리포니아 대학교 출판사, 1998년\n 다케다 쓰네야스, 《구황족이 말하는 천황의 일본사》,PHP연구소, 2008년\n\n\n",
         "구황족의 관점에서 본 일본 천황의 역사를 다룬 다케다 쓰네야스의 《구황족이 말하는 천황의 일본사》는 PHP연구소가 2008년에 펴냈다. 다카시 후지타니의 《훌륭한 왕조 : 현대 일본의 권력과 화려한 왕실 행사》는 캘리포니아 대학교 출판사가 1998년에 펴냈다.\n\n"),
    ),
    310286: (
        ("참고 문헌 \n 구도 미요코, 《황혼의 시인: 호리구치 다이가쿠와 그 아버지의 이야기》, 《매거진하우스》지, 2001년.\n 가시와쿠라 야스오, 《패배한 나라의 가을의 끝: 평전 - 호리구치 구마이치》, 사유샤(左右社), 2008년.\n\n\n\n",
         "구도 미요코는 《황혼의 시인: 호리구치 다이가쿠와 그 아버지의 이야기》(《매거진하우스》지, 2001)에서 호리구치 다이가쿠와 그의 아버지를 다룬다. 가시와쿠라 야스오의 《패배한 나라의 가을의 끝: 평전 - 호리구치 구마이치》는 사유샤(左右社)에서 2008년에 나왔다.\n\n"),
    ),
    330811: (
        ("참고 문헌 \n 김정위, 《이슬람사상사》, 민음사, 1987.\n 김정위 외, 《이슬람 사상의 형성과 발전》, 아카넷, 2000.\n\n",
         "이슬람 사상사를 다룬 문헌으로 김정위의 《이슬람사상사》(민음사, 1987)와 김정위 외의 《이슬람 사상의 형성과 발전》(아카넷, 2000)이 있다.\n\n"),
    ),
    391337: (
        ("참고 문헌 \n\n 이바르 리스너, 《서양》, 살림, 2005\n 비비안 그린, 《권력과 광기》, 말글빛냄, 2005\n\n",
         ""),
    ),
    392914: (
        ("참고 문헌 \n 샹관핑, 《중국사 열전 황제》, 달과소, 2008\n 샹관핑, 《중국사 열전, 후비 - 황제를 지배한 여인들》, 달과소, 2008\n\n",
         "중국 황제와 후비의 인물사는 샹관핑의 《중국사 열전 황제》와 《중국사 열전, 후비 - 황제를 지배한 여인들》에서 다룬다. 달과소가 두 책을 2008년에 펴냈다.\n\n"),
    ),
    433472: (
        ("참고 문헌 \n 강주훈, 《의원내각제의 비교 헌법적 연구》, 대구 : 홍익출판사, 2010\n 강원택, 《대통령제, 내각제와 이원정부제》, 고양 : 인간사랑, 2006\n 양현모, 《독일정부론》, 서울 : 대영문화사, 2006\n 김계동, 《현대유럽정치론》, 서울 : 서울대학교출판문화원, 2007\n 유럽정치연구회, 《유럽정치》, 서울 : 백산서당, 2004\n\n",
         "독일의 정부 형태는 양현모의 《독일정부론》(서울 대영문화사, 2006)의 주제이다. 의원내각제와 다른 정부 형태의 비교에 관한 문헌으로 강주훈의 《의원내각제의 비교 헌법적 연구》(대구 홍익출판사, 2010)와 강원택의 《대통령제, 내각제와 이원정부제》(고양 인간사랑, 2006)가 있다.\n\n"),
    ),
    505555: (
        ("참고 문헌 \n 남기심·고영근, 《표준국어문법론》, 탑출판사, 2011년, 152-3쪽, \n 고영근, 《표준중세국어문법론》, 집문당, 2010년, 136-8쪽\n\n",
         "현대국어 어미는 남기심·고영근의 《표준국어문법론》(탑출판사, 2011) 152–153쪽에서, 중세국어 어미는 고영근의 《표준중세국어문법론》(집문당, 2010) 136–138쪽에서 다룬다.\n\n"),
    ),
    174394: (
        ("참고 문헌 \n 손동권, 『체계적 형법연습』, 율곡출판사, 2005.\n 최준혁, 『중지미수의 이론 』, 경인문화사, 2008.\n\n",
         "최준혁의 《중지미수의 이론》은 경인문화사가 2008년에 펴냈다.\n\n"),
    ),
    66400: (
        ("<ref>Poem or To. F.S. first appeared in The Crisis in May 1925, and was reprinted in The Weary Blues' and The Dream Keeper. Hughes never publicly identified F.S., but it is conjectured he was Ferdinand Smith, a merchant seaman whom the poet first met in New York in the early 1920s. Nine years older than Hughes, Smith first influenced the poet to go to sea. Born in Jamaica in 1893, Smith spent most of his life as a ship steward and political activist at sea--and later in New York as a resident of Harlem. Smith was deported back to Jamaica for alleged Communist activities and illegal alien status in 1951. Hughes corresponded with Smith up until 1961, when Smith died. Berry, p.347</ref>",
         ""),
        ("유럽에서 휴즈는 파리에서 잠시 체류를 위하여 S.S 말론을 떠났다.",
         "유럽에서 휴즈는 파리에서 잠시 체류를 위하여 S.S 말론을 떠났다.\n\n베리(347쪽)에 따르면, 「Poem or To. F.S.」는 1925년 5월 《The Crisis》에 처음 발표된 뒤 《The Weary Blues》와 《The Dream Keeper》에 재수록되었다. 휴즈는 F.S.가 누구인지 공개적으로 밝히지 않았다. F.S.는 1920년대 초 휴즈가 뉴욕에서 만난 상선 선원 페르디난드 스미스였을 것으로 추정된다. 휴즈보다 아홉 살 많았던 스미스는 휴즈가 처음 바다로 나가는 데 영향을 주었다. 1893년 자메이카에서 태어난 스미스는 생애 대부분을 배에서 스튜어드와 정치 활동가로 지냈고, 이후 뉴욕 할렘에 거주했다. 그는 공산주의 활동 혐의와 불법 체류자 신분을 이유로 1951년 자메이카로 추방되었다. 휴즈는 스미스가 사망한 1961년까지 그와 서신을 주고받았다."),
    ),
    299257: (
        ("2010년 4월 12일 북한의 조선혁명박물관과 우호 관계를 맺었다.<ref>朝鮮革命博物館 ホーチミン博物館と友好関係設定に合意  조선신보, 2010년 4월 23일</ref>",
         "2010년 4월 12일 호찌민 박물관은 북한 조선혁명박물관과 우호 관계를 맺었다. 조선신보는 2010년 4월 23일 기사 「朝鮮革命博物館 ホーチミン博物館と友好関係設定に合意」에서 이 일을 보도했다."),
    ),
    448640: (
        ("거의 말년에 해당되는 거의 말년에 해당되는",
         "말년에 해당하는"),
        ("같이 보기 \n 사인비구 제작 동종\n 강화역사박물관\n\n\n참고 자료 \n \n 사인비구 제작 동종-강화 동종 - 강화군 문화관광\n 인천역사문화총서40, 《인천의 문화유산을 찾아서》, 인천광역시 역사자료관, 강화 동종, 19-20쪽\n\n인천광역시의 보물\n강화역사박물관 소장품\n동종\n1711년 작품\n",
         "인천광역시 역사자료관이 펴낸 인천역사문화총서 제40권 《인천의 문화유산을 찾아서》 19–20쪽에 강화 동종 항목이 실려 있다. 강화군 문화관광 자료도 이 종을 소개한다.\n"),
        ("사인비구 제작 동종 - 강화동종(思印比丘 製作 銅鍾 - 江華銅鍾)은 인천광역시 강화군 하점면, 강화역사박물관에 있는 조선시대의 종이다. 1963년 1월 21일 대한민국의 보물 제11호로 지정되었다가, 2000년 2월 15일 사인비구 주성 동종 7구가 보물로 지정됨에 따라 =0028476399&isEbook=Y 보물지정번호변경], 문화재청장, 2000-02-18</ref>",
         "사인비구 제작 동종 - 강화동종(思印比丘 製作 銅鍾 - 江華銅鍾)은 인천광역시 강화군 하점면, 강화역사박물관에 있는 조선시대의 종이다. 1963년 1월 21일 대한민국의 보물 제11호로 지정되었다. 2000년 2월 15일 사인비구가 주조한 동종 7구가 보물로 지정되었다. 지정 번호가 바뀐 내용은 문화재청장의 2000년 2월 18일자 「보물지정번호변경」에 기록되어 있다."),
    ),
    601489: (
        ("\"영녀\"는 1979년에 개봉한 대한민국의 영화이다.",
         "《영녀》는 1979년에 개봉한 대한민국의 한국어 영화로, 로맨스·스릴러·미스터리 장르의 작품이다. 다음영화·무비스트·한국영화 데이터베이스에는 제목이 《0女》로 표기되어 있다."),
        ("외부 링크 \n 0女 - 다음영화\n 0女 - 무비스트\n 0女 - 한국영화 데이터베이스\n\n한국어 영화 작품\n1979년 영화\n대한민국의 영화 작품\n대한민국의 로맨스 영화\n대한민국의 스릴러 영화\n대한민국의 미스터리 영화\n",
         ""),
    ),
    607728: (
        ("\"십이야: 깊고 붉은 열두 개의 밤 Chapter 1\"은 2015년에 개봉한 대한민국의 영화이다.",
         "《십이야: 깊고 붉은 열두 개의 밤 Chapter 1》은 2015년에 개봉한 대한민국의 한국어 공포·스릴러 영화다. 다음영화·무비스트·한국영화 데이터베이스에는 제목이 《十二夜》로 표기되어 있다."),
        (" 박은석 : <남의소리> 광현 역    \n",
         " 박은석은 〈남의소리〉에서 광현 역을 맡았다.\n"),
        ("외부 링크 \n 十二夜 - 다음영화\n 十二夜 - 무비스트\n 十二夜 - 한국영화 데이터베이스\n\n한국어 영화 작품\n2015년 영화\n대한민국의 영화 작품\n대한민국의 공포 영화\n대한민국의 스릴러 영화\n",
         ""),
    ),
    663531: (
        ("\"삼일낮 삼일밤\"은 1983년에 개봉한 대한민국의 영화이다.",
         "\"삼일낮 삼일밤\"은 1983년에 개봉한 대한민국의 영화이다. 다음영화·무비스트·한국영화 데이터베이스에는 제목이 《3일낮 3일밤》로 표기되어 있다."),
    ),
    677650: (
        ("\"김두한과 서대문 1번지\"는 1981년에 개봉한 대한민국의 영화이다.",
         "\"김두한과 서대문 1번지\"는 1981년에 개봉한 대한민국의 영화이다. 다음영화·무비스트·한국영화 데이터베이스에는 제목이 《金斗漢과 西大門一番地》로 표기되어 있다."),
    ),
    7482: (
        ("그리고 그 영향력은 또한 댕디의 '스콜라'를 통하여 현대에 이르고 있다.",
         "그리고 그 영향력은 또한 댕디의 '스콜라'를 통하여 현대에 이르고 있다. 뱅상 댕디가 쓴 전기 《César Franck》의 영어 번역본은 1910년 런던에서 John Lane, Bodley Head가 펴냈고, 로자 뉴마치의 서문이 실렸다. 뉴욕의 Dover는 1965년에 이 번역본을 재판했다."),
        ("참고 문헌 \n\n \n d'Indy, Vincent (1910). César Franck; a Translation from the French of Vincent d'Indy: with an Introduction by Rosa Newmarch. London: John Lane, Bodley Head. Reprinted 1965 NY: Dover. . original French version on Wikisource\n Davies, Laurence (1970). César Franck and His Circle. Boston: Houghton Mifflin.\n \n \"Franck, César.\" Norton/Grove Concise Encyclopedia of Music. (Pub. in UK as Grove Concise Dictionary of Music.). New York: Norton, 1988.\n Ober, William B. (1970). \"De Mortibus Musicorum: Some cases drawn from a pathologist's notebook.\" Stereo Review, vol. 25 no. 5 (November 1970).\n Smith, Rollin (1997). Playing the Organ Works of César Franck. Series: The Complete Organ No. 1. Hillsdale, NY: Pendragon Press .\n ——— (2002). Toward an Authentic Interpretation of the Organ Works of César Franck. Second edition, revised and expanded. Series: The Complete Organ No. 6; Juilliard Performance Guide No. 1. Hillsdale, NY: Pendragon Press. .\n Stove, R. J. (2012). César Franck: His Life and Times. Lanham, Maryland: Scarecrow Press. .\n Vallas, Léon (1951). César Franck. Trans. Hubert J. Foss. New York: Oxford University Press. Trans. of La véritable histoire de César Franck (1949)\n\n외부 링크 \n\n \n Free scores \n International César Franck Society\n L'Organiste played on virtual harmoniums\n More works by César Franck performed on virtual instruments\n \n \n Official MySpace Page\n \n \n\n",
         ""),
    ),
    31236: (
        ("클론(Clon)은 구준엽과 강원래로 구성된 대한민국의 2인조 댄스 그룹이다.",
         "클론(Clon)은 1996년에 결성된 대한민국의 남성 2인조 댄스·팝 아이돌 그룹이다. 멤버는 구준엽과 강원래다."),
        ("수상\n\n시상식\n\n가요 프로그램 1위\n\n",
         "수상\n\n클론은 골든디스크 본상과 인기상, 하이원 서울가요대상 대상을 수상했다.\n\n"),
        ("외부 링크 \n \n\n골든디스크 본상 수상 음악가\n골든디스크 인기상 수상 음악가\n하이원 서울가요대상 대상 수상 음악가\n미디어 라인 음악가\n남성 듀오\n2인조 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 팝 음악 그룹\n1996년 결성된 음악 그룹\n대한민국의 아이돌 그룹\n아이돌 그룹\n\n",
         ""),
    ),
    86329: (
        ("은 대한민국의 은퇴한 핸드볼 선수이다.",
         "은 서울특별시 출신의 대한민국 은퇴 핸드볼 선수이다."),
        ("핸드볼을 시작한 윤경신은 고려대학교",
         "핸드볼을 시작한 윤경신은 광운중학교를 거쳐 고려대학교"),
        ("국가대표로 모두 다섯 번의 아시안 게임에서 금메달을 땄으며, 함부르크에서는",
         "아시안 게임 핸드볼에는 1990년, 1994년, 1998년, 2002년, 2006년, 2010년에 출전했다. 아시안 게임에서 모두 다섯 차례 금메달을 땄으며, 메달을 획득한 대회 연도는 1990년, 1994년, 1998년, 2002년, 2010년이다. 함부르크에서는"),
        ("2012년 하계 올림픽에서 대한민국 대표 선수단의",
         "하계 올림픽 핸드볼에는 1992년, 2000년, 2004년, 2008년, 2012년에 출전했다. 2012년 하계 올림픽에서 대한민국 대표 선수단의"),
        ("각주\n\nCF \n 1995년 필립스 필리쉐이브\n\n외부 링크 \n",
         "윤경신은 체육훈장 백마장을 받았다.\n\nCF \n 1995년 필립스 필리쉐이브\n\n"),
        (" \n  윤경신 - 대한핸드볼협회\n  윤경신 - 유럽 핸드볼 연맹\n  윤경신 - Sports Reference.com\n\n1973년 출생\n살아있는 사람\n대한민국의 남자 핸드볼 선수\n대한민국 핸드볼 국가대표팀 선수\n대한민국의 올림픽 핸드볼 참가 선수\n1992년 하계 올림픽 핸드볼 참가 선수\n2000년 하계 올림픽 핸드볼 참가 선수\n2004년 하계 올림픽 핸드볼 참가 선수\n2008년 하계 올림픽 핸드볼 참가 선수\n2012년 하계 올림픽 핸드볼 참가 선수\n대한민국의 아시안 게임 금메달리스트\n아시안 게임 핸드볼 메달리스트\n1990년 아시안 게임 메달리스트\n1994년 아시안 게임 메달리스트\n1998년 아시안 게임 메달리스트\n2002년 아시안 게임 메달리스트\n2010년 아시안 게임 메달리스트\n대한민국의 아시안 게임 핸드볼 참가 선수\n1990년 아시안 게임 핸드볼 참가 선수\n1994년 아시안 게임 핸드볼 참가 선수\n1998년 아시안 게임 핸드볼 참가 선수\n2002년 아시안 게임 핸드볼 참가 선수\n2006년 아시안 게임 핸드볼 참가 선수\n2010년 아시안 게임 핸드볼 참가 선수\n체육훈장 백마장 수훈자\n서울특별시 출신\n숭덕초등학교 동문\n광운중학교 동문\n고려대학교 사범대학 부속고등학교 동문\n경희대학교 동문\n독일에 거주한 대한민국인\n\n",
         ""),
    ),
    100019: (
        ("초연되었다. 출판은 1816년 빈의 슈타이너를 통해 이루어졌다.",
         "초연되었다. 빈의 슈타이너가 이 작품을 출판했다."),
        ("출판은 1816년 빈의 슈타이너를 통해 이루어졌다. 작품은 피에르 로드를 위해 쓰여졌으나 헌정은 루돌프 대공에게 이루어졌다.\n",
         "작품은 피에르 로드를 위해 쓰였고 루돌프 대공에게 헌정되었다.\n"),
        ("소나타는 1815년 출판되기 전에 약간의 수정이 가해졌을 수 있다.",
         "소나타는 출판 전에 일부 수정되었을 가능성이 있다."),
        ("같이 보기 \n\n 베토벤의 바이올린 소나타\n\n\n참고 문헌 \n\n CD 박스 세트 베토벤, 슈만, 브람스 - 바이올린 소나타와 함께 제공되는 소책자. 도이치 그라모폰 프로덕션 (유니버설), 2003.\n Harenberg 문화 가이드 실내악. Brockhaus, Mannheim 2008, ISBN 978-3-411-07093-0\n Jürgen Heidrich : 바이올린 소나타에서 : 베토벤 설명서. Bärenreiter, Kassel 2009, ISBN 978-3476021533. 466-475 쪽.\n\n외부 링크 \n\n \n안네 소피 무터(vn), 램퍼트 오키스(pf)의 \"베토벤 - 바이올린 소나타 10번\" 연주 영상 (1998년, 프랑스 샹젤리제 극장) on YouTube\n\n10\n사장조 작품\n헌정곡\n바이올린 소나타\n\n",
         "Jürgen Heidrich가 쓴 베토벤의 바이올린 소나타 해설은 2009년 카셀의 Bärenreiter가 펴낸 베토벤 설명서 466–475쪽에 실렸다(ISBN 978-3476021533). 도이치 그라모폰 프로덕션은 2003년에 베토벤, 슈만, 브람스의 바이올린 소나타 CD 모음에 소책자를 함께 제공했다. 실내악 안내서로는 2008년 만하임 Brockhaus에서 펴낸 《Harenberg 문화 가이드 실내악》(ISBN 978-3-411-07093-0)이 있다.\n\n1998년 프랑스 샹젤리제 극장에서 안네 소피 무터가 바이올린을, 램퍼트 오키스가 피아노를 연주한 이 작품의 공연 영상이 유튜브에 공개되어 있다.\n\n"),
    ),
    163473: (
        ('《게드전기: 어스시의 전설》()은', '《게드전기: 어스시의 전설》은'),
        ("일본에서는 스튜디오 지브리 제작, 도호 배급으로 2007년 7월 29일에 개봉하였다.",
         "스튜디오 지브리가 제작하고 도호가 일본 개봉을 맡았다."),
        ("2006년 일본 방화 1위를 차지했다.",
         "일본 영화 가운데 흥행 1위를 차지했다."),
        ("참고 자료로 영화 《게드 전기》 공식 웹사이트, Madman Entertainment 공식 웹사이트, VIFF의 미야자키 고로 인터뷰와 작품 리뷰, 영화 공식 블로그, 미야자키 고로 블로그(영어 번역), 제작자 스즈키 도시오 인터뷰 번역, 어슐러 K. 르 귄 공식 웹사이트의 시놉시스, 홍콩·러시아 웹사이트가 제시되어 있다.\n",
         "VIFF 자료에는 미야자키 고로 감독과의 인터뷰 및 작품 리뷰가 실렸다. 제작자 스즈키 도시오의 인터뷰 번역과 고로 감독 블로그의 영어 번역도 있다. 원작자 어슐러 K. 르 귄의 공식 웹사이트에는 작품 줄거리 요약이 있다.\n"),
    ),
    188644: (
        ('마쓰이 가즈오(본명: (동음), 1975년', '마쓰이 가즈오(1975년'),
    ),
    325238: (
        ("세키쇼선은 홋카이도 여객철도의 철도 노선 가운데 하나이다. 일본 홋카이도 지토세시에 위치한 미나미치토세역과 가미카와 군 신토쿠정에 위치한 신토쿠역을 잇는 구간과, 유바리시에 위치한 신유바리역과 유바리역을 잇는 구간으로 구성된다.\n",
         "세키쇼선은 홋카이도 여객철도의 철도 노선이다. 본선은 일본 홋카이도 지토세시의 미나미치토세역과 가미카와군 신토쿠정의 신토쿠역을 잇는다. 유바리 지선은 유바리시의 신유바리역과 유바리역을 이었고, 2019년 4월 1일에 폐선되었다.\n"),
        ("1892년 유바리선이라는 이름으로 개통되었다.",
         "세키쇼선의 전신인 유바리선은 1892년에 개통했다."),
        ("폐선된다고 발표했으며, 2019년 4월 1일 폐선되었다.",
         "폐선된다고 발표했다."),
        ("역 목록\n\n본선\n\n유바리 지선 (폐선)\n",
         ""),
        ("이후로도 폐선이 된까지 신유바리 ~ 유바리 구간은 여전히 유바리 선이라는 통칭이 통용되었다.",
         "이후에도 폐선될 때까지 신유바리~유바리 구간에는 ‘유바리선’이라는 통칭이 쓰였다."),
        ("외부 링크 \n\n \n홋카이도 여객철도의 철도 노선\n홋카이도의 철도 노선\n1892년 개통한 철도 노선\n일본국유철도의 철도 노선\n일본의 퀘이프 궤간\n\n",
         ""),
    ),
    372524: (
        ("역 목록 \n 모든 역이 후쿠오카현에 소재한다.\n",
         "이 노선의 역은 모두 후쿠오카현에 있다.\n"),
        ("외부 링크 \n\n \n큐슈여객철도의 철도 노선\n규슈 지방의 철도 노선\n후쿠오카현의 철도 교통\n1904년 개통한 철도 노선\n일본국유철도의 철도 노선\n후쿠오쿠유카타선\n일본의 퀘이프 궤간\n\n",
         ""),
    ),
    522189: (
        ("같이 보기 \n 서울 지하철 4호선\n 수도권 전철 4호선\n 안산선\n 과천선\n 진접차량사업소\n\n각주 \n 내용주\n\n 참조주\n\n수도권 전철 4호선\n2022년 개통한 철도 노선\n대한민국의 철도 노선\n\n",
         ""),
    ),
    43846: (
        ("참고 문헌 \n 「사립대학의 경영과 회계」, 학교법인의 조직과 기능, 이동규 저 선학사(2001년판)\n\n",
         "학교법인의 조직과 기능은 이동규의 《사립대학의 경영과 회계》(선학사, 2001년판)에서 다룬다.\n\n"),
    ),
    215332: (
        ("조시 전기 철도(}})는",
         "조시 전기 철도는"),
        ("각주\n\n관련 사이트 \n\n  공식 웹사이트\n\n \n1922년 설립된 기업\n일본의 철도 기업\n\n",
         ""),
    ),
    258577: (
        ("각주 \n\n 프로필과 사진\n\n1875년 출생\n1932년 사망\n1896년 하계 올림픽 수영 참가 선수\n1896년 하계 올림픽 메달리스트\n오스트리아의 남자 수영 선수\n올림픽 수영 메달리스트\n빈 출신\n국제 수영 명예의 전당 헌액자\n오스트리아의 올림픽 금메달리스트\n오스트리아의 올림픽 수영 참가 선수\n남자 자유형 선수\n\n",
         ""),
    ),
    258814: (
        ("참고 문헌 \n \n \n\n",
         ""),
    ),
    270290: (
        ("도쿄 임해 고속 철도 70-000형 전동차는 1996년 3월 30일부터 운행하고 있는 도쿄 임해 고속 철도 린카이 선의 전동차이다.",
         "도쿄 임해 고속 철도 70-000형 전동차는 1996년 3월 30일부터 운행하고 있는 도쿄 임해 고속 철도 린카이 선의 전동차이다. 도쿄 임해 고속 철도의 2010년 7월 1일자 공식 안내 「車輌について」는 70-000형 전동차를 다룬다. 《철도 팬》 제418호(1996년 2월) 68쪽에는 「東京臨海高速鉄道70-000形」이 실렸다."),
        ("각주\n\n사진\n\n참고 자료 \n\n 車輌について, 도쿄 임해 고속 철도 70-000형 전동차, 2010년 7월 1일\n \"東京臨海高速鉄道70-000形\" 철도 팬 No. 418 (1996년 2월), p. 68\n 도쿄 임해 고속 철도의 공식 안내 \n\n70-000형\n70-000형\n\n",
         ""),
    ),
    315988: (
        ('대한민국의 소설가이다. 본관은 의성이며,',
         '대한민국의 소설가이다. 《한국현대문학대사전》에는 김형경 항목이 실려 있다. 본관은 의성이며,'),
        ('참고 자료\n 《한국현대문학대사전》-김형경 \n\n', ''),
    ),
    428007: (
        ("이 산 이름에서 성산동 지명이 유래하였다.",
         "이 산 이름에서 성산동 지명이 유래하였다. 마포신문의 「성산동유래」에서도 이 지명의 유래를 다룬다."),
        (" 마포신문 - 성산동유래\n",
         ""),
    ),
    912550: (
        ("우크라이나의 텔레비전 방송국인 1+1에서 방영되었다.",
         "우크라이나의 텔레비전 방송국인 1+1에서 방영되었다. 1+1과 HQ 플러스의 프로그램 안내에는 제목이 《인민의 종》으로 표시된다."),
        (" 1+1의 《인민의 종》 홈페이지 \n",
         ""),
        (" HQ 플러스의 《인민의 종》 소개\n",
         ""),
    ),
    938127: (
        ("이후에 6번 개정이 이루어졌다.",
         "이후에 6번 개정이 이루어졌다. 판본의 변천은 「A brief history of the editions of Colon Classification」에서 다룬다."),
        (" A brief history of the editions of Colon Classification\n",
         ""),
    ),
    947774: (
        ("외부 링크 \n\n Anthologie sonore de la poésie française à écouter et à lire librement\n 프랑시스 잠 협회 사이트, 오르테즈.\n Francis Jammes. Poète. Exposition numérique mettant en valeur les manuscrits de F. Jammes. (Pirenas.fr)\n https://archive.org/details/oeuvresdefrancis03jamm Tome 2 des Œuvres de Francis Jammes publiées en 1922 au Mercure de France. La Prière (Chanson de Georges Brassens) y figure dans le recueil L’Église Habillée de Feuilles.",
         "Mercure de France가 1922년에 출판한 《Œuvres de Francis Jammes》 제2권에는 《L’Église Habillée de Feuilles》에 수록된 「La Prière」가 실려 있다. 「La Prière」는 조르주 브라상의 노래로도 알려져 있다. 제2권의 판본 정보는 Internet Archive의 oeuvresdefrancis03jamm에 있다."),
    ),
}


def rewrite_known_tail(data, number, counts):
    if number in REVIEWED_WHOLE_PASSAGES:
        expected, prose = REVIEWED_WHOLE_PASSAGES[number]
        if sha256(data).hexdigest()!=expected:
            raise ValueError(f'직접 정제한 문서의 본문이 달라졌습니다. {number}')
        counts['manual_documents']+=1
        counts['manual_changed_spans']+=1
        return prose.encode()+BREAK
    if number in RESUMED_PASSAGES:
        for original,replacement in RESUMED_PASSAGES[number]:
            previous=original.encode()
            if data.count(previous)!=1:
                raise ValueError(f'확정된 문서 수정 위치가 달라졌습니다. {number}')
            data=data.replace(previous,replacement.encode())
        counts['manual_documents']+=1
        counts['manual_changed_spans']+=len(RESUMED_PASSAGES[number])
        return data
    if number == 10999:
        original = FAMILY_REGISTER_BIBLIOGRAPHY.encode()
        replacement = FAMILY_REGISTER_SOURCES.encode()
    elif number == 148570:
        original = '참고 문헌 \n 영화 슈퍼스타 감사용에서'.encode()
        replacement = '영화 슈퍼스타 감사용에서'.encode()
    elif number == 221284:
        original = '참고 문헌 \n  김철용, 행정법 2(김철용)(제5판), 박영사.'.encode()
        replacement = '관리관계의 참고 자료로는 박영사가 펴낸 김철용의 《행정법 2》 제5판이 있다.'.encode()
    elif number == 214192:
        original = OYANO_BIBLIOGRAPHY.encode()
        replacement = ('쓰루타 분시(鶴田文史)가 편저한 기리시탄 관련 자료 '
                       '《슈텐의 기리시탄 분카소오란(文化綜覧)》은 '
                       '아마쿠사 문화 출판사가 1983년에 펴냈다.').encode()
    elif number == 304882:
        original = KOMATSU_APPENDIX.encode()
        replacement = b''
    elif number == 284692:
        original = OLYMPIC_APPENDIX.encode()
        replacement = ('국제 올림픽 위원회 자료에는 1904년 하계 올림픽의 기계 체조 경기 결과가 '
                       '실려 있다.\n').encode()
        counts['conflicting_year'] += 1
    else:
        return data
    if data.count(original) != 1:
        raise ValueError(f'확정된 문서 수정 위치가 달라졌습니다. {number}')
    counts['manual_documents'] += 1
    counts['manual_changed_spans'] += 1
    return data.replace(original, replacement)


def write_tail():
    with v1.with_name(v1.name+'.work').open('rb') as fp:
        previous = latest_slot(fp)
        doc_index = previous['document_index']
        fp.seek(doc_index['offset'])
        rows = fp.read(doc_index['rows'] * DOCUMENT_POSITION.size)
    forbidden = {ordinal(ident) for ident in restricted}
    with (v1.open('rb') as original, mmap.mmap(original.fileno(), 0, access=mmap.ACCESS_READ) as source,
          part.open('r+b', buffering=1<<20) as output, meta.open('r+b', buffering=1<<20) as index):
        state = resume_pair(original, output, index)
        if state['stage'] not in ('legacy_saved', 'tail') or state['input_stamp'] != previous['output']:
            raise ValueError('v1 인덱스와 앞부분 작업 상태가 일치하지 않습니다.')
        counts = Counter(state['counts'])
        if state['stage'] == 'legacy_saved':
            write_gap(source, output, index, state, doc_index['text_start'], counts)
            state.update(stage='tail', next_tail=0, counts=counts)
            checkpoint(output, index, state)
        cursor = state['cursor']
        done = state['next_tail']
        for i, (number, width, _) in enumerate(DOCUMENT_POSITION.iter_unpack(rows[done*DOCUMENT_POSITION.size:]), done):
            if i % 5000 == 0 and datetime.now(deadline.tzinfo) >= deadline:
                break
            body = b''
            if width:
                if number in forbidden:
                    raise ValueError(f'본문이 있는 제한 원문을 인덱스에서 발견했습니다. {number}')
                before = source[cursor:cursor+width]
                if not before.endswith(BREAK):
                    raise ValueError(f'v1 후속 문서 경계가 달라졌습니다. {number}')
                body = transform(rewrite_known_tail(before, number, counts), counts)
            output.write(body)
            index.write(position.pack(number, width, len(body)))
            cursor += width
            state.update(cursor=cursor, rows=state['rows']+1, next_tail=i+1)
            if (i+1)%5000 == 0:
                checkpoint(output, index, state)
        if state['next_tail'] == doc_index['rows']:
            if cursor != len(source):
                raise ValueError('후속 인덱스와 입력 파일 끝이 다릅니다.')
            state.update(stage='first_refinement_saved', deferred=previous['deferred'])
        if stamp(original)!=state['input_stamp']:
            raise ValueError('v1이 정제 중 바뀌었습니다.')
        checkpoint(output, index, state)
        print(json.dumps(state, ensure_ascii=False))


def refine_contextual_footers(*, linked_only=False):
    if datetime.now(deadline.tzinfo) >= deadline:
        raise SystemExit('작업 종료 시각에 도달했습니다.')
    known = set(legacy_receipts()['legacy_admission_hold']['documents'])
    blocked = {ordinal(ident) for ident in restricted}
    working = part if part.exists() else result
    with (v1.open('rb') as original, mmap.mmap(original.fileno(), 0, access=mmap.ACCESS_READ) as source,
          working.open('r+b', buffering=1<<20) as output, meta.open('r+b', buffering=1<<20) as index):
        state = resume_pair(original, output, index)
        if working == result:
            if state['stage'] != 'published' or part.exists() or result.samefile(v1):
                raise ValueError('다시 작업할 v1.1 위치가 기대한 상태와 다릅니다.')
            result.rename(part)
        if state['stage'] in ('first_refinement_saved', 'refined', 'published'):
            state.pop('first_counts',None)
            state.update(stage='refining', next_record=0, next_source=0, counts={}, unlinked_output_bytes=0,
                         linked_only=linked_only or state.get('linked_only',False),
                         exact_repeats=sorted(EXACT_REPEATS.items()),
                         article_ui_repeats=sorted(ARTICLE_UI_REPEATS.items()),
                         registry_repeats=sorted(REGISTRY_REPEATS.items()),
                         boundary_repeats=sorted(BOUNDARY_REPEATS.items()),
                         content_admission_hold=sorted(CONTENT_ADMISSION_HOLD),
                         validation_overlap=VALIDATION_OVERLAP,
                         validation_word_overlap=VALIDATION_WORD_OVERLAP,
                         withheld_fields={'publication_year':[100019],'agency':[31236],
                                          'rail_opening_year':[372524],'designation_number':[448640],
                                          'film_release_year':[163473],'registry_number':[526382],
                                          'subject_attribution':[695566],
                                          'sequel_cast_and_language':[639049],
                                          'missing_math_notation':[170561],
                                          'biography_death_date_and_loan':[55301],
                                          'museum_alias_and_collection':[76428],
                                          'fortress_completion_year_and_classification':[26677]},
                         film_identity_evidence=[639049,639046,199954],
                         admission_review={'train_validation_overlap':[n for n,*_ in VALIDATION_OVERLAP+VALIDATION_WORD_OVERLAP],
                                           'related_validation_overlap':[558421,937519,935763,243394]})
            output.seek(0)
            checkpoint(output, index, state)
        elif state['stage'] != 'refining':
            raise ValueError('v1.1의 첫 정제가 아직 저장되지 않았습니다.')
        elif linked_only and not state.get('linked_only'):
            raise ValueError('진행 중인 정제를 저장한 뒤 원문 연결이 확인된 범위를 저장하세요.')
        linked_only=state.get('linked_only',False)
        review_only={n for group in state['admission_review'].values() for n in group} if linked_only else set()
        start = state['next_record']
        input_offset = state['next_source']
        index_end = reserved + state['rows'] * position.size
        index.seek(reserved + start * position.size)
        rows = index.read((state['rows']-start) * position.size)
        if len(rows) != (state['rows']-start) * position.size:
            raise ValueError('v1의 문서 위치 기록이 줄었습니다.')
        index.seek(reserved + start * position.size)
        counts = Counter(state['counts'])
        for i, (number, width, previous_width) in enumerate(position.iter_unpack(rows), start):
            if i % 10_000 == 0 and datetime.now(deadline.tzinfo) >= deadline:
                break
            end = input_offset + width
            output_start = output.tell()
            if number == 0 and linked_only:
                counts['unlinked_ranges_held']+=1
                counts['unlinked_bytes_held']+=width
            elif number == 0:
                read_at = input_offset
                edits = gap_edits(source, input_offset, end)
                for lo, hi, changed in edits:
                    copy_segment(source, output, read_at, lo)
                    output.write(changed)
                    read_at = hi
                copy_segment(source, output, read_at, end)
                counts['manual_documents'] += sum(input_offset<=begin<end
                                                    for begin,_,_ in REVIEWED_GAP_POSITIONS.values())
                counts['manual_changed_spans'] += len(edits)
                state['unlinked_output_bytes'] += output.tell()-output_start
            elif number in blocked and width:
                if number not in known or previous_width:
                    raise ValueError(f'기록된 보호 위치가 다릅니다. {number}')
                counts['carried_admission_hold'] += 1
                counts['carried_admission_hold_bytes'] += width
            elif number in EXACT_REPEATS and width:
                counts['exact_duplicate_documents'] += 1
                counts['exact_duplicate_input_bytes'] += width
            elif number in ARTICLE_UI_REPEATS and width:
                counts['article_ui_duplicate_documents']+=1
                counts['article_ui_duplicate_input_bytes']+=width
            elif number in REGISTRY_REPEATS and width:
                counts['registry_duplicate_documents']+=1
                counts['registry_duplicate_input_bytes']+=width
            elif number in BOUNDARY_REPEATS and width:
                counts['boundary_duplicate_documents']+=1
                counts['boundary_duplicate_input_bytes']+=width
            elif number in CONTENT_ADMISSION_HOLD and width:
                counts['content_admission_hold_documents']+=1
                counts['content_admission_hold_bytes']+=width
            elif number in review_only and width:
                counts['admission_review_documents']+=1
                counts['admission_review_bytes']+=width
            elif width:
                data = rewrite_bound_body(source,input_offset,end,number,counts)
                output.write(transform(data, counts))
            saved = output.tell() - output_start
            index.write(position.pack(number, width, saved))
            input_offset = end
            state.update(next_record=i+1, next_source=end, counts=counts)
            if (i+1) % 100_000 == 0:
                index.seek(index_end)
                checkpoint(output, index, state)
                index.seek(reserved + (i+1) * position.size)
                print(f"{i+1:,}문서 처리, 분류 앞 빈 절 {counts['empty_before_categories']:,}개", flush=True)
        if state['next_record'] == state['rows']:
            if (input_offset != len(source) or counts['carried_admission_hold'] != len(known)
                    or counts['exact_duplicate_documents'] != len(EXACT_REPEATS)
                    or counts['article_ui_duplicate_documents']!=len(ARTICLE_UI_REPEATS)
                    or counts['registry_duplicate_documents']!=len(REGISTRY_REPEATS)
                    or counts['boundary_duplicate_documents']!=len(BOUNDARY_REPEATS)
                    or counts['content_admission_hold_documents']!=len(CONTENT_ADMISSION_HOLD)
                    or counts['admission_review_documents']!=len(review_only)):
                raise ValueError('추가 정제의 입력 끝과 보류 기록 수가 다릅니다.')
            state['stage'] = 'refined'
            output.truncate(output.tell())
        if stamp(original) != state['input_stamp']:
            raise ValueError('v1이 정제 중 바뀌었습니다.')
        index.seek(index_end)
        checkpoint(output, index, state)
        print(json.dumps(state, ensure_ascii=False))


def original_gap_variants(number,end,text):
    from dataclasses import replace
    from next_cleanup_batch import automatic_format,clean_empty_initial_alias,clean_number_article

    document=Document(number,0,end,text)
    structural,_=automatic_format(replace(document,prepare_structure=True))
    metadata,_=automatic_format(replace(document,prepare_structure=True,prepare_metadata=True,
                                        automatic_text=clean_number_article(text)))
    simple,_=automatic_format(document)
    result=set()
    for value in (text,simple,structural,metadata):
        for version in (value,clean_empty_initial_alias(value,dated_names=False),clean_empty_initial_alias(value)):
            if version and version.strip():
                result.add(version.strip('\r\n').encode()+BREAK)
                result.add(version.strip().encode()+BREAK)
                head,separator,rest=version.partition('\n')
                repeated=rest.partition('\n')[0]
                if separator and 8<=len(head)<=125 and head.strip()==repeated.strip():
                    result.add(rest.strip('\r\n').encode()+BREAK)
                alias = re.match(r'\A[가-힣][가-힣A-Za-z0-9 ·ㆍ\-]{0,54}(?P<alias>\((?P<fields>[^()\n]{0,140})\))'
                                 r'(?=[은는이가의에와과을를 ,])',version)
                if alias:
                    fields = [item.strip() for item in re.split(r'[,;，；]',alias['fields'])]
                    if '' in fields:
                        retained = ', '.join(item for item in fields if item)
                        first,last = alias.span('alias')
                        revised = version[:first] + (f'({retained})' if retained else '') + version[last:]
                        result.add(revised.strip('\r\n').encode()+BREAK)
    return result


def unique_source_lead(source, drafts, begin, end, expected):
    for body in drafts:
        paragraph=body.split(BREAK,1)[0]
        leads = ((paragraph[:115],95), (body[:100],64), (paragraph.split(b'\n',1)[0][:115],64))
        for lead, minimum in leads:
            if (len(lead)>=minimum and source.find(lead,begin,end)==expected
                    and source.find(lead,expected+1,end)==-1):
                return True
    positions=set()
    for body in drafts:
        opening=body[:1500].decode('utf-8','ignore')
        topic=TOPIC_NAME.match(opening)
        if not topic:
            continue
        name=topic[1].strip().encode()
        if len(name)<6:
            continue
        sentences=re.split(r'(?<=[.!?。])[ \t\r\n]+|\n{2,}',opening,maxsplit=3)[:3]
        phrases=[]
        for sentence in sentences:
            words=sentence.split()
            for at in (0,max(0,len(words)-12)):
                text=words[at:at+12]
                phrase=' '.join(text).encode()
                if len(text)>=8 and 85<=len(phrase)<=250 and name not in phrase:
                    phrases.append(phrase)
        point=begin-1
        while (point:=source.find(name,point+1,end))>=0:
            after=point+len(name)
            suffix=source[after:after+3].decode('utf-8','ignore')[:1]
            if ((point==begin or source[point-2:point]==BREAK)
                    and suffix in ('(', ' ', '은', '는', '이', '가', '의')
                    and any(source.find(phrase,after,min(point+760,end))>=0 for phrase in phrases)):
                positions.add(point)
    if positions:
        return positions=={expected}
    for body in drafts:
        lines=[line for line in body.splitlines()[:8] if line.strip()]
        if len(lines)<2 or not 12<=len(lines[0])<=125:
            continue
        head=lines[0]
        if head.endswith((b'.',b'?',b'!')) or len(head.decode('utf-8','ignore'))<4:
            continue
        marker=head+b'\n'
        located=begin-1
        while (located:=source.find(marker,located+1,end))>=0:
            if located!=begin and source[located-2:located]!=BREAK:
                continue
            if any(source.find(line[:125],located+len(marker),min(located+1100,end))>=0
                   for line in lines[1:] if len(line)>=90):
                positions.add(located)
    return positions=={expected}


def same_source_lines(body, drafts):
    take=[line.strip() for line in body.splitlines() if line.strip()]
    width=sum(map(len,take))
    if len(take)<3 or width<230:
        return False
    for draft in drafts:
        full=[line.strip() for line in draft.splitlines() if line.strip()]
        if 100*width<78*sum(map(len,full)):
            continue
        cursor=iter(full)
        if all(any(line==candidate for candidate in cursor) for line in take):
            return True
    return False


def same_source_words(body,drafts,*,entire_gap=False):
    from difflib import SequenceMatcher

    current=body.split()
    terminal_header=SOURCE_ARTICLE_HEADER.search(body)
    if len(current)<(75 if entire_gap else 64):
        return False
    for draft in drafts:
        if terminal_header and terminal_header[1] not in draft:
            continue
        original=draft.split()
        lower,upper = (.68,1.12) if entire_gap else (.63,1.10)
        if not lower*len(original)<=len(current)<=upper*len(original):
            continue
        matcher=SequenceMatcher(None,original,current,autojunk=False)
        if matcher.quick_ratio()<(.83 if entire_gap else .85):
            continue
        matches=matcher.get_matching_blocks()
        if entire_gap:
            covered=sum(block.size for block in matches)
            anchors=[block for block in matches if block.size>=14]
            if (len(anchors)>=2 and covered>=.88*len(current) and covered>=.69*len(original)
                    and max(block.size for block in matches)>=32 and anchors[0].b<=20
                    and len(current)-anchors[-1].b-anchors[-1].size<=24
                    and len(original)-anchors[-1].a-anchors[-1].size<=max(100,len(original)//5)):
                return True
            continue
        if sum(width for _,_,width in matches)<.9*len(current) or max(b.size for b in matches)<45:
            continue
        substantial=[(at,at+width) for _,at,width in matches if width>=12]
        changed=max((stop-start for kind,_,_,start,stop in matcher.get_opcodes() if kind!='equal'),default=0)
        if changed<=22 and substantial[0][0]<=8 and len(current)-substantial[-1][1]<=13:
            return True
    return False


def guarded_original_variants(numbers):
    from array import array
    from next_cleanup_batch import file_stamp,local_file,signature,was_done
    from scripts.diag_p106b_native_expansion import ByteCodec

    if CONTENT_ADMISSION_HOLD.intersection(numbers):
        raise ValueError('수록 보류 위치는 원문 대조 범위에서 제외합니다.')
    sys.path.insert(0,str(audit.resolve()))
    import active_guard_v6_preflight_v1 as safety

    safety.activate()
    contract = safety.checked_contract()
    forbidden = set(contract['restricted_ids']) | set(contract['trusted_metadata'])
    forbidden.update('expanded_train:'+str(n-1) for n in legacy_receipts()['legacy_admission_hold']['documents'])
    hashes = {value.upper() for value in contract['restricted_hashes']}
    with v1.with_name(v1.name+'.work').open('rb') as fp:
        previous = latest_slot(fp)
        fp.seek(previous['baseline_offset'])
        baseline = fp.read(previous['baseline_bytes'])
    if sha256(baseline).hexdigest().lower()!=previous['baseline_sha256'].lower():
        raise ValueError('기존 원문 판정 목록의 해시가 다릅니다.')
    inputs = previous['inputs']
    paths = [local_file(Path(p)) for p in inputs['source']+[inputs['tokenizer']]]

    def current_pin():
        return signature([inputs['format'],[(str(path),file_stamp(path.stat())) for path in paths]])

    if current_pin()!=previous['source'] or paths[0]!=Path(scope['inputs'][0]['path']).resolve():
        raise ValueError('기존 원문 파일이나 토크나이저가 바뀌었습니다.')
    blocked = [(row['start'][1],row['end'][1]) for row in previous['deferred']
               if row['start'][0]==row['end'][0]==0]
    cache = work/'cache_reviewed_partial_v18'
    built = (cache/'built.json').read_bytes()
    if sha256(built).hexdigest().lower()!=legacy_receipts()['legacy_cache_span']['built_sha256'].lower():
        raise ValueError('기존 판정 원장의 증거 파일이 바뀌었습니다.')
    ledger = json.loads(built)['manifests']['ledger']
    candidates = {}
    for shard in ledger['shards']:
        raw = (cache/'ledger'/shard['path']).read_bytes()
        if len(raw)!=shard['bytes'] or sha256(raw).hexdigest().upper()!=shard['sha256']:
            raise ValueError('기존 판정 원장의 일부가 바뀌었습니다.')
        for encoded in raw.splitlines():
            row = json.loads(encoded)
            if row['source']!='expanded_train':
                continue
            number = int(row['id'].split(':')[-1])+1
            if number not in numbers:
                continue
            first, last = row['source_ids']
            start,end=2*first,2*last
            body_hash = row.get('original_text_sha256')
            token_hash = row.get('source_ids_sha256')
            if (row['id'] in forbidden or was_done(baseline,number-1) or end-start!=2*row['input_ids']
                    or not 0<=start<end<=scope['inputs'][0]['bytes']
                    or any(start<b and a<end for a,b in blocked)
                    or not body_hash or not token_hash or body_hash.upper() in hashes or token_hash.upper() in hashes):
                raise ValueError(f'원문 대조가 허용된 위치가 아닙니다. {number}')
            candidates[number]=(start,end,body_hash.upper(),token_hash.upper())
        if candidates.keys()==numbers:
            break
    if candidates.keys()!=numbers:
        raise ValueError('지정한 원문 위치를 판정 원장에서 모두 찾지 못했습니다.')
    with paths[-1].open('rb') as tokenizer:
        codec=ByteCodec(json.load(tokenizer))
    variants={}
    with paths[0].open('rb',buffering=0) as raw_source:
        for number in sorted(numbers):
            start,end,body_hash,token_hash=candidates[number]
            raw=os.pread(raw_source.fileno(),end-start,start)
            if raw[-2:]!=bytes((2,0)) or sha256(raw).hexdigest().upper()!=token_hash:
                raise ValueError(f'원문 위치 경계 또는 해시가 다릅니다. {number}')
            ids=array('H')
            ids.frombytes(raw[:-2])
            if sys.byteorder!='little':
                ids.byteswap()
            text,body=codec.text(ids)
            if sha256(body).hexdigest().upper()!=body_hash:
                raise ValueError(f'원문 본문 해시가 다릅니다. {number}')
            variants[number]=original_gap_variants(number,end,text)
    if current_pin()!=previous['source']:
        raise ValueError('원문 대조 도중 입력 파일이 바뀌었습니다.')
    safety.assert_no_protected_opens()
    return variants


def source_gap_matches(source, requested, *, boundaries=None):
    numbers = {number for number,_,_,_ in requested}
    boundaries=boundaries or {}
    numbers.update(right for _,_,right,_,_ in boundaries.values() if right is not None)
    variants = guarded_original_variants(numbers)
    found={}
    for number,first,last,slot in requested:
        current=source[first:last]
        if slot!=0 or not current.endswith(BREAK):
            raise ValueError(f'v1 문서 경계가 다릅니다. {number}')
        if current not in variants[number]:
            if number not in boundaries:
                reviewed=REVIEWED_UNORDERED_BODY_SHA.get(number)
                if reviewed and sha256(current).hexdigest()==reviewed:
                    found[number]=(first,last)
                    continue
                identity=SOURCE_EMPTY_FORMATTING.sub(b'',current)
                if len(identity)>=120 and any(SOURCE_EMPTY_FORMATTING.sub(b'',d)==identity
                                              for d in variants[number]):
                    found[number]=(first,last)
                    continue
                raise ValueError(f'v1 전체 문서가 기존 원문이나 정제 결과와 일치하지 않습니다. {number}')
            lo,hi,following,method,single=boundaries[number]
            correct_start=(method in (2,3,4) and single and first==lo) or unique_source_lead(source,variants[number],lo,hi,first)
            correct_end=(last==hi if following is None else
                         unique_source_lead(source,variants[following],lo,hi,last))
            if method==3:
                if number in REVIEWED_TRAILING_FRAGMENT:
                    end,tail_sha=REVIEWED_TRAILING_FRAGMENT[number]
                    correct_end=last==end and sha256(source[last:hi]).hexdigest()==tail_sha
                if number in REVIEWED_ADJACENT_BODY_SHA:
                    same_body=sha256(current).hexdigest()==REVIEWED_ADJACENT_BODY_SHA[number]
                else:
                    same_body=((number==161 or number in REVIEWED_TRAILING_FRAGMENT
                                or (single and first==lo and last==hi and following is None))
                               and sha256(current).hexdigest()==REVIEWED_BODY_SHA[number])
            elif method==4:
                same_body=(single and first==lo and last==hi and following is None
                           and same_source_words(current,variants[number],entire_gap=True))
            else:
                compare=same_source_lines if method==1 else same_source_words
                same_body=compare(current,variants[number])
            if not (correct_start and correct_end and same_body):
                raise ValueError(f'v1 문서의 경계와 원문 순서를 모두 입증하지 못했습니다. {number}')
        found[number]=(first,last)
    return found


def new_gap_rows(source, start, end, requested, *, from_source=False):
    by_number = {row[0]: row for row in requested}
    if not requested or len(by_number) != len(requested):
        raise ValueError('문서 위치가 비었거나 중복됩니다.')
    if any(not start<=first<last<=end for _,first,last,_ in requested):
        raise ValueError('기존 미연결 구간 바깥의 위치입니다.')
    found = source_gap_matches(source,requested) if from_source else {}
    verified = set(restricted)
    if not from_source:
        with (work/'hold_first_pass.txt.work').open('rb') as loc, (work/'hold_first_pass.txt').open('rb') as draft:
            for line in loc:
                if not line.startswith(b'['):
                    continue
                number, slot, _, _, offset, width, *_ = json.loads(line)
                if number not in by_number:
                    continue
                _, first, last, expected_slot = by_number[number]
                ident = scope['inputs'][slot]['name'] + ':' + str(number-1-starts[scope['inputs'][slot]['name']])
                if ident in verified or slot != expected_slot or width != last-first:
                    raise ValueError(f'추가 문서 위치가 기존 기록과 다릅니다. {number}')
                body = os.pread(draft.fileno(),width,offset)
                if len(body)!=width or not body.endswith(BREAK) or body!=source[first:last]:
                    raise ValueError(f'추가 문서 위치가 v1과 일치하지 않습니다. {number}')
                found[number] = (first,last)
                if len(found)==len(requested):
                    break
    if found.keys()!=by_number.keys():
        raise ValueError('기존 기록에서 추가 위치를 찾지 못했습니다.')
    rows = []
    cursor = start
    for number,(first,last) in sorted(found.items(),key=lambda row: row[1][0]):
        if first<cursor:
            raise ValueError('추가 위치가 겹칩니다.')
        if first>cursor:
            rows.append((0,first-cursor,0))
        rows.append((number,last-first,0))
        cursor=last
    if end>cursor:
        rows.append((0,end-cursor,0))
    return rows


def gap_binding_groups(old, requested, *, ordered):
    from next_cleanup_batch import was_done

    if (not isinstance(requested,list) or not requested
            or any(not isinstance(row,list) or len(row)!=4 or
                   any(type(value) is not int for value in row) for row in requested)):
        raise ValueError('추가 연결 문서의 번호와 위치가 잘못됐습니다.')
    numbers={row[0] for row in requested}
    if len(numbers)!=len(requested) or min(numbers)<=0:
        raise ValueError('추가 연결 문서 번호가 비었거나 중복됩니다.')
    if any(mode not in (0,1,2) and not (ordered and (mode==4 or (mode==3 and
               (number in REVIEWED_BODY_SHA or number in REVIEWED_ADJACENT_BODY_SHA))))
           for number,_,_,mode in requested):
        raise ValueError('추가 연결의 근거 또는 원문 분할이 잘못됐습니다.')
    positions=sorted(requested,key=lambda row: row[1])
    if any(left[2]>right[1] for left,right in zip(positions,positions[1:])):
        raise ValueError('추가 연결 위치가 서로 겹칩니다.')
    groups={}
    pending=0
    at=out_at=0
    last=0
    legacy_end=legacy_receipts()['legacy_cache_span']['end']
    if ordered:
        with v1.with_name(v1.name+'.work').open('rb') as fp:
            prior=latest_slot(fp)
            fp.seek(prior['baseline_offset'])
            baseline=fp.read(prior['baseline_bytes'])
        if sha256(baseline).hexdigest().lower()!=prior['baseline_sha256'].lower():
            raise ValueError('원문 판정 목록이 바뀌었습니다.')
    boundaries={}
    for index,(number,width,saved) in enumerate(position.iter_unpack(old)):
        end=at+width
        if number and number in numbers:
            raise ValueError(f'기존 위치표에 이미 연결됐습니다. {number}')
        if not number and pending<len(positions) and positions[pending][1]<end:
            chosen=[]
            while pending<len(positions) and positions[pending][1]<end:
                entry=positions[pending]
                if not at<=entry[1]<entry[2]<=end:
                    raise ValueError(f'기존 미연결 범위 안의 위치가 아닙니다. {entry[0]}')
                chosen.append(entry)
                pending+=1
            groups[index]=(at,end,out_at,saved,chosen)
            if ordered:
                following=position.unpack_from(old,(index+1)*position.size)[0]
                if not (at>=legacy_end and following>last):
                    raise ValueError('주변의 기존 문서 순서를 확인하지 못했습니다.')
                available=[n for n in range(last+1,following) if not was_done(baseline,n-1)]
                lookup={n:i for i,n in enumerate(available)}
                for n,begin,stop,method in chosen:
                    if n not in lookup:
                        raise ValueError(f'기존 문서 순서에 없는 번호입니다. {n}')
                    if method:
                        k=lookup[n]+1
                        next_number=available[k] if k<len(available) else None
                        boundaries[n]=(at,end,next_number,method,last>0 and len(available)==1)
        elif number and at>=legacy_end:
            last=number
        at=end
        out_at+=saved
    if pending!=len(positions):
        raise ValueError('기존 미연결 범위를 찾지 못한 위치가 있습니다.')
    return groups,boundaries


def draft_gap_link_plan(source,index,state,requested,*,from_source,ordered):
    old_end=reserved+state['rows']*position.size
    prior_proof=read_source_binding_proof(index,state)
    index.seek(reserved)
    old=index.read(state['rows']*position.size)
    if len(old)!=state['rows']*position.size:
        raise ValueError('기존 문서 위치 배열이 줄었습니다.')
    groups,boundaries=gap_binding_groups(old,requested,ordered=ordered)
    originals=[(n,a,b,0 if ordered else slot) for n,a,b,slot in requested]
    if any(a and source[a-2:a]!=BREAK for _,a,_,_ in requested):
        raise ValueError('추가 연결 문서의 도입 경계가 다릅니다.')
    found=source_gap_matches(source,originals,boundaries=boundaries) if from_source else {}
    endpoint_proof={n for n,_,_,_ in originals if n in REVIEWED_UNORDERED_BODY_SHA and n not in boundaries} if from_source else set()
    proof_rows=list(SOURCE_BINDING.iter_unpack(prior_proof))
    if from_source:
        proof_rows.extend((n,boundaries[n][2] or 0,boundaries[n][3]+1) if n in boundaries
                          else (n,0,4 if n in endpoint_proof else 1)
                          for n,_,_,_ in originals)
    proof=b''.join(SOURCE_BINDING.pack(*row) for row in sorted(proof_rows))
    first=min(groups)
    plan=bytearray()
    new_total=state['rows']
    old_inputs=old_outputs=0
    for row_index,old_row in enumerate(position.iter_unpack(old[first*position.size:]),first):
        group=groups.get(row_index)
        if group is None:
            plan.extend(position.pack(*old_row))
            continue
        lo,hi,_,old_width,chosen=group
        old_inputs+=hi-lo
        old_outputs+=old_width
        if from_source:
            pieces=[]
            at=lo
            for n,_,_,_ in chosen:
                start,end=found[n]
                if at<start:
                    pieces.append((0,start-at,0))
                pieces.append((n,end-start,0))
                at=end
            if at<hi:
                pieces.append((0,hi-at,0))
        else:
            pieces=new_gap_rows(source,lo,hi,chosen)
        for number,width,_ in pieces:
            plan.extend(position.pack(number,width,NEW_GAP_ROW))
        new_total+=len(pieces)-1
    new_end=reserved+new_total*position.size
    receipt=dict(offset=new_end,rows=len(proof_rows),sha256=sha256(proof).hexdigest()) if proof else None
    pending_proof=max(old_end+len(prior_proof),new_end+len(proof))
    binding=dict(offset=pending_proof+len(proof),bytes=len(plan),prefix_rows=first,
                 input_start=groups[first][0],new_total=new_total,digest=sha256(plan).hexdigest(),
                 gaps_replaced=len(groups),old_input=old_inputs,old_output=old_outputs,proof=receipt,
                 pending_proof=pending_proof,
                 source_exact=(len(requested)-len(boundaries)-len(endpoint_proof) if from_source else 0),
                 source_ordered=sum(value[3]==1 for value in boundaries.values()),
                 source_words=sum(value[3]==2 for value in boundaries.values()),
                 source_manual=sum(value[3]==3 for value in boundaries.values())+len(endpoint_proof),
                 source_entire_gap=sum(value[3]==4 for value in boundaries.values()))
    journal=json.dumps(binding,separators=(',',':')).encode()
    pending=dict(offset=binding['offset']+len(plan),bytes=len(journal),sha256=sha256(journal).hexdigest())
    prefix=groups[first][2]
    position_header(dict(state,stage='binding_gap',link_plan=pending,
                         output_bytes=prefix,revision=state['revision']+1))
    index.seek(pending_proof)
    index.write(proof)
    index.write(plan)
    index.write(journal)
    index.seek(old_end)
    return plan,binding,pending,proof,prefix


def gap_copy(source,output,start,end):
    cursor=start
    for first,last,replacement in gap_edits(source,start,end):
        copy_segment(source,output,cursor,first)
        output.write(replacement)
        cursor=last
    copy_segment(source,output,cursor,end)


def bind_recovered_gap(*, from_source=False,ordered=False):
    if datetime.now(deadline.tzinfo)>=deadline:
        raise SystemExit('작업 종료 시각에 도달했습니다.')
    working=part if part.exists() else result
    with (v1.open('rb') as original, mmap.mmap(original.fileno(),0,access=mmap.ACCESS_READ) as source,
          working.open('r+b',buffering=1<<20) as output, meta.open('r+b',buffering=1<<20) as index):
        lock(output)
        lock(index)
        state=load_position(index)
        if state['input_stamp']!=stamp(original):
            raise ValueError('v1이 바뀌었습니다.')
        if state['stage'] in ('refined','published'):
            if working.samefile(v1) or stamp(output)[2]!=state['output_bytes']:
                raise ValueError('v1.1의 저장 위치가 달라졌습니다.')
            plan,binding,pending,proof,prefix=draft_gap_link_plan(
                source,index,state,json.load(sys.stdin),from_source=from_source,ordered=ordered)
            if working==result:
                if part.exists():
                    raise FileExistsError(part)
                result.rename(part)
            state.update(stage='binding_gap',link_plan=pending)
            output.seek(prefix)
            checkpoint(output,index,state)
        elif state['stage']=='binding_gap':
            binding=state['link_plan']
            if 'sha256' in binding:
                index.seek(binding['offset'])
                journal=index.read(binding['bytes'])
                if len(journal)!=binding['bytes'] or sha256(journal).hexdigest()!=binding['sha256']:
                    raise ValueError('이어받을 묶음 요약이 바뀌었습니다.')
                binding=json.loads(journal)
            index.seek(binding['offset'])
            plan=index.read(binding['bytes'])
            if len(plan)!=binding['bytes'] or sha256(plan).hexdigest()!=binding['digest']:
                raise ValueError('이어받을 위치 기록이 바뀌었습니다.')
            receipt=binding['proof']
            proof=b''
            if receipt:
                index.seek(binding.get('pending_proof',receipt['offset']))
                proof=index.read(receipt['rows']*SOURCE_BINDING.size)
                if len(proof)!=receipt['rows']*SOURCE_BINDING.size or sha256(proof).hexdigest()!=receipt['sha256']:
                    raise ValueError('이어받을 원문 연결 근거가 바뀌었습니다.')
            output.seek(state['output_bytes'])
        else:
            raise ValueError('추가 위치를 연결할 v1.1 작업본을 찾지 못했습니다.')
        index.seek(reserved+binding['prefix_rows']*position.size)
        cursor=binding['input_start']
        additions=Counter()
        for number,width,prior_width in position.iter_unpack(plan):
            if datetime.now(deadline.tzinfo)>=deadline:
                return
            end=cursor+width
            where=output.tell()
            new=prior_width==NEW_GAP_ROW
            if not number:
                if not state.get('linked_only'):
                    gap_copy(source,output,cursor,end)
                if new:
                    additions['unlinked_segments']+=1
                    additions['unlinked_input_bytes']+=width
                    additions['unlinked_output_bytes']+=output.tell()-where
            elif new:
                body_counts=Counter() if number in REVIEWED_GAP_POSITIONS else additions
                body=rewrite_bound_body(source,cursor,end,number,body_counts)
                output.write(transform(body,additions))
                additions['recovered_gap_documents']+=1
                additions['recovered_gap_bytes']+=width
            elif prior_width:
                output.write(transform(rewrite_bound_body(source,cursor,end,number,Counter()),Counter()))
            saved=output.tell()-where
            if not new and saved!=prior_width:
                raise ValueError(
                    f'기존 본문 길이가 달라졌습니다. {number}번 문서의 저장 당시 규칙으로 위치 연결을 '
                    '재개하고 새 규칙은 연결 뒤 전체 정제에 적용하세요.'
                )
            index.write(position.pack(number,width,saved))
            cursor=end
        if cursor!=len(source) or stamp(original)!=state['input_stamp']:
            raise ValueError('추가 연결 뒤 입력 끝이 달라졌습니다.')
        for label in ('source_exact','source_ordered','source_words','source_manual','source_entire_gap'):
            if binding.get(label):
                key=label+'_recovered'
                state[key]=state.get(key,0)+binding[label]
        for key,removed in (('recovered_gap_documents',0),('recovered_gap_bytes',0),
                            ('unlinked_segments',binding['gaps_replaced']),
                            ('unlinked_input_bytes',binding['old_input']),('unlinked_output_bytes',binding['old_output'])):
            state[key]=state.get(key,1 if key=='unlinked_segments' else 0)+additions.pop(key,0)-removed
        state['counts']=Counter(state['counts'])+additions
        if state.get('linked_only'):
            state['counts']['unlinked_ranges_held']=state['unlinked_segments']
            state['counts']['unlinked_bytes_held']=state['unlinked_input_bytes']
        state.update(stage='refined',rows=binding['new_total'],next_record=binding['new_total'])
        if binding['proof']:
            state['source_binding_proof']=binding['proof']
        del state['link_plan']
        output.truncate(output.tell())
        new_end=reserved+state['rows']*position.size
        index.seek(new_end)
        index.write(proof)
        index.seek(new_end)
        checkpoint(output,index,state)
        checkpoint(output,index,state)
        index.truncate(new_end+len(proof))
        index.flush()
        os.fsync(index.fileno())
        print(json.dumps({k:state[k] for k in ('stage','rows','output_bytes','counts',
              'recovered_gap_documents','recovered_gap_bytes','unlinked_input_bytes')},ensure_ascii=False))


def publish_refinement():
    working = part if part.exists() else result
    with (v1.open('rb') as original, working.open('r+b') as output, meta.open('r+b') as index):
        lock(output)
        lock(index)
        state = load_position(index)
        if (state['stage'] not in ('refined', 'published') or stamp(original) != state['input_stamp']
                or stamp(output)[2] != state['output_bytes']):
            raise ValueError('v1.1 최종 저장 전 파일 또는 작업 위치가 달라졌습니다.')
        read_source_binding_proof(index,state)
        index.seek(reserved)
        records = index.read(state['rows']*position.size)
        input_bytes = output_bytes = written = gaps = 0
        held = set(legacy_receipts()['legacy_admission_hold']['documents'])
        held.update(state.get('content_admission_hold', ()))
        if state.get('linked_only'):
            held.update(n for group in state['admission_review'].values() for n in group)
        saved_holds = set()
        repeats = dict(state.get('exact_repeats', ()))
        repeats.update(state.get('article_ui_repeats', ()))
        repeats.update(state.get('registry_repeats', ()))
        repeats.update(state.get('boundary_repeats', ()))
        for number, old_width, new_width in position.iter_unpack(records):
            if not number and new_width and state.get('linked_only'):
                raise ValueError('원문과 연결되지 않은 구간이 v1.1에 들어갔습니다.')
            if number in held and old_width:
                if new_width:
                    raise ValueError(f'보호 위치가 v1.1에 들어갔습니다. {number}')
                saved_holds.add(number)
            if number in repeats and new_width:
                raise ValueError(f'확인한 전체 문서 중복이 v1.1에 남았습니다. {number}')
            input_bytes += old_width
            output_bytes += new_width
            written += int(number != 0 and new_width > 0)
            gaps += int(number == 0)
        if (len(records) != state['rows']*position.size or input_bytes != state['input_stamp'][2]
                or output_bytes != state['output_bytes'] or saved_holds != held
                or gaps != state.get('unlinked_segments',1)):
            raise ValueError('최종 인덱스의 문서 위치 또는 보호 범위 수가 맞지 않습니다.')
        if result.exists() or result.is_symlink():
            if result.is_symlink() or not result.samefile(working):
                raise FileExistsError(result)
        else:
            os.link(working, result)
        if part.exists() and part.samefile(result):
            part.unlink()
        directory = os.open(result.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        if state['stage'] != 'published':
            state.update(stage='published', stored_documents=written,
                         published_at=datetime.now(deadline.tzinfo).isoformat(timespec='seconds'))
            output.seek(output_bytes)
            checkpoint(output,index,state)
        print(json.dumps({
            'path':str(result.resolve()), 'metadata':str(meta.resolve()),
            'published_at':state['published_at'], 'bytes':output_bytes,
            'indexed_bodies':written, 'counts':state['counts'],
            'recovered_gap_documents':state.get('recovered_gap_documents',0),
            'source_exact_recovered':state.get('source_exact_recovered',0),
            'source_ordered_recovered':state.get('source_ordered_recovered',0),
            'source_words_recovered':state.get('source_words_recovered',0),
            'source_manual_recovered':state.get('source_manual_recovered',0),
            'source_entire_gap_recovered':state.get('source_entire_gap_recovered',0),
            'unlinked_input_bytes':state['unlinked_input_bytes'],
            'deferred':sum(row['count'] for row in state['deferred']),
        },ensure_ascii=False))


if __name__ == '__main__':
    if sys.argv[1:] == ['--legacy']:
        write_legacy()
    elif sys.argv[1:] == ['--tail']:
        write_tail()
    elif sys.argv[1:] == ['--refine']:
        refine_contextual_footers()
    elif sys.argv[1:] == ['--refine-linked']:
        refine_contextual_footers(linked_only=True)
    elif sys.argv[1:] == ['--bind-gap']:
        bind_recovered_gap()
    elif sys.argv[1:] == ['--bind-source-gap']:
        bind_recovered_gap(from_source=True)
    elif sys.argv[1:] == ['--bind-source-order']:
        bind_recovered_gap(from_source=True,ordered=True)
    elif sys.argv[1:] == ['--publish']:
        publish_refinement()
    elif not sys.argv[1:]:
        write_prefix()
    else:
        raise SystemExit('사용법: refine_cleanup_text.py [--legacy | --tail | --refine | --refine-linked | --bind-gap | --bind-source-gap | --bind-source-order | --publish]')
