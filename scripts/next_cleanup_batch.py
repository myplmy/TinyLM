#!/usr/bin/env python3
"""원문 순서대로 다음 정제 묶음을 출력한다. 본문은 쓰지 않는다."""

from __future__ import annotations

import argparse
from array import array
from bisect import bisect_left
from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, replace
import fcntl
from hashlib import blake2b, sha256
from itertools import accumulate
import json
import mmap
import os
from pathlib import Path
import re
import stat
from struct import Struct
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import HEADINGS, normalize_heading

SLOT_BYTES = 4096
BASELINE_START = 2 * SLOT_BYTES
REPORT_EVERY = 5000
BATCH_BYTES = 100_000
BATCH_DOCUMENTS = 48
FOCUSED_DOCUMENTS = 160
FOCUSED_SOURCE_BYTES = 500_000
MAX_PLANNED_BATCHES = 16
MAX_PAYLOAD = 19_999_999
EOS = 2
EOS_BYTES = EOS.to_bytes(2, 'little')
BREAK = b'\n\n'
DOCUMENT_POSITION = Struct('<IIQ')
EMPTY_FOOTER_LINES = HEADINGS | {
    '분류', 'footnotes', 'bibliography', 'categories', '<ref/>', '<ref />', '<ref></ref>',
}
CONTEXT_MARKUP = re.compile(
    r'```|~~~|\{\||\{\{|<!--|<\s*/?\s*(?:pre|code|blockquote|table)\b|^[ \t]*>',
    re.I | re.M,
)
FORMAT_HINT = re.compile(
    r'\[\[|\]\]|\{\{|\}\}|<\s*/?\s*[a-z][\w:-]*\b|https?://|www\.'
    r'|\(\s*(?:(?:영어|일본어|중국어|한자)\s*:\s*)?[,，]*\s*\)'
    r'|^\s*(?:관련 기사|관련 문서|참고 자료|외부 자료|로그인|구독하기|'
    r'related articles|sign in|skip to content|table of contents)\s*$'
    r'|^\s*\|[|!+}{-]', re.I,
)
LIFE_DATE = r'([12][0-9]{3})년[ \t]*[0-9]{1,2}월[ \t]*[0-9]{1,2}일'
INTRO_LIFE_DATES = re.compile(
    r'\A[ \t]*[^()\r\n]{1,100}\(' + LIFE_DATE + r'[ \t]*[~∼–—-][ \t]*(?:'
    + LIFE_DATE + r')?[ \t]*\)[ \t]*(?:은|는)[ \t]+')
LIFE_CATEGORY = re.compile(r'([12][0-9]{3})년[ _\t]+(출생|사망)')
NUMBER_INTRO = re.compile(
    r'([1-9][0-9]{0,5})\([가-힣 ]+\)(?:은|는) ([0-9]+)보다 크고 ([0-9]+)보다 작은 자연수이다\.')
NUMBER_SORT = re.compile(r'([1-9][0-9]?)e0?([0-5])[ \t]+([0-9]+)')
NUMBER_OUTLINE = {'수학', '과학', '기타', '교통', '문화', '같이 보기', '각주', '외부 링크'}
NAME_WITH_EMPTY_ALIAS = re.compile(
    r'\A(?P<name>[가-힣][가-힣A-Za-z0-9·ㆍ \'’.-]{1,90})'
    r'(?P<alias>\([ \t]*[,，][ \t,，]*\))(?P<particle>은|는|의)[ \t]+')
NAMED_ERA_WITH_EMPTY_SLOT = re.compile(
    r'\A[가-힣·ㆍ ]{2,65}\([\u3400-\u9fff]+(?P<gap>[,，][ \t]*[,，][ \t]*)'
    r'(?=[가-힣]+\([\u3400-\u9fff]+\)[ \t]+[가-힣]+\([\u3400-\u9fff]+\)[ \t]+'
    r'[0-9]{1,3}년[ \t]+[0-9]{1,2}월[ \t]+[0-9]{1,2}일)')
DEFINED_ENTITY = re.compile(r'야구 구단|축구 구단|등장인물|편의점 브랜드|레코드 회사|로마자 표기법|다른 뜻은 다음과 같다')
ALIAS_LITERAL = re.compile(r'함수|튜플|좌표|쉼표|문장 부호|문법|배열|행렬|인수|인자|예제|호출')


def arguments(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--source', type=Path, action='append',
                        help='원문 파일. 여러 파일은 실제 순서대로 반복 지정.')
    parser.add_argument('--cleaned', type=Path, required=True, help='정제 TXT 파일.')
    parser.add_argument('--metadata', type=Path, help='기본값은 정제 TXT 뒤에 .work를 붙인 파일.')
    parser.add_argument('--format', choices=('jsonl', 'lines', 'u16-eos'),
                        help='JSONL text 필드, 한 줄당 한 문서, 또는 EOS 2가 경계인 uint16 LE.')
    parser.add_argument('--tokenizer', type=Path, help='u16-eos 원문을 읽을 토크나이저 JSON.')
    return parser


def local_file(path, *, may_create=False):
    protected = ROOT / 'datasets/TinyDataset'
    absolute = Path(os.path.abspath(path.expanduser()))
    if absolute.is_relative_to(protected):
        raise ValueError('보호 데이터 폴더는 이 도구에서 열 수 없습니다.')
    resolved = absolute.resolve(strict=not may_create)
    if resolved.is_relative_to(protected):
        raise ValueError('보호 데이터 폴더로 연결된 경로입니다.')
    try:
        mode = resolved.stat().st_mode
    except FileNotFoundError:
        if not may_create:
            raise
    else:
        if not stat.S_ISREG(mode):
            raise ValueError(f'일반 파일이 필요합니다. {resolved}')
    return resolved


def file_stamp(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]


def stamp(file):
    return file_stamp(os.fstat(file.fileno()))


def signature(value):
    return sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def lock(file):
    deadline = time.monotonic() + 3
    while True:
        try:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError as exc:
            if time.monotonic() >= deadline:
                raise ValueError('다른 정제 명령이 같은 파일을 사용 중입니다.') from exc
            time.sleep(0.05)


class Progress:
    """One file, alternating checksummed state slots and an immutable legacy bitmap."""

    def __init__(self, path, stack, output):
        self.path, self.stack = path, stack
        self.revision, self.baseline = 0, b''
        try:
            self.file = stack.enter_context(path.open('r+b', buffering=0))
        except FileNotFoundError:
            self.file = None
        else:
            if stamp(self.file)[:2] == stamp(output)[:2]:
                raise ValueError('정제본과 메타데이터 파일이 같습니다.')
            lock(self.file)

    def load(self):
        if self.file is None:
            return None
        fd = self.file.fileno()
        versions = []
        for offset in (0, SLOT_BYTES):
            raw = os.pread(fd, SLOT_BYTES, offset)
            checksum, sep, state = raw.rstrip(b'\0').partition(b'\n')
            if len(raw) == SLOT_BYTES and sep and sha256(state).hexdigest().encode() == checksum:
                versions.append(json.loads(state))
        if not versions:
            raise ValueError('작업 메타데이터에서 온전한 저장 위치를 찾지 못했습니다.')
        state = max(versions, key=lambda value: value['revision'])
        if state.get('version') != 1:
            raise ValueError('지원하는 작업 메타데이터 형식이 아닙니다.')
        self.revision = state['revision']
        offset = state.get('baseline_offset', BASELINE_START)
        if offset not in (BASELINE_START, BASELINE_START + state['baseline_bytes']):
            raise ValueError('완료 목록 위치가 잘못됐습니다.')
        self.baseline = os.pread(fd, state['baseline_bytes'], offset)
        if (len(self.baseline) != state['baseline_bytes']
                or sha256(self.baseline).hexdigest() != state['baseline_sha256']):
            raise ValueError('이전 완료 목록이 손상됐습니다.')
        positions = state.get('document_index')
        if positions and positions['offset'] + positions['rows'] * DOCUMENT_POSITION.size > os.fstat(fd).st_size:
            raise ValueError('저장된 문서 위치 기록이 짧아졌습니다.')
        total, done, milestone = (state[k] for k in ('total', 'done', 'milestone'))
        if (any(type(n) is not int for n in (total, done, milestone))
                or not 0 <= done <= total or milestone < -REPORT_EVERY
                or milestone % REPORT_EVERY or total - done < milestone):
            raise ValueError('저장된 문서 수 또는 보고 위치가 잘못됐습니다.')
        return state

    def save(self, state):
        revision = self.revision + 1
        body = json.dumps(dict(state, revision=revision), separators=(',', ':')).encode()
        raw = sha256(body).hexdigest().encode() + b'\n' + body
        if len(raw) > SLOT_BYTES:
            raise ValueError('파일 경로 또는 작업 위치 정보가 저장 한도를 넘었습니다.')
        new = self.file is None
        if new:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            self.file = self.stack.enter_context(os.fdopen(fd, 'r+b', buffering=0))
            lock(self.file)
            if self.baseline and os.pwrite(fd, self.baseline, BASELINE_START) != len(self.baseline):
                raise OSError('이전 완료 목록을 온전히 쓰지 못했습니다.')
            os.fsync(fd)
        fd = self.file.fileno()
        if stamp(self.file)[:2] != file_stamp(self.path.stat())[:2]:
            raise ValueError('작업 메타데이터 파일이 교체됐습니다.')
        offset = ((revision - 1) % 2) * SLOT_BYTES
        if os.pwrite(fd, raw.ljust(SLOT_BYTES, b'\0'), offset) != SLOT_BYTES:
            raise OSError('작업 위치를 온전히 쓰지 못했습니다.')
        os.fsync(fd)
        if new:
            directory = os.open(self.path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        self.revision = revision


def count_docs(file, binary):
    file.seek(0)
    count, tail = 0, b''
    for block in iter(lambda: file.read(4 * 1024 * 1024), b''):
        if binary:
            if len(block) % 2:
                raise ValueError('uint16 원문이 홀수 바이트에서 끝납니다.')
            words = array('H')
            words.frombytes(block)
            if sys.byteorder != 'little':
                words.byteswap()
            count += words.count(EOS)
            tail = block[-2:]
        else:
            count += block.count(b'\n')
            tail = block[-1:]
    return count + bool(tail and tail != (EOS_BYTES if binary else b'\n'))


def eos_records(file):
    body = bytearray()
    base = file.tell()
    for block in iter(lambda: file.read(64 * 1024), b''):
        start, search = 0, 0
        while (boundary := block.find(EOS_BYTES, search)) >= 0:
            search = boundary + 1
            if boundary % 2:
                continue
            body.extend(block[start:boundary])
            if len(body) > MAX_PAYLOAD:
                raise ValueError('원문 한 구간이 너무 커서 온전한 본문을 출력할 수 없습니다.')
            yield base + boundary + 2, bytes(body), True
            body.clear()
            start = boundary + 2
        body.extend(block[start:])
        if len(body) > MAX_PAYLOAD:
            raise ValueError('원문 한 구간이 너무 커서 온전한 본문을 출력할 수 없습니다.')
        base += len(block)
    if body:
        yield base, bytes(body), False


@dataclass(frozen=True)
class Document:
    number: int
    file: int
    offset: int
    text: str | None
    note: str = ''
    prepare_structure: bool = False
    compact_preview: bool = False
    prepare_metadata: bool = False
    automatic_text: str | None = None


def empty_footer(doc):
    """Remove only an empty, separate footer. Return the draft and removed labels."""
    original = doc.text
    if not original or doc.note:
        return original, ()
    lines = original.splitlines(keepends=True)
    removed, separated = [], False
    index = len(lines) - 1
    while index >= 0:
        line = lines[index]
        if not line.strip():
            separated = True
        elif not line[0].isspace() and normalize_heading(line) in EMPTY_FOOTER_LINES:
            removed.append(line.strip())
            separated = False
        else:
            break
        index -= 1
    if not removed or index < 0 or not separated or CONTEXT_MARKUP.search(original):
        return original, ()
    return ''.join(lines[:index + 1]).rstrip('\r\n'), tuple(reversed(removed))


def automatic_format(doc):
    if doc.automatic_text is not None:
        return doc.automatic_text, ('자연수 문서의 빈 절과 정렬 표식',)
    draft, removed = empty_footer(doc)
    if not doc.prepare_structure or not draft or doc.note or CONTEXT_MARKUP.search(draft):
        return draft, removed
    from scripts.p106b_hold_resolution_policy_v4 import empty_sections, intro
    from scripts.p106b_hold_resolution_policy_v6 import empty_reference_slots
    from scripts.p106b_hold_resolution_policy_v18 import first_nominal_alias
    from scripts.p106b_hold_resolution_policy_v22 import typed_initial_alias

    if not intro(draft):
        return draft, removed
    for rule, label in ((empty_sections, '내용 없는 절'),
                        (empty_reference_slots, '내용 없는 서지 항목'),
                        (first_nominal_alias, '이름 병기의 빈 구분자'),
                        (typed_initial_alias, '정의 서두의 빈 별칭 괄호')):
        clean, changes = rule(draft)
        if changes and clean.strip():
            draft = clean
            removed += (f'{label} {len(changes)}곳',)
    if doc.prepare_metadata:
        draft, labels = format_category_footer(draft)
        removed += labels
    return draft, removed


def format_category_footer(text):
    from scripts.p106b_hold_resolution_policy_v17 import BLOCK, PERSON_ROLE, intro, separate_metadata_suffix

    draft, empty, proven = separate_metadata_suffix(text)
    labels = (f'분류 앞 빈 절 {len(empty)}곳',) if empty else ()
    dates = INTRO_LIFE_DATES.match(draft)
    if not proven or dates is None or not PERSON_ROLE.search(intro(draft) or ''):
        return draft, labels
    blocks = [block for block in BLOCK.finditer(draft) if block[0].strip()]
    tail = blocks[-1]
    kept, count = [], 0
    years = {'출생': dates[1], '사망': dates[2]}
    for line in tail[0].splitlines(keepends=True):
        label = LIFE_CATEGORY.fullmatch(line.strip())
        if label is not None and label[1] == years[label[2]]:
            count += 1
        else:
            kept.append(line)
    if count:
        draft = draft[:tail.start()] + ''.join(kept) + draft[tail.end():]
        labels += (f'첫 문장의 생몰 연도와 일치한 분류 {count}곳',)
    return draft, labels


def clean_number_article(text):
    if not text or CONTEXT_MARKUP.search(text):
        return None
    lines = text.split('\n')
    entries = [i for i, line in enumerate(lines) if line.strip()]
    if len(entries) < 5:
        return None
    intro = NUMBER_INTRO.fullmatch(lines[entries[0]].strip())
    marker = NUMBER_SORT.fullmatch(lines[entries[-1]].strip())
    if intro is None or marker is None:
        return None
    number, previous, following = map(int, intro.groups())
    bucket, exponent, key = map(int, marker.groups())
    if (previous != number - 1 or following != number + 1 or key != number
            or number // 10**exponent != bucket or entries[-1] - entries[-2] < 2
            or lines[entries[1]].strip() != '수학'):
        return None
    removed = {entries[-1]}
    facts = 0
    for index, subsequent in zip(entries[1:-1], entries[2:]):
        line = lines[index].strip()
        if line in NUMBER_OUTLINE:
            empty = lines[subsequent].strip() in NUMBER_OUTLINE or subsequent == entries[-1]
            if empty and subsequent - index >= 2:
                removed.add(index)
            elif line in {'같이 보기', '각주', '외부 링크'} or empty:
                return None
        elif (line.endswith(('.', '。')) and not FORMAT_HINT.search(line)
              or line == f'연도: {number}년 기원전 {number}년'):
            facts += 1
        else:
            return None
    if facts < 2:
        return None
    return '\n'.join(line for i, line in enumerate(lines) if i not in removed).rstrip('\n')


def clean_empty_initial_alias(text, *, dated_names=True):
    match = NAME_WITH_EMPTY_ALIAS.match(text)
    era = NAMED_ERA_WITH_EMPTY_SLOT.match(text) if dated_names and match is None else None
    if (match is None and era is None) or CONTEXT_MARKUP.search(text):
        return text
    if era is not None:
        lo, hi = era.span('gap')
        return text[:lo] + text[lo] + ' ' + text[hi:]
    sentence = re.split(r'(?<=[.!?。])[ \t]+|\n', text[match.end():], maxsplit=1)[0]
    if not sentence or ALIAS_LITERAL.search(match['name'] + ' ' + sentence):
        return text
    from scripts.p106b_hold_resolution_policy_v4 import ENTITY

    if not (ENTITY.search(sentence) or DEFINED_ENTITY.search(sentence)):
        return text
    last = match['name'][-1]
    if match['particle'] != '의' and (
            not '가' <= last <= '힣'
            or ('은' if (ord(last) - ord('가')) % 28 else '는') != match['particle']):
        return text
    lo, hi = match.span('alias')
    return text[:lo] + text[hi:]


def preview_excerpt(line):
    raw = line.encode('utf-8')
    if len(raw) <= 160:
        return line
    hint = FORMAT_HINT.search(line)
    offset = len(line[:hint.start()].encode('utf-8')) if hint else 0
    if offset > 100:
        head = raw[:55].decode('utf-8', 'ignore')
        clue = raw[offset - 20:offset + 85].decode('utf-8', 'ignore')
        return f'{head} … {clue} [일부 표시]'
    return raw[:160].decode('utf-8', 'ignore') + ' [일부 표시]'


def preview_lines(body, focus, abbreviate_repeats=False, compact=False):
    lines = body.split('\n')
    if not focus or len(lines) <= 18:
        return enumerate(lines, 1)
    protected = CONTEXT_MARKUP.search(body)
    compact = compact and not protected
    opening, ending = (2, 4) if compact else (3, 7)
    visible = set(range(opening)) | set(range(len(lines) - ending, len(lines)))
    repeated = Counter(line.strip() for line in lines if len(line.strip()) >= 12)
    for index, line in enumerate(lines):
        if (normalize_heading(line) in EMPTY_FOOTER_LINES or FORMAT_HINT.search(line)
                or repeated[line.strip()] > 1):
            visible.update(range(max(0, index - 1), min(len(lines), index + 2)))
    if not abbreviate_repeats or protected:
        return ((index + 1, lines[index]) for index in sorted(visible))
    snippets, first = [], {}
    for index in sorted(visible):
        line = lines[index]
        previous = first.setdefault(line, index + 1) if len(line) >= 45 else index + 1
        if compact:
            line = preview_excerpt(line)
        snippets.append((index + 1, line if previous == index + 1 else f'[같은 문장: {previous}줄]'))
    return snippets


def review_size(doc):
    if doc.automatic_text is not None:
        return len(str(doc.number)) + 2
    draft, _ = automatic_format(doc)
    if not draft:
        return 80
    return 100 + sum(len(line.encode('utf-8')) + len(str(number)) + 2
                     for number, line in preview_lines(draft, True, doc.prepare_structure, doc.compact_preview))


class Sources:
    def __init__(self, args, stack, output):
        self.format = args.format
        self.binary = self.format == 'u16-eos'
        if self.binary != (args.tokenizer is not None):
            raise ValueError('u16-eos를 사용할 때만 토크나이저를 하나 지정하세요.')
        self.paths = [local_file(path) for path in args.source]
        self.files = [stack.enter_context(path.open('rb')) for path in self.paths]
        self.tokenizer = None
        items = list(zip(self.paths, self.files))
        if self.binary:
            path = local_file(args.tokenizer)
            self.tokenizer = stack.enter_context(path.open('rb'))
            items.append((path, self.tokenizer))
        self.inputs = [(path, file, stamp(file)) for path, file in items]
        self.sizes = [stamp(file)[2] for file in self.files]
        identities = {tuple(info[:2]) for _, _, info in self.inputs}
        if len(identities) != len(self.inputs) or tuple(stamp(output)[:2]) in identities:
            raise ValueError('중복 원문이나 원문과 동일한 정제본을 지정했습니다.')
        self.key = signature([self.format, [(str(path), info) for path, _, info in self.inputs]])
        self.config = dict(source=[str(path) for path in self.paths], format=self.format,
                           tokenizer=str(items[-1][0]) if self.binary else None)
        self.codec = None

    def check(self):
        for path, file, original in self.inputs:
            if stamp(file) != original or file_stamp(path.stat()) != original:
                raise ValueError(f'원문 또는 토크나이저 파일이 바뀌었습니다. {path}')

    def total(self):
        return sum(count_docs(file, self.binary) for file in self.files)

    def records(self, cursor):
        slot, offset = cursor
        if not 0 <= slot < len(self.files) or not 0 <= offset <= self.sizes[slot]:
            raise ValueError('정제본의 재개 위치가 원문 범위를 벗어났습니다.')
        if self.binary and offset % 2:
            raise ValueError('정제본의 재개 위치가 uint16 경계와 다릅니다.')
        for index in range(slot, len(self.files)):
            file = self.files[index]
            file.seek(offset if index == slot else 0)
            if self.binary:
                for end, raw, complete in eos_records(file):
                    yield index, end, raw, complete
            else:
                for raw in iter(lambda: file.readline(MAX_PAYLOAD + 1), b''):
                    if len(raw) > MAX_PAYLOAD:
                        raise ValueError('원문 한 줄이 너무 커서 온전한 본문을 출력할 수 없습니다.')
                    yield index, file.tell(), raw, True

    def document(self, number, index, offset, raw, complete):
        note = ''
        if self.binary:
            if self.codec is None:
                from scripts.diag_p106b_native_expansion import ByteCodec
                self.codec = ByteCodec(json.load(self.tokenizer))
            words = array('H')
            words.frombytes(raw)
            if sys.byteorder != 'little':
                words.byteswap()
            try:
                text, _ = self.codec.text(words)
            except UnicodeError:
                return Document(number, index, offset, None, '원문 UTF-8 손상')
            if not complete:
                note = '원문의 마지막 구간에 EOS가 없습니다.'
        else:
            text = raw.decode('utf-8').removesuffix('\n').removesuffix('\r')
            if self.format == 'jsonl':
                row = json.loads(text)
                if not isinstance(row, dict) or not isinstance(row.get('text'), str):
                    raise ValueError(f'JSONL text 필드가 없습니다. {self.paths[index]} @ {offset}')
                text = row['text']
        return Document(number, index, offset, text, note)


def existing_inputs(config):
    return argparse.Namespace(source=[Path(path) for path in config['source']],
                              format=config['format'],
                              tokenizer=Path(config['tokenizer']) if config['tokenizer'] else None)


def history_scope(path):
    base = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
    if path != base / 'hold_cleaned.txt':
        raise ValueError('이전 완료 기록이 연결된 기존 hold_cleaned.txt를 지정하세요.')
    return json.loads((base / 'scope.json').read_bytes())


def digest(file):
    file.seek(0)
    value = sha256()
    for block in iter(lambda: file.read(4 * 1024 * 1024), b''):
        value.update(block)
    return value.hexdigest().upper()


def historical_rows(directory, manifest):
    for shard in manifest['shards']:
        value, count = sha256(), 0
        path = directory / shard['path']
        with path.open('rb') as stream:
            for raw in stream:
                value.update(raw)
                count += 1
                yield json.loads(raw)
        if count != shard['rows'] or value.hexdigest().upper() != shard['sha256']:
            raise ValueError(f'기존 기록 파일이 확인된 내용과 다릅니다. {path}')


def verified_selection(audit, restricted):
    """Adopted IDs and bodies only; this history never supplies new work."""
    sys.path.insert(0, str(audit))
    from selection_metadata_store_v1 import SelectionStore

    last = audit / 'ROOT_AUTHORED_SELECTIONS_V64.json'
    prior = audit / 'ROOT_AUTHORED_SELECTIONS_V44.json'
    receipt = json.loads((audit / 'ROOT64_AUTHORED_LITERAL_SELECTION_INDEPENDENT_VERIFIED_V1.json').read_bytes())
    store = SelectionStore(audit)
    old = {row['original_text_sha256'] for row in store.read(prior)['rows']}
    rows = store.read(last, receipt['input_pins'][str(last.relative_to(ROOT))])['rows']
    for row in rows:
        selected = row['selected']
        if (row['id'] not in restricted and row['original_text_sha256'] not in old
                and selected['decision'] in {'KEEP', 'EDIT'}):
            yield row['id'], row['original_text_sha256'], selected


def covered_bytes(spans):
    total, end = 0, 0
    for lo, hi in sorted(spans):
        if hi > end:
            total += hi - max(end, lo)
            end = hi
    return total


def restore_history(path, output, sources, scope):
    # The old TXT has no IDs. Recover only exact saved ranges or a verified
    # sequence found in that actual file. Remaining work is picked from source.
    for file, spec in zip(sources.files + [sources.tokenizer], scope['inputs'] + [scope['tokenizer']]):
        if digest(file) != spec['sha256']:
            raise ValueError(f'이전 기록을 연결할 원문 또는 토크나이저가 바뀌었습니다. {file.name}')
    starts, total = {}, 0
    for row in scope['inputs']:
        starts[row['name']] = total, row['intervals']
        total += row['intervals']
    baseline = bytearray((total + 7) // 8)
    counts, spans, origins = Counter(), [], set()

    def ordinal(ident):
        name, number = ident.split(':')
        offset, length = starts[name]
        index = int(number)
        if not 0 <= index < length:
            raise ValueError(f'기존 원문 ID가 범위를 벗어났습니다. {ident}')
        return offset + index

    def mark(ident, why):
        index = ordinal(ident)
        if not was_done(baseline, index):
            baseline[index // 8] |= 1 << (index % 8)
            counts[why] += 1

    base = path.parent
    audit = ROOT / 'handoff/audit/hold_resolution_20261027_goalc'
    guard = json.loads((audit / 'GUARDED_SOURCE_METADATA_CONTRACT_V6.json').read_bytes())
    restricted = set(guard['restricted_ids']) | set(guard['trusted_metadata'])
    cache = base / 'cache_reviewed_partial_v18'
    built = json.loads((cache / 'built.json').read_bytes())
    proof = json.loads((cache / 'verified.json').read_bytes())
    if (proof['status'] != 'CPU_FULL_CACHE_VERIFIED'
            or built['lineage']['scope_sha256'] != sha256((base / 'scope.json').read_bytes()).hexdigest().upper()
            or built['counts']['documents'] != total):
        raise ValueError('이전 정제 기록이 확인된 원문 범위에 연결되지 않습니다.')
    manifests = built['manifests']
    with mmap.mmap(output.fileno(), 0, access=mmap.ACCESS_READ) as txt:
        with (base / 'hold_text_edits.jsonl').open('rb') as index:
            for raw in index:
                row = json.loads(raw)
                body = row['body']
                lo, hi = body['start'], body['end']
                if (row['id'] not in restricted and ROOT / body['path'] == path
                        and 0 <= lo < hi <= len(txt) - len(BREAK)
                        and txt[hi:hi + len(BREAK)] == BREAK
                        and sha256(txt[lo:hi]).hexdigest().upper() == body['sha256']):
                    mark(row['id'], 'indexed')
                    origins.add(row['source']['sha256'])
                    spans.append((lo, hi + len(BREAK)))

        def blob(row):
            return row['text'].encode() + BREAK

        train_path = cache / 'text/train'
        first_shard = train_path / manifests['text_train']['shards'][0]['path']
        with first_shard.open('rb') as file:
            marker = blob(json.loads(file.readline())) + blob(json.loads(file.readline()))
        start = txt.find(marker)
        if start >= 0 and txt.find(marker, start + 1) >= 0:
            start = -1
        # The earlier export appended adopted bodies immediately before this
        # sequence. Recover the exact suffix, without guessing at other spans.
        end = start
        if start >= 0:
            for ident, original_hash, selected in reversed(list(verified_selection(audit, restricted))):
                body_path = (ROOT / selected['body']).resolve()
                if not body_path.is_relative_to(base) or not body_path.is_file():
                    break
                body = body_path.read_bytes()
                if sha256(body).hexdigest().upper() != selected['clean_text_sha256']:
                    break
                size = len(body) + len(BREAK)
                lo = end - size
                if lo < 0 or txt[lo:end] != body + BREAK:
                    break
                mark(ident, 'selected')
                origins.add(original_hash)
                spans.append((lo, end))
                end = lo

        end = start
        aligned = start >= 0
        for split in ('train', 'val'):
            manifest = manifests['text_' + split]
            for row in historical_rows(cache / 'text' / split, manifest):
                if not aligned:
                    continue
                body = blob(row)
                if txt[end:end + len(body)] == body:
                    end += len(body)
                    if row['id'] not in restricted:
                        mark(row['id'], 'copied')
                elif txt[:len(body)] == body and len(body) <= start and row['id'] not in restricted:
                    # The prior export skipped exact bodies already in its prefix.
                    mark(row['id'], 'already_present')
                    spans.append((0, len(body)))
                else:
                    earlier = txt.find(BREAK + body, 0, start)
                    if earlier < 0:
                        aligned = False
                    elif row['id'] not in restricted:
                        mark(row['id'], 'already_present')
                        spans.append((earlier + len(BREAK), earlier + len(BREAK) + len(body)))
        if start >= 0:
            spans.append((start, end))
        counts['unmapped_bytes'] = len(txt) - covered_bytes(spans)

    for row in historical_rows(cache / 'ledger', manifests['ledger']):
        if row['decision'] == 'EXCLUDE':
            mark(row['id'], 'excluded')
        elif (row['decision'] == 'HOLD' and row['id'] not in restricted
              and row['original_text_sha256'] in origins):
            mark(row['id'], 'earlier_source_alias')
    counts['text_confirmed'] = sum(counts[key] for key in ('indexed', 'selected', 'copied', 'already_present'))
    return total, bytes(baseline), dict(counts, restricted=sorted(map(ordinal, restricted)))


def initial_state(sources, output_stamp, total, baseline=b'', restored=None):
    done = sum(byte.bit_count() for byte in baseline)
    left = total - done
    mark = ((left - 1) // REPORT_EVERY) * REPORT_EVERY if left else 0
    return dict(version=1, source=sources.key, inputs=sources.config, output=output_stamp,
                cursor=[0, 0], scanned=0, done=done, total=total, milestone=mark,
                baseline_bytes=len(baseline), baseline_sha256=sha256(baseline).hexdigest(),
                restored=restored)


@contextmanager
def open_pair(args, *, initialize):
    path = local_file(args.cleaned)
    metadata_path = local_file(args.metadata or path.with_name(path.name + '.work'), may_create=True)
    with ExitStack() as stack:
        output = stack.enter_context(path.open('r+b', buffering=0))
        lock(output)
        before = stamp(output)
        progress = Progress(metadata_path, stack, output)
        state = progress.load()
        if state is None and not initialize:
            raise ValueError('먼저 다음 묶음 조회 도구를 실행하세요.')
        recover = getattr(args, 'recover_previous', False)
        if recover and state is not None:
            raise ValueError('이전 완료분을 이미 불러온 메타데이터가 있습니다.')
        if state is None and before[2] and not recover:
            raise ValueError(f'이전 완료 정보를 먼저 연결해야 합니다. {path}')
        spec = history_scope(path) if recover else None
        if spec is not None:
            if args.source or args.format or args.tokenizer:
                raise ValueError('이전 완료 정보 복구에는 기존 범위 파일의 원문을 사용하세요.')
            source_args = existing_inputs(dict(source=[str(ROOT / row['path']) for row in spec['inputs']],
                                               format='u16-eos', tokenizer=str(ROOT / spec['tokenizer']['path'])))
        elif args.source and args.format:
            source_args = args
        elif state is not None and not (args.source or args.format or args.tokenizer):
            source_args = existing_inputs(state['inputs'])
        else:
            raise ValueError('처음에는 실제 원문 파일과 문서 형식을 함께 지정하세요.')
        sources = Sources(source_args, stack, output)
        if progress.file is not None and any(stamp(progress.file)[:2] == info[:2]
                                             for _, _, info in sources.inputs):
            raise ValueError('원문과 작업 메타데이터가 같은 파일입니다.')
        if recover:
            total, progress.baseline, summary = restore_history(path, output, sources, spec)
            state = initial_state(sources, before, total, progress.baseline, summary)
        elif state is None:
            state = initial_state(sources, before, sources.total())
        if state.get('source') != sources.key:
            raise ValueError('이 정제본에 연결된 원문, 순서 또는 토크나이저가 다릅니다.')
        expected = state['output']
        if before != stamp(output) or before != file_stamp(path.stat()) or before[:2] != expected[:2]:
            raise ValueError('정제본 파일이 교체됐습니다.')
        if 'pending' not in state and before != expected:
            raise ValueError('정제본이 도구 외부에서 수정됐습니다.')
        sources.check()
        yield sources, output, progress, state


def remaining(state):
    return state['total'] - state['done']


def deferred_count(state):
    return sum(batch['count'] for batch in state.get('deferred', ()))


def was_done(baseline, index):
    return bool(baseline and baseline[index // 8] & (1 << (index % 8)))


def next_docs(sources, state, baseline):
    left = remaining(state)
    available = left - deferred_count(state)
    if not available:
        return []
    until_report = left - state['milestone'] if state['milestone'] >= 0 else left
    focused = state['scanned'] >= state.get('focus_after', state['total'] + 1)
    cap_after, cap_bytes = state.get('focus_source_budget', (state['total'] + 1, FOCUSED_SOURCE_BYTES))
    source_limit = cap_bytes if state['scanned'] >= cap_after else FOCUSED_SOURCE_BYTES
    split_end = next((number for number in state.get('split_ends', ())
                      if number > state['scanned']), None)
    prepare_structure = state['scanned'] >= state.get('prepare_structure_after', state['total'] + 1)
    compact_preview = state['scanned'] >= state.get('compact_preview_after', state['total'] + 1)
    prepare_metadata = state['scanned'] >= state.get('prepare_metadata_after', state['total'] + 1)
    document_limit = (max(FOCUSED_DOCUMENTS, 320) if prepare_metadata else FOCUSED_DOCUMENTS)
    limit = min(document_limit if focused else BATCH_DOCUMENTS, available, until_report)
    if limit < 1:
        raise ValueError('다음 묶음 조회 도구에서 잔여량 보고를 먼저 출력하세요.')
    docs, size, source_size = [], 0, 0
    restricted = set((state['restored'] or {}).get('restricted', ()))
    records = sources.records(state['cursor'])
    for index, (slot, offset, raw, complete) in enumerate(records, state['scanned']):
        if index >= state['total']:
            raise ValueError('원문 문서 수와 저장된 범위가 달라졌습니다.')
        if was_done(baseline, index):
            continue
        if index in restricted:
            doc = Document(index + 1, slot, offset, None, '원문 판독 보류 범위')
        else:
            doc = sources.document(index + 1, slot, offset, raw, complete)
            if prepare_structure or compact_preview or prepare_metadata:
                auto = clean_number_article(doc.text) if prepare_metadata and slot == 0 and not doc.note else None
                doc = replace(doc, prepare_structure=prepare_structure, compact_preview=compact_preview,
                              prepare_metadata=prepare_metadata, automatic_text=auto)
        source_length = len((doc.text or '').encode('utf-8'))
        length = review_size(doc) if focused else source_length
        if docs and (size + length > BATCH_BYTES
                     or focused and source_size + source_length > source_limit):
            break
        docs.append(doc)
        size += length
        source_size += source_length
        if len(docs) == limit or size >= BATCH_BYTES or doc.number == split_end:
            break
    if not docs:
        raise ValueError('저장된 잔여량과 실제 원문 끝이 일치하지 않습니다.')
    return docs


def batch_id(state, docs):
    return signature([state['source'], state['output'], state['cursor'], state['done'],
                      [(d.number, d.file, d.offset, d.text, d.note) for d in docs]])


def planned_batches(sources, state, baseline, count):
    position = state.copy()
    for _ in range(count):
        if remaining(position) == deferred_count(position):
            return
        if remaining(position) == position['milestone']:
            position['milestone'] -= REPORT_EVERY
        docs = next_docs(sources, position, baseline)
        yield docs
        last = docs[-1]
        position.update(cursor=[last.file, last.offset], scanned=last.number,
                        done=position['done'] + len(docs))


def activate_focused_batches(args):
    with open_pair(args, initialize=False) as (sources, output, progress, state):
        if 'pending' in state:
            raise ValueError('진행 중인 저장이 있습니다.')
        fence = args.focus_batches_after
        if fence != state['scanned'] and not any(
                docs[-1].number == fence
                for docs in planned_batches(sources, state, progress.baseline, MAX_PLANNED_BATCHES)):
            raise ValueError('현재 저장 위치 또는 배정된 마지막 묶음의 끝 문서를 지정하세요.')
        sources.check()
        if args.source_batch_bytes is None:
            if 'focus_after' in state:
                raise ValueError('표시 분량 기준이 이미 설정됐습니다.')
            state['focus_after'] = fence
        else:
            if ('focus_after' not in state or fence < state['focus_after']
                    or 'focus_source_budget' in state
                    or not FOCUSED_SOURCE_BYTES <= args.source_batch_bytes <= MAX_PAYLOAD):
                raise ValueError('후보 표시 기준과 원문 한도를 확인하세요.')
            state['focus_source_budget'] = [fence, args.source_batch_bytes]
        progress.save(state)
        if args.source_batch_bytes is None:
            print(f'문서 {fence} 뒤부터 표시 분량 기준의 묶음을 사용합니다.')
        else:
            print(f'문서 {fence} 뒤부터 묶음 원문 한도를 {args.source_batch_bytes:,}바이트로 적용합니다.')


def split_current_batch(args):
    first, parts = args.split_current or args.split_planned
    with open_pair(args, initialize=False) as (sources, output, progress, state):
        if 'pending' in state or str(first) in state.get('waiting', {}):
            raise ValueError('이미 입력을 접수했거나 저장이 진행 중인 묶음입니다.')
        if args.split_current:
            docs = next_docs(sources, state, progress.baseline)
        else:
            docs = next((batch for batch in planned_batches(sources, state, progress.baseline, MAX_PLANNED_BATCHES)
                         if batch[0].number == first), None)
        if not docs or docs[0].number != first or not 2 <= parts <= min(5, len(docs)):
            raise ValueError('정제할 묶음의 첫 문서 번호와 나눌 개수를 확인하세요.')
        work = list(accumulate(review_size(doc) + len((doc.text or '').encode('utf-8')) // 8
                               for doc in docs))
        ends = [0]
        for part in range(1, parts):
            where = bisect_left(work, (work[-1] * part + parts - 1) // parts) + 1
            ends.append(max(ends[-1] + 1, min(where, len(docs) - parts + part)))
        ends.append(len(docs))
        sources.check()
        state['split_ends'] = sorted(set(state.get('split_ends', ())) |
                                      {docs[index - 1].number for index in ends[1:]})
        progress.save(state)
        for start, end in zip(ends, ends[1:]):
            print(f'{docs[start].number}–{docs[end - 1].number}  {end - start}문서')


def prepare_future_batches(args):
    with open_pair(args, initialize=False) as (sources, _, progress, state):
        modes = (('prepare_structure_after', args.prepare_after, '기존 빈 구조 정리 규칙을 초안에 적용합니다'),
                 ('compact_preview_after', args.compact_after, '형식 후보 주변을 발췌합니다'),
                 ('prepare_metadata_after', args.metadata_after, '확인된 분류 말미의 빈 절과 중복 생몰 연도를 정리합니다'))
        setting, fence, action = next(mode for mode in modes if mode[1] is not None)
        if 'pending' in state or setting in state:
            raise ValueError('저장이 진행 중이거나 새 조회 방식의 적용 지점이 이미 설정됐습니다.')
        if args.prepare_after is None and fence < state.get('prepare_structure_after', state['total'] + 1):
            raise ValueError('자동 형식 초안이 적용되는 지점 이후를 지정하세요.')
        if fence != state['scanned'] and not any(
                docs[-1].number == fence
                for docs in planned_batches(sources, state, progress.baseline, MAX_PLANNED_BATCHES)):
            raise ValueError('현재 저장 위치 또는 이미 배정된 마지막 묶음의 끝을 지정하세요.')
        sources.check()
        state[setting] = fence
        progress.save(state)
        print(f'{fence}번 뒤의 새 묶음부터 {action}.')


def defer_current_batch(args):
    with open_pair(args, initialize=False) as (sources, _, progress, state):
        if 'pending' in state or str(args.defer_current) in state.get('waiting', {}):
            raise ValueError('저장이 진행 중인 묶음입니다.')
        docs = next_docs(sources, state, progress.baseline)
        if not docs or docs[0].number != args.defer_current:
            raise ValueError('현재 미저장 묶음의 첫 문서 번호를 지정하세요.')
        last = docs[-1]
        cursor = [last.file, last.offset]
        state.setdefault('deferred', []).append(dict(first=docs[0].number, last=last.number,
                                                     count=len(docs), start=state['cursor'],
                                                     scanned=state['scanned'], end=cursor,
                                                     reason='content_filter'))
        state.update(cursor=cursor, scanned=last.number)
        if 'split_ends' in state and last.number >= state['split_ends'][-1]:
            state.pop('split_ends')
        sources.check()
        progress.save(state)
        print(f'{docs[0].number}–{last.number} {len(docs)}문서를 미처리에 유지하고 다음 묶음으로 이동했습니다.')


def identical_sources(sources, state, baseline, splits):
    validation = set()
    for slot, split in enumerate(splits):
        if split == 'val':
            file = sources.files[slot]
            file.seek(0)
            validation.update(raw for _, raw, complete in eos_records(file) if complete and raw)
    restricted = set((state['restored'] or {}).get('restricted', ()))
    seen = defaultdict(list)
    matches = {}
    validation_hits = 0
    for index, (slot, end, raw, complete) in enumerate(
            sources.records(state['cursor']), state['scanned']):
        if (splits[slot] != 'train' or not complete or not raw or index in restricted
                or was_done(baseline, index)):
            continue
        if raw in validation:
            validation_hits += 1
            continue
        key = blake2b(raw, digest_size=16).digest()
        for first, first_slot, start, size in seen[key]:
            if size == len(raw) and os.pread(sources.files[first_slot].fileno(), size, start) == raw:
                matches[index] = (first, first_slot, slot, size, sha256(raw).hexdigest()[:12])
                break
        else:
            seen[key].append((index, slot, end - len(EOS_BYTES) - len(raw), len(raw)))
    return matches, validation_hits


def adopt_duplicates(args):
    if args.preserve_through < 0:
        raise ValueError('배정된 마지막 문서 번호는 음수일 수 없습니다.')
    scope = history_scope(local_file(args.cleaned))
    splits = [row['split'] for row in scope['inputs']]
    paths = [str(ROOT / row['path']) for row in scope['inputs']]
    with open_pair(args, initialize=False) as (_, output, progress, snapshot):
        if 'pending' in snapshot or snapshot.get('waiting') or 'duplicate_sources' in snapshot:
            raise ValueError('진행 중인 저장 또는 이미 반영한 중복 처리가 있습니다.')
        if snapshot['inputs']['source'] != paths or snapshot['inputs']['format'] != 'u16-eos':
            raise ValueError('기존 범위의 학습·검증 원문 순서를 확인하지 못했습니다.')
        before = progress.baseline
    with ExitStack() as stack:
        output = stack.enter_context(args.cleaned.open('rb'))
        sources = Sources(existing_inputs(snapshot['inputs']), stack, output)
        if sources.key != snapshot['source']:
            raise ValueError('중복 비교 중 원문 구성이 바뀌었습니다.')
        matches, validation_hits = identical_sources(sources, snapshot, before, splits)
        sources.check()

    with open_pair(args, initialize=False) as (sources, output, progress, state):
        if ('pending' in state or state.get('waiting') or 'duplicate_sources' in state or progress.baseline != before
                or state['source'] != snapshot['source']):
            raise ValueError('비교 중 작업 상태가 바뀌어 중복 처리를 반영하지 않았습니다.')
        fence = max(args.preserve_through, state['scanned'])
        duplicates = {index: owner for index, owner in matches.items() if index >= fence
                      and owner[0] >= state['scanned']}
        if not duplicates:
            print('현재 배정 이후에 반영할 동일 원문이 없습니다.')
            return
        bitmap = bytearray(before or bytes((state['total'] + 7) // 8))
        for index in duplicates:
            bitmap[index // 8] |= 1 << (index % 8)
        updated = dict(state, done=state['done'] + len(duplicates))
        left = remaining(updated)
        updated['milestone'] = (left - 1) // REPORT_EVERY * REPORT_EVERY if left else 0

        def already_assigned(position, baseline):
            batch_ids = []
            for docs in planned_batches(sources, position, baseline, MAX_PLANNED_BATCHES):
                if docs[0].number > fence:
                    break
                batch_ids.append(tuple(doc.number for doc in docs))
            return batch_ids

        if already_assigned(state, before) != already_assigned(updated, bitmap):
            raise ValueError('현재 배정의 문서 경계가 달라져 중복 처리를 반영하지 않았습니다.')
        sources.check()
        offset = BASELINE_START + len(bitmap)
        if os.pwrite(progress.file.fileno(), bitmap, offset) != len(bitmap):
            raise OSError('동일 원문 처리 목록을 온전히 저장하지 못했습니다.')
        os.fsync(progress.file.fileno())
        updated.update(baseline_offset=offset, baseline_bytes=len(bitmap),
                       baseline_sha256=sha256(bitmap).hexdigest(),
                       duplicate_sources=len(duplicates))
        progress.save(updated)
        cross = sum(first_slot != slot for _, first_slot, slot, _, _ in duplicates.values())
        print(f'학습 구분 내 동일 원문 제외 {len(duplicates):,}위치 '
              f'(같은 입력 {len(duplicates) - cross:,}, 두 학습 입력 사이 {cross:,}), 잔여 {left:,}문서')
        print(f'검증 원문과 완전히 일치한 학습 위치 {validation_hits:,}개는 별도 검토 대상입니다.')
        for index, (first, first_slot, slot, size, key) in list(duplicates.items())[:2]:
            print(f'대표 {first + 1} (입력 {first_slot + 1}), 반복 {index + 1} (입력 {slot + 1}), '
                  f'전체 {size:,}바이트 SHA-256 {key}')


def pending_suffix(output, state):
    start = state['output'][2]
    current = stamp(output)
    length = current[2] - start
    if not 0 <= length <= state['pending']['bytes'] <= MAX_PAYLOAD:
        raise ValueError('미완료 쓰기 범위를 벗어난 변경이 있습니다.')
    suffix = os.pread(output.fileno(), length, start)
    if len(suffix) != length or stamp(output) != current:
        raise ValueError('미완료 본문을 읽는 동안 정제본이 바뀌었습니다.')
    return suffix


def finish_write(output, progress, state):
    os.fsync(output.fileno())
    pending = state.pop('pending')
    if 'index_batch' in pending:
        offset, size, expected = pending['index_batch']
        records = os.pread(progress.file.fileno(), size, offset)
        if len(records) != size or sha256(records).hexdigest() != expected:
            raise ValueError('저장 중이던 문서 위치 기록이 맞지 않습니다.')
        state['document_index'] = pending['document_index']
    state.update(output=stamp(output), cursor=pending['cursor'], done=pending['done'],
                 scanned=pending['scanned'])
    if 'queued' in pending:
        del state['waiting'][pending['queued']]
        if not state['waiting']:
            state.pop('waiting')
    if pending.get('automatic'):
        state['automatic_documents'] = state.get('automatic_documents', 0) + pending['automatic']
    if 'split_ends' in state and state['scanned'] >= state['split_ends'][-1]:
        state.pop('split_ends')
    progress.save(state)


def report_due(progress, state):
    if remaining(state) == state['milestone']:
        print(f'잔여 {remaining(state):,}문서', flush=True)
        state['milestone'] -= REPORT_EVERY
        progress.save(state)


def preview(args):
    if (args.focus or args.document is not None) and args.first is None:
        raise ValueError('--focus와 --document에는 배정 묶음의 --first가 필요합니다.')
    if args.lines is not None and (args.document is None or not 1 <= args.lines[0] <= args.lines[1]):
        raise ValueError('--lines에는 --document와 올바른 시작 줄, 끝 줄이 필요합니다.')
    if args.docs is not None and (not args.focus or args.document is not None
                                  or not 1 <= args.docs[0] <= args.docs[1]):
        raise ValueError('--docs에는 --focus와 올바른 첫 문서 번호, 끝 문서 번호가 필요합니다.')
    excerpts = defaultdict(list)
    if args.excerpt:
        if args.first is None or args.document is not None or args.focus:
            raise ValueError('--excerpt에는 배정 묶음의 --first만 지정하세요.')
        for number, lo, hi in args.excerpt:
            if not 1 <= lo <= hi:
                raise ValueError(f'문서 {number}의 발췌 시작 줄과 끝 줄을 확인하세요.')
            excerpts[number].append((lo, hi))
    with open_pair(args, initialize=not args.status) as (sources, output, progress, state):
        if args.status:
            print(json.dumps(dict(total=state['total'], done=state['done'], remaining=remaining(state),
                                  scanned=state['scanned'], bytes=state['output'][2],
                                  duplicates=state.get('duplicate_sources', 0),
                                  automatic=state.get('automatic_documents', 0),
                                  indexed=state.get('document_index', {}).get('rows', 0),
                                  deferred=deferred_count(state),
                                  deferred_ranges=[(row['first'], row['last'])
                                                   for row in state.get('deferred', ())],
                                  correction_pending=sorted(map(int, state.get('pending_text_corrections', {}))),
                                  waiting=[int(n) for n in state.get('waiting', {})],
                                  pending='pending' in state)))
            return
        if args.recover_previous:
            progress.save(state)
            old = state['restored']
            print(f'기존 정제본과 연결 {old["text_confirmed"]:,}구간, 기존 제외 결정 '
                  f'{old["excluded"]:,}구간, 이미 완료한 원문과 동일한 추가 위치 '
                  f'{old.get("earlier_source_alias", 0):,}구간을 {progress.path}에 옮겼습니다.')
            print(f'원문 ID를 연결하지 못한 기존 TXT 부분 {old["unmapped_bytes"]:,}바이트.')
            return
        if 'pending' in state:
            data = pending_suffix(output, state)
            pending = state['pending']
            if len(data) != pending['bytes']:
                raise ValueError(f'이전 저장이 중간에 끊겼습니다. 묶음 {pending["batch"]}의 '
                                 '같은 정제 입력을 저장 도구에 다시 전달하세요.')
            if sha256(data).hexdigest() != pending['sha256']:
                raise ValueError('중단된 저장의 끝부분이 제출했던 내용과 다릅니다.')
            finish_write(output, progress, state)
        report_due(progress, state)
        if args.assign:
            for docs in planned_batches(sources, state, progress.baseline, args.assign):
                size = sum(len((doc.text or '').encode('utf-8')) for doc in docs)
                automatic = sum(doc.automatic_text is not None for doc in docs)
                label = f'  규칙 처리 {automatic}' if automatic else ''
                print(f'{docs[0].number}–{docs[-1].number}  {len(docs)}문서  {size}바이트{label}')
            sources.check()
            if progress.file is None:
                progress.save(state)
            return
        if args.first is None:
            docs = next_docs(sources, state, progress.baseline)
            label = f'묶음 {batch_id(state, docs)}' if docs else ''
        else:
            if 0 < args.first <= state['scanned']:
                raise ValueError(f'문서 {args.first}의 번호가 현재 원문 위치 {state["scanned"]}보다 앞에 있습니다.')
            if str(args.first) in state.get('waiting', {}):
                raise ValueError(f'문서 {args.first}부터의 정제 입력을 접수했습니다. 앞 묶음 저장 뒤 반영됩니다.')
            batches = planned_batches(sources, state, progress.baseline, MAX_PLANNED_BATCHES)
            docs = next((batch for batch in batches if batch[0].number == args.first), None)
            if docs is None:
                raise ValueError('현재 배정 가능한 범위에서 해당 첫 문서 번호를 찾지 못했습니다.')
            label = f'묶음 첫 문서 {args.first}'
        if args.document is not None:
            docs = [doc for doc in docs if doc.number == args.document]
            if not docs:
                raise ValueError('해당 문서는 배정 묶음에 없습니다.')
        if excerpts:
            docs = [doc for doc in docs if doc.number in excerpts]
            if {doc.number for doc in docs} != set(excerpts):
                raise ValueError('발췌 요청에 현재 배정에 없는 문서가 포함됐습니다.')
        sources.check()
        if progress.file is None:
            progress.save(state)
        paths = sources.paths
    if not docs:
        print(f'미처리 보류 {deferred_count(state):,}문서' if deferred_count(state)
              else '다음 작업 문서가 없습니다.')
        return
    print(label)
    compact_paths = args.focus and docs[0].compact_preview and not args.original
    if args.focus:
        view = docs
        if args.document is None and not args.original:
            auto = [doc for doc in docs if doc.automatic_text is not None]
            if auto:
                print(f'기존 구조 규칙으로 저장할 문서 {len(auto)}건  ' + ' '.join(str(doc.number) for doc in auto))
                view = [doc for doc in docs if doc.automatic_text is None]
        print(f'배정 문서 {len(view)}건  ' + ' '.join(str(doc.number) for doc in view))
        print('형식 후보와 앞뒤 문맥을 표시합니다. 같은 번호로 --document를 지정하면 전문을 볼 수 있습니다.')
        if docs[0].prepare_structure and not args.original:
            print('같은 문장은 번호별 위치를 표시합니다. 정제 초안에는 문장이 각각 남아 있습니다.')
        if docs[0].compact_preview and not args.original:
            print('[일부 표시] 줄은 --document 문서 --lines 시작줄 끝줄로 정확한 내용을 열 수 있습니다.')
        docs = view
        if args.docs is not None:
            lo, hi = args.docs
            docs = [doc for doc in docs if lo <= doc.number <= hi]
            print(f'{lo}–{hi} 범위에서 후보 {len(docs)}문서를 표시합니다.')
    if compact_paths:
        for slot in sorted({doc.file for doc in docs}):
            print(f'원문 {slot + 1}  {paths[slot]}')
    for doc in docs:
        draft, removed = automatic_format(doc)
        if draft and doc.prepare_metadata and not args.original:
            clean = clean_empty_initial_alias(draft)
            if clean != draft:
                draft = clean
                removed += ('이름 병기의 비어 있는 자리',)
        if removed:
            print(f'자동 형식 정리 문서 {doc.number}: {", ".join(removed)}')
        location = f'원문 {doc.file + 1}' if compact_paths else paths[doc.file]
        print(f'\n=== 문서 {doc.number} | {location} ===')
        if doc.note:
            print(f'[{doc.note}]')
        body = doc.text if args.original else draft
        if args.first is not None and body:
            lines = preview_lines(body, args.focus and args.document is None,
                                  doc.prepare_structure and not args.original,
                                  doc.compact_preview and not args.original)
            ranges = excerpts.get(doc.number)
            if args.lines is not None:
                ranges = [args.lines]
            if ranges:
                exact = body.split('\n')
                if any(hi > len(exact) for _, hi in ranges):
                    raise ValueError(f'문서 {doc.number}의 마지막 줄 {len(exact)}를 넘었습니다.')
                numbers = sorted({n for lo, hi in ranges for n in range(lo, hi + 1)})
                lines = ((n, exact[n - 1]) for n in numbers)
            for number, line in lines:
                print(f'{number}\t{line}')
        else:
            print(body if body else '[본문 없음]')


def main():
    parser = arguments(__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--recover-previous', action='store_true',
                      help='TinyLM 기존 정제본의 확인된 완료 기록을 작업 메타데이터로 한 번 옮김.')
    mode.add_argument('--assign', type=int, choices=range(1, MAX_PLANNED_BATCHES + 1),
                      help='다음 묶음들의 첫 문서, 끝 문서, 문서 수, 원문 크기만 출력.')
    mode.add_argument('--first', type=int, metavar='문서',
                      help='배정된 묶음의 자동 정리 초안을 줄 번호와 함께 출력.')
    mode.add_argument('--status', action='store_true', help='요청 시 현재 저장 위치와 잔여 문서 수 출력.')
    mode.add_argument('--deduplicate', action='store_true',
                      help='같은 학습 구분에서 원문 전체가 같은 반복 위치만 작업 메타데이터에 반영.')
    mode.add_argument('--focus-batches-after', type=int, metavar='문서',
                      help='지정한 묶음 이후부터 후보 표시 분량을 기준으로 묶음 크기를 결정.')
    mode.add_argument('--split-current', nargs=2, type=int, metavar=('첫문서', '개수'),
                      help='현재 미저장 묶음만 지정 개수로 나누고 뒤 묶음의 경계를 유지.')
    mode.add_argument('--split-planned', nargs=2, type=int, metavar=('첫문서', '개수'),
                      help='아직 배정하지 않은 뒤 묶음 하나만 읽을 분량에 따라 나눔.')
    mode.add_argument('--prepare-after', type=int, metavar='끝문서',
                      help='기존 배정 끝 뒤에서부터 빈 절과 이름 병기 등을 자동 정제 초안에 반영.')
    mode.add_argument('--compact-after', type=int, metavar='끝문서',
                      help='배정 끝 이후부터 긴 형식 후보를 읽기 전용 발췌로 표시.')
    mode.add_argument('--metadata-after', type=int, metavar='끝문서',
                      help='배정 끝 이후부터 출생·사망 연도와 정확히 일치하는 분류 중복을 정리.')
    mode.add_argument('--defer-current', type=int, metavar='첫문서',
                      help='콘텐츠 필터에서 멈춘 현재 묶음을 미처리로 두고 다음 묶음으로 이동.')
    parser.add_argument('--preserve-through', type=int, default=0, metavar='문서',
                        help='중복 처리에서 이미 배정한 마지막 문서까지 유지.')
    parser.add_argument('--source-batch-bytes', type=int, metavar='바이트',
                        help='--focus-batches-after 이후 묶음에 적용할 원문 분량 한도.')
    parser.add_argument('--original', action='store_true', help='자동 정리 전 원문을 출력.')
    parser.add_argument('--focus', action='store_true', help='자동 정리 초안의 형식 후보 및 주변 줄을 출력.')
    parser.add_argument('--document', type=int, metavar='문서', help='배정 묶음의 이 문서 전문만 출력.')
    parser.add_argument('--docs', nargs=2, type=int, metavar=('첫문서', '끝문서'),
                        help='--focus에서 해당 배정의 지정 문서 번호 범위만 출력.')
    parser.add_argument('--lines', nargs=2, type=int, metavar=('첫줄', '끝줄'),
                        help='지정한 문서에서 필요한 줄을 길이 축약 없이 출력.')
    parser.add_argument('--excerpt', nargs=3, type=int, action='append', metavar=('문서', '첫줄', '끝줄'),
                        help='여러 문서의 필요한 정확한 줄을 한 번 조회. 반복 지정 가능.')
    try:
        args = parser.parse_args()
        if args.source_batch_bytes is not None and args.focus_batches_after is None:
            parser.error('--source-batch-bytes에는 --focus-batches-after가 필요합니다.')
        if args.deduplicate:
            adopt_duplicates(args)
        elif args.focus_batches_after is not None:
            activate_focused_batches(args)
        elif args.split_current is not None or args.split_planned is not None:
            split_current_batch(args)
        elif any(value is not None for value in (args.prepare_after, args.compact_after, args.metadata_after)):
            prepare_future_batches(args)
        elif args.defer_current is not None:
            defer_current_batch(args)
        else:
            preview(args)
    except (OSError, ValueError, KeyError, ImportError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
