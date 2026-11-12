"""Add exact supplemental reads and exclude metadata-only rows from full-read credit."""
from pathlib import Path
import hashlib
import json
import re
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard

FROZEN=AUDIT/'record_hold_stages_v6.py'
assert guard.inv.file_sha(FROZEN)=='32BC6D84E15188EA70DE60800A50D969566117691092931B1D3EC4414F08708A'
code=FROZEN.read_text(encoding='utf-8')
code=code.replace('active_guard_v5_preflight_v1','active_guard_v6_preflight_v1')
code=code.replace('GUARDED_SOURCE_METADATA_CONTRACT_V5','GUARDED_SOURCE_METADATA_CONTRACT_V6')
code=code.replace('01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338',guard.EXPECTED)
anchor="    env=dict(__name__='immutable_human_review_metadata_prefix',__file__=str(Path(__file__)))"
assert code.count(anchor)==1
replacement="""    saved_before = "    saved = [row for row in records if row['status'] != 'NO_SAVED_REVIEW_ROW']"
    saved_after = "    metadata_only_read_credit_excluded.extend(dict(id=row['id'],cohort=cohort) for row in records if row.get('metadata_only') or row.get('individual_human_full_read_completed') is False)" + chr(10) + "    saved = [row for row in records if row['status'] != 'NO_SAVED_REVIEW_ROW' and not row.get('metadata_only') and row.get('individual_human_full_read_completed') is not False]"
    assert source.count(saved_before)==1
    source=source.replace(saved_before,saved_after)
    # Snapshot saved counts include metadata dispositions. Compare before filtering.
    source=source.replace("    assert len(saved) == sum(row['saved'] for row in snapshot['coverage'].values())", "    assert sum(row['status'] != 'NO_SAVED_REVIEW_ROW' for row in records) == sum(row['saved'] for row in snapshot['coverage'].values())")
    env=dict(__name__='immutable_human_review_metadata_prefix',__file__=str(Path(__file__)),metadata_only_read_credit_excluded=[])
""".rstrip()
code=code.replace(anchor,replacement)
anchor="    prior=read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json');prior_ids={r['id'] for r in prior['rows']}"
assert code.count(anchor)==1
code=code.replace(anchor,"    BIND_SUPPLEMENTAL_READS(env,c,pins,read)"+chr(10)+anchor)
anchor="    receipt=dict(status='HUMAN_FULL_READ_AND_APPROVED_RULE_STAGES_RECONCILED_SEPARATELY',"
assert code.count(anchor)==1
code=code.replace(anchor,anchor+chr(10)+
    "        metadata_only_dispositions_excluded_from_human_full_read_credit=env['metadata_only_read_credit_excluded'],"+chr(10)+
    "        supplemental_full_read_coverage=c.get('additional_full_read_coverage',[]),")
anchor="for path in [Path(__file__),frozen,AUDIT/'active_guard_v6_preflight_v1.py'"
assert code.count(anchor)==1
code=code.replace(anchor,"for path in [STAGE6_FROZEN,Path(__file__),frozen,AUDIT/'active_guard_v6_preflight_v1.py'")


def bind_extra(env,config,pins,read):
    for spec in config.get('additional_full_read_coverage',[]):
        assert spec['cohort']=='remaining_rule30_independent_context_v1' and spec['expected_sources']==6
        path=guard.inv.BASE/(spec['cohort']+'_snapshots')/spec['version']/'complete.json'
        summary=read(path,spec['snapshot_sha256'])
        assert not summary['errors'] and sum(v['saved'] for v in summary['coverage'].values())==6
        manifest=read(guard.inv.BASE/spec['cohort']/'manifest.json')
        sources={r['id']:r for r in manifest['rows']}
        records=[]
        for shard in summary['shards']:
            records.extend(read(ROOT/shard['path'],shard['sha256']))
        count=positions=0
        for row in records:
            assert row['status']!='NO_SAVED_REVIEW_ROW' and not row.get('metadata_only')
            assert re.search(r'EOF|전문|전체|full',row['read_scope'],re.I)
            source=sources[row['id']]
            assert row['original']['sha256']==source['original']['sha256']
            if row['id'] in env['reviewed']:
                assert env['reviewed'][row['id']]['source']['original']['sha256']==source['original']['sha256']
                continue
            env['reviewed'][row['id']]=dict(source=source,record=row,cohort=spec['cohort'])
            count+=1
            positions+=source['occurrences']
        env['coverage'].append(dict(cohort=spec['cohort'],version=spec['version'],saved=count,positions=positions,
            independent_additional_read_not_full_rule_read_claim=True))


exec(compile(code,str(FROZEN),'exec'),dict(__name__='__main__',__file__=str(Path(__file__)),
    BIND_SUPPLEMENTAL_READS=bind_extra,STAGE6_FROZEN=FROZEN))
