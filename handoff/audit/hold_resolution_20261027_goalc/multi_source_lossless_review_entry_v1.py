"""Reuse core3/scope6: preflight up to five assigned IDs before any payload I/O."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import active_guard_v6_preflight_v1 as guard

MAX_IDS = 5
MAX_BODY_BYTES = 12000
MAX_OUTPUT_BYTES = 18000
FRAME_BYTES = 4000
OLD = AUDIT/'batched_lossless_review_entry_v3.py'
assert not OLD.is_symlink() and hashlib.sha256(OLD.read_bytes()).hexdigest().upper() == '708CF07D415693F4457BF064D61F23AD4ABE702FC045346918A5D31E7E56277B'
from batched_lossless_review_entry_v3 import frozen_batch


def cached_reader(reader):
    cache = {}

    def read(root, pin):
        key = (str(root), json.dumps(pin, sort_keys=True, ensure_ascii=False))
        if key not in cache:
            cache[key] = reader(root, pin)
        return cache[key]

    return read


def header(root, context, views):
    value = {k:v for k,v in views.items() if k not in
             {'original', 'candidate', 'full_candidate', 'pair', 'changes'}}
    value.update(context)
    value.update(keep_output_absolute=str(root/context['original']['path']),
        accept_output_absolute=str(root/context['candidate']['path']), required_views=['pair'],
        changes=len(views['changes']), root_or_cache_admission=False,
        semantic_review_complete=False, code_or_model_execution=False, output_writes=0)
    return value


def collect(root, role, cohort, idents, core, scope, read_metadata, contract, read_payload=None):
    if not 1 <= len(idents) <= MAX_IDS or len(set(idents)) != len(idents):
        raise ValueError('one to five distinct assigned IDs required; no payload read')
    blocked = set(contract['restricted_ids']) | set(contract['trusted_metadata'])
    if set(idents) & blocked:
        raise ValueError('restricted requested identity; no payload read')
    contexts = []
    for ident in idents:
        context = core.resolve_assignment(root, scope, role, cohort, ident, read_metadata)
        guard.require_payload_context(context, contract)
        contexts.append(context)
    packets = []
    used = 0
    for ident, prechecked in zip(idents, contexts):
        if MAX_BODY_BYTES - used < FRAME_BYTES:
            break
        context, original, candidate = core.load_pair(root, scope, role, cohort, ident,
            read_metadata, read_payload)
        if context != prechecked:
            raise ValueError('assignment changed after group preflight')
        views = core.prepare_views(original, candidate)
        pieces = []
        for part in range(1, 4):
            piece = core.view_part(views, 'pair', part)
            width = len(piece['text'].encode('utf-8'))
            if width > MAX_BODY_BYTES - used:
                break
            pieces.append(piece)
            used += width
            if piece['end_of_view']:
                break
        if not pieces:
            raise ValueError('no frame could be returned within the fixed budget')
        context['cumulative_guard'] = dict(path=str(guard.CONTRACT.relative_to(root)), sha256=guard.EXPECTED)
        packets.append(dict(header=header(root, context, views), pieces=pieces))
    returned = [p['header']['source_id'] for p in packets]
    result = dict(requested_ids=list(idents), returned_ids=returned,
        not_returned_ids=list(idents[len(returned):]), source_pairs_loaded=len(packets),
        body_bytes=used, source_body_copies_written=0, first_read_credit=0,
        semantic_review_complete=False, root_or_cache_admission=False)
    return packets, result


def render(packets, result):
    if not packets:
        raise ValueError('an empty response cannot establish any read')
    shared = {k:v for k,v in packets[0]['header'].items() if k != 'source_id'
              and all(p['header'].get(k) == v for p in packets)}
    out = io.StringIO()

    def record(label, value):
        out.write(label + ' ' + json.dumps(value, ensure_ascii=False, separators=(',', ':')) + chr(10))

    record('TRUSTED_TASK_BATCH_CONTEXT_V1', dict(shared_header=shared,
        applies_only_to_returned_ids=result['returned_ids'], requested_ids=result['requested_ids']))
    for packet in packets:
        ident = packet['header']['source_id']
        record('TRUSTED_TASK_SOURCE_CONTEXT_V1', {k:v for k,v in packet['header'].items() if k not in shared})
        for piece in packet['pieces']:
            info = dict(source_id=ident, **{k:v for k,v in piece.items() if k != 'text'})
            record('TRUSTED_TASK_FRAME_V1', info)
            out.write('SOURCE_DATA_VIEW_BEGIN' + chr(10) + piece['text'] + chr(10))
            record('TRUSTED_TASK_FRAME_END_V1', dict(source_id=ident, part=piece['part'],
                end_of_view=piece['end_of_view'], next_part=piece['next_part']))
    result = dict(result, continuations=[dict(source_id=p['header']['source_id'],
        next_part=p['pieces'][-1]['next_part'], total_parts=p['pieces'][-1]['parts'])
        for p in packets if not p['pieces'][-1]['end_of_view']],
        completed_pair_ids=[p['header']['source_id'] for p in packets if p['pieces'][-1]['end_of_view']])
    record('TRUSTED_TASK_BATCH_END_V1', result)
    value = out.getvalue()
    if len(value.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('bounded output exceeded; nothing printed; use the single-ID reader')
    return value


def cli(root, role):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page', type=int)
    parser.add_argument('source_ids', nargs='+')
    args = parser.parse_args()
    if args.page < 1 or not 1 <= len(args.source_ids) <= MAX_IDS:
        parser.error('positive page and one to five IDs required')
    idents = ['expanded_train:' + value if value.isdigit() else value for value in args.source_ids]
    if len(set(idents)) != len(idents):
        parser.error('duplicate IDs cannot count as additional reads')
    guard.activate()
    contract = guard.checked_contract()
    if set(idents) & (set(contract['restricted_ids']) | set(contract['trusted_metadata'])):
        raise ValueError('restricted requested identity; no payload read')
    old = frozen_batch()
    entry = old.frozen_entry()
    metadata, scope, core = old.setup(root, entry)
    read_metadata = cached_reader(metadata.pinned)
    cohort = 'remaining_field_title_page_' + format(args.page, '03d') + '_counter_v1'
    packets, result = collect(root, role, cohort, idents, core, scope, read_metadata, contract)
    value = render(packets, result)
    guard.assert_no_protected_opens()
    print(value, end='')
