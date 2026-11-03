"""Read back every exact choice under the actual cache engine's body guards."""
from collections import Counter
from pathlib import Path
import argparse
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_reviewed_cache_v2 as reviewed
from scripts import p106b_hold_resolution_policy_v26 as policy
sys.path.insert(0,str(AUDIT))
import guarded_reviewed_cache_v3 as guarded
import exact_runtime_pair_guard_v1 as exact


def audit(selection, output):
    inv.require(not output.exists(), 'new immutable guard receipt required')
    document = inv.cache.read(selection)
    contract_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
    protected = set(inv.cache.read(contract_path)['restricted_hashes'])
    cases = reviewed.literal.load_registry()
    instance = guarded.GuardedResolutionEngine.__new__(guarded.GuardedResolutionEngine)
    instance.exact_cases = exact.load_registry()
    instance.literal_cases = cases
    from types import SimpleNamespace
    instance.guard = SimpleNamespace(phonetic_case=guarded.phonetic_case())
    reviewed_holds = guarded.hold_cases()
    records, counts, pins = [], Counter(), {}
    started = last = time.monotonic()

    def pin(name, expected):
        if name not in pins:
            pins[name] = inv.file_sha(ROOT/name)
        inv.require(pins[name] == expected, 'exact selection artifact changed: '+name)

    for selected in document['rows']:
        ident = selected['id']
        key = selected['original_text_sha256']
        choice = selected['selected']
        record = dict(id=ident, original_text_sha256=key, decision=choice['decision'],
                      clean_text_sha256=choice.get('clean_text_sha256'))
        counts['sources'] += 1
        if choice['decision'] == 'EXCLUDE':
            records.append(dict(record, explicit_exclusion=True, original_body_opened=False))
            counts['explicit_exclusions'] += 1
            continue
        if choice['decision'] == 'HOLD':
            case = reviewed_holds[key]
            inv.require(case['id'] == ident and choice.get('content_reviewed') is True and choice.get('hold_review_evidence') == case['authority_pin'] and not choice.get('body') and not choice.get('clean_text_sha256'), 'reviewed HOLD lacks exact evidence or leaks a body')
            records.append(dict(record, reviewed_nonadmission=True, original_body_opened=False))
            counts['reviewed_nonadmissions'] += 1
            continue
        pin(choice['body'], choice['clean_text_sha256'])
        clean = (ROOT/choice['body']).read_text(encoding='utf-8')
        if key in protected:
            view = choice.get('compare_source')
            inv.require(view and choice['decision']=='EDIT', 'restricted selection lacks exact safe-view EDIT')
            pin(view['path'], view['sha256'])
            source = view['path']
            original = (ROOT/source).read_text(encoding='utf-8')
            runtime_pass = reviewed.final.engine.policy.code_preserved(original,clean) and \
                reviewed.final.engine.policy.unicode_examples_preserved(original,clean)
            record.update(original_body_opened=False, restricted_safe_source_view=view)
        else:
            sources = [choice['original']['path']]
            inv.require(sources, 'ordinary selection lacks original source pin')
            source = sources[0]
            pin(source,key)
            original = (ROOT/source).read_text(encoding='utf-8')
            instance.current = (dict(id=ident,text=original),3)
            runtime_pass = instance.code_guard(original,clean,dict(literal_guard_case_id=ident,exact_runtime_pair_id=ident,phonetic_stress_pair_id=ident))
            record['original_body_opened'] = True
        inv.require(inv.sha(clean)==choice['clean_text_sha256'], 'clean UTF-8 identity differs')
        style = policy.semantic_style_preserved(original,clean)
        memo = bool(inv.corpus.MEMOS.search(clean))
        record.update(body=choice['body'], original_comparison_source=source,
            runtime_code_and_unicode_pass=runtime_pass, semantic_style_pass=style,
            editor_memo_present=memo, original_characters=len(original), clean_characters=len(clean),
            ordered_source_deletion=policy.ordered_deletion(original,clean),
            exact_literal_case=ident if ident in cases and reviewed.literal.exact_pair_preserved(original,clean,ident,cases) else None)
        for label, value in [('runtime_guard_failure',not runtime_pass),('style_flag',not style),
                             ('memo_flag',memo),('ordered_flag',not record['ordered_source_deletion'])]:
            counts[label] += value
        counts['bodies_checked'] += 1
        records.append(record)
        if time.monotonic()-last > 15:
            print(json.dumps(dict(phase='exact_body_runtime_guards',counts=dict(counts))),flush=True)
            last=time.monotonic()
    for name,expected in pins.items():
        inv.require(inv.file_sha(ROOT/name)==expected,'body changed during guard audit')
    for path in [selection,contract_path,Path(__file__)]:
        pins[str(path.relative_to(ROOT))]=inv.file_sha(path)
    result=dict(status='EXACT_SELECTION_RUNTIME_GUARDS_CHECKED_NOT_CACHE_OR_SEMANTIC_COMPLETION',
        counts=dict(counts), records=records,input_pins=pins, seconds=time.monotonic()-started,
        full_restricted_original_bodies_opened=False, cache_admitted=0, goal_complete=False,training_authorized=False)
    inv.require(len(json.dumps(result,ensure_ascii=False).encode())<20_000_000,'audit needs ordered shards')
    inv.write_json(output,result)
    print(json.dumps(dict(counts=result['counts'],seconds=result['seconds'])),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    audit(args.selection.resolve(),args.output.resolve())
