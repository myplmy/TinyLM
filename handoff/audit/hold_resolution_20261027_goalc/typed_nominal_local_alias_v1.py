"""Prove only a unique empty alias on a positively typed, completed lead subject."""
import hashlib
import re

SUBJECT = re.compile(r"\A(?P<space>[ \t\r\n]*)(?P<name>[가-힣〈《][^()\r\n]{1,159})"
                     r"(?P<empty>\([ \t]*\))(?P<topic>은|는)(?P<predicate>[ \t]+[^\r\n]+)")
ROLE = re.compile(r"(?:(?:공립|사립|국립|공공)[ \t]+)?(?:커뮤니티[ \t]+칼리지|대학교|대학|학교|"
                  r"박물관|도서관|연구소|정당|단체|기업|회사|군주|왕|가수|배우|작가|"
                  r"음악가|축구[ \t]*선수|야구[ \t]*선수|감독|정치인|영화|싱글|음반|"
                  r"노래|소설|만화|게임|도시|자치체|교량|다리|산|강|섬)(?=이며|이자|이다|였|이었다|로|으로|[ .,。])")
TECHNICAL = re.compile(r"수학|방정식|함수|수식|변수|계수|정리|증명|행렬|공식|연산|"
                       r"기호|문자|글리프|유니코드|U\+|발음|음운|로마자|괄호|코드|소스|"
                       r"프로그래밍|메서드|메소드|문법|호출|[=+*/\\{}\[\]<>`]|"
                       r"\b(?:Python|Java|SQL|Unicode|codepoint|function)\b", re.I)
QUOTE = re.compile(r"인용|전사|문구|예문|문자열|따옴표|quoted|quotation|transcription", re.I)
COMPLETE = re.compile(r"[.!?。][ \t]*(?:\r?\n)?\Z")


def prove(text):
    first = text.lstrip().split("\n\n", 1)[0]
    if not first or not COMPLETE.search(first) or TECHNICAL.search(first) or QUOTE.search(first):
        return None
    match = SUBJECT.match(text)
    if match is None or not re.search(r"[가-힣]", match['name']):
        return None
    # The role has to be in the actual first subject's predicate, rather than
    # an unrelated paragraph or an entity name alone.
    predicate = match['predicate'].split('. ', 1)[0]
    role = ROLE.search(predicate)
    if role is None or len(re.findall(r"\([ \t]*\)", text)) != 1:
        return None
    lo, hi = match.span('empty')
    clean = text[:lo] + text[hi:]
    return dict(candidate=clean, source_characters=[lo, hi], original=text[lo:hi],
        replacement='', role=role[0], subject=match['name'],
        rule='UNIQUE_EMPTY_ALIAS_ON_EXPLICIT_NOMINAL_SUBJECT_WITH_SOURCE_ROLE_V1',
        source_text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest().upper(),
        clean_text_sha256=hashlib.sha256(clean.encode('utf-8')).hexdigest().upper())
