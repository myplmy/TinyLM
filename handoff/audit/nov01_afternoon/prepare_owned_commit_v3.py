"""Explicit ownership inventory for the afternoon local commit, no Git writes."""
from pathlib import Path
import hashlib
import json
import subprocess
ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).parent

TRACKED={'.gitignore','ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md','checkpoints.tsv',
 'docs/EXPERIMENT_BASELINES.md','docs/METHODS.md','docs/methods/03_knowledge_quality.md',
 'docs/methods/05_training_speed.md','experiments.tsv','handoff/COMPASS.md',
 'handoff/WIP_20261022_작업원장.md',
 'test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md',
 'test_plan/P107_문서가시성과-shift를-분리한-causal-MNTP-계약.md','test_plan/실험계획목록.md',
 'test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md',
 'test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md',
 'test_result/실험목록.md','tinylm/train/adaptive_training.py'}
SCRIPTS=['diag_p106b_falcon_logitreuse_shots','test_p106b_falcon_logitreuse_shots',
 'diag_p107_disk_resume','test_p107_disk_resume_driver','test_p107_session_boundary',
 'test_p107_causal_teacher','test_p107_causal_integration','test_p107_causal_kd_driver',
 'diag_p107_causal_kd_cost','diag_p107_process_resume','test_p107_process_resume']
EXACT={'scripts/'+name+'.py' for name in SCRIPTS}|{'tinylm/train/'+name+'.py'
 for name in ('boundary_store','causal_teacher','document_source','hybrid_session')}
EXACT|={'docs/research/'+name+'.md' for name in (
 '20261101_Falcon5_오후_전량평가_설계','20261101_P107_causal_KD_연결_설계',
 '20261101_P107_문서원천과_디스크재개_설계','20261101_오후_독립연구_결과보고')}
EXACT|={'proposal/20261101_정제세션-격리와-공용검사-범위-명시-제안서.md',
 'handoff/audit/nov01_independent/MMLU_EXTERNAL_COMPARISON_v3.json'}
EXACT|={name+'-done.sh' for name in ('run_P106B_Stage14iW_mmlu_falcon5_logitreuse_cost',
 'run_P106B_Stage14jW_mmlu_falcon5_logitreuse_full','run_P107_Stage5W_document_schedule_disk_resume',
 'run_P107_Stage6W_causal_teacher_kl_cost','run_P107_Stage7W_fresh_process_disk_resume',
 'run_P107_Stage0W_mntp_metadata_contract','run_P107_Stage1W_mntp_forward_backward_cost')}
PREFIXES=('handoff/audit/nov01_afternoon/',
 'test_result/evidence/p106b_falcon_logitreuse_shots_v1_20261101/',
 'test_result/evidence/p107_session_disk_v1_20261101/',
 'test_result/evidence/p107_causal_kd_cost_v1_20261101/',
 'test_result/evidence/p107_process_resume_v1_20261101/',
 'test_result/evidence/p106b_nvml_probe_v1_20261101/')
RAW={'test_result/'+name+'.txt' for name in (
 '101_log_20261101_P106B_Stage14iW_mmlu_falcon5_logitreuse_cost',
 '101_log_20261101_P106B_Stage14jW_mmlu_falcon5_logitreuse_full',
 '107_log_20261101_P107_Stage5W_document_schedule_disk_resume',
 '107_log_20261101_P107_Stage6W_causal_teacher_kl_cost',
 '107_log_20261101_P107_Stage7W_fresh_process_disk_resume')}


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def names(data):return {x.decode() for x in data.split(bytes([0])) if x}


def main():
    assert not names(git('diff','--cached','--name-only','-z')),'foreign index must not be changed'
    tracked=names(git('diff','--name-only','-z'))
    others=names(git('ls-files','--others','--exclude-standard','-z'))
    selected=sorted((tracked&TRACKED)|{x for x in others if x in EXACT|RAW or x.startswith(PREFIXES)})
    assert RAW<=set(selected) and 'scripts/flag_whitelist.tsv' not in selected
    assert all(not x.endswith(('.jsonl','.pt','.bin','.paths','.lock')) for x in selected)
    records=[]
    for name in selected:
        p=ROOT/name
        assert p.is_file() and not p.is_symlink() and not any(x.is_symlink() for x in p.parents)
        assert not name.startswith(('datasets/','data_cache/','runs/','HF/','.agents/','.codex/','agents/'))
        assert 'hold_resolution_' not in name and 'source_cleanup_' not in name
        data=p.read_bytes()
        assert len(data)<20_000_000,(name,len(data))
        records.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest().upper()))
    scope=BASE/'COMMIT_SCOPE_v3.json'
    assert not scope.exists()
    selected.append(str(scope.relative_to(ROOT)));selected=sorted(selected)
    payload=dict(schema='AFTERNOON_OWNED_COMMIT_SCOPE_V2',authority='user105',
        head=git('rev-parse','HEAD').decode().strip(),branch=git('branch','--show-current').decode().strip(),
        index_was_empty=True,paths=selected,bytes_before_audit=sum(r['bytes'] for r in records),
        bindings_before_audit=records,raw_logs=sorted(RAW),all_files_below20mb=True,
        foreign_tracked_preserved=sorted(tracked-TRACKED),unowned_untracked_count=len(others-set(selected)),
        unowned_paths_recorded=False,
        deferred_index_receipt='handoff/audit/nov01_afternoon/INDEX_CHECK_v2.json',push=False)
    with scope.open('x',encoding='utf-8') as f:json.dump(payload,f,ensure_ascii=False,indent=2)
    allow=BASE/'STAGE_ALLOWLIST_v3.paths'
    with allow.open('xb') as f:f.write(bytes([0]).join(x.encode() for x in selected)+bytes([0]))
    print(json.dumps(dict(paths=len(selected),raw_logs=len(RAW),bytes=payload['bytes_before_audit'],
        foreign_tracked_preserved=payload['foreign_tracked_preserved'],unowned_untracked_count=payload['unowned_untracked_count'])))
    return 0


if __name__=='__main__':raise SystemExit(main())
