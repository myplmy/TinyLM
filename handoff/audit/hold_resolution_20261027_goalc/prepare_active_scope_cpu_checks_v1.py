"""Reuse WIP/output/TASK tests and exercise the six-path Git authorization."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
fixture=(AUDIT/'test_current_checkpoint_fixture_v2.py').read_text(encoding='utf-8')
for before,after in [('commit_explicit_checkpoint_v2.py','commit_explicit_checkpoint_v3.py'),
                     ('CURRENT_BIRTH_SCOPE_GIT_CHECKS_V2.json','RESUME_ACTIVE_SCOPE_GIT_CHECKS_V1.json'),
                     ('tinylm_hold_current_save_git_fixture_20261102_v2','tinylm_hold_active_save_git_fixture_20261102_v3'),
                     ('EIGHT_ISOLATED_GIT_CHECKS_PASS','TEN_ISOLATED_GIT_CHECKS_PASS')]:
    assert fixture.count(before)==1,before
    fixture=fixture.replace(before,after,1)
anchor='invoke()\nassert git("diff", "--cached", "--name-only", "-z") == b"" and not receipt.exists()'
addition='''for number, name in enumerate(sorted(path for path in namespace["OWNED_SCRIPTS"] if "repeat_context" in path),1):
    path=FIXTURE/name
    path.write_text("# exact owned repeat fixture"+chr(10),encoding="utf-8")
    repeat_manifest=make_manifest("repeat_"+str(number)+".json",[path])
    invoke(repeat_manifest, audit/("repeat_receipt_"+str(number)+".json"))
    checks.append("exact_new_repeat_recovery_path_allowed_"+str(number))
'''
assert fixture.count(anchor)==1
fixture=fixture.replace(anchor,addition+anchor,1)
with (AUDIT/'test_active_checkpoint_fixture_v1.py').open('x',encoding='utf-8') as stream:
    stream.write(fixture)
checks=(AUDIT/'run_resume_join_cpu_checks_v1.py').read_text(encoding='utf-8')
checks=checks.replace('RESUME_JOIN_CPU_CHECKS_V1.json','RESUME_ACTIVE_SCOPE_CPU_CHECKS_V1.json')
checks=checks.replace('resume_join_cpu_check_v1_','resume_active_scope_cpu_check_v1_')
before=" ['handoff/audit/hold_resolution_20261027_goalc/test_typed_nominal_local_alias_v2.py'],"
after=before+'''
 ['handoff/audit/hold_resolution_20261027_goalc/test_guarded_scan_metadata_v1.py'],
 ['handoff/audit/hold_resolution_20261027_goalc/test_guarded_reviewed_cache_v1.py'],
 ['handoff/audit/hold_resolution_20261027_goalc/test_exact_runtime_pair_guard_v1.py'],
 ['handoff/audit/hold_resolution_20261027_goalc/test_active_checkpoint_fixture_v1.py'],'''
assert checks.count(before)==1
checks=checks.replace(before,after,1)
with (AUDIT/'run_active_scope_cpu_checks_v1.py').open('x',encoding='utf-8') as stream:
    stream.write(checks)
print('RELEVANT_CPU_AND_TEN_ISOLATED_GIT_CHECKS_PREPARED')
