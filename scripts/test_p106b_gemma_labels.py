#!/usr/bin/env python3
"""CPU label/prompt/recovery fixtures; no real assets, data, checkpoint or GPU."""
import copy
from contextlib import redirect_stdout,redirect_stderr
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_gemma_labels as labels
from scripts import p106b_gemma_teacher as old
from scripts import diag_p106b_gemma_teacher_gate as gate
from scripts import diag_p106b_gemma_label_recovery as recovery
from scripts import diag_p106b_grounded_gemma_pilot as pilot
from scripts import diag_p106b_grounded_gemma_label_pilot as grounded
from scripts import diag_p106b_epoch_retention_recovery as epoch_old
from scripts import diag_p106b_epoch_geometry_recovery as epoch_new


def reply(text='QUESTION:\n색은?\nANSWER:\n빨간색\nNOTE:\n',finish='stop'):
    return {'choices':[{'finish_reason':finish,'message':
        {'content':text,'reasoning_content':'thought kept outside student'}}],
        'usage':{'completion_tokens':20}}


class LabelTests(unittest.TestCase):
    def test_start_labels_and_empty_note(self):
        value=labels.parsed_response(reply(),'ko')
        self.assertEqual(value['format_status'],labels.COMPLETE)
        self.assertEqual(value['parsed_content']['assistant_text'],'빨간색')
        self.assertEqual(value['parsed_content']['correction_note'],'')
        self.assertEqual(value['teacher_reasoning_content'],'thought kept outside student')

    def test_inline_and_multiline_fields_preserve_content(self):
        final='QUESTION: What is RAM?\nANSWER: First line\nSecond line\nNOTE: one note'
        v=labels.parse_labels(final,language='en')
        self.assertEqual(v['user_text'],'What is RAM?')
        self.assertEqual(v['assistant_text'],'First line\nSecond line')
        self.assertEqual(v['correction_note'],'one note')

    def test_missing_duplicate_reordered_headers_rejected(self):
        text=reply()['choices'][0]['message']['content']
        for bad in (text.replace('NOTE:\n',''),text+'ANSWER: another',
                    text.replace('QUESTION:','ANSWER:',1),'intro\n'+text,
                    text.replace('ANSWER:\n빨간색','ANSWER:')):
            with self.subTest(text=bad):
                self.assertEqual(labels.parsed_response(reply(bad),'ko')['format_status'],'PARSE_ERROR')

    def test_truncation_never_passes_even_if_headers_complete(self):
        for finish in ('length',None,'tool_calls'):
            v=labels.parsed_response(reply(finish=finish),'ko')
            self.assertEqual(v['format_status'],'INCOMPLETE')
            self.assertIsNone(v['parsed_content'])

    def test_code_fenced_literal_headers_are_not_structural(self):
        final='QUESTION:\nShow labels\nANSWER:\n```text\nQUESTION: literal\nANSWER: literal\nNOTE: literal\n```\nNOTE:\n'
        v=labels.parse_labels(final,language='en')
        self.assertIn('QUESTION: literal',v['assistant_text'])

    def test_unclosed_fence_is_not_silently_accepted(self):
        final='QUESTION:\nShow labels\nANSWER:\n```text\nANSWER: literal\nNOTE:\n'
        self.assertEqual(labels.parsed_response(reply(final),'en')['format_status'],'PARSE_ERROR')

    def test_old_bracket_format_is_not_retrospectively_promoted(self):
        text='[[QUESTION]]\nq\n[[/QUESTION]]\n[[ANSWER]]\na\n[[/ANSWER]]'
        self.assertEqual(labels.parsed_response(reply(text),'en')['format_status'],'PARSE_ERROR')
        text='QUESTION:\nq\nANSWER:\na\n[[/ANSWER]]\nNOTE:\n'
        self.assertEqual(labels.parsed_response(reply(text),'en')['format_status'],'PARSE_ERROR')

    def test_bounds_and_invalid_language(self):
        for text in ('QUESTION:\n'+'q'*2001+'\nANSWER:\na\nNOTE:\n',
                     'QUESTION:\nq\nANSWER:\n'+'a'*6001+'\nNOTE:\n',
                     'QUESTION:\nq\nANSWER:\na\nNOTE:\n'+'n'*701):
            with self.assertRaises(ValueError):labels.parse_labels(text,language='en')
        with self.assertRaises(ValueError):labels.parse_labels('QUESTION: q\nANSWER: a\nNOTE:',language='xx')

    def test_prompt_native_sampler_and_no_bonsai_effort(self):
        before=copy.deepcopy(old.SAMPLER)
        p=labels.payload(old.cases()[0],7)
        self.assertEqual(p['temperature'],1.0);self.assertEqual(p['top_p'],.95);self.assertEqual(p['top_k'],64)
        self.assertTrue(p['messages'][0]['content'].startswith('<|think|>'))
        self.assertIn('QUESTION:',p['messages'][0]['content'])
        self.assertNotIn('[[/QUESTION]]',p['messages'][0]['content'])
        self.assertIn('INSIDE ANSWER',p['messages'][0]['content'])
        self.assertNotIn('reasoning_effort',p);self.assertEqual(old.SAMPLER,before)

    def test_grounded_provenance_and_previous_turns_preserved(self):
        from scripts.test_p106b_capability_prepare import row
        source=row();source['meta'].update(source_repo='public/repo',source_revision='r1',
            source_sha256='A'*64,source_id='original-id',source_family='real-family')
        before=copy.deepcopy(source);history=[dict(user_text='first',assistant_text='answer')]
        p=labels.grounded_payload(source,'ko','multiturn',3,history=history)
        body=json.loads(p['messages'][1]['content'])
        self.assertEqual(body['source']['public_context'],source['messages'])
        self.assertEqual(body['source']['explicit_previous_turns'],history)
        self.assertEqual(body['task'],'next_turn');self.assertEqual(source,before)
        self.assertIn('Use only',p['messages'][0]['content'])

    def test_student_counts_do_not_contain_reasoning_or_mutate_status(self):
        from tinylm.data.prepare import SyntheticTokenizer
        v=labels.parsed_response(reply(),'ko');before=copy.deepcopy(v)
        counts=labels.wire_counts(v,SyntheticTokenizer())
        self.assertTrue(counts['technical_ready']);self.assertGreater(counts['targets'],0)
        self.assertEqual(v,before);self.assertNotIn('thought',v['parsed_content']['assistant_text'])
        self.assertEqual(counts['semantic_truth'],'NOT_REVIEWED')
        self.assertEqual(labels.wire_counts(labels.parsed_response(reply(finish='length'),'ko'),None)['x_tokens'],0)

    def test_legacy_profile_and_parser_unchanged(self):
        old_payload=old.payload(old.cases()[0],1);new_payload=labels.payload(old.cases()[0],1)
        self.assertIn('[[/ANSWER]]',old_payload['messages'][0]['content'])
        self.assertNotIn('[[/ANSWER]]',new_payload['messages'][0]['content'])
        self.assertEqual(old.parsed_response(reply(),'ko')['format_status'],'PARSE_ERROR')
        self.assertEqual(gate.COMPLETE_STATUS,'TAGGED_COMPLETE')
        self.assertEqual(pilot.COMPLETE_STATUS,'TAGGED_COMPLETE')

    def test_role_check_uses_new_output_and_prior_asset_without_gpu(self):
        before=(gate.OUTPUT,gate.profile)
        seen=[]
        def fake_check(mode):
            seen.append((mode,gate.OUTPUT,gate.profile,gate.ASSET_FILE))
            return {'planned_requests':16}
        with patch.object(recovery,'digest',return_value=recovery.ASSET_SHA),\
             patch.object(recovery,'safe_repo_path',side_effect=lambda x:x),patch.object(gate,'check',side_effect=fake_check):
            info=recovery.check()
        self.assertEqual(seen[0][1],recovery.OUTPUT);self.assertIs(seen[0][2],labels)
        self.assertEqual((gate.OUTPUT,gate.profile),before)
        self.assertEqual(info['wire_contract'],labels.CONTRACT)

    def test_role_check_only_cannot_execute_and_restores_old_defaults(self):
        with patch.object(sys,'argv',['role-recovery','--check-only']),\
             patch.object(recovery,'check',return_value={'planned_requests':16}),\
             patch.object(gate,'role',side_effect=AssertionError('must not load teacher')),redirect_stdout(io.StringIO()):
            self.assertEqual(recovery.main(),0)

    def test_role_execute_has_label_status_only_inside_process(self):
        before=(gate.OUTPUT,gate.profile,gate.COMPLETE_STATUS,gate.ROLE_SCHEMA)
        seen=[]
        def fake_role(info):
            seen.append((gate.OUTPUT,gate.profile,gate.COMPLETE_STATUS,gate.ROLE_SCHEMA));return 8
        with patch.object(sys,'argv',['role-recovery','--execute']),\
             patch.object(recovery,'check',return_value={}),patch.object(gate,'role',side_effect=fake_role):
            self.assertEqual(recovery.main(),8)
        self.assertEqual(seen[0][2],labels.COMPLETE)
        self.assertEqual((gate.OUTPUT,gate.profile,gate.COMPLETE_STATUS,gate.ROLE_SCHEMA),before)

    def test_role_existing_output_is_hold_not_replaced(self):
        with patch.object(sys,'argv',['role-recovery','--execute']),\
             patch.object(recovery,'check',side_effect=FileExistsError('existing output')),\
             patch.object(gate,'role',side_effect=AssertionError('must not execute')),redirect_stderr(io.StringIO()):
            self.assertEqual(recovery.main(),8)

    def test_grounded_execute_uses_labels_and_restores_old_output(self):
        before=(pilot.OUTPUT,pilot.teacher,pilot.COMPLETE_STATUS);seen=[]
        def fake_execute(jobs,info):
            seen.append((pilot.OUTPUT,pilot.teacher,pilot.COMPLETE_STATUS));return 8
        with patch.object(sys,'argv',['grounded-label','--execute']),\
             patch.object(grounded,'check',return_value=([{'source':'original'}],{})),\
             patch.object(pilot,'execute',side_effect=fake_execute):
            self.assertEqual(grounded.main(),8)
        self.assertEqual(seen[0],(grounded.OUTPUT,labels,labels.COMPLETE))
        self.assertEqual((pilot.OUTPUT,pilot.teacher,pilot.COMPLETE_STATUS),before)

    def test_epoch_new_namespace_does_not_change_old_defaults(self):
        before=(epoch_old.OUTPUT,epoch_old.STAGE,epoch_old.FAILED_OUTPUT_POLICY,epoch_old.__doc__);seen=[]
        def fake_main():
            seen.append((epoch_old.OUTPUT,epoch_old.STAGE,epoch_old.__doc__));return 0
        with patch.object(epoch_old,'main',side_effect=fake_main):self.assertEqual(epoch_new.main(),0)
        self.assertEqual(seen[0][:2],(epoch_new.OUTPUT,'Stage4eWc'))
        self.assertIn('Stage4eWc',seen[0][2])
        self.assertEqual((epoch_old.OUTPUT,epoch_old.STAGE,epoch_old.FAILED_OUTPUT_POLICY,epoch_old.__doc__),before)

    def role_fixture(self):
        return dict(schema='P106B_GEMMA4_ROLE_LABELS_V1',actual_requests=16,
            input={'wire_contract':labels.CONTRACT},
            answers=[dict(round=r,mtp=mtp,case_id=c['id'],format_status=labels.COMPLETE,
                          wire={'technical_ready':True})
                     for r,order in enumerate(((False,True),(True,False)))
                     for mtp in order for c in labels.cases()])

    def test_new_role_needs_16_flushed_rows_and_technical_wire(self):
        report=self.role_fixture()
        with patch.object(gate,'COMPLETE_STATUS',labels.COMPLETE),patch.object(gate,'REQUIRE_TECHNICAL_WIRE',True):
            self.assertTrue(gate.collection_complete(report))
            report['answers'][0]['wire']['technical_ready']=False
            self.assertFalse(gate.collection_complete(report))
            report=self.role_fixture();report['answers'].pop()
            self.assertFalse(gate.collection_complete(report))

    def test_grounded_prerequisite_requires_off8_but_not_mtp_adoption(self):
        report=self.role_fixture();grounded.require_base_off(report)
        for a in report['answers']:
            if a['mtp']:a['format_status']='PARSE_ERROR';a['wire']['technical_ready']=False
        grounded.require_base_off(report)
        report['answers'][0]['wire']['technical_ready']=False
        with self.assertRaises(FileNotFoundError):grounded.require_base_off(report)

    def test_grounded_rejects_old_contract_or_case_substitution(self):
        report=self.role_fixture();report['input']['wire_contract']='OLD_TAGGED'
        with self.assertRaises(ValueError):grounded.require_base_off(report)
        report=self.role_fixture();report['answers'][0]['case_id']='other-question'
        with self.assertRaises(FileNotFoundError):grounded.require_base_off(report)
        report=self.role_fixture();report['answers'][-1]['round']=0
        with self.assertRaises(FileNotFoundError):grounded.require_base_off(report)


if __name__=='__main__':unittest.main()
