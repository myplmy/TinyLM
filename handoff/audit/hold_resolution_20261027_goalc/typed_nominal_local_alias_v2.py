"""Reject a predicate's subordinate object misread as the lead subject's role."""
from pathlib import Path
import importlib.util
import re

spec = importlib.util.spec_from_file_location('nominal_alias_v1', Path(__file__).with_name('typed_nominal_local_alias_v1.py'))
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
old_tail = '이며|이자|이다|였|이었다|로|으로|[ .,。]'
assert previous.ROLE.pattern.count(old_tail) == 1
PREDICATE_ROLE = re.compile(previous.ROLE.pattern.replace(old_tail, '이며|이자|이다|이고|였다|이었다|인[ \\t]|[.]'))
GEOGRAPHIC = {
    '산': re.compile(r'높이|해발|산맥|봉우리|위치|소재|[가-힣]+(?:시|군|도|현)[ \t]'),
    '강': re.compile(r'흐르|흘러|하천|유역|지류|발원|위치|[가-힣]+(?:시|군|도|현)[ \t]'),
    '섬': re.compile(r'위치|소재|해안|바다|해상|군도|[가-힣]+(?:시|군|도|현)[ \t]'),
}


def prove(text):
    value = previous.prove(text)
    if value is None:
        return None
    subject = previous.SUBJECT.match(text)
    # A comma between complete clauses cannot lend a later object's entity
    # word to the lead subject. Numeric grouping commas are not boundaries.
    predicate = re.split(r'(?<![0-9])[,，]|[,，](?![0-9])|[;；]', subject['predicate'], maxsplit=1)[0]
    role = PREDICATE_ROLE.search(predicate)
    if role is None:
        return None
    stripped_role = re.sub(r'^(?:공립|사립|국립|공공)[ \t]+', '', role[0])
    if stripped_role in GEOGRAPHIC and not GEOGRAPHIC[stripped_role].search(predicate):
        return None
    return dict(value, role=role[0],
        rule='UNIQUE_EMPTY_ALIAS_WITH_FIRST_CLAUSE_SUBJECT_ROLE_AND_GEOGRAPHIC_CONTEXT_V2')
