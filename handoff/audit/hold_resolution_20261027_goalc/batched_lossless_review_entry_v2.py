"""Guard6 before the unchanged V6 assignment and bounded lossless frame reader."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import active_guard_v6_preflight_v1 as guard

FROZEN_SHA = '14943F3CE41791986B529541A38E74653A3AA854C52AD91CA7D06EABE3D83829'


def frozen_batch():
    path = AUDIT/'batched_lossless_review_entry_v1.py'
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest().upper() != FROZEN_SHA:
        raise ValueError('frozen bounded frame reader changed')
    spec = importlib.util.spec_from_file_location('guard6_unchanged_batch_v1', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cli(root, role):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page', type=int)
    parser.add_argument('source_id')
    parser.add_argument('first_part', type=int)
    parser.add_argument('count', type=int, nargs='?', default=3)
    args = parser.parse_args()
    if args.page < 1 or args.first_part < 1 or not 1 <= args.count <= 3:
        parser.error('positive page/first_part and count 1..3 required')
    guard.activate()
    data = guard.checked_contract()
    ident = 'expanded_train:' + args.source_id if args.source_id.isdigit() else args.source_id
    if ident in set(data['restricted_ids']) | set(data['trusted_metadata']):
        raise ValueError('restricted source identity; no payload read')
    cohort = 'remaining_field_title_page_' + format(args.page, '03d') + '_counter_v1'
    batch = frozen_batch()
    entry = batch.frozen_entry()
    metadata, scope, core = batch.setup(root, entry)
    context = core.resolve_assignment(root, scope, role, cohort, ident, metadata.pinned)
    guard.require_payload_context(context, data)
    context, views, pieces = batch.batch(core, root, scope, role, cohort, ident,
        args.first_part, args.count, metadata.pinned)
    context['cumulative_guard'] = dict(path=str(guard.CONTRACT.relative_to(root)), sha256=guard.EXPECTED)
    batch.emit(root, context, views, pieces)
    guard.assert_no_protected_opens()

