"""Independent line-boundary proof: keep every metadata value and body character."""
from pathlib import Path
import argparse
import hashlib
import importlib
import json
import re
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from scripts import p106b_hold_resolution_inventory as inv

OLD=AUDIT/'verify_rule27_literal_delta_v1.py'
assert inv.file_sha(OLD)=='ECF8B7F4F3B325FAFDB67AAC87C9D7DE5FACE18BCF34B4E55A4599759778B331'
import verify_rule27_literal_delta_v1 as literal


def last_paragraph(text):
    # Deliberately use line positions, not the production BLOCK or prove().
    lines=text.splitlines(keepends=True)
    end=len(lines)
    while end and not lines[end-1].strip():
        end-=1
    start=end
    while start and lines[start-1].strip():
        start-=1
    return ''.join(lines[:start]), ''.join(lines[start:end]).rstrip(chr(13)+chr(10))


def explicit_events(suffix):
    records=[]
    for line in suffix.splitlines():
        match=re.fullmatch(r'[ \t]*([12][0-9]{3})년[ _]+(설립|설치|폐지|해체)[ \t]*',line)
        if match:
            records.append((int(match[1]),match[2]))
    starts=[year for year,kind in records if kind in {'설립','설치'}]
    ends=[year for year,kind in records if kind in {'폐지','해체'}]
    return bool(starts and ends and max(starts)<=min(ends) and len(suffix.splitlines())>=3)


def evaluate(original,candidate):
    source_prefix,source_suffix=last_paragraph(original)
    target_prefix,target_suffix=last_paragraph(candidate)
    stripped_source,source_heads=literal.empty_eof_appendix(source_prefix)
    stripped_target,target_heads=literal.empty_eof_appendix(target_prefix)
    a=literal.literal_stream(stripped_source+chr(10)*2+source_suffix)
    b=literal.literal_stream(stripped_target+chr(10)*2+target_suffix)
    base=literal.evaluate(original,candidate)
    guards=dict(base['guards'],all_populated_characters_in_source_order=a==b,
                exact_metadata_values_preserved=source_suffix==target_suffix,
                independent_explicit_event_pair=explicit_events(source_suffix))
    return dict(guards=guards,eligible_narrow_literal_delta=all(guards.values()),
                source_populated_stream_sha256=inv.sha(a),candidate_populated_stream_sha256=inv.sha(b),
                source_empty_eof_appendix_headings=source_heads,
                candidate_empty_eof_appendix_headings=target_heads,
                metadata_sha256=inv.sha(source_suffix),
                other_literal_changes=[] if a==b else ['POPULATED_CHARACTER_STREAM_DIFFERS'],
                production_metadata_prove_called=False)


def run(census_path,output_path):
    activate()
    guard=checked_contract()
    raw=census_path.read_bytes()
    census=json.loads(raw)
    for name,expected in census['input_pins'].items():
        assert inv.file_sha(ROOT/name)==expected,name
    config=json.loads((ROOT/next(name for name in census['input_pins'] if name.endswith('_CONFIG.json'))).read_bytes())
    policy=importlib.import_module(config['proposed_policy'])
    directory=ROOT/census['metadata_directory']
    inv.verify(directory,census['metadata_manifest'])
    rows=[]
    for row in inv.cache.rows(directory,census['metadata_manifest']):
        if not row['eligible_rule_candidate']:
            continue
        assert row['id'] not in guard['restricted_ids']
        assert row['original']['sha256'] not in guard['restricted_hashes']
        path=(ROOT/row['original']['path']).resolve()
        assert path.is_relative_to(inv.BASE) and not path.is_symlink()
        original_raw=path.read_bytes()
        assert hashlib.sha256(original_raw).hexdigest().upper()==row['original']['sha256']
        original=original_raw.decode('utf-8')
        proposed=policy.propose(dict(id=row['id'],text=original,complete_eos=True,valid_utf8=True))
        candidate=proposed.get('candidate',proposed['text'])
        assert proposed['decision']==row['proposed_decision']
        assert inv.sha(candidate)==row['proposed_body_sha256']
        proof=evaluate(original,candidate)
        rows.append(dict(id=row['id'],original=row['original'],occurrences=row['occurrences'],
            proposed_body_sha256=row['proposed_body_sha256'],**proof,
            individual_human_full_text_read_claimed=False,root_approved=False,cache_admitted=False))
    assert len(rows)==census['counts']['new_terminal_candidates']
    assert_no_protected_opens()
    passed=[r for r in rows if r['eligible_narrow_literal_delta']]
    result=dict(status='ALL_EVENT_METADATA_DELTAS_INDEPENDENT_LITERAL_AUDIT_NOT_ADMISSION',
        candidates=len(rows),verified=len(passed),requires_context=len(rows)-len(passed),
        verified_positions=sum(r['occurrences'] for r in passed),rows=rows,
        input_pins={str(census_path.relative_to(ROOT)):inv.file_sha(census_path),
                    str(Path(__file__).relative_to(ROOT)):inv.file_sha(Path(__file__)),
                    str(OLD.relative_to(ROOT)):inv.file_sha(OLD)},
        copied_payload_bytes=0,automatic_root_admissions=0,goal_complete=False,training_authorized=False)
    with output_path.open('xb') as stream:
        stream.write((json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode())
    print(json.dumps({k:v for k,v in result.items() if k not in {'rows','input_pins'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--census',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    paths=[Path(p).resolve() for p in [args.census,args.output]]
    assert all(p.parent==AUDIT and not p.is_symlink() for p in paths)
    assert not paths[1].exists()
    run(*paths)
