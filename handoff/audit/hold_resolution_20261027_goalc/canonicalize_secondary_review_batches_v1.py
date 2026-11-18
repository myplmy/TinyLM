"""Freeze author metadata, merge explicit corrections, quarantine invalid rows."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
from collections import Counter

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from check_authored_exact_context_batch_v1 import DECISIONS


def parse_rows(text):
    records, invalid = [], []
    for number, line in enumerate(text.splitlines(), 1):
        cells = line.split('|', 5)
        if len(cells) != 6:
            continue
        clean = lambda s: s.strip().strip('`').strip()
        ident = clean(cells[1])
        if not re.fullmatch(r'(?:(?:expanded_train|validation):)?[0-9]+', ident):
            continue
        if ident.isdigit():
            ident = 'expanded_train:'+ident
        sha, decision = clean(cells[2]), clean(cells[3])
        if sha in DECISIONS:
            sha, decision = decision, sha
        views = clean(cells[4])
        reason = cells[5].rsplit('|', 1)[0].strip()
        if not re.fullmatch('[A-Fa-f0-9]{64}', sha) or decision not in DECISIONS or not views or not reason:
            invalid.append(dict(id=ident, line=number, reason='INVALID_HASH_DECISION_OR_REVIEW_FIELDS'))
            continue
        records.append(dict(id=ident, body_sha256=sha.upper(), decision=decision, actual_views=views, reason=reason))
    return records, invalid


def pin(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=guard.inv.file_sha(path))


def freeze(path):
    assert not path.is_symlink() and path.suffix == '.md'
    raw = path.read_bytes()
    assert raw == path.read_bytes() and 0 < len(raw) < 20_000_000
    sha = hashlib.sha256(raw).hexdigest().upper()
    archive = AUDIT/'exact_cohort_review_archive_v1'/sha[:2]/(sha+'.md')
    archive.parent.mkdir(exist_ok=True)
    if archive.exists():
        assert archive.read_bytes() == raw
    else:
        archive.write_bytes(raw)
    return raw.decode('utf-8'), dict(source=pin(path), archive=pin(archive))


def run(config_path):
    guard.activate()
    assert config_path.parent == AUDIT and not config_path.is_symlink()
    config = json.loads(config_path.read_bytes())
    output = AUDIT/config['directory']
    assert not output.exists()
    output.mkdir()
    groups, invalid, archive_records, summaries = [], [], [], []
    for group in config['groups']:
        scope_path = ROOT/group['scope']['path']
        assert guard.inv.file_sha(scope_path) == group['scope']['sha256']
        scope = json.loads(scope_path.read_bytes())
        cases = {row['id']: row for row in scope['cases']}
        current, origins, quarantined = {}, {}, set()
        for mode in ['base', 'corrections', 'native_corrections']:
            for name in group.get(mode, []):
                text, record = freeze(ROOT/name)
                archive_records.append(record)
                rows, bad = parse_rows(text)
                invalid.extend(dict(item, review=record['archive'], group=group['name']) for item in bad)
                quarantined.update(item['id'] for item in bad)
                for row in rows:
                    ident = row['id']
                    if ident not in cases or row['body_sha256'] != cases[ident]['body']['sha256']:
                        invalid.append(dict(id=ident, reason='UNASSIGNED_ID_OR_BODY_HASH_MISMATCH', review=record['archive'], group=group['name']))
                        quarantined.add(ident)
                        continue
                    if mode == 'base' and ident in current:
                        invalid.append(dict(id=ident, reason='DUPLICATE_BASE_REVIEW_REQUIRES_EXPLICIT_RECONCILIATION', review=record['archive'], group=group['name']))
                        quarantined.add(ident)
                        continue
                    if mode == 'native_corrections' and row['decision'] == 'APPROVE_EXISTING_BODY' and ident not in group.get('native_positive_ids', []):
                        continue
                    current[ident] = row
                    origins[ident] = record['archive']
        for ident in quarantined:
            current.pop(ident, None)
            origins.pop(ident, None)
        lines = ['# Canonical secondary review metadata',
                 'Exact author rows and explicit corrections only; no new source read or ROOT/cache adoption.',
                 '', '| ID | BODY_SHA256 | DECISION | ACTUAL_VIEWS_AND_EOF | SOURCE_MEANING_OR_REMAINING_ISSUE |',
                 '|---|---|---|---|---|']
        for ident, row in current.items():
            lines.append('| '+ident+' | '+row['body_sha256']+' | '+row['decision']+' | '+row['actual_views']+' | '+row['reason']+' |')
        path = output/(group['name']+'.md')
        path.write_text(chr(10).join(lines)+chr(10), encoding='utf-8')
        groups.append(dict(name=group['name'], scope=group['scope'], reviews=[pin(path)]))
        summaries.append(dict(group=group['name'], assigned=len(cases), rows=len(current),
            missing_ids=sorted(set(cases)-set(current)), counts=dict(Counter(row['decision'] for row in current.values())),
            exact_row_origins=origins, canonical_review=pin(path)))
    result = dict(status='CANONICAL_AUTHOR_ROWS_FROZEN_NOT_ROOT_OR_CACHE_ADMISSION', groups=groups,
        summaries=summaries, invalid_rows=invalid, archives=archive_records,
        source_or_body_opens=0, source_or_body_copies=0, firstread_credit=0,
        input_pins={str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in [config_path, Path(__file__), guard.CONTRACT]},
        root_approved=False, cache_admitted=False, goal_complete=False, training_authorized=False)
    path = AUDIT/config['output']
    assert not path.exists()
    guard.inv.write_json(path, result)
    guard.assert_no_protected_opens()
    print(json.dumps(dict(groups=len(groups), rows=sum(s['rows'] for s in summaries), invalid=len(invalid),
        missing=sum(len(s['missing_ids']) for s in summaries), body_copies=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    run(parser.parse_args().config.resolve())
