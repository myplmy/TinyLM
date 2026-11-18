"""Filter independently proven empty body sections using existing proof metadata."""
from pathlib import Path
import argparse
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard


def run(path, expected, output):
    guard.activate()
    assert path.parent == AUDIT and not path.is_symlink()
    assert guard.inv.file_sha(path) == expected
    prior = json.loads(path.read_bytes())
    assert prior['root_approved'] is prior['cache_admitted'] is False
    assert prior['cumulative_guard_sha256'] == guard.EXPECTED
    checks, deferred = [], list(prior['deferred_rows'])
    removed = []
    for row in prior['checks']:
        proof = row['fresh_preservation_proof']
        sections = proof.get('candidate_empty_eof_appendix_headings', []) + proof.get('candidate_independently_empty_section_lines', [])
        assert all(proof['guards'].values()) and all(row['additional_readiness_guards'].values())
        if sections:
            removed.append(row['id'])
            deferred.append(dict(id=row['id'], body=row['body'], occurrences=row['occurrences'],
                reasons=['INDEPENDENTLY_PROVEN_EMPTY_SECTION_REMAINS_IN_FINAL_BODY'], sections=sections))
        else:
            value = dict(row)
            value['additional_readiness_guards'] = dict(row['additional_readiness_guards'],
                no_independently_proven_empty_final_body_section=True)
            checks.append(value)
    pins = dict(prior['input_pins'])
    for value in [path, Path(__file__), guard.CONTRACT]:
        pins[str(value.relative_to(ROOT))] = guard.inv.file_sha(value)
    result = dict(prior, status='SOURCE_CONTEXT_LITERAL_AND_FINAL_EMPTY_SECTION_GATES_PENDING_ROOT',
        checks=checks, verified=len(checks), verified_positions=sum(r['occurrences'] for r in checks),
        deferred_rows=deferred, deferred=len(deferred), final_structure_deferred_ids=removed,
        prior_readiness=dict(path=str(path.relative_to(ROOT)), sha256=expected), input_pins=pins,
        structural_filter_payload_opens=0, source_or_body_copies_written=0)
    assert output.parent == AUDIT and not output.exists()
    guard.inv.write_json(output, result)
    guard.assert_no_protected_opens()
    print(json.dumps(dict(verified=result['verified'], positions=result['verified_positions'],
        final_structure_deferred_ids=removed, payload_opens=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.proof.resolve(), args.expected_sha, args.output.resolve())
