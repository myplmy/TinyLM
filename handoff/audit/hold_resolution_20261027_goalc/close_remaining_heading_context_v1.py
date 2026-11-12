"""Add discovered content-heading counterexamples to existing literal proofs."""
from pathlib import Path
from collections import Counter
import argparse
import importlib
import json
import re
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from verify_event_metadata_literal_delta_v1 import last_paragraph
from scripts.p106b_hold_resolution_metadata_v4 import empty_content_headings

EXTRA_HEADS={re.sub(r'\s+','',value) for value in [
    '운항 노선','화물 노선','갤러리','작품 연보','기후','사진']}


def remaining_headings(text):
    prefix,_suffix=last_paragraph(text)
    found=set(empty_content_headings(prefix)+empty_content_headings(text))
    for block in re.split(r'\n\s*\n',prefix):
        lines=[line.strip() for line in block.splitlines() if line.strip()]
        if lines and all(re.sub(r'\s+','',line) in EXTRA_HEADS for line in lines):
            found.update(lines)
    return sorted(found)


def run(config_path):
    guard.activate()
    config=json.loads(config_path.read_bytes())
    inputs={str(config_path.relative_to(ROOT)):guard.inv.file_sha(config_path)}
    for item in config['inputs'].values():
        path=ROOT/item['path']
        assert not path.is_symlink() and guard.inv.file_sha(path)==item['sha256']
        inputs[item['path']]=item['sha256']
    proof=json.loads((ROOT/config['inputs']['literal']['path']).read_bytes())
    census=json.loads((ROOT/config['inputs']['census']['path']).read_bytes())
    policy=importlib.import_module(config['policy'])
    directory=ROOT/census['metadata_directory']
    guard.inv.verify(directory,census['metadata_manifest'])
    corpus={row['id']:row for row in guard.inv.cache.rows(directory,census['metadata_manifest'])
            if row['eligible_rule_candidate']}
    assert len(corpus)==len(proof['rows'])==config['expected_candidates']
    rows=[]
    heads=Counter()
    for previous in proof['rows']:
        row=corpus[previous['id']]
        assert previous['original']==row['original']
        guard.require_payload_context(dict(source_id=row['id'],original=row['original'],candidate=row['prior_candidate']))
        path=ROOT/row['original']['path']
        assert not path.is_symlink() and path.resolve().is_relative_to(guard.inv.BASE)
        raw=path.read_bytes()
        assert guard.inv.sha(raw.decode('utf-8'))==row['original']['sha256']
        proposed=policy.propose(dict(id=row['id'],text=raw.decode('utf-8'),complete_eos=True,valid_utf8=True))
        candidate=proposed.get('candidate',proposed['text'])
        assert proposed['decision']==row['proposed_decision']
        assert guard.inv.sha(candidate)==row['proposed_body_sha256']==previous['proposed_body_sha256']
        findings=remaining_headings(candidate)
        heads.update(findings)
        rows.append(dict(id=row['id'],original=row['original'],occurrences=row['occurrences'],
            proposed_body_sha256=row['proposed_body_sha256'],proposed_decision=row['proposed_decision'],
            prior_literal_eligible=previous['eligible_narrow_literal_delta'],remaining_content_headings=findings,
            eligible=previous['eligible_narrow_literal_delta'] and not findings,
            individual_human_full_text_read_claimed=False,root_adopted=False,cache_admitted=False))
    lookup={row['id']:row for row in rows}
    assert all(not lookup[ident]['eligible'] for ident in config['required_negative_ids'])
    assert all(lookup[ident]['eligible'] for ident in config['required_positive_ids'])
    guard.assert_no_protected_opens()
    good=[row for row in rows if row['eligible']]
    for path in [Path(__file__),AUDIT/'REMAINING_HEADING_CONTEXT_F3_F4_V1.md',
                 AUDIT/'REMAINING_HEADING_CONTEXT_TESTS_V1.log',guard.CONTRACT]:
        inputs[str(path.relative_to(ROOT))]=guard.inv.file_sha(path)
    output=AUDIT/config['output']
    assert not output.exists()
    report=dict(status='ADDITIONAL_CONTENT_CONTEXT_CLOSURE_NOT_ADMISSION',
        candidates=len(rows),verified=len(good),verified_positions=sum(r['occurrences'] for r in good),
        requires_context=len(rows)-len(good),newly_deferred=sum(r['prior_literal_eligible'] and not r['eligible'] for r in rows),
        remaining_heading_counts=dict(heads),rows=rows,input_pins=inputs,
        protected_payload_open_attempts=0,copied_payload_bytes=0,automatic_root_admissions=0,
        individual_human_full_text_read_credit=0,goal_complete=False,training_authorized=False)
    guard.inv.write_json(output,report)
    print(json.dumps({k:v for k,v in report.items() if k not in {'rows','input_pins'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    args=parser.parse_args()
    path=Path(args.config).resolve()
    assert path.parent==AUDIT and not path.is_symlink()
    run(path)
