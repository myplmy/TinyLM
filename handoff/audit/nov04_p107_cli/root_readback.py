"""Independent byte/state receipt recheck after the two CLI processes exit."""
import hashlib
import json
from pathlib import Path

from scripts import interactive_research_infer as manual

ROOT = Path.cwd()
BASE = Path('handoff/audit/nov04_p107_cli')
TAG = 'p107_document_cli_v1_20261104'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    output = BASE/'ROOT_READBACK_v1.json'
    if output.exists():
        raise FileExistsError(output)
    profile = read(BASE/'PROFILE_v1.json')
    digest = manual.file_sha(BASE/'PROFILE_v1.json')
    reports = {mode:read(Path('test_result/evidence')/TAG/mode/'report.json') for mode in ('run','resume')}
    for mode, report in reports.items():
        if (report['status'] != 'COMPLETE' or report['actual_exit'] != 0
                or report['profile_sha256'] != digest or report['source_pins'] != profile['source_pins']
                or not report['original_checkpoint_unchanged'] or not report['inputs_sources_unchanged']
                or report['final_cuda_cleanup']['allocated_bytes'] != 0
                or report['final_cuda_cleanup']['reserved_bytes'] != 0):
            raise ValueError('actual CLI process is incomplete or changed: '+mode)
    if reports['resume']['fresh_process_resume_equivalence'] != 'EXACT':
        raise ValueError('fresh process was not exact')
    if reports['run']['final_state_hashes'] != reports['resume']['final_state_hashes']:
        raise ValueError('independent final full-state hash comparison differs')
    keys = ('loss','masked_targets','causal_targets','schedule_lrs')
    for key in keys:
        if reports['run']['updates'][-1][key] != reports['resume']['updates'][-1][key]:
            raise ValueError('independent continuation metric differs: '+key)
    for name, expected in profile['source_pins'].items():
        if manual.file_sha(manual.owned_path(name)) != expected:
            raise ValueError('source changed: '+name)
    parent = reports['run']['origin']
    spec = manual.resolve_model('native595-q')
    if parent['path'] != spec.checkpoint or manual.file_sha(manual.owned_path(parent['path'])) != parent['sha256']:
        raise ValueError('original checkpoint changed')
    folder = manual.owned_path(profile['snapshot'])
    snapshot = read(folder/'manifest.json')
    if snapshot != reports['run']['snapshot_manifest']:
        raise ValueError('saved snapshot manifest differs')
    whole = hashlib.sha256();total = 0
    for index, part in enumerate(snapshot['parts']):
        if part['path'] != 'part_'+format(index,'06d')+'.bin':
            raise ValueError('unexpected snapshot part path')
        p = folder/part['path'];one = hashlib.sha256();count = 0
        if p.is_symlink() or not 0 < part['bytes'] <= 16_000_000:
            raise ValueError('linked/oversized snapshot part')
        with p.open('rb') as stream:
            while True:
                data = stream.read(1 << 20)
                if not data:break
                count += len(data);one.update(data);whole.update(data)
        if count != part['bytes'] or one.hexdigest().upper() != part['sha256']:
            raise ValueError('snapshot part changed')
        total += count
    if total != snapshot['bytes'] or whole.hexdigest().upper() != snapshot['sha256']:
        raise ValueError('whole snapshot changed')
    physical = sum(r['physical_updates'] for r in reports.values())
    inputs = sum(r['executed_input_tokens'] for r in reports.values())
    if physical != 3 or inputs != 393216:
        raise ValueError('physical replay accounting differs')
    value = dict(schema='P107_DOCUMENT_CLI_INDEPENDENT_READBACK_V1', actual_exit=0,
        profile_sha256=digest, source_files=len(profile['source_pins']),
        full_state_hashes_exact=True, continuation_loss_targets_lr_exact=True,
        logical_updates=2, logical_input_tokens=262144,
        physical_updates=physical, physical_input_tokens=inputs,
        snapshot_parts=len(snapshot['parts']), snapshot_bytes=total,
        snapshot_sha256=snapshot['sha256'], original_checkpoint_unchanged=True,
        owned_cuda_allocated_reserved_after_cleanup=[0,0],
        worker_seconds={mode:r['wall_seconds'] for mode,r in reports.items()},
        allocated_peak_bytes=max(u['peak_allocated_bytes'] for r in reports.values() for u in r['updates']),
        reserved_peak_bytes=max(u['peak_reserved_bytes'] for r in reports.values() for u in r['updates']),
        quality_claim=False, corpus_training=False, real_corpus_admission=False,
        checkpoint_deletions=0, parent_tensor_loads_by_this_readback=0)
    with output.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    print(json.dumps(value))


if __name__ == '__main__':
    main()
