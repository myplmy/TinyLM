"""Verify all source IDs and every ordered packet occur in their exact TASK."""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards

rows=[]
totals=Counter()
for cohort in ('repeat_named_roles_counter_v2','remaining_birth_full_counter_v1'):
    manifest_path=inv.BASE/cohort/'manifest.json'
    manifest=inv.cache.read(manifest_path)
    for role,assigned in manifest['assignments'].items():
        directory=inv.BASE/'agents'/role/cohort
        tasks=[]
        for path in sorted(directory.glob('TASK_*.md')):
            text=path.read_text(encoding='utf-8')
            tasks.append((path,text,safeguards.explicit_task_ids(text)))
        for source in [r for r in manifest['rows'] if r['role']==role]:
            matching=[(p,t) for p,t,ids in tasks if source['id'] in ids]
            inv.require(len(matching)==1,'source must belong to one exact TASK')
            task,text=matching[0]
            packets=[str(ROOT/p['path']) for p in source['reading_parts']]
            missing=[p for p in packets if p not in text]
            present=[text.index(p) for p in packets if p in text]
            ordered=present==sorted(present)
            totals[cohort+'_sources_checked']+=1
            totals[cohort+'_packets_checked']+=len(packets)
            if missing or not ordered:
                rows.append(dict(id=source['id'],role=role,cohort=cohort,
                    task=str(task.relative_to(ROOT)),task_sha256=inv.file_sha(task),
                    missing_explicit_packet_paths=missing,ordered=ordered))
out=AUDIT/'EXACT_TASK_PACKET_CONTRACT_V1.json'
with out.open('x',encoding='utf-8') as stream:
    json.dump(dict(status='TASK_PACKET_REFERENCE_CHECK_NOT_MEANING_APPROVAL',counts=dict(totals),
        exceptions=rows,exceptions_count=len(rows),producer_sha256=inv.file_sha(Path(__file__)),
        original_bodies_opened=0,goal_complete=False,training_authorized=False),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(dict(counts=dict(totals),exceptions=rows),ensure_ascii=False))
