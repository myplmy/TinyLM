"""Close the inspected empty appendix tails in an already checked ROOT batch."""
from copy import deepcopy
from pathlib import Path
import json
import re
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from root_only_bulk_delta_v2 import source_basis
from root_empty_section_contract_v3 import preservation
from verify_event_metadata_literal_delta_v1 import last_paragraph
from verify_rule27_literal_delta_v1 import empty_eof_appendix
from numeric_atom_integrity_v1 import numeric_atom_changes
from structural_delimiter_deferrals_v2 import deferrals as delimiters
from authored_literal_readiness_v1 import deferrals
from scripts import p106b_hold_resolution_policy_v32 as policy

SCOPED = {'expanded_train:' + value for value in ['303708', '309061', '378495']}


def trim(text, ident, footer):
    if ident == 'expanded_train:303708':
        value, count = re.subn(r'\n\s*\n각주\s*\n(?:\s*\n)+ㄷ\s*\Z', '\n', text)
        assert count == 1, ident
        return value
    prefix, suffix = last_paragraph(text)
    assert suffix == footer
    prefix, removed = empty_eof_appendix(prefix)
    assert [row['label'] for row in removed] == ['각주'], (ident, removed)
    return prefix + chr(10) * 2 + suffix + chr(10)


def main():
    guard.activate()
    path = AUDIT / 'B_ROOT_ONLY_BULK_DELTA_READINESS_V2.json'
    result = deepcopy(json.loads(path.read_bytes()))
    assert result['verified'] == 27 and result['verified_positions'] == 54
    pins = result['input_pins']
    for name, sha in pins.items():
        assert guard.inv.file_sha(ROOT / name) == sha, name
    new_files = []
    for row in result['checks']:
        if row['id'] not in SCOPED:
            continue
        guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['body']))
        assert guard.inv.file_sha(ROOT / row['original']['path']) == row['original']['sha256']
        assert guard.inv.file_sha(ROOT / row['body']['path']) == row['body']['sha256']
        source = (ROOT / row['original']['path']).read_text(encoding='utf-8')
        before = (ROOT / row['body']['path']).read_text(encoding='utf-8')
        basis = source_basis(source, row['id'])[0]
        footer = last_paragraph(source)[1]
        basis = trim(basis, row['id'], footer)
        body = trim(before, row['id'], footer)
        proof = preservation(basis, body)
        assert all(proof['guards'].values()), (row['id'], proof)
        assert not numeric_atom_changes(source, body)
        assert policy.code_preserved(source, body)
        assert policy.unicode_examples_preserved(source, body)
        assert policy.semantic_style_preserved(source, body)
        flags = set(deferrals(body) + delimiters(body) + policy.literal_holes(body))
        flags.discard('POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT')
        assert not flags, (row['id'], flags)
        assert not re.search(r'\n\s*\n각주\s*(?:\n\s*)*\Z', body)
        raw = body.encode('utf-8')
        sha = guard.inv.sha(body)
        target = guard.inv.BASE / 'root_only_literal_repairs_v1' / sha[:2] / (sha + '.txt')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == raw
        else:
            with target.open('xb') as stream:
                stream.write(raw)
            new_files.append(dict(path=str(target.relative_to(ROOT)), sha256=sha, bytes=len(raw)))
        row['body'] = dict(path=str(target.relative_to(ROOT)), sha256=sha, bytes=len(raw))
        row['fresh_preservation_proof'] = dict(proof,
            original_source_sha256=row['original']['sha256'],
            prior_literal_proof=row['fresh_preservation_proof'],
            root_context='EXACT_SOURCE_EMPTY_FOOTNOTE_BEFORE_INSPECTED_NOMINAL_FOOTER_OR_KOREAN_SORT_KEY',
            retained_footer_sha256=guard.inv.sha(footer) if row['id'] != 'expanded_train:303708' else None,
            raw_source_unchanged=True, universal_scanner_relaxation=False)
        row['additional_readiness_guards']['ROOT_inspected_empty_appendix_and_retained_footer_closed'] = True
        row['reason'] += ' / ROOT exact empty appendix closure; populated lists and all literal values retained'
    for name in [path, Path(__file__), AUDIT / 'root_only_bulk_delta_v2.py']:
        pins[str(name.relative_to(ROOT))] = guard.inv.file_sha(name)
    result['status'] = 'ROOT_ONLY_EMPTY_SECTION_AND_FOOTER_BATCH_WITH_OBSERVED_TAILS_CLOSED'
    result['root_tail_closure_new_files'] = new_files
    result['root_tail_closure_new_bytes'] = sum(row['bytes'] for row in new_files)
    output = AUDIT / 'B_ROOT_ONLY_BULK_DELTA_CLOSED_V1.json'
    assert not output.exists()
    guard.inv.write_json(output, result)
    guard.assert_no_protected_opens()
    print(json.dumps(dict(verified=result['verified'], positions=result['verified_positions'],
        tail_repairs=3, new_files=len(new_files), bytes=result['root_tail_closure_new_bytes'])))


if __name__ == '__main__':
    main()
