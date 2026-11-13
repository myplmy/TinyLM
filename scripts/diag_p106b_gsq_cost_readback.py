"""Independent numeric closure of the two completed full-geometry cost arms."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'test_result/evidence/p106b_gsq_objective_v2_20261105'


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1<<20),b''):
            value.update(part)
    return value.hexdigest().upper()


def main():
    profile = json.loads((BASE/'profile.json').read_text(encoding='utf-8'))
    data = profile['training_data']
    if sha(ROOT/data['path']) != data['sha256']:
        raise ValueError('frozen technical rows changed')
    rows = json.loads((ROOT/data['path']).read_text(encoding='utf-8'))['rows']
    languages, targets = Counter(), Counter()
    for row in rows:
        languages[row['language']] += len(row['record']['x'])
        targets[row['language']] += row['ce_targets']
    expected = profile['counts']
    if sum(languages.values()) != expected['actual_x_tokens'] or sum(targets.values()) != expected['ce_targets']:
        raise ValueError('actual input/CE target counts differ')
    reports = {}
    for arm in ('ste','gsq'):
        path = BASE/arm/'report.json'
        report = json.loads(path.read_text(encoding='utf-8'))
        if (report['status'] != 'TECHNICAL_COST_COMPLETE' or report['returncode'] != 0
                or report['profile_sha256'] != sha(BASE/'profile.json')
                or report['policy'] != profile['policy']
                or report['updates'] != 3 or report['quality_evaluation']
                or report['checkpoint_saving'] or not report['original_checkpoint_unchanged']):
            raise ValueError('closed technical cost identity/limits differ: '+arm)
        if any(report['final_cuda_cleanup'][k] != 0 for k in ('allocated_bytes','reserved_bytes')):
            raise ValueError('owned CUDA cleanup incomplete')
        events = report['events']
        if len(events) != 3:
            raise ValueError('exact three actual updates required')
        for index,event in enumerate(events):
            if (event['update'] != index+1 or event['warmup'] != (index==0)
                    or event['ce_targets'] != expected['ce_targets']
                    or event['kd_chunks'] != expected['kd_chunks']
                    or event['actual_x_tokens'] != expected['actual_x_tokens']
                    or event['padded_slots'] != expected['padded_slots']
                    or any(not math.isfinite(event[k]) for k in
                           ('seconds','ce_sum','kl_sum','grad_norm_before_clip'))
                    or event['seconds'] <= 0):
                raise ValueError('actual technical event/count changed')
        mean = math.fsum(e['seconds'] for e in events[1:])/2
        if not math.isclose(mean,report['measured_update_seconds'],rel_tol=1e-12):
            raise ValueError('timed-update mean changed')
        reports[arm] = dict(report_sha256=sha(path),mean_update_seconds=mean,
            update_seconds=[e['seconds'] for e in events],
            peak_allocated_bytes=report['peak_allocated_bytes'],
            peak_reserved_bytes=report['peak_reserved_bytes'],
            maximum_preclip_grad_norm=max(e['grad_norm_before_clip'] for e in events),
            wall_seconds=report['wall_seconds_before_report_write'],
            original_checkpoint_unchanged=True,final_cuda_allocated=0,final_cuda_reserved=0)
    if sha(ROOT/profile['checkpoint']) != profile['entry']['checkpoint']['sha256']:
        raise ValueError('original checkpoint changed after both arms')
    result = dict(schema='P106B_GSQ_COST_ROOT_READBACK_V1',
        status='TECHNICAL_COST_CLOSED_NOT_QUALITY_ADOPTION',
        profile_sha256=sha(BASE/'profile.json'),reports=reports,
        time_ratio_gsq_over_ste=reports['gsq']['mean_update_seconds']/reports['ste']['mean_update_seconds'],
        peak_reserved_ratio=reports['gsq']['peak_reserved_bytes']/reports['ste']['peak_reserved_bytes'],
        actual_input_tokens_per_update=dict(languages),assistant_targets_per_update=dict(targets),
        exposures=dict(ephemeral_optimizer_updates=6,
            actual_input_tokens=expected['actual_x_tokens']*6,
            assistant_targets=expected['ce_targets']*6,
            kd_chunks=expected['kd_chunks']*6,padded_slots=expected['padded_slots']*6),
        flags=['PRECLIP_GRAD_NORM_OVER100_CLIP1_APPLIED_NOT_STABILITY_PASS',
               'TWO_TIMED_UPDATES_NO_STEADY_STATE_UNCERTAINTY',
               'SPARSE_ASSISTANT_TARGETS_NOT_FULL_NTP_THROUGHPUT',
               'COMMON_ADAM_LR_IS_COST_CONTROL_NOT_A_VALIDATED_CATEGORICAL_LEARNING_RATE'],
        model_quality='NOT_RUN',benchmark='NOT_RUN',deployment='NOT_RUN')
    target=BASE/'readback/report_v1.json'
    target.parent.mkdir(exist_ok=True)
    with target.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
