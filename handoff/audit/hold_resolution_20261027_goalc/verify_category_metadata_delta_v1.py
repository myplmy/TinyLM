"""Independent literal/category-tail and remaining-body checks; never store bodies."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import importlib
import json
import re
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from scripts import p106b_hold_resolution_metadata_v4 as content_stubs
from authored_literal_readiness_v1 import deferrals as authored_deferrals

FROZEN=AUDIT/'verify_event_metadata_literal_delta_v1.py'
assert guard.inv.file_sha(FROZEN)=='DDB9D878E91AC0536DDFA4919A83874DE58396F3FE2B555EF994957777889DE1'
import verify_event_metadata_literal_delta_v1 as literal


def category_markers(suffix):
    values=[v.strip() for v in suffix.splitlines() if v.strip()]
    if len(values)<2 or any(len(v)>100 or re.search(r'[.!?。《》\[\]<>`{}=\"\'‘’“”]',v) for v in values):
        return False
    # Independent lexical roles, not production CATEGORY/prove().
    nominal={v for v in values if re.fullmatch(r'.+의[ _]+[^.!?]+',v)
        or re.fullmatch(r'.+(?:학교|대학|대학교)[ _]*동문',v)
        or re.fullmatch(r'[가-힣]+계[ _]*[가-힣]+인',v)
        or re.fullmatch(r'.+[ _]+출신(?:[ _]+인물)?',v)
        or re.fullmatch(r'[0-9]+세기[ _]+.+사람',v)}
    birth=any(re.fullmatch(r'[12][0-9]{2,3}(?:년대|년)[ _]+출생',v) for v in values)
    end=any(re.fullmatch(r'[12][0-9]{2,3}년[ _]+사망|살아있는[ _]+사람',v) for v in values)
    return len(nominal)>=2 or bool(birth and end and nominal)


def context_deferrals(candidate):
    prefix,_suffix=literal.last_paragraph(candidate)
    reasons=[value for value in authored_deferrals(prefix)
             if value!='POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT']
    # A separately typed category block and a noun-only list are not prose.
    # A sentence-bearing paragraph with an unfinished Hangul tail remains held.
    for block in re.split(r'\n\s*\n',prefix):
        value=block.strip()
        if (len(value)>=70 and len(value.split())>=8 and re.search(r'[.!?。]',value)
                and re.search(r'[가-힣]$',value)
                and not re.search(r'(?:다|음|임|함|됨|있음|없음|하기|한다|이다)$',value)):
            reasons.append('POSSIBLE_UNFINISHED_SENTENCE_PARAGRAPH_NEEDS_CONTEXT')
            break
    if content_stubs.empty_content_headings(prefix) or content_stubs.empty_content_headings(candidate):
        reasons.append('UNFILLED_CONTENT_HEADING_REMAINS')
    return sorted(set(reasons))


def evaluate(original,candidate,decision):
    proof=literal.evaluate(original,candidate)
    guards=dict(proof['guards'])
    guards.pop('independent_explicit_event_pair')
    _prefix,suffix=literal.last_paragraph(original)
    reasons=context_deferrals(candidate)
    guards.update(independent_literal_category_markers=category_markers(suffix),
        actual_terminal_body_contract=(original!=candidate if decision=='EDIT' else original==candidate if decision=='KEEP' else False),
        remaining_body_context_gates=not reasons)
    return dict(proof,guards=guards,eligible_narrow_literal_delta=all(guards.values()),
        context_deferrals=reasons,independent_verifier_does_not_call_production_category_prove=True)


def run(config_path,census_path,output_path):
    guard.activate()
    config=json.loads(config_path.read_bytes())
    census=json.loads(census_path.read_bytes())
    assert census['input_pins'][str(config_path.relative_to(ROOT))]==guard.inv.file_sha(config_path)
    for name,sha in census['input_pins'].items():
        assert guard.inv.file_sha(ROOT/name)==sha,name
    module_name=config['proposed_policy']
    assert module_name.startswith('scripts.p106b_hold_resolution_policy_v')
    policy=importlib.import_module(module_name)
    directory=ROOT/census['metadata_directory']
    guard.inv.verify(directory,census['metadata_manifest'])
    rows=[]
    failures=Counter()
    for row in guard.inv.cache.rows(directory,census['metadata_manifest']):
        if not row['eligible_rule_candidate']:
            continue
        guard.require_payload_context(dict(source_id=row['id'],original=row['original'],candidate=row['prior_candidate']))
        path=ROOT/row['original']['path']
        assert not path.is_symlink() and path.resolve().is_relative_to(guard.inv.BASE)
        raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper()==row['original']['sha256']
        original=raw.decode('utf-8')
        proposed=policy.propose(dict(id=row['id'],text=original,complete_eos=True,valid_utf8=True))
        candidate=proposed.get('candidate',proposed['text'])
        assert proposed['decision']==row['proposed_decision']
        assert guard.inv.sha(candidate)==row['proposed_body_sha256']
        proof=evaluate(original,candidate,proposed['decision'])
        failures.update(k for k,v in proof['guards'].items() if not v)
        rows.append(dict(id=row['id'],original=row['original'],occurrences=row['occurrences'],
            proposed_body_sha256=row['proposed_body_sha256'],proposed_decision=proposed['decision'],**proof,
            individual_human_full_text_read_claimed=False,root_approved=False,cache_admitted=False))
    assert len(rows)==census['counts']['new_terminal_candidates']
    guard.assert_no_protected_opens()
    good=[r for r in rows if r['eligible_narrow_literal_delta']]
    report=dict(status='CATEGORY_METADATA_ALL_ROW_LITERAL_AND_REMAINING_BODY_AUDIT_NOT_ADMISSION',
        candidates=len(rows),verified=len(good),requires_context=len(rows)-len(good),
        verified_positions=sum(r['occurrences'] for r in good),guard_failures=dict(failures),rows=rows,
        input_pins={str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in
            [Path(__file__),config_path,census_path,FROZEN,guard.CONTRACT,
             AUDIT/'authored_literal_readiness_v1.py',AUDIT/'CATEGORY_METADATA_DELTA_TESTS_V1.log']},
        protected_payload_open_attempts=0,copied_payload_bytes=0,automatic_root_admissions=0,
        goal_complete=False,training_authorized=False)
    assert not output_path.exists()
    payload=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
    assert len(payload)<20_000_000
    with output_path.open('xb') as stream:
        stream.write(payload)
    print(json.dumps({k:v for k,v in report.items() if k not in {'rows','input_pins'}}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--census',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    paths=[Path(v).resolve() for v in [args.config,args.census,args.output]]
    assert all(p.parent==AUDIT and not p.is_symlink() for p in paths)
    run(*paths)
