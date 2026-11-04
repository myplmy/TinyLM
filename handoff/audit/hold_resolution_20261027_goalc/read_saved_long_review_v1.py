"""Root-only bounded saved-review reads, reusing the pinned short-reader guards."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
FROZEN = AUDIT / 'read_counter_exact_pair_v1.py'
FROZEN_SHA = 'FFEBACB569D1655DA3250BA19805C3FF473C66080E28B74BCE58B163171B5057'


def load_saved(args):
    assert re.fullmatch(r'(root12_independent_admission_counter_v1|remaining_literal_full_counter_v1|remaining_field_title_page_[0-9]{3}_counter_v1)', args.cohort)
    assert re.fullmatch(r'(expanded_train|validation):[0-9]+', args.source_id)
    assert args.part >= 1
    assert not FROZEN.is_symlink()
    raw = FROZEN.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == FROZEN_SHA
    source = raw.decode('utf-8')
    boundary = 'for number in args.ids:'
    assert source.count(boundary) == 1
    prefix = source.split(boundary)[0]
    before = "snapshot_path = BASE / 'root12_independent_admission_counter_v1_snapshots' / args.version / 'complete.json'"
    assert prefix.count(before) == 1
    prefix = prefix.replace(before, "snapshot_path = BASE / " + repr(args.cohort + '_snapshots') + " / args.version / 'complete.json'", 1)
    observer = 'unreviewed_payload_open_attempts' if args.cohort == 'root12_independent_admission_counter_v1' else 'protected_payload_open_attempts'
    before = "assert not snapshot['errors'] and snapshot['unreviewed_payload_open_attempts'] == 0"
    assert prefix.count(before) == 1
    prefix = prefix.replace(before, "assert not snapshot['errors'] and snapshot[" + repr(observer) + "] == 0", 1)
    namespace = dict(__name__='saved_review_metadata_only_prefix', __file__=str(FROZEN))
    previous_argv = sys.argv
    try:
        sys.argv = [str(FROZEN), '--version', args.version, '--snapshot-sha256', args.snapshot_sha256, args.source_id.split(':')[1]]
        exec(compile(prefix, str(FROZEN), 'exec'), namespace)
    finally:
        sys.argv = previous_argv
    guard = namespace['guard']
    assert args.source_id not in guard['restricted_ids'], 'restricted ID; no corpus payload read'
    row = namespace['by_id'][args.source_id]
    assert row['status'] in {'PINNED_BODY_NOT_ROOT_ADMISSION', 'MATERIALIZED_BODY_NOT_ROOT_ADMISSION', 'TEXT_ADJUDICATION_NOT_ADMISSION'}, 'not a saved eligible review'
    pins = dict(original=row['original'])
    if row.get('body'):
        pins['body'] = dict(path=row['body'], sha256=row['clean_text_sha256'])
    assert all(pin['sha256'] not in guard['restricted_hashes'] for pin in pins.values()), 'restricted SHA; no corpus payload read'
    for pin in pins.values():
        path = ROOT / pin['path']
        assert not path.is_symlink() and path.resolve().is_relative_to(BASE)
    return namespace, row, pins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--snapshot-sha256', required=True)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--view', choices=['original', 'body', 'diff-json'], required=True)
    parser.add_argument('--part', type=int, default=1)
    parser.add_argument('--output-basename')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    output = None
    if args.view == 'diff-json':
        assert args.output_basename and re.fullmatch(r'[A-Z0-9_]{1,120}[.]json', args.output_basename)
        output = AUDIT / args.output_basename
        assert not output.exists() and not output.is_symlink(), 'new immutable diff artifact required'
    else:
        assert args.output_basename is None
    namespace, row, pins = load_saved(args)
    assert args.view == 'original' or 'body' in pins, 'no saved body for this source'
    if args.check_only:
        print(json.dumps(dict(status='SAVED_REVIEW_METADATA_ONLY_PREFLIGHT_PASS', id=args.source_id, pins=pins,
                              original_or_body_payload_opens=0, output_writes=0), ensure_ascii=False))
        return
    if args.view == 'diff-json':
        texts = [namespace['read_pin'](ROOT / pins[key]['path'], pins[key]['sha256']).decode('utf-8')
                 for key in ['original', 'body']]
        changes = [dict(op=op, source_range=[i, j], body_range=[k, l], before=texts[0][i:j], after=texts[1][k:l])
                   for op, i, j, k, l in difflib.SequenceMatcher(None, *texts, autojunk=False).get_opcodes() if op != 'equal']
        result = dict(status='FULL_CHARACTER_DIFF_FOR_ROOT_READING_NOT_ADMISSION', id=args.source_id,
                      original=pins['original'], body=pins['body'], review=row['review'], changes=changes,
                      source_snapshot=dict(path=str(namespace['snapshot_path'].relative_to(ROOT)), sha256=args.snapshot_sha256),
                      frozen_guard_reader=dict(path=str(FROZEN.relative_to(ROOT)), sha256=FROZEN_SHA),
                      original_characters=len(texts[0]), body_characters=len(texts[1]),
                      root_full_diff_read=False, root_training_TXT_authored=0, goal_complete=False, training_authorized=False)
        data = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        assert 0 < len(data) < 20_000_000
        with output.open('xb') as stream:
            stream.write(data)
        print(json.dumps(dict(status=result['status'], changes=len(changes), bytes=len(data),
                              artifact=str(output.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest().upper())))
        return
    pin = pins[args.view]
    value = namespace['read_pin'](ROOT / pin['path'], pin['sha256']).decode('utf-8')
    parts = max(1, (len(value) + 5999) // 6000)
    assert args.part <= parts, 'part outside text; no excerpt printed'
    lo, hi = 6000 * (args.part - 1), min(6000 * args.part, len(value))
    print(json.dumps(dict(id=args.source_id, view=args.view, pin=pin, part=args.part, parts=parts,
                          range=[lo, hi], total_characters=len(value), review=row['review']['path']), ensure_ascii=False))
    print('SAVED_CONTEXT_BEGIN')
    print(value[lo:hi], end='')
    print('\nSAVED_CONTEXT_' + ('EOF' if args.part == parts else 'PART_END_MORE_REMAINS'))


if __name__ == '__main__':
    main()
