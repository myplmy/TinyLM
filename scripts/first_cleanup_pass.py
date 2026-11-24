#!/usr/bin/env python3
"""남은 원문을 한 번 훑어 의미 보존 규칙만 적용한 1차 TXT와 작업 위치를 만든다."""

from collections import Counter
from contextlib import ExitStack
from dataclasses import replace
from hashlib import sha256
import json
import mmap
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from next_cleanup_batch import (BREAK, EOS_BYTES, FORMAT_HINT, REPORT_EVERY, Sources,
                                arguments, automatic_format, clean_empty_initial_alias,
                                clean_number_article, deferred_count, existing_inputs,
                                historical_rows, history_scope, local_file, lock, open_pair, preview_lines,
                                remaining, was_done)
from scripts.p106b_corpus_cache import independent_control_risks
from scripts.p106b_corpus_cleanup import propose


def send_row(index, row):
    index.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode() + b'\n')


def checkpoint(out, index, position, *, complete=False):
    out.flush()
    os.fsync(out.fileno())
    send_row(index, dict(position, type='complete' if complete else 'checkpoint', bytes=out.tell()))
    index.flush()
    os.fsync(index.fileno())


def resume(out, index):
    header = json.loads(index.readline())
    if header.get('type') != 'first_pass':
        raise ValueError('이 도구에서 만든 1차 정제 작업 메타데이터를 지정하세요.')
    position, end = header['start'], index.tell()
    while line := index.readline():
        if not line.endswith(b'\n'):
            break
        event = json.loads(line)
        if isinstance(event, dict) and event.get('type') == 'complete':
            raise ValueError('이미 이 범위의 1차 정제가 완료됐습니다.')
        if isinstance(event, dict) and event.get('type') == 'checkpoint':
            position, end = event, index.tell()
    if os.fstat(out.fileno()).st_size < position['bytes']:
        raise ValueError('1차 TXT가 마지막 저장 위치보다 짧습니다.')
    return header, position, end


def draft_for(sources, number, slot, end, raw, complete, restricted):
    if number - 1 in restricted or not complete:
        return '', False, False, ['SOURCE_BOUNDARY_OR_RESTRICTED']
    doc = sources.document(number, slot, end, raw, complete)
    if doc.note or not doc.text or not doc.text.strip() or '\x00' in doc.text:
        return '', False, False, ['NO_READABLE_BODY']
    automatic = clean_number_article(doc.text) if slot == 0 else None
    draft, _ = automatic_format(replace(doc, prepare_structure=True, prepare_metadata=True,
                                        automatic_text=automatic))
    draft = clean_empty_initial_alias(draft)
    if automatic is not None:
        return draft, draft != doc.text, True, []
    _, _, _, existing = propose(draft)
    hints = existing + independent_control_risks(draft)
    if any(FORMAT_HINT.search(line) for line in draft.splitlines()):
        hints.append('FORMAT_HINT')
    return draft, draft != doc.text, False, sorted(set(hints)) or ['CONTEXT_NEEDS_REVIEW']


def first_pass(args):
    source_txt = local_file(args.cleaned)
    target = local_file(args.output, may_create=True)
    target_index = local_file(target.with_name(target.name + '.work'), may_create=True)
    if (target.parent != source_txt.parent or target == source_txt or target == target_index
            or target in {local_file(source_txt.with_name(source_txt.name + '.work'))}):
        raise ValueError('정제본과 같은 작업 폴더에 전용 1차 TXT 이름을 지정하세요.')
    with open_pair(args, initialize=False) as (_, _, progress, current):
        baseline = progress.baseline
    scope = history_scope(source_txt)
    start = dict(cursor=current['cursor'], scanned=current['scanned'], counts={}, bytes=0)
    header = dict(type='first_pass', input=current['source'], baseline=current['baseline_sha256'],
                  start=start, documents=remaining(current) - deferred_count(current),
                  deferred=current.get('deferred', []),
                  source_files=[dict(path=row['path'], split=row['split']) for row in scope['inputs']],
                  row_fields=['document', 'source_slot', 'source_start', 'source_end',
                              'text_start', 'text_bytes', 'edited', 'format_rule_completed', 'review_hints'])
    if not args.resume and (target.exists() or target_index.exists()):
        raise ValueError('1차 산출물이 이미 있습니다. 중단된 작업을 이어갈 때만 --resume을 사용하세요.')
    with ExitStack() as stack:
        mode = 'r+b' if args.resume else 'xb'
        out = stack.enter_context(target.open(mode))
        lock(out)
        index = stack.enter_context(target_index.open(mode))
        sources = Sources(existing_inputs(current['inputs']), stack, out)
        if sources.key != header['input']:
            raise ValueError('원문 또는 토크나이저의 작업 구성이 바뀌었습니다.')
        position = start
        if args.resume:
            saved, position, end = resume(out, index)
            if saved['input'] != header['input'] or saved['baseline'] != header['baseline']:
                raise ValueError('기록된 1차 정제 범위와 현재 원문이 다릅니다.')
            header = saved
            out.seek(position['bytes'])
            out.truncate()
            index.seek(end)
            index.truncate()
        else:
            send_row(index, header)
            index.flush()
            os.fsync(index.fileno())
        counts = Counter(position['counts'])
        restricted = set((current.get('restored') or {}).get('restricted', ()))
        print(f"1차 정제 원문 {header['documents']:,}건, 먼저 막힌 범위 {sum(x['count'] for x in header['deferred']):,}건", flush=True)
        for i, (slot, end, raw, complete) in enumerate(sources.records(position['cursor']), position['scanned']):
            if was_done(baseline, i):
                continue
            if i >= current['total']:
                raise ValueError('원문 레코드 수가 저장한 범위와 다릅니다.')
            text, edited, exact, hints = draft_for(sources, i + 1, slot, end, raw, complete, restricted)
            data = text.encode('utf-8') + BREAK if text else b''
            offset = out.tell()
            out.write(data)
            begin = end - len(raw) - (len(EOS_BYTES) if sources.binary and complete else 0)
            send_row(index, [i + 1, slot, begin, end, offset, len(data), edited, exact, hints])
            counts.update(seen=1, saved=int(bool(text)), edited=int(edited),
                          rule_completed=int(exact), review=int(bool(hints)),
                          no_body=int(not text), validation=int(scope['inputs'][slot]['split'] == 'val'))
            position = dict(cursor=[slot, end], scanned=i + 1, counts=counts)
            if counts['seen'] % REPORT_EVERY == 0:
                checkpoint(out, index, position)
                print(f"1차 자동처리 {counts['seen']:,}건, 형식 수정 {counts['edited']:,}건", flush=True)
        sources.check()
        if counts['seen'] != header['documents'] or counts['saved'] + counts['no_body'] != counts['seen']:
            raise ValueError('1차 정제의 입력과 결과 수가 맞지 않습니다.')
        checkpoint(out, index, position, complete=True)
        print(json.dumps(dict(counts, bytes=out.tell()), ensure_ascii=False), flush=True)


def read_index(index, begin=0, end=None):
    header, rows, complete = json.loads(index.readline()), [], None
    if header.get('type') != 'first_pass':
        raise ValueError('1차 정제 작업 메타데이터가 아닙니다.')
    for line in index:
        row = json.loads(line)
        if isinstance(row, dict):
            if row.get('type') == 'complete':
                complete = row
        elif row[0] >= begin and (end is None or row[0] <= end):
            rows.append(row)
    if complete is None:
        raise ValueError('아직 쓰고 있는 1차 정제본입니다.')
    return header, rows, complete


def second_pass_preview(args):
    first, last = args.second_pass
    if not 1 <= first <= last:
        raise ValueError('배정 시작 문서와 끝 문서 번호를 확인하세요.')
    with open_pair(args, initialize=False) as (_, _, _, current):
        if first <= current['scanned']:
            raise ValueError('이미 작업한 문서를 다시 조회하지 않습니다.')
    target = local_file(args.output)
    with target.with_name(target.name + '.work').open('rb') as index:
        header, rows, complete = read_index(index, first, last)
    if (header['input'] != current['source'] or header['baseline'] != current['baseline_sha256']
            or not rows or rows[0][0] != first or rows[-1][0] != last):
        raise ValueError('배정 시작·끝 또는 1차 정제본의 원문 범위가 맞지 않습니다.')
    excerpts = {}
    for number, lo, hi in args.excerpt or ():
        if not 1 <= lo <= hi or number not in {row[0] for row in rows}:
            raise ValueError('배정 안의 문서 번호와 읽을 줄 범위를 지정하세요.')
        excerpts.setdefault(number, []).append((lo, hi))
    print(f'2차 정제 묶음 {first}–{last}')
    planned = [str(row[0]) for row in rows if not row[7]]
    print(f'배정 문서 {len(planned)}건  ' + ' '.join(planned))
    print('1차 정제문을 표시합니다. 정확한 전문이 필요한 줄은 --excerpt 문서 첫줄 끝줄로 조회합니다.')
    with target.open('rb') as out:
        if os.fstat(out.fileno()).st_size != complete['bytes']:
            raise ValueError('완료 기록과 1차 TXT 크기가 다릅니다.')
        for number, slot, _, _, offset, width, _, rule_completed, hints in rows:
            if excerpts and number not in excerpts or rule_completed and not excerpts:
                continue
            print(f'\n=== 문서 {number} | 원문 {slot + 1} ===')
            if not width:
                print('[판독 가능한 본문 없음]')
                continue
            out.seek(offset)
            data = out.read(width)
            if len(data) != width or not data.endswith(BREAK):
                raise ValueError(f'문서 {number}의 저장 위치가 1차 TXT와 일치하지 않습니다.')
            body = data[:-len(BREAK)].decode('utf-8')
            if excerpts:
                lines = body.split('\n')
                for n in sorted({n for lo, hi in excerpts[number] for n in range(lo, hi + 1)}):
                    if n > len(lines):
                        raise ValueError(f'문서 {number}의 끝줄 {len(lines)}을 넘었습니다.')
                    print(f'{n}\t{lines[n-1]}')
            else:
                print('확인할 항목  ' + ', '.join(hints))
                for n, line in preview_lines(body, True, True, True):
                    print(f'{n}\t{line}')


def output_binding(args, *, record):
    target = local_file(args.output)
    with open_pair(args, initialize=False) as (sources, _, progress, current):
        source_txt = str(local_file(args.cleaned))
        source_bytes = current['output'][2]
        scanned = current['scanned']
        if 'pending' in current:
            raise ValueError('진행 중인 수동 저장을 마친 뒤 기준 위치를 연결하세요.')
        with target.with_name(target.name + '.work').open('r+b') as index:
            lock(index)
            header, rows, complete = read_index(index)
            if header['input'] != sources.key or header['baseline'] != current['baseline_sha256']:
                raise ValueError('1차 정제본과 기존 정제본의 원문 범위가 다릅니다.')
            pos, last, overlap = 0, header['start']['scanned'], 0
            for row in rows:
                if row[0] <= last or row[4] != pos or row[5] < 0:
                    raise ValueError('1차 문서 번호나 본문 저장 위치가 맞지 않습니다.')
                last, pos = row[0], pos + row[5]
                overlap += int(row[0] <= scanned)
            if (len(rows) != header['documents'] or pos != complete['bytes']
                    or pos != target.stat().st_size
                    or len(rows) - overlap + deferred_count(current) != remaining(current)):
                raise ValueError('기존 정제본에 연결할 때 잔여량 또는 1차 TXT가 일치하지 않습니다.')
            start = rows[overlap][4] if overlap < len(rows) else pos
            binding = dict(type='delivery', previous_txt=source_txt, previous_bytes=source_bytes,
                           previous_scanned=scanned, first_pass_start=start, first_pass_end=pos,
                           later_review_overlaps=overlap, remaining_documents=len(rows)-overlap,
                           deferred=deferred_count(current))
            if record:
                send_row(index, binding)
                index.flush()
                os.fsync(index.fileno())
    return binding, tuple(current['output'][:2])


def copy_range(source, output, start, end, digest):
    source.seek(start)
    for offset in range(start, end, 8 << 20):
        size = min(8 << 20, end - offset)
        data = source.read(size)
        if len(data) != size:
            raise OSError('합치는 동안 원본의 지정 범위가 줄었습니다.')
        output.write(data)
        digest.update(data)


def combine_first_pass(args):
    path = local_file(args.merge, may_create=True)
    first_pass = local_file(args.output)
    if path.parent != first_pass.parent or path.exists():
        raise ValueError('같은 정제 작업 폴더의 새 1차 통합 TXT 경로를 지정하세요.')
    binding, manual_identity = output_binding(args, record=False)
    previous = Path(binding['previous_txt'])
    begin, end = binding['first_pass_start'], binding['first_pass_end']
    boundary = binding['previous_bytes']
    expected = boundary + end - begin
    digest = sha256()
    print(f'수동 정제 저장분과 남은 1차 정제문을 {expected:,}바이트 TXT로 합칩니다.', flush=True)
    with previous.open('rb') as base, first_pass.open('rb') as auto:
        info = os.fstat(base.fileno())
        if (info.st_dev, info.st_ino) != manual_identity or info.st_size < boundary:
            raise ValueError('확정한 기존 정제본의 위치가 바뀌었습니다.')
        if os.fstat(auto.fileno()).st_size != end:
            raise ValueError('1차 정제 본문의 크기가 바뀌었습니다.')
        with NamedTemporaryFile(mode='w+b', dir=path.parent, prefix='.first-pass-') as out:
            copy_range(base, out, 0, boundary, digest)
            copy_range(auto, out, begin, end, digest)
            out.flush()
            os.fsync(out.fileno())
            if out.tell() != expected:
                raise ValueError('통합 정제문의 크기가 기대한 값과 다릅니다.')
            tail = min(boundary, 4096)
            out.seek(boundary - tail)
            base.seek(boundary - tail)
            auto.seek(begin)
            seam = base.read(tail) + auto.read(min(4096, end - begin))
            if out.read(len(seam)) != seam:
                raise ValueError('수동 정제문과 자동 정제문의 접합부가 일치하지 않습니다.')
            os.link(out.name, path)
    result = dict(binding, type='combined', path=str(path), bytes=expected, sha256=digest.hexdigest())
    with first_pass.with_name(first_pass.name + '.work').open('ab') as index:
        lock(index)
        send_row(index, result)
        index.flush()
        os.fsync(index.fileno())
    print(json.dumps(result, ensure_ascii=False), flush=True)


def bind_legacy_prefix(args):
    target = local_file(args.bind_legacy)
    first_pass = local_file(args.output)
    with open_pair(args, initialize=False) as (_, _, _, current):
        restricted = set((current.get('restored') or {}).get('restricted', ()))
    scope = history_scope(local_file(args.cleaned))
    offsets, count = {}, 0
    for source in scope['inputs']:
        offsets[source['name']] = count
        count += source['intervals']

    work = first_pass.with_name(first_pass.name + '.work')
    with work.open('rb') as index:
        combined = next(row for row in map(json.loads, index)
                        if isinstance(row, dict) and row.get('type') == 'combined' and row['path'] == str(target))
    if target.stat().st_size != combined['bytes']:
        raise ValueError('통합 정제문의 크기가 기록과 다릅니다.')
    base = args.cleaned.resolve().parent
    cache = base / 'cache_reviewed_partial_v18'
    built_path = cache / 'built.json'
    built = json.loads(built_path.read_bytes())
    verified = json.loads((cache / 'verified.json').read_bytes())
    if (verified['status'] != 'CPU_FULL_CACHE_VERIFIED'
            or built['lineage']['scope_sha256'] != sha256((base / 'scope.json').read_bytes()).hexdigest().upper()):
        raise ValueError('기존 검증 캐시와 원문 범위가 연결되지 않습니다.')
    manifests = built['manifests']
    train_path = cache / 'text/train'
    first_shard = train_path / manifests['text_train']['shards'][0]['path']
    with first_shard.open('rb') as fp:
        marker = b''.join(json.loads(fp.readline())['text'].encode() + BREAK for _ in range(2))
    counts, skipped = Counter(), []
    with target.open('rb') as fp, mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ) as txt:
        limit = combined['previous_bytes']
        begin = txt.find(marker, 0, limit)
        if begin < 0 or txt.find(marker, begin + 1, limit) >= 0:
            raise ValueError('기존 검증 캐시의 시작 위치를 하나로 확인하지 못했습니다.')
        pos = begin
        print(f'기존 캐시의 시작 위치 {begin:,}바이트를 찾았습니다.', flush=True)
        for split in ('train', 'val'):
            for row in historical_rows(cache / 'text' / split, manifests['text_' + split]):
                source_name, ordinal = row['id'].split(':')
                ordinal = offsets[source_name] + int(ordinal)
                data = row['text'].encode() + BREAK
                if pos + len(data) <= limit and txt[pos:pos + len(data)] == data:
                    pos += len(data)
                    counts.update([split])
                    counts['restricted'] += int(ordinal in restricted)
                    counts['with_original_url'] += int(bool(row.get('source_url')))
                    counts['with_original_id'] += int(bool(row.get('original_document_id')))
                elif ordinal in restricted or txt.find(BREAK + data, 0, begin) >= 0:
                    skipped.append(row['id'])
                else:
                    raise ValueError(f'검증 캐시의 {row["id"]}에서 통합본의 원문 순서가 다릅니다. 마지막 위치 {pos:,}.')
    result = dict(type='legacy_cache_span', combined_sha256=combined['sha256'], start=begin, end=pos,
                  cache=str(cache), built_sha256=sha256(built_path.read_bytes()).hexdigest(),
                  counts=dict(counts), skipped=skipped, earlier_bytes=begin, later_bytes=limit-pos)
    with work.open('ab') as index:
        lock(index)
        send_row(index, result)
        index.flush()
        os.fsync(index.fileno())
    print(json.dumps(result, ensure_ascii=False), flush=True)


def main():
    parser = arguments(__doc__)
    parser.add_argument('--output', required=True, type=Path, help='잔여 범위 1차 정제 TXT')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--resume', action='store_true', help='직전 저장 위치부터 이어서 처리')
    mode.add_argument('--pair', action='store_true', help='원문 ID로 기존 저장분과 1차 결과의 연결 위치 확인')
    mode.add_argument('--merge', type=Path, help='기존 정제 저장분과 남은 1차 결과를 통합 TXT로 저장')
    mode.add_argument('--bind-legacy', type=Path, help='통합본에서 기존 검증 캐시가 정확히 대응하는 범위를 확인')
    mode.add_argument('--second-pass', nargs=2, type=int, metavar=('첫문서', '끝문서'),
                      help='현재 배정 내 2차 정제 대상의 1차 본문 미리보기')
    parser.add_argument('--excerpt', nargs=3, type=int, action='append', metavar=('문서', '첫줄', '끝줄'),
                        help='2차에서 여러 문서의 정확한 줄을 한 번에 확인')
    args = parser.parse_args()
    if args.excerpt and not args.second_pass:
        parser.error('--excerpt에는 --second-pass가 필요합니다.')
    try:
        if args.pair:
            binding, _ = output_binding(args, record=True)
            print(json.dumps(binding, ensure_ascii=False))
        elif args.merge:
            combine_first_pass(args)
        elif args.bind_legacy:
            bind_legacy_prefix(args)
        elif args.second_pass:
            second_pass_preview(args)
        else:
            first_pass(args)
    except (OSError, ValueError, KeyError, ImportError, StopIteration) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
