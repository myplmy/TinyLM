"""Tiny fresh token/graph oracles only; no Native model or corpus."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import unittest

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint

from scripts import p106b_dskdv2_contract as dense
from scripts.p106b_dskdv2_microbatch import CausalMicrobatchFrames
from scripts.p106b_dskdv2_training import CEKDGroup
from scripts.p106b_dskdv2_window import StudentFrame
from scripts.p106b_feature_window import FeatureWindow
from tinylm.train.mtp_sft import Record, pad_records

CONTROLS = []
ROOTS = []
CALLS = dict(fresh_fixture_models=0, forwards=0, manual_backwards=0, adapter_backwards=0)


class TinyTokenStudent(torch.nn.Module):
    def __init__(self, dtype, *, dropout=0., checkpoint_body=False):
        super().__init__()
        generator = torch.Generator(device='cpu').manual_seed(1337)
        self.embedding = torch.nn.Parameter(torch.randn((11, 2), generator=generator, dtype=dtype) * .2)
        self.input_projection = torch.nn.Parameter(torch.randn((2, 3), generator=generator, dtype=dtype) * .3)
        self.body = torch.nn.Parameter(torch.randn((3, 3), generator=generator, dtype=dtype) * .3)
        self.up = torch.nn.Parameter(torch.randn((3, 2), generator=generator, dtype=dtype) * .2)
        self.register_buffer('forward_count', torch.zeros((), dtype=torch.long))
        self.dropout = dropout
        self.checkpoint_body = checkpoint_body
        self._wq = None
        self.bad_shape = False
        self.shapes = []
        CALLS['fresh_fixture_models'] += 1

    def _emb_w(self): return self.embedding
    def _emb_up_w(self): return self.up
    def embedding_quantized(self): return None
    def _head_logits(self, hidden): return F.linear(F.linear(hidden, self.up.T), self.embedding)

    def forward(self, x, *, return_hidden, use_cache, past_kv):
        assert return_hidden is True and use_cache is False and past_kv is None
        assert x.dtype == torch.long and x.device.type == 'cpu'
        self.forward_count += 1
        self.shapes.append(list(x.shape))
        CALLS['forwards'] += 1
        self._wq = torch.tanh(self.body)
        base = F.embedding(x, self.embedding) @ self.input_projection
        def work(values):
            hidden = torch.tanh(values @ self._wq)
            # Batch coupling intentionally makes accidental row-wise forwarding wrong.
            hidden = hidden + .2 * hidden.mean(dim=0, keepdim=True)
            return F.dropout(hidden, self.dropout, training=self.training)
        hidden = checkpoint(work, base, use_reentrant=False, preserve_rng_state=True) if self.checkpoint_body else work(base)
        return hidden[:, :-1] if self.bad_shape else hidden


class Fixture:
    def __init__(self, *, dtype=torch.float64, dropout=0., checkpoint_body=False, write_features=True):
        base = Path(os.environ['TL_DSKD_MICROBATCH_FIXTURE_ROOT'])
        self.root = base / ('fixture_%03d' % len(ROOTS))
        self.root.mkdir(exist_ok=False)
        ROOTS.append(str(self.root))
        self.model = TinyTokenStudent(dtype, dropout=dropout, checkpoint_body=checkpoint_body)
        generator = torch.Generator(device='cpu').manual_seed(2024)
        self.teacher = torch.randn((13, 4), generator=generator, dtype=dtype) * .2
        self.t2s = torch.nn.Parameter(torch.randn((4, 3), generator=generator, dtype=dtype) * .2)
        self.s2t = torch.randn((3, 4), generator=generator, dtype=dtype) * .2
        self.mapping = [i % 11 for i in range(13)]
        self.modes = [1 if i % 2 else 3 for i in range(13)]
        self.rows, self.packed = [], []
        for i in range(17):
            n = 6+i % 2
            ids = [(i+j*3) % 11 for j in range(n)]
            labels = [v if j in (1, 2, n-2, n-1) else -100 for j, v in enumerate(ids)]
            owners = [1+i % 3 if label != -100 else 0 for label in labels]
            packed = dict(ids=ids, labels=labels, turn_ids=owners)
            raw = json.dumps(packed, sort_keys=True, separators=(',', ':')).encode()
            self.packed.append(packed)
            self.rows.append(dict(row_id='r%02d' % i, semantic_root_id='root_%02d' % i,
                record_sha256=hashlib.sha256(b'record'+raw).hexdigest().upper(),
                source_row_sha256=hashlib.sha256(b'source'+raw).hexdigest().upper(),
                student_tokens=n, split='train', ce_targets=sum(v != -100 for v in labels)))
        self.features, self.records = {}, []
        if write_features:
            for i in (0, 7, 8, 16):
                row, packed = self.rows[i], self.packed[i]
                array = (np.linspace(-.5, .6, 24, dtype=np.float32).reshape(6, 4)+i*.01).astype(np.float32)
                path = self.root/(row['row_id']+'.npy')
                with path.open('xb') as f: np.save(f, array, allow_pickle=False)
                positions = []
                for si, ti in zip((len(packed['ids'])-2, 0, 1), (4, 0, 2)):
                    native = (ti+i) % 13
                    positions.append(dict(student_predictor_raw_index=si, student_target_raw_index=si+1,
                        teacher_predictor_raw_index=ti, teacher_target_raw_index=ti+1,
                        student_target_id=packed['labels'][si+1], teacher_native_argmax=native,
                        mapped_student_argmax=self.mapping[native], mapping_mode=self.modes[native],
                        owner=packed['turn_ids'][si+1], lookahead_bytes=0, accepted=True))
                self.features[row['row_id']] = array
                self.records.append(dict(row, teacher_tokens=6, feature_file=path.name,
                    feature_sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(), positions=positions))
        with (self.root/'fixture_tokens_and_positions.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(rows=self.rows,packed_students=self.packed,feature_records=self.records,
                schema='NEW_NUMERICAL_TOKENS_NOT_LANGUAGE_OR_CORPUS_V1'),stream,sort_keys=True)
            stream.write('\n')

    def parameters(self): return list(self.model.parameters())+[self.t2s]

    def group(self, *, kd=True):
        reader = FeatureWindow(self.records, root=self.root, identities={key:letter*64 for key,letter in zip(
            ('teacher_sha256','tokenizer_sha256','mapping_sha256','data_sha256'),'ABCD')},
            split='train', hidden_width=4, batch_positions=5) if kd else None
        return CEKDGroup(self.model, self.rows, up=self.model.up, embedding=self.model.embedding,
            student_width=8, reader=reader, teacher_head=self.teacher, t2s=self.t2s, s2t=self.s2t,
            teacher_width=8, mapping=self.mapping, mapping_modes=self.modes, chunk_positions=2,
            ce_chunk=3, checkpoint_heads=True, kd_rate=.3, parameters=self.parameters())

    def adapter(self, **kwargs):
        return CausalMicrobatchFrames(self.model, self.rows, self.packed,
            student_width=8, batch_size=8, pad_id=0, **kwargs)

    def reference(self, *, kd=True):
        model = TinyTokenStudent(self.model.body.dtype, dropout=self.model.dropout,
                                 checkpoint_body=self.model.checkpoint_body)
        model.load_state_dict(copy.deepcopy(self.model.state_dict()))
        projector = torch.nn.Parameter(self.t2s.detach().clone())
        records = [Record(row['ids'][:-1], row['labels'][1:], row['turn_ids'][1:]) for row in self.packed]
        total, ce_total, kd_total = 0., 0., 0.
        by_id = {row['row_id']:row for row in self.records}
        denominator = sum(row['ce_targets'] for row in self.rows)
        kd_denominator = sum(len(row['positions']) for row in self.records) if kd else 0
        torch.manual_seed(12345)
        for start in range(0, 17, 8):
            x, y, owners = pad_records(records[start:start+8], 0, 'cpu', fixed_width=8, batch_size=8)
            hidden = model(x, return_hidden=True, use_cache=False, past_kv=None)
            logits = hidden @ model.up @ model.embedding.T
            ce_sum = F.cross_entropy(logits.reshape(-1, 11), y.reshape(-1), ignore_index=-100, reduction='sum')
            loss = ce_sum/denominator
            ce_total += float(ce_sum.detach())
            if kd:
                for local, row in enumerate(self.rows[start:start+8]):
                    if row['row_id'] not in by_id: continue
                    record = by_id[row['row_id']]
                    positions = record['positions']
                    si = [p['student_predictor_raw_index'] for p in positions]
                    ti = [p['teacher_predictor_raw_index'] for p in positions]
                    targets = torch.tensor([p['mapped_student_argmax'] for p in positions])
                    ht = torch.tensor(self.features[row['row_id']][ti], dtype=model.body.dtype)
                    terms = dense.dskd_sums(hidden[local, si], ht, model.up @ model.embedding.T,
                        self.teacher.T, projector, self.s2t, targets)
                    loss = loss+.3*terms['total_sum']/kd_denominator
                    kd_total += float(terms['total_sum'].detach())
            loss.backward()
            CALLS['manual_backwards'] += 1
            total += float(loss.detach())
        return dict(model=model, projector=projector, loss=total, ce_sum=ce_total, kd_sum=kd_total,
            rng=torch.get_rng_state().clone(), ce_denominator=denominator, kd_denominator=kd_denominator)


class MicrobatchFrameTests(unittest.TestCase):
    def compare(self, *, dtype, kd, dropout=0., checkpoint_body=False):
        f = Fixture(dtype=dtype, dropout=dropout, checkpoint_body=checkpoint_body, write_features=kd)
        before = [p.detach().clone() for p in f.parameters()]
        expected = f.reference(kd=kd)
        adapter, group = f.adapter(), f.group(kd=kd)
        contexts = []
        def backward(loss, context):
            contexts.append(dict(context))
            loss.backward(retain_graph=context['retain_graph'])
            CALLS['adapter_backwards'] += 1
        torch.manual_seed(12345)
        actual = adapter.consume(group, backward)
        rng_exact = torch.equal(torch.get_rng_state(), expected['rng'])
        self.assertTrue(rng_exact)
        atol, rtol = (2e-10, 2e-9) if dtype == torch.float64 else (3e-5, 3e-4)
        self.assertTrue(abs(actual['group']['normalized_total']-expected['loss']) <= atol+rtol*abs(expected['loss']))
        pairs = list(zip(f.model.parameters(), expected['model'].parameters()))+[(f.t2s, expected['projector'])]
        gradient_arrays=[]
        maximum = 0.
        gradient_tensors = 0
        for original, reference in pairs:
            if reference.grad is None:
                self.assertIsNone(original.grad)
            else:
                self.assertIsNotNone(original.grad)
                torch.testing.assert_close(original.grad, reference.grad, atol=atol, rtol=rtol)
                maximum = max(maximum, float((original.grad-reference.grad).abs().max()))
                gradient_tensors += 1
            gradient_arrays.append(dict(shape=list(original.shape),dtype=str(original.dtype),
                actual=None if original.grad is None else original.grad.detach().tolist(),
                reference=None if reference.grad is None else reference.grad.detach().tolist()))
        self.assertTrue(all(torch.equal(p.detach(), old) for p, old in zip(f.parameters(), before)))
        self.assertIsNone(f.teacher.grad); self.assertIsNone(f.s2t.grad)
        self.assertEqual(actual['group']['global_ce_denominator'], expected['ce_denominator'])
        self.assertEqual(actual['group']['global_kd_denominator'], expected['kd_denominator'])
        self.assertEqual(actual['group']['original_ce_order'], [r['row_id'] for r in f.rows])
        self.assertEqual(actual['provider_rows'], 17)
        self.assertEqual(actual['forward_calls'], 3)
        self.assertEqual(f.model.shapes, [[8,8]]*3)
        self.assertEqual(expected['model'].shapes, [[8,8]]*3)
        self.assertEqual([v['dummy_rows'] for v in actual['microbatches']], [0,0,7])
        self.assertEqual(sum(not c['retain_graph'] for c in contexts), 3)
        self.assertTrue(all(c['microbatch_last_real_row'] and c['row_complete']
                            for c in contexts if not c['retain_graph']))
        self.assertEqual(adapter.phase, 'CLOSED'); self.assertIsNone(adapter._active)
        self.assertEqual(actual['owned_active_graphs'], 0)
        self.assertFalse(actual['full_training_resume_or_scaler_optimizer_integration'])
        with self.assertRaises(RuntimeError): adapter.consume(group, backward)
        CONTROLS.append(dict(name='DENSE_FIXED_MICROBATCH_ORACLE', dtype=str(dtype), kd=kd,
            dropout=dropout, checkpoint_body=checkpoint_body, numerical_parameters=sum(p.numel() for p in f.parameters()),
            gradient_tensors=gradient_tensors, maximum_gradient_absolute_error=maximum,
            actual_loss=actual['group']['normalized_total'], reference_loss=expected['loss'],
            atol=atol, rtol=rtol, Torch_RNG_exact=rng_exact, forward_calls=3, shape=[8,8],
            real_rows=17, dummy_rows=[0,0,7], ce_denominator=expected['ce_denominator'],
            kd_denominator=expected['kd_denominator'], backward_callback_calls=len(contexts),
            retained_callbacks=actual['retained_callbacks'], released_callbacks=3,
            all_parameters_unchanged=True, frozen_teacher_reverse_gradient_free=True,
            full_tiny_gradient_arrays=gradient_arrays,fixture_root=str(f.root)))

    def test_fp64_complete_ce_kd_original_fixed_batches(self):
        self.compare(dtype=torch.float64, kd=True)

    def test_fp32_dropout_checkpoint_shared_cache_and_RNG(self):
        self.compare(dtype=torch.float32, kd=True, dropout=.25, checkpoint_body=True)

    def test_ce_only_keeps_projector_inactive(self):
        self.compare(dtype=torch.float64, kd=False)

    def test_naive_row_graph_policy_is_a_caught_negative_control(self):
        f = Fixture(write_features=False)
        records = [Record(r['ids'][:-1], r['labels'][1:], r['turn_ids'][1:]) for r in f.packed[:8]]
        x,y,owners = pad_records(records,0,'cpu',fixed_width=8,batch_size=8)
        hidden = f.model(x,return_hidden=True,use_cache=False,past_kv=None)
        cursor = 0
        def provider(row):
            nonlocal cursor
            i = cursor; cursor += 1
            return StudentFrame(row['row_id'],row['semantic_root_id'],row['record_sha256'],hidden[i],y[i],owners[i])
        group = f.group(kd=False)
        with self.assertRaisesRegex(RuntimeError,'backward through the graph'):
            group.consume(provider, lambda loss,context:loss.backward(retain_graph=context['retain_graph']))
        self.assertEqual(group.phase,'FAILED')
        self.assertGreaterEqual(cursor,2)
        CONTROLS.append(dict(name='PLAIN_ROW_FINAL_GRAPH_FREE_NEGATIVE_CONTROL',expected_exception=True,
            forward_calls=1,model_quality_claim=False))

    def test_one_shift_label_owner_and_original_count_faults_precede_forward(self):
        f = Fixture(write_features=False)
        faults = []
        for fault in ('raw_count','double_shift','target_identity','owner','first_target','duplicate_row'):
            rows, packed = copy.deepcopy(f.rows), copy.deepcopy(f.packed)
            if fault == 'raw_count': rows[0]['student_tokens'] -= 1
            elif fault == 'double_shift': packed[0] = {k:v[1:] for k,v in packed[0].items()}
            elif fault == 'target_identity': packed[0]['labels'][1] = (packed[0]['ids'][1]+1)%11
            elif fault == 'owner': packed[0]['turn_ids'][1] = 0
            elif fault == 'first_target': packed[0]['labels'][0]=packed[0]['ids'][0];packed[0]['turn_ids'][0]=1
            else: rows[1]['row_id']=rows[0]['row_id']
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                CausalMicrobatchFrames(f.model,rows,packed,student_width=8,batch_size=8,pad_id=0)
            faults.append(fault)
        self.assertEqual(int(f.model.forward_count),0)
        CONTROLS.append(dict(name='PRE_FORWARD_ORIGINAL_TOKEN_FAULTS',faults=faults,forwards=0))

    def test_quant_cache_or_parameter_mutation_invalidates_and_rejects_reuse(self):
        for fault in ('cache','parameter','targets'):
            with self.subTest(fault=fault):
                f = Fixture(write_features=False)
                adapter, group = f.adapter(), f.group(kd=False)
                def backward(loss,context):
                    loss.backward(retain_graph=context['retain_graph'])
                    if fault == 'cache': f.model._wq=f.model._wq.detach().clone()
                    elif fault == 'parameter':
                        with torch.no_grad(): f.model.body.add_(0.)
                    else: adapter._active[3][0,0]=-100
                with self.assertRaises(ValueError): adapter.consume(group,backward)
                self.assertEqual(adapter.phase,'FAILED');self.assertEqual(group.phase,'FAILED')
                self.assertIsNone(adapter._active);self.assertIsNone(adapter._cache_pins)
                with self.assertRaises(RuntimeError):adapter.consume(group,backward)
        CONTROLS.append(dict(name='IN_FLIGHT_CACHE_PARAMETER_TARGET_MUTATION',faults=3,
            failed_objects_not_reusable=True,owned_references_released=True,partial_gradients_rollback_claim=False))

    def test_bad_hidden_shape_releases_failed_adapter_references(self):
        f = Fixture(write_features=False)
        adapter, group = f.adapter(),f.group(kd=False)
        f.model.bad_shape=True
        with self.assertRaisesRegex(ValueError,'fixed-size original hidden'):
            adapter.consume(group,lambda loss,context:loss.backward(retain_graph=context['retain_graph']))
        self.assertEqual(adapter.phase,'FAILED');self.assertIsNone(adapter._active)
        self.assertEqual(int(f.model.forward_count),1)
        CONTROLS.append(dict(name='BAD_FORWARD_SHAPE_INVALIDATES',expected_exception=True,owned_graphs=0))

    def test_preflight_group_order_and_unsupported_cache_mode(self):
        f = Fixture(write_features=False)
        adapter = f.adapter()
        wrong = copy.deepcopy(f.rows);wrong[0],wrong[1]=wrong[1],wrong[0]
        group=CEKDGroup(f.model,wrong,up=f.model.up,embedding=f.model.embedding,student_width=8,
            reader=None,parameters=f.parameters())
        with self.assertRaises(ValueError):adapter.consume(group,lambda *_:None)
        self.assertEqual(adapter.phase,'READY');self.assertEqual(int(f.model.forward_count),0)
        for attribute,value in (('_quant_frozen',True),('_p102a_quant_update',[]),('_unpack_cache',True)):
            setattr(f.model,attribute,value)
            with self.assertRaises(ValueError):f.adapter()
            setattr(f.model,attribute,False if attribute!='_p102a_quant_update'else None)
        self.assertEqual(int(f.model.forward_count),0)
        CONTROLS.append(dict(name='GROUP_ORDER_AND_UNSUPPORTED_CACHE_PREFLIGHT',expected_faults=4,forwards=0))


if __name__ == '__main__':
    unittest.main()
