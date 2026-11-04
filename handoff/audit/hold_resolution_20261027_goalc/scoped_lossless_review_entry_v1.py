"""Fixed-role CLI for complete originals and lossless candidate representations."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

AUDIT = Path(__file__).resolve().parent
METADATA_HELPER_SHA = '53C408863DCF2474BD9825DE23EA15D765DCC0F6EDC356CD5767E5C59A18F8CE'
CONTRACT_PATH = 'handoff/audit/hold_resolution_20261027_goalc/GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
CONTRACT_SHA = '7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'


def _module(path, expected, name):
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest().upper() != expected:
        raise ValueError('fixed reader code bytes changed')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cli(root, role, config_pin):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--view', choices=['original', 'candidate'], required=True)
    parser.add_argument('--part', type=int, default=1)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    metadata = _module(AUDIT/'field_scoped_packet_entry_v1.py', METADATA_HELPER_SHA,
                       'unchanged_lossless_metadata_guard')
    scope = json.loads(metadata.pinned(root, config_pin))
    if (scope['contract']['path'], scope['contract']['sha256']) != (CONTRACT_PATH, CONTRACT_SHA):
        raise ValueError('current V3 guard contract is mandatory')
    core_pin = scope['core']
    if core_pin['path'] != 'handoff/audit/hold_resolution_20261027_goalc/lossless_review_packet_v1.py':
        raise ValueError('unexpected lossless core path')
    metadata.pinned(root, core_pin)
    core = _module(root/core_pin['path'], core_pin['sha256'], 'pinned_lossless_review_core')
    if args.check_only:
        context = core.resolve_assignment(root, scope, role, args.cohort, args.source_id, metadata.pinned)
        print(json.dumps(dict(status='LOSSLESS_REVIEW_METADATA_ONLY_PREFLIGHT_PASS', **context,
                              payload_opens=0, output_writes=0), ensure_ascii=False))
        return
    context, original, candidate = core.load_pair(
        root, scope, role, args.cohort, args.source_id, metadata.pinned)
    views = core.prepare_views(original, candidate)
    piece = core.view_part(views, args.view, args.part)
    info = {k: v for k, v in views.items() if k not in {'original', 'candidate', 'changes'}}
    info.update(context)
    info.update({k: v for k, v in piece.items() if k != 'text'})
    info.update(required_views=['original', 'candidate'], changes=len(views['changes']),
                root_or_cache_admission=False, semantic_review_complete=False,
                code_or_model_execution=False, output_writes=0)
    print('TRUSTED_LOSSLESS_VIEW ' + json.dumps(info, ensure_ascii=False))
    print('SOURCE_DATA_VIEW_BEGIN')
    print(piece['text'], end='')
    print('\nSOURCE_DATA_VIEW_' + ('EOF' if piece['end_of_view'] else 'MORE_PARTS_REMAIN'))
