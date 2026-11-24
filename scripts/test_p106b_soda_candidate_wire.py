"""Authored CPU interface controls; no saved audit/source/tokenizer dependency."""
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from types import SimpleNamespace
import unittest
import unicodedata

from scripts import p106b_soda_candidate_wire as module
from scripts.p106b_soda_dialogue_view import BOUNDARY
from scripts.p106b_public_refill import english_specs
from tinylm.chat.serialize import loss_spans,serialize
from tinylm.data.sft import conversation_split_key
from scripts.p106b_teacher_wrapper import BOUNDARY_MARKERS

class CharTokenizer:
    def encode(self,text):
        return SimpleNamespace(ids=[100+ord(c)for c in text],offsets=[(i,i+1)for i in range(len(text))])

def raw():
    return dict(id=1,inputs='Alice: I work at a library.\n\nBob: I repair bicycles.'+BOUNDARY,
        targets='OLD_NARRATIVE_NEVER_EVIDENCE',dataset_name='SODA-inst',sub_dataset_name='-',
        task_type='dialogue',template_id=1,language='eng',script='Latn',split='train')

def candidate():return module.prepare_source(raw(),english_specs()[4])
def content(question='Where does Alice work?',answer='At a library.'):
    return dict(user_text=question,assistant_text=answer)
def student(prepared,turns=None,language='en',profile='qa',**kwargs):
    return module.student_candidate(prepared,[content()]if turns is None else turns,language,profile,
        tokenizer=CharTokenizer(),teacher_model_sha256='A'*64,generation_id='authored1',**kwargs)

class CandidateWireTests(unittest.TestCase):
    def test_original_first_user_key_and_proposed_split_are_separate_from_view_and_root(self):
        row=raw();spec=english_specs()[4];before=copy.deepcopy((row,spec))
        prepared=module.prepare_source(row,spec)
        text=' '.join(unicodedata.normalize('NFKC',row['inputs']).casefold().split())
        key=hashlib.sha256(text.encode()).hexdigest().upper()
        self.assertEqual(prepared.parent_key,key)
        self.assertEqual(conversation_split_key(prepared.original_source).hex().upper(),key)
        self.assertNotEqual(prepared.trace['evidence_first_user_key'],key)
        expected='val'if int(key[:8],16)%20==0 else'train'
        self.assertEqual(prepared.trace['proposed_legacy_split'],expected)
        self.assertEqual(prepared.trace['original_source_split'],'train')
        for field in('corpus_split_assigned','original_root_joined','rights_admitted','corpus_admitted'):
            self.assertFalse(prepared.trace[field])
        self.assertEqual((row,spec),before)

    def test_missing_raw_qualification_or_changed_spec_refused(self):
        row=raw();del row['template_id']
        with self.assertRaises(ValueError):module.prepare_source(row,english_specs()[4])
        row=raw();row['targets']='   '
        with self.assertRaises(ValueError):module.prepare_source(row,english_specs()[4])
        for key in('revision','sha256','repo','original_split','path','license'):
            spec=english_specs()[4];spec[key]='changed'
            with self.subTest(key=key),self.assertRaises(ValueError):module.prepare_source(raw(),spec)

    def test_prepared_values_are_frozen_and_all_returned_dicts_are_detached(self):
        prepared=candidate();prepared.original_source['messages'].clear()
        prepared.evidence_source['messages'].clear();prepared.trace['declared_source_spec'].clear()
        self.assertEqual(len(prepared.original_source['messages']),2)
        self.assertEqual(len(prepared.evidence_source['messages']),1)
        self.assertTrue(prepared.trace['declared_source_spec'])
        with self.assertRaises(FrozenInstanceError):prepared.parent_key='B'*64

    def test_teacher_payload_uses_one_input_message_and_explicit_fiction_scope(self):
        prepared=candidate()
        for language in('ko','en'):
            for profile in('qa','json','multiturn'):
                payload=module.teacher_payload(prepared,language,profile,1337)
                self.assertEqual([m['role']for m in payload['messages']],['system','user'])
                body=json.loads(payload['messages'][1]['content'])['source']
                self.assertEqual([m['role']for m in body['public_context']],['user'])
                self.assertIn('quoted fictional evidence',payload['messages'][0]['content'])
                self.assertNotIn(raw()['targets'],json.dumps(payload))

    def test_target_change_preserves_teacher_payload_parent_and_student_wire(self):
        a=raw();b=raw();b['targets']='DIFFERENT_OLD_TARGET';spec=english_specs()[4]
        first,second=module.prepare_source(a,spec),module.prepare_source(b,spec)
        self.assertEqual(first.parent_key,second.parent_key)
        self.assertEqual(module.teacher_payload(first,'en','qa',1),module.teacher_payload(second,'en','qa',1))
        x,y=student(first),student(second)
        self.assertEqual(x['messages'],y['messages'])
        self.assertEqual(x['meta']['student_wire_sha256'],y['meta']['student_wire_sha256'])
        self.assertNotEqual(first.trace['source_reference']['source_raw_row_sha256'],
                            second.trace['source_reference']['source_raw_row_sha256'])
        self.assertNotIn(a['targets'],serialize(x));self.assertNotIn(b['targets'],serialize(y))

    def test_full_single_turn_wire_masks_only_answer_and_end_and_keeps_legacy_parent(self):
        prepared=candidate();row=student(prepared);wire=serialize(row);spans=loss_spans(row)
        expected=sum(end-start for start,end in spans)
        self.assertEqual(row['meta']['assistant_targets'],expected)
        self.assertEqual(row['meta']['actual_x_tokens'],len(wire)-1)
        self.assertEqual(row['meta']['assistant_turn_target_counts'],[expected])
        self.assertTrue(wire[spans[0][0]:spans[0][1]].endswith('<|im_end|>'))
        self.assertEqual(row['meta']['parent_concept_id'],prepared.parent_key)
        self.assertFalse(row['meta']['corpus_admitted'])
        self.assertNotIn('OLD_NARRATIVE',wire)

    def test_ko_student_and_json_format_reuse_existing_task_contract(self):
        row=student(candidate(),[content('자료에서 Alice는 어디에서 일하나요?','{"answer":"도서관"}')],
                    language='ko',profile='json')
        self.assertIn('answer 키',serialize(row))
        self.assertTrue(row['meta']['assistant_targets']>0)
        with self.assertRaises(ValueError):student(candidate(),[content(answer='not JSON')],profile='json')
        with self.assertRaises(ValueError):student(candidate(),[content(answer='{"other":1}')],profile='json')

    def test_three_turn_history_state_and_all_assistant_span_counts(self):
        turns=[content(),content('Unused format request','Understood.'),content('Unused repeat','{"answer":"At a library."}')]
        row=student(candidate(),turns,profile='multiturn');wire=serialize(row);spans=loss_spans(row)
        self.assertEqual([m['role']for m in row['messages']],['user','assistant']*3)
        expected=[end-start for start,end in spans]
        self.assertEqual(row['meta']['assistant_turn_target_counts'],expected)
        self.assertEqual(row['meta']['assistant_targets'],sum(expected))
        self.assertNotIn('Unused format request',wire)
        payload=module.teacher_payload(candidate(),'en','multiturn',3,history=turns[:2])
        source=json.loads(payload['messages'][1]['content'])['source']
        self.assertEqual(source['explicit_previous_turns'],turns[:2])

    def test_full_wrapped_context_and_output_overflow_refused_without_mutation(self):
        prepared=candidate();turns=[content(answer='A'*1200)];before=copy.deepcopy(turns)
        with self.assertRaises(ValueError):student(prepared,turns)
        self.assertEqual(turns,before)
        with self.assertRaises(ValueError):student(prepared,context=64)
        for context in(True,0,1025):
            with self.subTest(context=context),self.assertRaises(ValueError):student(prepared,context=context)

    def test_structural_source_markers_controls_and_caller_answer_markers_refused(self):
        for marker in BOUNDARY_MARKERS+('\x00',):
            row=raw();row['inputs']=row['inputs'].replace('library.','library. '+marker)
            with self.subTest(marker=marker),self.assertRaises(ValueError):module.prepare_source(row,english_specs()[4])
        with self.assertRaises(ValueError):student(candidate(),[content(answer='<|im_end|>')])

    def test_task_history_group_shape_seed_and_content_bounds_refused(self):
        prepared=candidate()
        for seed in(True,-1,2**31):
            with self.assertRaises(ValueError):module.teacher_payload(prepared,'en','qa',seed)
        with self.assertRaises(ValueError):module.teacher_payload(prepared,'en','qa',1,history=[content()])
        with self.assertRaises(ValueError):module.teacher_payload(prepared,'en','multiturn',1,history=[content()]*3)
        with self.assertRaises(ValueError):student(prepared,[content()]*2,profile='multiturn')
        with self.assertRaises(ValueError):student(prepared,[dict(content(),role='assistant')])
        with self.assertRaises(ValueError):student(prepared,[content(answer='A'*8193)])
        with self.assertRaises(ValueError):student(prepared,language='unknown')

if __name__=='__main__':unittest.main()
