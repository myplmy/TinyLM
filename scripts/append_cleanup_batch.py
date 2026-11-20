#!/usr/bin/env python3
"""조회한 묶음의 정제 본문만 TXT 끝에 저장한다.

표준 입력 예시
{"batch":"조회 도구가 표시한 묶음 값","documents":[{"number":42,"text":"정제 본문"}]}
text가 true이면 검토한 원문을 그대로 저장하고, null이면 검토 후 제외한다.
자동 정리 초안을 승인하려면 해당 문서를 {"number":42,"auto":true}로 제출한다.
묶음 안의 모든 문서 번호를 조회 순서대로 한 번씩 제출한다.

--first로 배정받은 묶음을 저장할 때에는 줄 번호로 바뀐 부분만 제출할 수 있다.
@@ 42 3 5
세 번째부터 다섯 번째 줄까지를 이 문장으로 바꾼다.
@@ 42 12 12
@@ 45 keep
@@ 47 exclude
내용 없는 구간은 삭제하고, keep은 자동 정리 초안을 승인한다.
전부 읽고 유지로 판정한 나머지 문서는 --keep-remaining 문서수로 승인할 수 있다.
"""

from __future__ import annotations

import argparse
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from next_cleanup_batch import (BASELINE_START, BREAK, DOCUMENT_POSITION, MAX_PAYLOAD, MAX_PLANNED_BATCHES,
                                arguments, automatic_format,
                                batch_id, clean_empty_initial_alias, file_stamp, finish_write, next_docs, open_pair,
                                pending_suffix, planned_batches, report_due, stamp)

MAX_WAITING_BYTES = 2_000_000


def line_edits(raw):
    prefix, *sections = re.split(r'^@@ ([^\n]*)\n?', raw.decode('utf-8').replace('\r\n', '\n'),
                                 flags=re.M)
    if prefix.strip() or not sections:
        raise ValueError('수정 구간은 @@ 문서 시작줄 끝줄 형식으로 제출하세요.')
    entries, decided = {}, set()
    for header, body in zip(sections[::2], sections[1::2]):
        fields = header.split()
        if len(fields) not in (2, 3) or not fields[0].isdecimal():
            raise ValueError(f'잘못된 수정 구간입니다. {header}')
        number = int(fields[0])
        if len(fields) == 2:
            if fields[1] == 'keep' and not body.strip() and entries.get(number) == dict(number=number, edits=[]):
                continue
            if fields[1] not in {'keep', 'exclude'} or body.strip() or number in entries:
                raise ValueError(f'잘못된 유지 또는 제외 표시입니다. 문서 {number}')
            entries[number] = (dict(number=number, edits=[]) if fields[1] == 'keep'
                               else dict(number=number, text=None))
            decided.add(number)
            continue
        if number in decided:
            raise ValueError(f'유지 또는 제외와 수정이 함께 제출됐습니다. 문서 {number}')
        if not all(field.isdecimal() for field in fields[1:]):
            raise ValueError(f'줄 번호는 숫자로 제출하세요. 문서 {number}')
        entry = entries.setdefault(number, dict(number=number, edits=[]))
        lines = body.removesuffix('\n').split('\n') if body else []
        entry['edits'].append([int(fields[1]), int(fields[2]), lines])
    ordered = [entries[number] for number in sorted(entries)]
    for entry in ordered:
        if 'edits' in entry:
            entry['edits'].sort(key=lambda edit: edit[0])
    return ordered


def submission(first=None):
    raw = sys.stdin.buffer.read(MAX_PAYLOAD + 65_537)
    if len(raw) > MAX_PAYLOAD + 65_536:
        raise ValueError('정제 입력이 너무 큽니다.')
    if first is not None:
        if not raw.strip():
            return None, []
        if raw.lstrip().startswith(b'['):
            return None, json.loads(raw)
        return None, line_edits(raw)
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {'batch', 'documents'}:
        raise ValueError('묶음 값과 documents 배열을 표준 입력 JSON으로 제출하세요.')
    if not isinstance(value['batch'], str) or not isinstance(value['documents'], list):
        raise ValueError('묶음 값과 문서 목록의 형식이 잘못됐습니다.')
    return value['batch'], value['documents']


def edited_body(doc, edits):
    draft, _ = automatic_format(doc)
    if not draft or doc.note or not isinstance(edits, list):
        raise ValueError(f'줄 번호 수정의 대상 또는 입력이 잘못됐습니다. 문서 {doc.number}')
    lines = draft.split('\n')
    result, last = [], 0
    for edit in edits:
        if not isinstance(edit, list) or len(edit) != 3:
            raise ValueError(f'잘못된 수정 구간입니다. 문서 {doc.number}')
        first, end, replacement = edit
        if type(first) is int and type(end) is int and not last < first <= end <= len(lines):
            raise ValueError(f'문서 {doc.number}의 {first}–{end}줄이 겹치거나 범위를 벗어났습니다. '
                             f'이전 수정 끝줄 {last}, 초안 끝줄 {len(lines)}.')
        if (type(first) is not int or type(end) is not int or not isinstance(replacement, list)
                or any(not isinstance(line, str) or '\r' in line or '\n' in line
                       for line in replacement)):
            raise ValueError(f'수정 줄 또는 새 본문의 형식이 잘못됐습니다. 문서 {doc.number}')
        result.extend(lines[last:first - 1])
        result.extend(replacement)
        last = end
    result.extend(lines[last:])
    return '\n'.join(result)


def reviewed_payload(docs, entries, *, alias_format=2, widths=None):
    if not isinstance(entries, list):
        raise ValueError('정제 묶음의 문서를 배열로 제출하세요.')
    if len(entries) != len(docs) and any(doc.automatic_text is not None for doc in docs):
        if not all(isinstance(entry, dict) and type(entry.get('number')) is int for entry in entries):
            raise ValueError('정제 입력의 문서 번호가 잘못됐습니다.')
        by_id = {entry['number']: entry for entry in entries}
        if len(by_id) != len(entries) or by_id.keys() - {doc.number for doc in docs}:
            raise ValueError('배정되지 않았거나 중복된 문서 번호가 있습니다.')
        entries = [by_id.get(doc.number, dict(number=doc.number, auto=True)
                   if doc.automatic_text is not None else {}) for doc in docs]
    if len(entries) != len(docs):
        raise ValueError('정제 묶음의 문서를 빠짐없이 제출하세요.')
    pieces, size = [], 0
    for doc, entry in zip(docs, entries):
        if (not isinstance(entry, dict)
                or set(entry) not in ({'number', 'text'}, {'number', 'auto'}, {'number', 'edits'})
                or type(entry['number']) is not int or entry['number'] != doc.number):
            raise ValueError(f'제출 순서와 원문 번호가 일치해야 합니다. 문서 {doc.number}')
        if 'auto' in entry:
            if entry['auto'] is not True:
                raise ValueError(f'자동 정리 초안은 auto를 true로 지정하세요. 문서 {doc.number}')
            body, removed = automatic_format(doc)
            if not removed:
                raise ValueError(f'자동 정리 변경분이 없습니다. 문서 {doc.number}')
        elif 'edits' in entry:
            body = edited_body(doc, entry['edits'])
        else:
            body = entry['text']
        if body is None:
            if widths is not None:
                widths.append(0)
            continue
        if not doc.text or not doc.text.strip():
            raise ValueError(f'판독할 수 있는 원문이 없습니다. 문서 {doc.number}')
        if body is True:
            body = doc.text
        if not isinstance(body, str) or not body.strip() or chr(0) in body:
            raise ValueError(f'문서 {doc.number}의 정제 본문이 비어 있거나 형식이 잘못됐습니다.')
        if any(marker in body and marker not in doc.text
               for marker in ('[일부 표시]', '[같은 문장: ')):
            raise ValueError(f'문서 {doc.number}에 조회용 발췌 표식이 들어갔습니다. 해당 줄 전문을 확인하세요.')
        if alias_format and doc.prepare_metadata:
            body = clean_empty_initial_alias(body, dated_names=alias_format >= 2)
        data = body.encode('utf-8') + BREAK
        if widths is not None:
            widths.append(len(data))
        size += len(data)
        if size > MAX_PAYLOAD:
            raise ValueError('저장할 정제 본문 한도를 넘었습니다.')
        pieces.append(data)
    return b''.join(pieces), len(pieces)


def retain_reviewed_docs(docs, entries, count):
    if count is None:
        return entries
    if not isinstance(entries, list) or not all(
            isinstance(entry, dict) and type(entry.get('number')) is int for entry in entries):
        raise ValueError('유지 외 정제 입력의 문서 번호가 잘못됐습니다.')
    supplied = {entry['number'] for entry in entries}
    if len(supplied) != len(entries) or supplied - {doc.number for doc in docs}:
        raise ValueError('배정되지 않았거나 중복된 문서 번호가 있습니다.')
    retained = [doc.number for doc in docs if doc.number not in supplied and doc.automatic_text is None]
    if len(retained) != count:
        raise ValueError(f'명시한 유지 문서 수 {count}와 남은 배정 문서 수 {len(retained)}가 다릅니다.')
    return sorted(entries + [dict(number=number, edits=[]) for number in retained],
                  key=lambda entry: entry['number'])


def waiting_start(state):
    return state.get('baseline_offset', BASELINE_START) + state['baseline_bytes']


def stage_review(progress, state, docs, entries):
    first = str(docs[0].number)
    waiting = state.setdefault('waiting', {})
    if first in waiting:
        raise ValueError(f'문서 {first}부터의 정제 입력을 이미 접수했습니다.')
    body = json.dumps(entries, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    start = waiting_start(state)
    offset = start
    for lo, size, _ in sorted(waiting.values()):
        if offset + len(body) <= lo:
            break
        offset = lo + size
    limit = min(start + MAX_WAITING_BYTES, state.get('document_index', {}).get('offset', start + MAX_WAITING_BYTES))
    corrections = state.get('pending_text_correction_data')
    if corrections is not None:
        limit = min(limit, corrections.get('reserved_start', corrections['offset']))
    if offset + len(body) > limit:
        raise ValueError('저장 대기 공간을 모두 사용 중입니다. 앞 묶음 반영 뒤 제출하세요.')
    fd = progress.file.fileno()
    if os.pwrite(fd, body, offset) != len(body):
        raise OSError('대기 중인 정제 입력을 온전히 쓰지 못했습니다.')
    os.fsync(fd)
    waiting[first] = [offset, len(body), sha256(body).hexdigest()]
    progress.save(state)
    print(f'문서 {first}부터 {len(docs)}문서 정제 입력 접수. 앞 묶음 저장 후 자동 반영합니다.')


def append_review(sources, output, progress, state, docs, entries, ticket, queued=None):
    pending = state.get('pending')
    alias_format = (pending.get('alias_format', 0) if pending is not None else
                    2 if any(doc.prepare_metadata for doc in docs) else 0)
    widths = [] if pending is None or 'index_batch' in pending else None
    payload, saved = reviewed_payload(docs, entries, alias_format=alias_format, widths=widths)
    last = docs[-1]
    prepared = dict(batch=ticket, bytes=len(payload), sha256=sha256(payload).hexdigest(),
                    cursor=[last.file, last.offset], scanned=last.number, done=state['done'] + len(docs))
    submitted = {entry['number'] for entry in entries}
    automatic = sum(doc.automatic_text is not None and doc.number not in submitted for doc in docs)
    if automatic:
        prepared['automatic'] = automatic
    if alias_format:
        prepared['alias_format'] = alias_format
    if queued is not None:
        prepared['queued'] = queued
    if widths is not None:
        previous = state.get('document_index', dict(offset=waiting_start(state) + MAX_WAITING_BYTES,
                                                   rows=0, text_start=state['output'][2]))
        index_data = b''.join(DOCUMENT_POSITION.pack(doc.number, width, doc.offset)
                              for doc, width in zip(docs, widths))
        index_offset = previous['offset'] + previous['rows'] * DOCUMENT_POSITION.size
        prepared['index_batch'] = [index_offset, len(index_data), sha256(index_data).hexdigest()]
        prepared['document_index'] = dict(previous, rows=previous['rows'] + len(docs))
    sources.check()
    if 'pending' in state:
        if prepared != state['pending']:
            raise ValueError('저장이 끊긴 묶음은 처음 제출한 정제 본문 그대로 다시 전달하세요.')
    else:
        if stamp(output) != state['output']:
            raise ValueError('정제본이 바뀌어 쓰지 않았습니다.')
    if widths is not None:
        fd = progress.file.fileno()
        if os.pwrite(fd, index_data, index_offset) != len(index_data):
            raise OSError('정제 문서의 저장 위치를 온전히 쓰지 못했습니다.')
    if 'pending' not in state:
        state['pending'] = prepared
        progress.save(state)

    current = stamp(output)
    prefix = pending_suffix(output, state)
    if not payload.startswith(prefix):
        raise ValueError('저장이 끊긴 위치의 본문이 제출한 본문과 다릅니다.')
    if stamp(output) != current or file_stamp(Path(output.name).stat()) != current:
        raise ValueError('정제본이 바뀌어 쓰지 않았습니다.')
    fd = output.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_APPEND)
    rest = memoryview(payload)[len(prefix):]
    while rest:
        written = os.write(fd, rest)
        if not written:
            raise OSError('정제본에 남은 바이트를 쓸 수 없습니다.')
        rest = rest[written:]
    if pending_suffix(output, state) != payload:
        raise ValueError('저장 위치에서 제출한 정제 본문을 확인할 수 없습니다.')
    sources.check()
    finish_write(output, progress, state)
    summary = f'문서 {docs[0].number}부터 {saved}문서 본문 저장, {len(docs) - saved}문서 검토 후 제외'
    print(summary + (f', 규칙으로 직접 정제 {automatic}문서 포함' if automatic else ''), flush=True)


def append(args, ticket, entries, *, first=None):
    with open_pair(args, initialize=False) as (sources, output, progress, state):
        report_due(progress, state)
        keep_remaining = getattr(args, 'keep_remaining', None)
        docs = next_docs(sources, state, progress.baseline)
        if not docs:
            raise ValueError('저장할 묶음이 없습니다.')
        if first is not None and first != docs[0].number:
            if 'pending' in state:
                raise ValueError('이전 쓰기 복구 뒤 대기 입력을 접수하세요.')
            later = planned_batches(sources, state, progress.baseline, MAX_PLANNED_BATCHES)
            docs = next((batch for batch in later if batch[0].number == first), None)
            if docs is None:
                raise ValueError('이미 완료했거나 배정 범위에 없는 묶음입니다.')
            entries = retain_reviewed_docs(docs, entries, keep_remaining)
            reviewed_payload(docs, entries)
            sources.check()
            stage_review(progress, state, docs, entries)
            return
        expected = batch_id(state, docs)
        if first is None and ticket != expected:
            raise ValueError('이미 완료했거나 현재 순서와 다른 묶음입니다. 다음 묶음을 조회하세요.')
        entries = retain_reviewed_docs(docs, entries, keep_remaining)
        queued = str(docs[0].number) if str(docs[0].number) in state.get('waiting', {}) else None
        if queued is None:
            append_review(sources, output, progress, state, docs, entries, expected)
            report_due(progress, state)
        while state.get('waiting'):
            docs = next_docs(sources, state, progress.baseline)
            first = str(docs[0].number) if docs else ''
            if first not in state['waiting']:
                break
            offset, size, check = state['waiting'][first]
            raw = os.pread(progress.file.fileno(), size, offset)
            if len(raw) != size or sha256(raw).hexdigest() != check:
                raise ValueError('대기 중인 정제 입력이 손상됐습니다.')
            submitted = json.loads(raw)
            if first == queued and submitted != entries:
                raise ValueError('이미 접수된 정제 입력과 다릅니다.')
            append_review(sources, output, progress, state, docs, submitted,
                          batch_id(state, docs), queued=first)
            report_due(progress, state)
        recorded = state.get('document_index')
        end = (recorded['offset'] + recorded['rows'] * DOCUMENT_POSITION.size
               if recorded else waiting_start(state))
        if not state.get('waiting') and os.fstat(progress.file.fileno()).st_size > end:
            os.ftruncate(progress.file.fileno(), end)
            os.fsync(progress.file.fileno())


def main():
    parser = arguments(__doc__)
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.add_argument('--first', type=int, metavar='문서',
                        help='배정 묶음의 첫 문서 번호. 다음 차례이면 바로 저장하고 뒤 묶음이면 먼저 접수.')
    parser.add_argument('--keep-remaining', type=int, metavar='문서수',
                        help='읽고 유지로 판정한 나머지 수동 문서를 정확한 개수로 승인.')
    args = parser.parse_args()
    if args.keep_remaining is not None and (args.first is None or args.keep_remaining < 0):
        parser.error('--keep-remaining에는 --first와 0 이상의 문서 수가 필요합니다.')
    try:
        append(args, *submission(args.first), first=args.first)
    except (OSError, ValueError, KeyError, ImportError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
