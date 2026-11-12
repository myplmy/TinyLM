"""Reuse human-authored bodies and prove only literal empty-footer deltas."""
from pathlib import Path
from collections import Counter
import argparse
import json
import re
import sys
import time

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from verify_rule27_literal_delta_v1 import literal_stream,empty_eof_appendix
from verify_event_metadata_literal_delta_v1 import last_paragraph,explicit_events
from verify_category_metadata_delta_v1 import category_markers
from numeric_atom_integrity_v1 import numeric_atom_changes
from authored_literal_readiness_v1 import deferrals
from close_remaining_heading_context_v1 import remaining_headings
from scripts import p106b_hold_resolution_policy_v32 as policy


def preservation(original,body):
    a,a_heads=empty_eof_appendix(original)
    b,b_heads=empty_eof_appendix(body)
    basis='ACTUAL_EMPTY_SOURCE_EOF_HEADERS_ONLY'
    original_suffix=body_suffix=None
    typed=True
    if literal_stream(a)!=literal_stream(b):
        before,original_suffix=last_paragraph(original)
        after,body_suffix=last_paragraph(body)
        before,a_heads=empty_eof_appendix(before)
        after,b_heads=empty_eof_appendix(after)
        typed=bool(category_markers(original_suffix) or explicit_events(original_suffix))
        a=before+chr(10)*2+original_suffix
        b=after+chr(10)*2+body_suffix
        basis='EMPTY_EOF_PREFIX_HEADERS_BEFORE_INDEPENDENT_LITERAL_TYPED_METADATA'
    source,target=literal_stream(a),literal_stream(b)
    guards=dict(all_populated_characters_in_source_order=source==target,
        independent_metadata_boundary=typed,
        exact_metadata_values_preserved=original_suffix==body_suffix,
        numeric_atoms=not numeric_atom_changes(original,body),
        code=policy.code_preserved(original,body),unicode=policy.unicode_examples_preserved(original,body),
        style=policy.semantic_style_preserved(original,body),ordered=policy.ordered_deletion(original,body),
        no_memo=not bool(guard.inv.corpus.MEMOS.search(body)))
    return dict(guards=guards,eligible_narrow_literal_delta=all(guards.values()),comparison_basis=basis,
        source_populated_stream_sha256=guard.inv.sha(source),candidate_populated_stream_sha256=guard.inv.sha(target),
        source_empty_eof_appendix_headings=a_heads,candidate_empty_eof_appendix_headings=b_heads,
        production_metadata_boundary_prove_called=False)


def run(config_path):
    guard.activate();started=time.monotonic();pins={}
    config=json.loads(config_path.read_bytes())

    def read(pin):
        path=ROOT/pin['path']
        assert not path.is_symlink() and guard.inv.file_sha(path)==pin['sha256']
        pins[pin['path']]=pin['sha256']
        return json.loads(path.read_bytes())

    profile=read(config['profile'])
    runtime=read(config['runtime_basis'])
    for name,sha in runtime['input_pins'].items():
        path=ROOT/name
        assert not path.is_symlink() and guard.inv.file_sha(path)==sha,name
        pins[name]=sha
    old_readiness=read(config['prior_context_deferrals'])
    explicit={row['id']:[reason for reason in row['reasons'] if reason.startswith('ROOT_OBSERVED_')]
              for row in old_readiness['deferred_rows']}
    directory=ROOT/profile['metadata_directory']
    guard.inv.verify(directory,profile['metadata_manifest'])
    checks=[];deferred=[];reasons=Counter();types=Counter()
    for row in guard.inv.cache.rows(directory,profile['metadata_manifest']):
        if row['remaining_deferrals'] or row['remaining_headings']:
            continue
        if row['delta']['kind'] not in {'EXISTING_LITERAL_EQUAL','SOURCE_WORD_DELETIONS_ONLY',
                                     'WORD_ATOMS_IDENTICAL_ONLY_OTHER_CHARACTERS_DIFFER'}:
            continue
        guard.require_payload_context(dict(source_id=row['id'],original=row['original'],candidate=row['body']))
        values=[]
        for name in ['original','body']:
            path=ROOT/row[name]['path']
            assert not path.is_symlink() and path.resolve().is_relative_to(guard.inv.BASE)
            raw=path.read_bytes();value=raw.decode('utf-8')
            assert guard.inv.sha(value)==row[name]['sha256']
            values.append(value)
        proof=preservation(*values)
        failed=[name for name,passed in proof['guards'].items() if not passed]
        failed+=deferrals(values[1])+policy.literal_holes(values[1])
        failed+=['REMAINING_CONTENT_HEADING:'+value for value in remaining_headings(values[1])]
        failed+=explicit.get(row['id'],[])
        if failed:
            deferred.append(dict(id=row['id'],original_text_sha256=row['original']['sha256'],
                body=row['body'],occurrences=row['occurrences'],reasons=sorted(set(failed))))
            reasons.update(set(failed));continue
        for item in row['all_reviews']:
            assert guard.inv.file_sha(ROOT/item['path'])==item['sha256']
        types[proof['comparison_basis']]+=1
        checks.append(dict(id=row['id'],original=row['original'],original_text_sha256=row['original']['sha256'],
            body=dict(row['body'],bytes=len(values[1].encode('utf-8'))),
            decision='KEEP' if values[0]==values[1] else 'EDIT',occurrences=row['occurrences'],
            primary_review=row['primary_review'],primary_source_cohort=row['primary_cohort'],
            reason=row['reason'],all_saved_reviews=row['all_reviews'],
            full_source_read_by_primary_author_claimed=True,additional_human_full_text_read_claimed=False,
            fresh_preservation_proof=proof,additional_readiness_guards=dict(
                no_native_or_formal_gap=True,no_unfinished_prose_flag=True,no_unfilled_content_heading=True,
                no_explicit_ROOT_context_deferral=True,existing_saved_bodies_agree=True)))
    guard.assert_no_protected_opens()
    for path in [config_path,Path(__file__),guard.CONTRACT,AUDIT/'active_guard_v6_preflight_v1.py',
        AUDIT/'AUTHORED_LITERAL_METADATA_EXTENSION_F3_F4_V1.md',AUDIT/'AUTHORED_LITERAL_METADATA_TESTS_V1.log',
        AUDIT/'verify_rule27_literal_delta_v1.py',AUDIT/'verify_event_metadata_literal_delta_v1.py',
        AUDIT/'verify_category_metadata_delta_v1.py',AUDIT/'authored_literal_readiness_v1.py',
        AUDIT/'close_remaining_heading_context_v1.py',AUDIT/'numeric_atom_integrity_v1.py']:
        pins[str(path.relative_to(ROOT))]=guard.inv.file_sha(path)
    report=dict(status='AUTHORED_LITERAL_METADATA_ALL_ROW_READY_PENDING_ROOT_CONTEXT',
        candidates=len(checks)+len(deferred),verified=len(checks),verified_positions=sum(r['occurrences'] for r in checks),
        deferred=len(deferred),deferral_reason_counts=dict(reasons),proof_basis_counts=dict(types),
        checks=checks,deferred_rows=deferred,input_pins=pins,cumulative_guard_sha256=guard.EXPECTED,
        protected_payload_open_attempts=0,corpus_payload_copies_written=0,additional_human_full_read_credit=0,
        elapsed_seconds=time.monotonic()-started,root_approved=False,cache_admitted=False,
        goal_complete=False,training_authorized=False)
    path=AUDIT/config['output'];assert not path.exists();guard.inv.write_json(path,report)
    print(json.dumps({k:v for k,v in report.items() if k not in {'checks','deferred_rows','input_pins'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
    path=Path(args.config).resolve();assert path.parent==AUDIT and not path.is_symlink()
    run(path)
