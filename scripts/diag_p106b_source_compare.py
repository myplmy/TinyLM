"""CPU report-only pair readback, never teacher agreement = semantic truth."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
import json
from scripts import diag_p106b_source_course as gate


def summarize(a,b,corpus):
    matched=('parent_sha256','tokenizer_sha256','seed','micro_bs','accum','seq','grad_checkpoint',
             'compile','epochs','initial_core_sha256','corpus_sha256','updates','actual_x_tokens','assistant_targets')
    mismatch=[k for k in matched if a.get(k)!=b.get(k)]
    if a.get('updates')!=32 or b.get('updates')!=32:mismatch.append('expected32updates')
    expected=4*corpus['counts']['train']['reference_targets']
    if a.get('reference_target_events')!=0 or b.get('reference_target_events')!=expected:mismatch.append('reference_target_events')
    arms={}
    for name,r in [('sft_only',a),('reference_lm',b)]:
        before=r['native_before']['ce'];after=r['native_after']['ce']
        arms[name]=dict(updates=r['updates'],actual_x=r['actual_x_tokens'],assistant_targets=r['assistant_targets'],
            reference_targets=r['reference_target_events'],reference_weight=r['reference_weight'],
            sft_val_history=r['history'],native_ce_before=before,native_ce_after=after,native_delta=after-before,
            first_answer_descriptive=r['final_answers']['counts'],free_answers='UNSCORED_OFFLINE_CONTEXT_REVIEW_REQUIRED',
            legacy8=r['legacy8_after'],grad_max=r['grad_max'],peak_reserved_mib=r['peak_reserved_mib'],whole_sec=r['whole_sec'])
    return dict(schema='P106B_REFERENCE_OBJECTIVE_PAIR_V1',controls_matched=not mismatch,mismatch=mismatch,
        arms=arms,source_truth='PSEUDO_UNVERIFIED',general_intelligence='NOT_ESTABLISHED',
        changed_axes=['reference_loss_weight_and_supervised_user_reference_positions','CE_head_compute_cost'],
        same_input_token_exposure=True,automated_semantic_accept=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true',required=True);p.parse_args()
    try:
        corpus=json.loads((gate.CORPUS/'report.json').read_text());a=json.loads((gate.EVIDENCE/'sft_only_report.json').read_text());b=json.loads((gate.EVIDENCE/'reference_lm_report.json').read_text())
        value=summarize(a,b,corpus);gate.training.write(gate.EVIDENCE/'pair_report.json',value)
        print('[SOURCE_PAIR] '+json.dumps(dict(controls_matched=value['controls_matched'],mismatch=value['mismatch'],
            native_deltas={k:v['native_delta'] for k,v in value['arms'].items()},semantic_truth=value['source_truth'])))
        return 0 if value['controls_matched'] else 8
    except FileNotFoundError as exc:print('[HOLD] '+str(exc));return 8

if __name__=='__main__':raise SystemExit(main())
