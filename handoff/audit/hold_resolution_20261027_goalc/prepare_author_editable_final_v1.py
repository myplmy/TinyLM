"""Prepare exact bytes in the author's single final file; perform no semantic edits."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(AUDIT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from batched_lossless_review_entry_v1 import frozen_entry, setup


def main(config_path):
    config_path = Path(config_path).resolve()
    assert config_path.parent == AUDIT
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    receipt_path = AUDIT / config['receipt_name']
    assert receipt_path.parent == AUDIT and not receipt_path.exists()
    activate()
    checked_contract()
    metadata, scope, core = setup(ROOT, frozen_entry())
    prepared = []
    paths = set()
    for request in config['requests']:
        role, page, ident = request['role'], request['page'], request['id']
        cohort = 'remaining_field_title_page_' + format(page, '03d') + '_counter_v1'
        context = core.resolve_assignment(ROOT, scope, role, cohort, ident, metadata.pinned)
        filename = request['output_name']
        assert PurePosixPath(filename).name == filename
        assert filename.startswith('expanded_train_' + ident.split(':')[1] + '_') and filename.endswith('.txt')
        output = ROOT / core.base.DATA_ROOT / 'agents' / role / cohort / filename
        core.base.data_path(ROOT, str(output.relative_to(ROOT)))
        assert output.parent.is_dir() and not output.exists() and output not in paths
        paths.add(output)
        assert request['preimage'] in {'original', 'candidate'}
        pin = context[request['preimage']]
        raw = core.base.bounded_payload(ROOT, pin)
        assert len(raw) < 20_000_000 and core.base.digest(raw) == pin['sha256']
        raw.decode('utf-8')
        prepared.append((output, raw, dict(
            id=ident, author_role=role, original=context['original'],
            immutable_preimage=pin, preimage_kind=request['preimage'],
            editable_output=str(output.relative_to(ROOT)), pre_edit_sha256=pin['sha256'],
            bytes=len(raw), preimage_recoverable_from_immutable_input=True,
            one_exact_editable_final_authorized=True, semantic_edits_by_root=0,
            review_complete=False, root_approved=False, cache_admitted=False)))
    assert_no_protected_opens()
    for output, raw, _ in prepared:
        with output.open('xb') as stream:
            stream.write(raw)
    receipt = dict(status='EXACT_PINNED_EDITABLE_FINALS_PREPARED_NO_SEMANTIC_EDITS',
        configuration=dict(path=str(config_path.relative_to(ROOT)),
                           sha256=hashlib.sha256(config_raw).hexdigest().upper()),
        rows=[row for _, _, row in prepared], extra_intermediate_corpus_copies=0,
        original_or_existing_candidate_writes=0, protected_payload_opens=0,
        goal_complete=False, training_authorized=False)
    with receipt_path.open('xb') as stream:
        stream.write((json.dumps(receipt, ensure_ascii=False, indent=2) + chr(10)).encode())
    print(json.dumps(dict(status=receipt['status'], authors=len(prepared),
                         final_bytes=sum(len(raw) for _,raw,_ in prepared),
                         receipt=str(receipt_path.relative_to(ROOT))), ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
