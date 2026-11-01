"""원형 보고서·실제 종료·독립 상태 해시를 다시 읽는 CPU 전용 검산."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import statistics

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'handoff/audit/nov01_independent/p107_actual_root_readback_v1.json'


def sha(path):
    # 저장소의 Python 3.10에서도 동작하는 독립 스트리밍 해시다.
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path):
    return dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=sha(path))


def main():
    assert not OUT.exists(), '기존 검산은 덮어쓰지 않는다'
    folder = ROOT / 'test_result/evidence/p107_actual_train_link_v1_20261101'
    reports = {mode: json.loads((folder / mode / 'report.json').read_text())
               for mode in ('cost', 'resume')}
    receipts = {}
    for mode, result in reports.items():
        assert result['status'] == 'COMPLETE' and result['final_exit'] == 0
        assert result['parent_unchanged'] and result['source_unchanged']
        assert result['final_verification_errors'] == result['model_release_errors'] == []
        assert result['checkpoint_writes'] == 0 and not result['corpus_training']
        assert result['final_cuda_cleanup']['allocated_bytes'] == 0
        assert result['final_cuda_cleanup']['reserved_bytes'] == 0
        for name, expected in result['source']['files'].items():
            assert sha(ROOT / name) == expected, name
        suffix = 'training_cost' if mode == 'cost' else 'training_resume'
        stage = '4bW' if mode == 'cost' else '4cW'
        log = ROOT / f'test_result/107_log_20261101_P107_Stage{stage}_actual_{suffix}.txt'
        text = log.read_text()
        assert '[runlog] 종료코드 0' in text and 'actual_exit=0' in text
        receipts[mode] = dict(report=record(folder / mode / 'report.json'), log=record(log))
    cost, resume = reports['cost'], reports['resume']
    assert cost['completed_optimizer_updates'] == 24
    assert cost['observer_equivalence'] == 'EXACT'
    blocks = cost['blocks']
    assert [block['mode'] for block in blocks] == [
        'uniform', 'observe', 'adaptive', 'adaptive', 'observe', 'uniform']
    assert blocks[0]['final_equivalence'] == blocks[1]['final_equivalence']
    assert blocks[0]['final_equivalence'] == blocks[4]['final_equivalence']
    assert blocks[0]['final_equivalence'] == blocks[5]['final_equivalence']
    assert blocks[2]['final_equivalence'] == blocks[3]['final_equivalence']
    summary = {}
    for mode in ('uniform', 'observe', 'adaptive'):
        rows = [row for block in blocks if block['mode'] == mode for row in block['attempts'][1:]]
        median = statistics.median(row['seconds'] for row in rows)
        assert median == cost['summary'][mode]['median_seconds'] and len(rows) == 6
        summary[mode] = dict(median_seconds=median, measured_updates=len(rows),
                             id_seconds_median=statistics.median(row['id_seconds'] for row in rows),
                             observe_seconds_median=statistics.median(row['observe_seconds'] for row in rows))
    baseline = summary['uniform']['median_seconds']
    for value in summary.values():
        value['relative_seconds'] = value['median_seconds'] / baseline
    assert resume['resume_equivalence'] == 'EXACT'
    assert resume['expected_hashes'] == resume['actual_hashes']
    assert resume['completed_optimizer_updates'] == 6
    for expected, actual in zip(resume['continued'], resume['resumed'], strict=True):
        for key in ('loss', 'causal_targets', 'masked_targets', 'executed_input_tokens', 'update'):
            assert expected[key] == actual[key], key
    parent = ROOT / 'runs/ckpt/m100s10_ko-en_p106b_native595_v1_s1337_ternary_native.pt'
    parent_record = record(parent)
    assert parent_record['sha256'] == 'C0610452ABF357868DA1CCDF16D98482D408F2D9D076C634444292023108BDF5'
    result = dict(schema='P107_ACTUAL_ROOT_READBACK_V1', status='TECHNICAL_COMPLETE',
                  measured_at=datetime.now(timezone.utc).isoformat(), actual_tool_exit={'cost': 0, 'resume': 0},
                  receipts=receipts, parent=parent_record, summary=summary,
                  physical_optimizer_updates=30, physical_synthetic_input_positions=30 * 8 * 16 * 1024,
                  resume_state_hashes=resume['actual_hashes'],
                  vram_scope='SAMPLED_SHARED_GPU_INCREASE_NOT_EXACT_PROCESS_PEAK',
                  maximum_sampled_increase_bytes=max(r['vram_watch']['maximum_additional_bytes'] for r in reports.values()),
                  maximum_torch_reserved_bytes=max(
                      [row['peak_reserved_bytes'] for block in blocks for row in block['attempts']]
                      + [row['peak_reserved_bytes'] for key in ('prefix', 'continued', 'resumed') for row in resume[key]]),
                  serialized_memory_bytes=resume['serialized_checkpoint_bytes'],
                  corpus_tokens=0, checkpoint_writes=0, quality_evaluation=False,
                  not_completed=resume['not_measured'])
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + chr(10))
    print(json.dumps(dict(status=result['status'], optimizer_updates=30, output=str(OUT.relative_to(ROOT)))))


if __name__ == '__main__':
    main()
