"""Validate explicit A artifacts and prepare an exact local staging manifest."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    tests = {
        'SCOPE_FINAL_CPU_v3.log': 21,
        'STATIC_DEFAULT_FINAL_v3.log': 9,
        'SMOKE_CONTRACT_FINAL_v3.log': 46,
        'WIP_CPU_v1.log': 31,
    }
    rows = []
    for name, count in tests.items():
        path = BASE / name
        text = path.read_text()
        if not re.search(r'Ran ' + str(count) + r' tests? in ', text) or not text.rstrip().endswith('OK'):
            raise ValueError('final CPU log did not pass: ' + name)
        rows.append(dict(path=path.relative_to(ROOT).as_posix(), tests=count,
                         actual_exit=0, sha256=sha(path)))
    audit = json.loads((BASE / 'OWNED_STATIC_v5.json').read_text())
    if audit['schema'] != 'TINYLM_SCOPED_STATIC_AUDIT_V1' or audit['global_pass_eligible'] is not False:
        raise ValueError('owned scope must not become global closure evidence')
    if audit['counts']['pass'] != 6 or audit['counts']['errors'] != 0 or audit['counts']['not_run'] != 71:
        raise ValueError('unexpected final scoped counts')
    changed_docs = []
    for row in audit['validation_scope']['inputs']:
        if sha(ROOT / row['path']) != row['sha256']:
            if not row['path'].endswith('.md'):
                raise ValueError('validated source/shared metadata changed after CPU audit: ' + row['path'])
            changed_docs.append(row['path'])
    checker_reads = []
    for row in audit['checks']:
        if row['status'] == 'NOT_RUN':
            continue
        receipt = ROOT / row['scope_receipt']
        data = json.loads(receipt.read_text())
        if (data['scope_violations'] or not data['inputs_unchanged']
                or sha(receipt) != row['scope_receipt_sha256']):
            raise ValueError('scope receipt did not verify')
        checker_reads.append(dict(check=row['name'], checker_files=len(data['checker_reads']),
                                  integrity_files=len(data['integrity_reads']), violations=0))
    for name, success in [('HANDOFF_STRUCTURE_v2.log', 'SUMMARY files=1 errors=0'),
                           ('HANDOFF_TIME_v1.log', '모순 0건'),
                           ('HANDOFF_QUEUE_v1.log', 'errors=0'),
                           ('PROPOSAL_v2.log', 'errors=0')]:
        if success not in (BASE / name).read_text():
            raise ValueError('document contract did not pass: ' + name)
    summary = dict(schema='TINYLM_SCOPE_A_CPU_SUMMARY_V1', tests=rows,
                   scope_counts=audit['counts'], scope_inputs=audit['validation_scope']['input_count'],
                   global_pass_eligible=False, checker_reads=checker_reads,
                   post_audit_document_updates=changed_docs,
                   validated_python_sources_changed=False, gpu_model_runs_after_15=0,
                   current_full_smoke='NOT_RUN', user_files_deleted=0,
                   canonical_actions=106, canonical_children=44, canonical_training_commands=33,
                   default_profile_and_predicates_preserved=True,
                   raw_failures_preserved=True)
    summary_path = BASE / 'VALIDATION_SUMMARY_v1.json'
    with summary_path.open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    explicit = {
        'scripts/validation_scope.py', 'scripts/test_validation_scope.py',
        'scripts/check_static_all.py', 'scripts/check_flag_whitelist.py',
        'scripts/smoke_execution_contract.py', 'scripts/codex_smoke.py',
        'ai_dev_tool/Codex/06_Codex용_프로젝트지침과_메모리.md',
        'ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md',
        'docs/research/20261101_A_검사입력범위_구현계약.md',
        'docs/research/20261101_자율주도_연구_최종보고.md',
        'docs/research/20261101_오후_독립연구_결과보고.md',
        'handoff/202611011123_HANDOFF.md', 'handoff/WIP_20261022_작업원장.md',
        'proposal/20261101_정제세션-격리와-공용검사-범위-명시-제안서.md',
        'proposal/20261101_정제세션-격리와-공용검사-범위-명시-제안서-approved-on-going.md',
    }
    explicit.update(path.relative_to(ROOT).as_posix() for path in BASE.rglob('*') if path.is_file())
    plan_path = BASE / 'STAGE_PATHS_v1.json'
    explicit.add(plan_path.relative_to(ROOT).as_posix())
    for name in explicit:
        if name.startswith(('datasets/', 'HF/', 'data_cache/', 'runs/', '.git/', '.agents/', '.codex/')):
            raise ValueError('excluded staging path')
        path = ROOT / name
        if path.is_symlink():
            raise ValueError('linked staging path')
        if path.is_file():
            if path.stat().st_size >= 20_000_000:
                raise ValueError('20MB result limit exceeded: ' + name)
            if path.suffix == '.py':
                ast.parse(path.read_text(), filename=name)
    if 'scripts/flag_whitelist.tsv' in explicit:
        raise ValueError('foreign flag must remain unstaged')
    if subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT).strip():
        raise ValueError('index is not empty; preserve foreign staged work')
    plan = dict(base_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                paths=sorted(explicit), foreign_flag_sha256=sha(ROOT / 'scripts/flag_whitelist.tsv'),
                scope='user106 A implementation and CPU evidence only',
                result_file_size_limit=20_000_000)
    with plan_path.open('x', encoding='utf-8') as stream:
        json.dump(plan, stream, ensure_ascii=False, indent=2)
    Path('/tmp/tinylm_nov01_scope_a_stage_paths.nul').write_bytes(
        bytes([0]).join(name.encode('utf-8') for name in plan['paths']) + bytes([0]))
    print(json.dumps(dict(paths=len(explicit), source_changes_after_audit=0,
                          scope_counts=audit['counts'], current_full_smoke='NOT_RUN')))


if __name__ == '__main__':
    main()
