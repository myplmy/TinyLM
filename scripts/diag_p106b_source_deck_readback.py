"""Read-only frozen source identities, disjoint keys and lane quotas; no models."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from collections import Counter
import json
from scripts import diag_p106b_source_course as gate
from scripts import p106b_source_course as data


def main():
    rows,report=gate.read_deck();keys={s:set() for s in ('train','val')};counts=Counter();roots=set()
    for row in rows:
        root=row['root'];split=row['split'];k=data.document_keys(row['source'])
        if root in roots or keys[split]&k:raise ValueError('duplicate selected root/document')
        roots.add(root);keys[split].update(k);counts[split+':'+row['language']+':'+row['family']]+=1
    if keys['train']&keys['val']:raise ValueError('selected source/document split overlap')
    if len(rows)!=736 or dict(counts)!=report['identity']['family_counts']:raise ValueError('lane counts differ')
    value=dict(schema='P106B_SOURCE_DECK_READBACK_V1',source_report_sha256=gate.public.digest(gate.OUTPUT/'sources_report.json'),
        confirmed_selected_source_rows=len(rows),distinct_roots=len(roots),exact_long_message_overlap=0,
        counts=dict(counts),source_truth='NOT_REVIEWED; byte identity is not semantic truth',model_loading='NOT_RUN')
    gate.training.write(gate.EVIDENCE/'source_deck_readback.json',value)
    print('[SOURCE_DECK_READBACK] '+json.dumps(value));return 0

if __name__=='__main__':raise SystemExit(main())
