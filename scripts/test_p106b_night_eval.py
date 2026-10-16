from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import copy
from types import SimpleNamespace
from unittest.mock import patch
from scripts import diag_p106b_night_eval as e


class Eval(unittest.TestCase):
    def test_actual_history_is_not_replaced_by_gold(self):
        row = dict(messages=[dict(role='user', content='q1'), dict(role='assistant', content='5'),
            dict(role='user', content='q2'), dict(role='assistant', content='6')],
            meta=dict(semantic_root_id='r', kind='update', language='en'))
        calls = []
        def emit(messages):
            calls.append(messages)
            return ('wrong' if len(messages) == 1 else 'answer'), dict(finish_reason='EOT')
        events = e.dialogue(row, emit)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[1]['messages'][1]['content'], 'wrong')
        self.assertEqual(events[2]['messages'][1]['content'], '5')
        self.assertEqual(events[1]['history'], 'ACTUAL_MODEL')
        self.assertEqual(events[2]['history'], 'GOLD_REFERENCE')
        self.assertEqual(e.summarize_dialogue(events)['ACTUAL_MODEL/all']['n'], 2)

    def test_duplicate_retention_event_refused(self):
        row = dict(messages=[dict(role='user', content='q'), dict(role='assistant', content='a')],
            meta=dict(semantic_root_id='r', kind='arithmetic', language='ko'))
        events = e.dialogue(row, lambda messages: ('a', dict(finish_reason='EOT')))
        with self.assertRaises(ValueError): e.summarize_dialogue(events * 2)

    def test_frozen_dialogue_gold_and_prefix_recount(self):
        row = dict(messages=[dict(role='user', content='q1'), dict(role='assistant', content='5'),
            dict(role='user', content='q2'), dict(role='assistant', content='6')],
            meta=dict(semantic_root_id='r', kind='update', language='en'))
        events = e.dialogue(row, lambda messages: ('wrong', dict(finish_reason='EOT')))
        self.assertEqual(e.verify_dialogue_rows(events, [row]), e.summarize_dialogue(events))
        changed = copy.deepcopy(events); changed[-1]['gold'] = 'wrong'
        with self.assertRaises(ValueError): e.verify_dialogue_rows(changed, [row])
        changed = copy.deepcopy(events); changed[1]['messages'][1]['content'] = '5'
        with self.assertRaises(ValueError): e.verify_dialogue_rows(changed, [row])

    def test_public_id_gold_argmin_guards(self):
        case = dict(task='piqa', kind='mc', item=dict(_iid='piqa#1', gold=1, choices=['a', 'b']))
        event = dict(task='piqa', id='piqa#1', kind='mc', skipped=False,
                     gold=1, sum_nll=[2., 1.], pred_harness=1)
        self.assertEqual(e.public_recount([event], [case])['piqa']['correct'], 1)
        for field, value in (('gold', 0), ('pred_harness', 0), ('id', 'unknown')):
            changed = dict(event, **{field: value})
            with self.assertRaises(ValueError): e.public_recount([changed], [case])
        with self.assertRaises(ValueError): e.public_recount([event, event], [case])
        with self.assertRaises(ValueError): e.public_recount([], [case])
        for reason in ('gold_missing', 'seq_max_exceeded'):
            changed = dict(event, skipped=True, reason=reason)
            with self.assertRaises(ValueError): e.public_recount([changed], [case])

    def test_cpu_mc_eligibility_includes_continuation(self):
        class Tok:
            def encode(self, value): return SimpleNamespace(ids=list(range(len(value))))
        item = dict(ctx='abcdef', choices=['a', 'bbbb'], gold=1)
        self.assertIsNone(e.mc_skip_reason(item, Tok(), 10))
        self.assertEqual(e.mc_skip_reason(item, Tok(), 9), 'seq_max_exceeded')
        self.assertEqual(e.mc_skip_reason(dict(item, gold=-1), Tok()), 'gold_missing')

    def test_root_children_kept_together(self):
        rows = [dict(meta=dict(neutral_root=r, semantic_root_id=r + str(i))) for r in 'abc' for i in range(4)]
        subset = e.root_subset(rows, 2)
        self.assertEqual(len(subset), 8)
        self.assertEqual(len({r['meta']['neutral_root'] for r in subset}), 2)

    def test_parent_checkpoint_is_exact(self):
        self.assertEqual(e.checkpoint_spec('parent'), (e.c.PARENT, e.c.PARENT_SHA))

    def test_context_overflow_preserves_actual_prompt_and_empty_output_sha(self):
        class Tok:
            def encode(self, value): return SimpleNamespace(ids=list(range(1024)))
        with patch.object(e.train, 'deadline', lambda: None):
            emit = e.emit_function(object(), SimpleNamespace(max_seq_len=1024), Tok())
            answer, generation = emit([dict(role='user', content='question')])
        self.assertEqual(answer, '')
        self.assertEqual(generation['finish_reason'], 'CONTEXT_BUDGET_EXHAUSTED')
        self.assertEqual(generation['raw_answer_sha256'], e.c.data.sha(''))
        self.assertEqual(len(generation['actual_prompt_sha256']), 64)

    def test_all_lanes_and_native_consumers_required(self):
        inputs = dict(native_val_sha256='val', native256_val_offsets=list(range(256)))
        r = dict(status='ACTUAL_EVALUATION_COMPLETE', endpoint='parent', checkpoints_written=0,
                 directory=str((e.LOCAL / 'parent').relative_to(e.ROOT)), outputs={k: {} for k in e.OUTPUTS})
        for lane in e.OUTPUTS - {'native32', 'native256'}:
            r['outputs'][lane] = dict(counts=dict(n=1), manifest=dict(schema='P106B_WRITE_ONCE_SHARDS_V1',
                rows=1, shards=[dict(path='fixture_000000.jsonl')]))
        r['outputs']['native32'] = dict(ce=3.5, val_sha256='val', crops=32, targets=32768)
        r['outputs']['native256'] = dict(ce=3.5, val_sha256='val', windows=256, targets=262144,
            precision='FP32_MATH', offsets_sha256=e.c.data.sha(inputs['native256_val_offsets']))
        e.endpoint_contract(r, 'parent', inputs)
        for lane in e.OUTPUTS:
            changed = copy.deepcopy(r); del changed['outputs'][lane]
            with self.assertRaises(ValueError): e.endpoint_contract(changed, 'parent', inputs)
        for lane in e.OUTPUTS - {'native32', 'native256'}:
            changed = copy.deepcopy(r); changed['outputs'][lane] = {}
            with self.assertRaises(ValueError): e.endpoint_contract(changed, 'parent', inputs)
        for key, value in (('status', 'PARTIAL'), ('endpoint', 'ce'), ('directory', '../other')):
            changed = dict(r, **{key: value})
            with self.assertRaises(ValueError): e.endpoint_contract(changed, 'parent', inputs)
        for key, value in (('targets', 1), ('windows', 2), ('ce', float('nan')), ('offsets_sha256', 'wrong')):
            changed = copy.deepcopy(r); changed['outputs']['native256'][key] = value
            with self.assertRaises(ValueError): e.endpoint_contract(changed, 'parent', inputs)


if __name__ == '__main__': unittest.main()
