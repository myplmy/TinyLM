"""Verify frozen plan bytes with the original link base; mutate no snapshots."""
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def main():
    rows = []
    for tag, model in (('p108w_v1_20261104', 'new595-broad-q'),
                       ('p108w_v2_20261104', 'new595-broad-q'),
                       ('p108w_v3_20261104', 'new595-broad-f'),
                       ('p108j_v1_20261104', 'new595-broad-q')):
        directory = Path('test_result/evidence')/tag/model
        profile = json.loads((directory/'profile.json').read_text(encoding='utf-8'))
        path = directory/'initial_plan.md'
        digest = sha(path.read_bytes())
        expected = profile.get('initial_plan_sha256', profile.get('plan_sha256'))
        if expected is None:
            raise ValueError('sealed plan digest field missing: '+tag)
        if digest != expected:
            raise ValueError('frozen plan changed: '+tag)
        rows.append(dict(path=str(path), sha256=digest,
            original_logical_path='test_plan/P108_직접가중치-방향수리와-학습개입.md',
            relative_link_base='test_plan',
            disposition='IMMUTABLE_SOURCE_BYTES_NOT_RELOCATED_LIVE_MARKDOWN'))
    output = Path('handoff/audit/nov04_weight_space/ARCHIVAL_PLAN_CONTEXT_v1.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(dict(schema='P108_ARCHIVAL_PLAN_CONTEXT_V1', snapshots=rows,
            current_live_plan='test_plan/P108_직접가중치-방향수리와-학습개입.md',
            prior_static='handoff/audit/nov04_weight_space/OWNED_STATIC_v4.json',
            prior_broken_relative_links=5, snapshot_writes=0,
            alternatives=dict(A='REWRITE_OLD_BYTES_BREAKS_SEALED_SHA_REJECTED',
                B='CREATE_FAKE_RELATIVE_TARGET_DIRECTORIES_REJECTED',
                C='PRESERVE_SOURCE_BYTES_VERIFY_ORIGIN_AND_CHECK_LIVE_DOCUMENT_SELECTED'),
            live_link_rules_changed=False, global_link_pass_claim=False),
            stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps(dict(snapshots=len(rows), hashes='VERIFIED', original_writes=0)))


if __name__ == '__main__':
    main()
