#!/usr/bin/env python3
"""User-only V2 output-contract recovery, then conditional V3 corpus/training.

Old pilots, deficit outputs and checkpoints remain immutable. No input prompts,
automatic downloads or teacher/student co-residency. Import is CPU-only.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack, contextmanager
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import subprocess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_gemma_task_pilot as gate
from scripts import diag_p106b_gemma_deficit_production as producer
from scripts import p106b_gemma_deficit as control
from scripts import p106b_gemma_task_contract_v2 as tasks
from scripts import p106b_gemma_output_contract as output
from scripts.p106b_mixed_scale import safe_repo_path, digest
from scripts.p106b_teacher_wrapper import wrap_turns
from scripts.p106b_stage_receipt import pipeline
from scripts.p106b_shards import verify
from tinylm.data.sft import conversation_split_key

PILOTS = {mode: ROOT / ('HF/sft_ready/p106b_gemma_task_' + mode + '_v2')
          for mode in ('contract16', 'family64', 'structure4')}
PATHS = dict(OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_deficit_v2',
             CORPUS=ROOT/'HF/sft_ready/p106b_capability_gemma_v3',
             WIRE=ROOT/'HF/sft_ready/p106b_capability_gemma_wire_v3',
             STUDENT=ROOT/'HF/sft_ready/p106b_capability_gemma_student_v3',
             EVALUATION=ROOT/'HF/sft_ready/p106b_gemma_capability_multiaxis_v3')
TAG = 'p106b_s4_gemma_capability300m_chat32_outputv2_s1337'
REGRESSION = ['scripts.test_p106b_gemma_output_contract',
              'scripts.test_p106b_gemma_task_contract', 'scripts.test_p106b_gemma_deficit']
PERSON = dict(type='object', properties=dict(name={'type':'string'}, age={'type':'integer'}),
              required=['name', 'age'], additionalProperties=False)
SCHEMAS = dict(array=dict(type='array', items=PERSON, minItems=2, maxItems=2),
               nested=dict(type='object', properties=dict(people=dict(type='array', items=PERSON, minItems=2, maxItems=2),
                           count={'type':'integer'}), required=['people','count'], additionalProperties=False))


@contextmanager
def recovery_scope():
    """Opt-in dependency injection; restores legacy module state on every exit."""
    original_require = producer.require_pilots
    def require_recovery_pilots():
        structure_sha = require_structure4()
        return dict(original_require(), structure4_sha256=structure_sha)
    with ExitStack() as stack:
        for module, key, value in ((gate, 'tasks', tasks), (gate, 'OUTPUTS', PILOTS),
                                  (producer, 'tasks', tasks), (control, 'TAG', TAG)):
            stack.enter_context(patch.object(module, key, value))
        for key, value in PATHS.items():
            stack.enter_context(patch.object(control, key, value))
        stack.enter_context(patch.object(producer, 'require_pilots', require_recovery_pilots))
        yield


def require_structure4():
    path = safe_repo_path(PILOTS['structure4']/'report.json')
    if not path.is_file():
        raise FileNotFoundError('new structure4 array/nested pilot required before family64/production')
    sha = digest(path)
    report = json.loads(path.read_text(encoding='utf-8'))
    if (report.get('schema') != 'P106B_GEMMA_TASK_PILOT_V1'
            or report.get('status') != 'TASK_PILOT_COMPLETE'
            or report.get('accepted_groups') != 4 or report.get('candidate_manifest',{}).get('rows') != 4
            or report.get('input',{}).get('mode') != 'structure4'
            or report['input'].get('wire_contract') != tasks.CONTRACT
            or report['input'].get('role_report_sha256') != gate.ROLE_SHA):
        raise FileNotFoundError('completed exact structure4 required; no teacher allocated')
    verify(path.parent, report['candidate_manifest'])
    return sha


def structure_jobs():
    jobs = []
    for language in ('ko', 'en'):
        for kind, schema in SCHEMAS.items():
            facts = ('미나의 나이는 20세이고 준의 나이는 30세입니다.' if language == 'ko' else
                     'Mina is 20 years old and Jun is 30 years old.')
            instruction = {
                ('ko','array'): '두 사람을 name과 age 항목을 갖는 JSON 배열로 작성하세요. 이름은 Mina, Jun 순서입니다.',
                ('en','array'): 'Return a JSON array of two people with name and age fields, in Mina, Jun order.',
                ('ko','nested'): 'people 배열에 두 사람의 name과 age를 넣고 count에 인원수를 넣는 JSON 객체를 작성하세요. 이름은 Mina, Jun 순서입니다.',
                ('en','nested'): 'Return a JSON object with a people array of name/age objects in Mina, Jun order and a count field.',
            }[(language, kind)]
            question = facts + '\n' + instruction
            source_id = 'structure_' + kind + '_' + language
            sha = hashlib.sha256(question.encode('utf-8')).hexdigest().upper()
            source = wrap_turns([dict(user_text=question, assistant_text=facts)], source_id=source_id,
                source_sha256=sha, teacher_model_sha256='0'*64, language=language,
                source_license='CC0-1.0', generation_id='code_fixture', source_repo='TinyLM/code-authored-fixture',
                source_revision='gemma_structure_fixture_v1', source_object_id=source_id,
                source_transform='original', parent_concept_id=sha, source_rights_status='CARD_ONLY')
            source['meta']['source_family'] = 'code_authored_structure_fixture'
            jobs.append(dict(original=source, language=language, task='qa', fixed_question=question,
                output_contract=output.contract('STRUCTURED_JSON', producer='gemma_structure_fixture_v1', schema=schema),
                source_group_id=conversation_split_key(source).hex().upper(),
                source_family=source['meta']['source_family']))
    return jobs


def check_structure():
    directory = safe_repo_path(PILOTS['structure4'])
    if directory.exists() or directory.is_symlink():
        raise FileExistsError('prior structure output preserved; use a new stage')
    role = gate.read_report(gate.previous.role_gate.OUTPUT/'role/report.json', gate.ROLE_SHA)
    gate.previous.require_base_off(role)
    jobs = structure_jobs()
    return jobs, dict(schema='P106B_GEMMA_TASK_PREFLIGHT_V1', mode='structure4',
        wire_contract=tasks.CONTRACT, teacher_identity=role['input']['asset_identity'],
        old_report_sha256=gate.OLD_SHA, role_report_sha256=gate.ROLE_SHA,
        planned_groups=4, planned_turns=4, language_groups=dict(Counter(j['language'] for j in jobs)),
        maximum_attempts_per_turn=3, mtp=False, semantic_truth='PSEUDO_UNVERIFIED',
        scope='CODE_AUTHORED_ARRAY_NESTED_STRUCTURE_ONLY', student_training='NOT_RUN', new75M_ready=False)


def dispatch(args, *, execute):
    with recovery_scope():
        if args.mode in PILOTS:
            if '--max-wall-sec' in sys.argv:
                raise ValueError('pilot wall budget is fixed; producer wall option not accepted')
            if args.mode == 'family64':
                require_structure4()
            jobs, info = check_structure() if args.mode == 'structure4' else gate.check(args.mode)
            info['producer_code_sha256'] = {name:digest(ROOT/name) for name in tasks.EXTRA_CODE_PATHS}
            info['output_namespace'] = str(PILOTS[args.mode].relative_to(ROOT))
            if not execute:
                print('[CHECK_ONLY] '+json.dumps(info,ensure_ascii=False)); return 0
            return gate.execute(args.mode, jobs, info)
        child = ['deficit', '--mode', args.mode, '--execute' if execute else '--check-only']
        if '--max-wall-sec' in sys.argv:
            child += ['--max-wall-sec', str(args.max_wall_sec)]
        with patch.object(sys, 'argv', child):
            return producer.main()


def guarded_dispatch(args, *, execute):
    try:
        return dispatch(args, execute=execute)
    except (FileNotFoundError, FileExistsError) as exc:
        print('[HOLD] '+str(exc),file=sys.stderr); return 8
    except KeyboardInterrupt:
        print('[INTERRUPTED] original and partial outputs preserved',file=sys.stderr); return 130
    except Exception as exc:
        print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr); return 9


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=tuple(PILOTS)+('produce','resume','finalize','wire','train','eval'), required=True)
    parser.add_argument('--max-wall-sec', type=int, default=21600)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true')
    group.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only:
        return guarded_dispatch(args,execute=False)
    def launch(command):
        if command[0] == 'CHECK_ONLY':
            return guarded_dispatch(args,execute=False)
        if command[0] == 'EXECUTE':
            return guarded_dispatch(args,execute=True)
        return subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL).returncode
    phases = [('REGRESSION',[sys.executable,'-B','-X','utf8','-m','unittest']+REGRESSION),
              ('PREFLIGHT',['CHECK_ONLY',args.mode]),('EXECUTE',['EXECUTE',args.mode])]
    return pipeline(phases,launch,lambda line:print(line,flush=True),
                    experiment='P106B_GEMMA_OUTPUT_V2_'+args.mode)['returncode']


if __name__ == '__main__':
    raise SystemExit(main())
