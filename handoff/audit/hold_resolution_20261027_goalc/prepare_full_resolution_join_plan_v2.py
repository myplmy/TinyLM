"""Join the full verified draft and exact authored choices without admission."""
from collections import Counter
from pathlib import Path
import argparse
import json
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as metadata


def prepare(selection, name):
    inv.require(name.isascii() and name.replace('_','').isalnum(), 'safe version name required')
    output = inv.BASE/name
    inv.require(not output.exists(), 'new immutable whole-scope plan required')
    draft_path = inv.BASE/'draft_proposals_v26_delta_v1/complete.json'
    draft = inv.cache.read(draft_path)
    contract_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
    contract = inv.cache.read(contract_path)
    protected = set(contract['restricted_hashes'])
    evidence_path = AUDIT/'DRAFT_V26_DELTA_EXECUTION_RECEIPT_V1.json'
    evidence = inv.cache.read(evidence_path)
    inv.require(evidence['completed_artifact']['sha256'] == inv.file_sha(draft_path), 'verified26 draft changed')
    for path, expected in draft['lineage']['source_code_sha256'].items():
        inv.require(inv.file_sha(ROOT/path) == expected, 'frozen proposal code changed')
    selection_document = inv.cache.read(selection)
    inv.require(selection_document['unresolved_sources'] == 0, 'exact authored choices must be joined')
    authored = {}
    for source in selection_document['rows']:
        key = source['original_text_sha256']
        choice = source['selected']
        if key in authored:
            old = authored[key]['selected']
            inv.require((old['decision'],old.get('clean_text_sha256')) ==
                        (choice['decision'],choice.get('clean_text_sha256')), 'one raw source has different choices')
        else:
            authored[key] = source
    directory = draft_path.parent/'unique'
    inv.verify(directory,draft['unique_manifest'])
    inv.verify(draft_path.parent/'occurrences',draft['occurrence_manifest'])
    writer = inv.ShardWriter(output/'records','decisions',limit=19_999_999)
    outcomes, counts, groups = {}, Counter(), Counter()
    pending_reasons = Counter()
    started = time.monotonic()
    protected_projected = []
    for shard in draft['unique_manifest']['shards']:
        with (directory/shard['path']).open('rb') as stream:
            for line in stream:
                hashes = metadata.SOURCE_SHA.findall(line)
                inv.require(len(hashes) == 1, 'draft needs exactly one source SHA')
                key = hashes[0].decode('ascii').upper()
                if key in protected:
                    # The diagnostic/source candidate is skipped as opaque bytes.
                    fields = metadata.FIELDS | {'occurrences','decision','reasons','rules'}
                    with patch.object(metadata,'FIELDS',fields):
                        row = metadata.project_metadata(line)
                    inv.require(row['decision'] == 'PENDING' and row['id'] in contract['trusted_metadata'],
                                'restricted proposal cannot be inherited as an automatic body')
                    protected_projected.append(row['id'])
                else:
                    row = json.loads(line)
                inv.require(key == row['original_text_sha256'] and key not in outcomes, 'draft source identity repeats')
                keys = ['id','source','split','source_ids','source_ids_sha256','original_text_sha256',
                        'input_ids','language_bucket','occurrences']
                record = {field:row[field] for field in keys}
                choice_source = authored.get(key)
                if choice_source is not None:
                    choice = choice_source['selected']
                    decision = choice['decision']
                    group = 'EXACT_AUTHORED_SOURCE_BODY_CHOICE_PENDING_ROOT_CLOSURE'
                    reason = 'EXACT_SOURCE_CONTEXT_REVIEW_AND_ROOT_MEDIATION'
                    if decision in {'KEEP','EDIT'}:
                        inv.require(inv.file_sha(ROOT/choice['body']) == choice['clean_text_sha256'], 'authored body changed')
                        record['clean_text_sha256'] = choice['clean_text_sha256']
                        if decision == 'EDIT':
                            record['text'] = (ROOT/choice['body']).read_text(encoding='utf-8')
                    record['exact_authored_id'] = choice_source['id']
                elif row['decision'] in {'KEEP','EDIT','EXCLUDE'}:
                    decision = row['decision']
                    group = 'VERIFIED_V26_RULE_OUTCOME_PENDING_ROOT_ADMISSION'
                    reason = ','.join(row['reasons'])
                    if decision == 'EXCLUDE':
                        inv.require(row['id'] in {'historical_train:709976','validation:0','validation:3759'},
                                    'automatic exclusion is not an original irreparable boundary')
                    elif decision == 'KEEP':
                        inv.require(row['clean_text_sha256'] == key, 'KEEP changes the original body')
                        record['clean_text_sha256'] = key
                    else:
                        inv.require(inv.sha(row['text']) == row['clean_text_sha256'] and
                                    not inv.corpus.MEMOS.search(row['text']), 'verified edited body changed or has a memo')
                        record.update(text=row['text'], clean_text_sha256=row['clean_text_sha256'])
                    record['draft_rules'] = row['rules']
                else:
                    decision = 'HOLD'
                    group = 'UNRESOLVED_NOT_ADMITTED_NOT_A_TERMINAL_HOLD_APPROVAL'
                    reason = ','.join(row['reasons'])
                    record['review_status'] = 'UNRESOLVED_NOT_ADMITTED'
                    pending_reasons.update(row['reasons'])
                inv.require(decision in {'KEEP','EDIT','EXCLUDE','HOLD'}, 'unknown joined disposition')
                record.update(decision=decision, reason=reason, prospective_group=group,
                              root_approved=False, cache_admitted=False)
                writer.append(record)
                outcomes[key] = decision
                counts[decision] += 1
                groups[group] += 1
    inv.require(len(outcomes) == 297539 and set(authored) <= set(outcomes), 'whole unique source conservation differs')
    manifest = writer.close(lineage=dict(selection_sha256=inv.file_sha(selection),draft_sha256=inv.file_sha(draft_path)))
    weighted = Counter()
    for row in inv.cache.rows(draft_path.parent/'occurrences', draft['occurrence_manifest']):
        decision = outcomes[row['original_text_sha256']]
        weighted.update(documents=1,input_ids=row['input_ids'],**{decision:1})
        weighted[decision+'_input_ids'] += row['input_ids']
    inv.require(weighted['documents'] == 460695 and weighted['input_ids'] == 462874291, 'whole position/token conservation differs')
    pins = {str(path.relative_to(ROOT)):inv.file_sha(path) for path in
            [selection,draft_path,evidence_path,contract_path,Path(__file__),AUDIT/'guarded_scan_metadata_v1.py']}
    result = dict(status='WHOLE_SOURCE_JOIN_PLAN_NOT_ROOT_OR_CACHE_ADMISSION',counts=dict(counts),
        occurrence_counts=dict(weighted), groups=dict(groups), pending_reasons_unique=dict(pending_reasons),
        exact_authored_source_ids=len(selection_document['rows']), exact_authored_raw_shas=len(authored),
        restricted_draft_rows_metadata_only=protected_projected, full_restricted_original_bodies_opened=False,
        records_directory='records',manifest=manifest,input_pins=pins,
        remaining_hold=weighted['HOLD'],unprocessed=weighted['HOLD'],
        root_approved=False,cache_admitted=0,goal_complete=False,training_authorized=False,
        seconds=time.monotonic()-started)
    inv.write_json(output/'complete.json',result)
    print(json.dumps({key:result[key] for key in ['status','counts','occurrence_counts','groups','seconds']}),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--output-name',required=True)
    args=parser.parse_args()
    prepare(args.selection.resolve(),args.output_name)
