"""Independently audit the literal information retained by every rule27 delta.

This verifier does not call the alias-edit helper for its preservation proof.
Only an actually empty appendix at EOF may remove words. Elsewhere, the full
ordered character stream must survive after ignoring whitespace and optional
alias delimiters. Populated names, dates, descriptions and other punctuation
remain in that stream. Existing code and numeric guards are checked separately.
This is a rule-class audit, not a claim of individual human full-text reading.
"""
from collections import Counter
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(AUDIT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from numeric_atom_integrity_v1 import numeric_atom_changes
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v27 as policy

EMPTY_APPENDIX_HEADINGS = frozenset({
    'external links', 'further reading', 'references', 'see also', 'table of contents',
    '각주', '같이 보기', '내용주', '더 보기', '더보기', '외부 링크', '외부링크',
    '주석', '주해', '참고 문헌', '참고 자료', '참고문헌', '참고자료', '참조주', '출처',
})
IGNORABLE_ALIAS_DELIMITERS = frozenset('(),，;；')


def literal_stream(text):
    return ''.join(char for char in text if not char.isspace() and char not in IGNORABLE_ALIAS_DELIMITERS)


def empty_eof_appendix(text):
    lines = text.splitlines(keepends=True)
    index, removed = len(lines), []
    while index:
        line = lines[index - 1]
        label = ' '.join(line.strip().split()).casefold()
        if not label:
            index -= 1
        elif label in EMPTY_APPENDIX_HEADINGS:
            removed.append(dict(line=index, label=label))
            index -= 1
        else:
            break
    return ''.join(lines[:index]).rstrip(), list(reversed(removed))


def evaluate(original, candidate):
    source, empty_headings = empty_eof_appendix(original)
    target, target_headings = empty_eof_appendix(candidate)
    source_literal, target_literal = literal_stream(source), literal_stream(target)
    # A candidate may not keep populated text after the removed source EOF
    # headings, and a candidate heading left at EOF is not a new invention.
    guards = dict(
        all_populated_characters_in_source_order=source_literal == target_literal,
        numeric_atoms=not numeric_atom_changes(original, candidate),
        code=policy.code_preserved(original, candidate),
        unicode=policy.unicode_examples_preserved(original, candidate),
        style=policy.semantic_style_preserved(original, candidate),
        ordered=policy.ordered_deletion(original, candidate),
        no_memo=not bool(inv.corpus.MEMOS.search(candidate)),
    )
    spans = []
    if not guards['all_populated_characters_in_source_order']:
        for tag, a, b, c, d in difflib.SequenceMatcher(None, source_literal, target_literal, autojunk=False).get_opcodes():
            if tag != 'equal':
                spans.append(dict(operation=tag, source_interval=[a,b], candidate_interval=[c,d],
                    source_characters=b-a, candidate_characters=d-c))
    return dict(guards=guards, eligible_narrow_literal_delta=all(guards.values()),
        source_populated_stream_sha256=inv.sha(source_literal),
        candidate_populated_stream_sha256=inv.sha(target_literal),
        source_empty_eof_appendix_headings=empty_headings,
        candidate_empty_eof_appendix_headings=target_headings, other_literal_changes=spans)


def run():
    activate(); guard=checked_contract(); pins={}
    census_path=AUDIT/'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json'
    census=json.loads(census_path.read_bytes())
    assert inv.file_sha(census_path)=='0BBAF7B7B05B9F922ED780BA75A1529018934ADB0B899375E2C760F0194A40C6'
    pins[str(census_path.relative_to(ROOT))]=inv.file_sha(census_path)
    for name, expected in census['input_pins'].items():
        assert inv.file_sha(ROOT/name)==expected,name
    directory=ROOT/census['metadata_directory']; inv.verify(directory,census['metadata_manifest'])
    counts=Counter(); weights=Counter(); rows=[]
    for row in inv.cache.rows(directory,census['metadata_manifest']):
        if not row['eligible_rule_candidate']:
            continue
        assert row['id'] not in guard['restricted_ids']
        source_pin=row['original']; assert source_pin['sha256'] not in guard['restricted_hashes']
        path=(ROOT/source_pin['path']).resolve()
        assert path.is_relative_to(inv.BASE) and not path.is_symlink()
        raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest().upper()==source_pin['sha256']
        original=raw.decode('utf-8')
        result=policy.propose(dict(id=row['id'],text=original,complete_eos=True,valid_utf8=True))
        candidate=result.get('candidate',result['text'])
        assert result['decision']==row['proposed_decision'] and inv.sha(candidate)==row['proposed_body_sha256']
        proof=evaluate(original,candidate)
        outcome='LITERAL_DELTA_VERIFIED' if proof['eligible_narrow_literal_delta'] else 'REQUIRES_SEPARATE_CONTEXT_REVIEW'
        counts[outcome]+=1; weights[outcome]+=row['occurrences']
        rows.append(dict(id=row['id'],original=source_pin,occurrences=row['occurrences'],
            proposed_body_sha256=row['proposed_body_sha256'],outcome=outcome,**proof,
            individual_human_full_text_read_claimed=False,root_approved=False,cache_admitted=False))
    assert len(rows)==478
    assert_no_protected_opens()
    pins[str(Path(__file__).relative_to(ROOT))]=inv.file_sha(Path(__file__))
    result=dict(status='RULE27_ALL_CANDIDATE_LITERAL_DELTA_AUDIT_NOT_ADMISSION',
        candidates=len(rows),counts=dict(counts),position_weights=dict(weights),rows=rows,input_pins=pins,
        copied_original_or_candidate_payload_bytes=0,automatic_root_admissions=0,
        individual_human_full_text_read_claimed=False,goal_complete=False,training_authorized=False)
    inv.write_json(AUDIT/'RULE27_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json',result)
    print(json.dumps({k:result[k] for k in ['status','candidates','counts','position_weights','automatic_root_admissions']},ensure_ascii=False))


if __name__=='__main__':
    run()
