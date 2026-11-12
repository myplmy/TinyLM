"""Read one exact assigned pair once; expose up to three unchanged V6 frames."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

AUDIT = Path(__file__).resolve().parent
ENTRY_SHA = '1E4CA19CF2220910203F977B57315A1AACE072F073997C6B5BE215B60B1DEECB'
SCOPE_PIN = dict(path='handoff/audit/hold_resolution_20261027_goalc/LOSSLESS_REVIEW_READER_SCOPE_V6.json',
                 sha256='68D97F85C6DB1F76A284B12A65663633D39B44F07CA502E6EA1C8844B9F5CC46', bytes=40175)
MAX_PARTS = 3


def frozen_entry():
    path = AUDIT / 'scoped_lossless_review_entry_v4.py'
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest().upper() != ENTRY_SHA:
        raise ValueError('fixed V6 entry changed; no payload read')
    spec = importlib.util.spec_from_file_location('unchanged_v6_entry_for_batch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def setup(root, entry):
    metadata = entry.load_module(AUDIT/'field_scoped_packet_entry_v1.py',
        '53C408863DCF2474BD9825DE23EA15D765DCC0F6EDC356CD5767E5C59A18F8CE', 'batch_exact_metadata')
    scope = json.loads(metadata.pinned(root, SCOPE_PIN))
    if (scope['contract']['path'], scope['contract']['sha256']) != entry.CONTRACT:
        raise ValueError('current guard5 is mandatory before payload access')
    if scope.get('transport_protocol') != 'FULL_ORIGINAL_AND_LOSSLESS_CANDIDATE_V2':
        raise ValueError('unexpected transport contract')
    pin = scope['core']
    if pin['path'] != 'handoff/audit/hold_resolution_20261027_goalc/lossless_review_packet_v3.py':
        raise ValueError('unexpected lossless core path')
    metadata.pinned(root, pin)
    core = entry.load_module(root/pin['path'], pin['sha256'], 'unchanged_core3_for_batch')
    return metadata, scope, core


def batch(core, root, scope, role, cohort, ident, first, count, read_metadata, read_payload=None):
    if type(first) is not int or first < 1 or type(count) is not int or not 1 <= count <= MAX_PARTS:
        raise ValueError('invalid bounded consecutive batch; no payload read')
    context, original, candidate = core.load_pair(root, scope, role, cohort, ident,
                                                read_metadata, read_payload)
    views = core.prepare_views(original, candidate)
    first_piece = core.view_part(views, 'pair', first)
    last = min(first + count - 1, first_piece['parts'])
    pieces = [first_piece] + [core.view_part(views, 'pair', n) for n in range(first+1, last+1)]
    return context, views, pieces


def emit(root, context, views, pieces):
    for piece in pieces:
        info = {key:value for key,value in views.items() if key not in
                {'original', 'candidate', 'full_candidate', 'pair', 'changes'}}
        info.update(context)
        info.update({key:value for key,value in piece.items() if key != 'text'})
        info.update(keep_output_absolute=str(root/context['original']['path']),
                    accept_output_absolute=str(root/context['candidate']['path']),
                    required_views=['pair'], changes=len(views['changes']),
                    root_or_cache_admission=False, semantic_review_complete=False,
                    code_or_model_execution=False, output_writes=0)
        print('TRUSTED_LOSSLESS_VIEW_V2 ' + json.dumps(info, ensure_ascii=False, separators=(',', ':')))
        print('SOURCE_DATA_VIEW_BEGIN')
        print(piece['text'], end='')
        print('\nSOURCE_DATA_VIEW_' + ('EOF' if piece['end_of_view'] else 'MORE_PARTS_REMAIN'))
    print('TRUSTED_LOSSLESS_BATCH_END ' + json.dumps(dict(
        source_id=context['source_id'], role=context['role'], first_part=pieces[0]['part'],
        last_part=pieces[-1]['part'], parts=pieces[-1]['parts'], next_part=pieces[-1]['next_part'],
        pair_loads=1, returned_parts=len(pieces), payload_copies_written=0,
        semantic_review_complete=False), separators=(',', ':')))


def cli(root, role):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page', type=int)
    parser.add_argument('source_id')
    parser.add_argument('first_part', type=int)
    parser.add_argument('count', type=int, nargs='?', default=MAX_PARTS)
    args = parser.parse_args()
    if args.page < 1 or args.first_part < 1 or not 1 <= args.count <= MAX_PARTS:
        parser.error('positive page/first_part and count 1..3 required')
    ident = 'expanded_train:' + args.source_id if args.source_id.isdigit() else args.source_id
    cohort = 'remaining_field_title_page_' + format(args.page, '03d') + '_counter_v1'
    entry = frozen_entry()
    metadata, scope, core = setup(root, entry)
    context, views, pieces = batch(core, root, scope, role, cohort, ident,
                                  args.first_part, args.count, metadata.pinned)
    emit(root, context, views, pieces)
