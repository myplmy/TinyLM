"""Agent-invoked exact candidate copy; root checks metadata without writing TXT."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
COHORT = 'root12_independent_admission_counter_v1'
MANIFEST_SHA = 'A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'
GUARD_SHA = '7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(value).hexdigest().upper()


def local_path(path, boundary):
    require(path.is_absolute() and path.is_relative_to(boundary), 'outside allowed directory')
    require(not any(parent.is_symlink() for parent in (path, *path.parents)), 'symlink is not allowed')
    require(path.resolve().is_relative_to(boundary.resolve()), 'resolved path outside allowed directory')
    return path


def pinned_json(path, expected):
    value = local_path(path, ROOT).read_bytes()
    require(digest(value) == expected, 'metadata SHA mismatch')
    return json.loads(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['context_controls', 'context_latin'])
    parser.add_argument('task', type=int)
    parser.add_argument('source_id')
    parser.add_argument('output_basename')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    guard = pinned_json(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V3.json', GUARD_SHA)
    require(re.fullmatch(r'(expanded_train|validation):[0-9]+', args.source_id), 'invalid full source ID')
    require(args.source_id not in guard['restricted_ids'], 'restricted source ID; payload stays closed')
    manifest = pinned_json(BASE / COHORT / 'manifest.json', MANIFEST_SHA)
    assignments = manifest['assignments'][args.role]
    require(args.task >= 1 and args.source_id in assignments, 'source is outside role assignment')
    expected_task_ids = assignments[(args.task - 1) * 5:args.task * 5]
    require(args.source_id in expected_task_ids, 'source is outside specified TASK')
    matches = [row for row in manifest['rows'] if row['id'] == args.source_id]
    require(len(matches) == 1 and matches[0]['role'] == args.role, 'manifest role/ID mismatch')
    row = matches[0]
    for pin in (row['original'], row['candidate']):
        require(pin['sha256'] not in guard['restricted_hashes'], 'restricted source hash; payload stays closed')
    folder = local_path(BASE / 'agents' / args.role / COHORT, BASE)
    require(folder.is_dir(), 'assigned output directory does not exist')
    task_path = local_path(folder / f'TASK_{args.task:03d}.md', folder)
    task_bytes = task_path.read_bytes()
    task_text = task_bytes.decode('utf-8')
    require(task_text.splitlines()[0] == f'# TASK_{args.task:03d}', 'TASK heading mismatch')
    require(re.findall(r'^## ((?:expanded_train|validation):[0-9]+)$', task_text, re.M) == expected_task_ids,
            'TASK membership/order differs from frozen assignment')
    sections = re.findall(r'^## ' + re.escape(args.source_id) + r'\n(.*?)(?=^## |\Z)', task_text, re.M | re.S)
    require(len(sections) == 1, 'TASK source section is not unique')
    section = sections[0]
    for field, label in [('original', '원형 SHA'), ('candidate', '선택본문 SHA')]:
        pin = row[field]
        require(re.findall(r'^' + field + r': (.+)$', section, re.M) == [str(ROOT / pin['path'])],
                f'TASK {field} path mismatch')
        require(re.findall(r'^' + label + r': (.+)$', section, re.M) == [pin['sha256']],
                f'TASK {field} SHA mismatch')
    source_kind, number = args.source_id.split(':')
    if args.role == 'context_controls':
        pattern = re.escape(f'{source_kind}_{number}_root12_working_task{args.task:03d}_v') + r'[1-9][0-9]*\.txt'
    else:
        prefix = number if source_kind == 'expanded_train' else f'validation_{number}'
        pattern = re.escape(prefix + '_counter_working_v') + r'[1-9][0-9]*\.txt'
    require(re.fullmatch(pattern, args.output_basename), 'output must be an exact ID/TASK versioned basename')
    target = local_path(folder / args.output_basename, folder)
    require(not target.exists(), 'target already exists; preserve it and choose a new version')
    candidate = local_path(ROOT / row['candidate']['path'], BASE)
    require(candidate.is_file(), 'candidate path is not a regular file')
    require(0 < candidate.stat().st_size < 20_000_000, 'candidate size outside allowed bound')
    receipt = {
        'status': 'METADATA_ONLY_COPY_PREFLIGHT_PASS' if args.check_only else 'EXACT_ASSIGNED_CANDIDATE_COPIED',
        'role': args.role, 'task': args.task, 'id': args.source_id,
        'candidate': row['candidate'], 'output': str(target.relative_to(ROOT)),
        'task_sha256': digest(task_bytes), 'manifest_sha256': MANIFEST_SHA,
        'guard_sha256': GUARD_SHA, 'original_payload_opens': 0,
        'candidate_payload_opens': 0 if args.check_only else 1,
        'training_authorized': False, 'cache_admitted': False,
    }
    if not args.check_only:
        value = candidate.read_bytes()
        require(0 < len(value) < 20_000_000 and digest(value) == row['candidate']['sha256'],
                'candidate bytes do not match frozen SHA')
        value.decode('utf-8')
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as output:
            output.write(value)
        receipt['copied_bytes'] = len(value)
        receipt['copied_sha256'] = digest(value)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, UnicodeError) as exc:
        print(json.dumps({'status': 'COPY_REFUSED', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
