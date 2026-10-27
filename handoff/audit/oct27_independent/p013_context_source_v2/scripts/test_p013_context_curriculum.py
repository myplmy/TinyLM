"""Window-position coverage and source-RNG continuation, no learned model."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from tinylm.train.context_curriculum import ContextCursor, ContextPlan, split_update


class Sampler:
    def __init__(self, *, seed=1337, bs=2, seq=16):
        self.rng = np.random.default_rng(seed)
        self.bs, self.seq, self.calls = bs, seq, 0

    def __call__(self):
        starts = self.rng.integers(0, 100000, self.bs)
        t = torch.from_numpy(starts[:, None]+np.arange(self.seq+1))
        self.calls += 1
        return t[:, :-1], t[:, 1:]


def plan():
    return ContextPlan(((1, 4), (2, 8), (3, 16)), micro_bs=2, base_accum=2, full_length=16)


class ContextContract(unittest.TestCase):
    def test_explicit_integer_stages_and_final_full_length_required(self):
        for stages in ((), ((1, 4), (1, 16)), ((1, 8), (2, 4), (3, 16)),
                       ((1, 3), (2, 16)), ((1.0, 4), (2, 16)), ((True, 4), (2, 16)), ((1, 4),)):
            with self.subTest(stages=stages), self.assertRaises(ValueError):
                ContextPlan(stages, full_length=16)
        with self.assertRaises(ValueError):
            ContextPlan(((2, 16),), micro_bs=True, full_length=16)

    def test_full_300m_accounting_is_draw_not_unique_epoch(self):
        p = ContextPlan(((458, 256), (916, 512), (2289, 1024)))
        self.assertEqual(p.tokens_per_update, 131072)
        self.assertEqual(p.contract()['draw_tokens'], 300023808)
        self.assertFalse(p.contract()['unique_epoch_claim'])
        self.assertEqual([s['active_accum'] for s in p.summary()['stages']], [64, 32, 16])
        self.assertEqual(sum(s['source_calls'] for s in p.summary()['stages']), 2289*16)

    def test_all_original_xy_positions_exactly_once_including_chunk_final_target(self):
        p = plan(); s = Sampler(); source = tuple(s() for _ in range(p.base_accum))
        for length in (4, 8, 16):
            result = split_update(source, p, length)
            rows = [(x[row], y[row]) for x, y in result.batches for row in range(p.micro_bs)]
            counts = torch.zeros(p.base_accum, p.micro_bs, p.full_length, dtype=torch.long)
            self.assertEqual(len(rows), len(result.origins))
            for (x, y), (draw, row, start, end) in zip(rows, result.origins):
                self.assertTrue(torch.equal(x, source[draw][0][row, start:end]))
                self.assertTrue(torch.equal(y, source[draw][1][row, start:end]))
                counts[draw, row, start:end] += 1
            self.assertTrue(torch.equal(counts, torch.ones_like(counts)))
            self.assertEqual(result.accounting['ntp_targets'], p.tokens_per_update)
            self.assertEqual(rows[-1][1][-1], source[-1][1][-1, -1])

    def test_full_length_does_not_replace_original_tensor_objects(self):
        p = plan(); source = tuple(Sampler()() for _ in range(p.base_accum))
        result = split_update(source, p, p.full_length)
        for got, original in zip(result.batches, source):
            self.assertIs(got[0], original[0]); self.assertIs(got[1], original[1])
        self.assertEqual(result.accounting['added_context_resets'], 0)

    def test_global_target_denominator_on_context_independent_numeric_oracle(self):
        # This oracle ignores context, so changing its batching must preserve CE
        # and gradients. Actual causal Transformer gradients need not be equal.
        p=plan(); raw=tuple(Sampler()() for _ in range(p.base_accum))
        source=tuple((x.remainder(32),y.remainder(32)) for x,y in raw)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(17)
            original=torch.nn.Sequential(torch.nn.Embedding(32,8),torch.nn.Linear(8,32))
        reference=None
        for length in (16,8,4):
            model=deepcopy(original); loss_sum=0.
            result=split_update(source,p,length)
            for x,y in result.batches:
                loss=torch.nn.functional.cross_entropy(model(x).reshape(-1,32),y.reshape(-1),reduction='sum')/p.tokens_per_update
                loss.backward();loss_sum+=float(loss.detach())
            grads=tuple(q.grad.clone() for q in model.parameters())
            if reference is None:reference=(loss_sum,grads)
            else:
                self.assertAlmostEqual(loss_sum,reference[0],places=6)
                self.assertTrue(all(torch.allclose(a,b,atol=1e-7,rtol=1e-6) for a,b in zip(grads,reference[1])))

    def test_wrong_shift_sft_masks_dtype_and_partial_tail_refused(self):
        p = plan(); good = tuple(Sampler()() for _ in range(p.base_accum))
        for kind in ('shift', 'ignore', 'dtype', 'shape', 'mask'):
            x, y = (v.clone() for v in good[0])
            if kind == 'shift': y[0, 0] += 1
            elif kind == 'ignore': y[0, 0] = -100
            elif kind == 'dtype': x = x.int()
            elif kind == 'shape': x, y = x[:, :-1], y[:, :-1]
            first = (x, y, torch.ones_like(x)) if kind == 'mask' else (x, y)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                split_update((first, good[1]), p, 4)

    def test_fixed_source_calls_and_rng_match_independent_full_window_sampler(self):
        p = plan(); s, oracle = Sampler(), Sampler()
        c = ContextCursor(p, s, source_sha256='A'*64)
        for update in range(3):
            result = c.prepare(); expected = tuple(oracle() for _ in range(2))
            self.assertEqual(result.length, (4, 8, 16)[update])
            for (xx, yy), origin in zip([(x[i], y[i]) for x,y in result.batches for i in range(2)], result.origins):
                draw, row, start, end = origin
                self.assertTrue(torch.equal(xx, expected[draw][0][row, start:end]))
                self.assertTrue(torch.equal(yy, expected[draw][1][row, start:end]))
            c.finish(optimizer_applied=False)
            self.assertEqual(s.rng.bit_generator.state, oracle.rng.bit_generator.state)
        self.assertEqual(s.calls, 6)
        with self.assertRaises(StopIteration): c.prepare()
        self.assertEqual(s.calls, 6)

    def test_resume_after_json_roundtrip_matches_every_next_position(self):
        p = plan(); a = ContextCursor(p, Sampler(), source_sha256='A'*64)
        a.prepare(); a.finish(optimizer_applied=True)
        saved = json.loads(json.dumps(a.state_dict()))
        b = ContextCursor(p, Sampler(seed=999), source_sha256='A'*64); b.load_state_dict(saved)
        for _ in range(2):
            left, right = a.prepare(), b.prepare()
            self.assertEqual(left.accounting, right.accounting)
            for aa, bb in zip(left.batches, right.batches):
                self.assertTrue(all(torch.equal(x,y) for x,y in zip(aa,bb)))
            a.finish(optimizer_applied=True); b.finish(optimizer_applied=True)
        self.assertEqual(a.state_dict(), b.state_dict())

    def test_each_source_draw_is_snapshotted_before_scratch_buffer_reuse(self):
        class Reusing(Sampler):
            def __init__(self):
                super().__init__(); self.buffer=torch.empty(self.bs,self.seq+1,dtype=torch.long)
            def __call__(self):
                x,y=super().__call__()
                self.buffer[:,:-1].copy_(x); self.buffer[:,-1].copy_(y[:,-1])
                return self.buffer[:,:-1], self.buffer[:,1:]
        p=plan(); cursor=ContextCursor(p,Reusing(),source_sha256='A'*64)
        oracle=Sampler(); originals=tuple(oracle() for _ in range(p.base_accum)); result=cursor.prepare()
        rows=[(x[i],y[i]) for x,y in result.batches for i in range(p.micro_bs)]
        for (x,y),(draw,row,start,end) in zip(rows,result.origins):
            self.assertTrue(torch.equal(x,originals[draw][0][row,start:end]))
            self.assertTrue(torch.equal(y,originals[draw][1][row,start:end]))
        self.assertEqual(result.accounting['source_snapshot_bytes'],2*p.tokens_per_update*8)
        self.assertEqual(cursor.sampler.calls,p.base_accum)

    def test_skipped_optimizer_is_still_a_consumed_draw_update(self):
        c = ContextCursor(plan(), Sampler(), source_sha256='A'*64)
        c.prepare(); record = c.finish(optimizer_applied=False)
        state = c.state_dict()
        self.assertFalse(record['optimizer_applied'])
        self.assertEqual((state['next_update'],state['optimizer_updates'],state['draw_tokens']), (1,0,64))

    def test_mid_update_and_double_finish_cannot_save_or_redraw(self):
        c = ContextCursor(plan(), Sampler(), source_sha256='A'*64)
        c.prepare(); calls = c.sampler.calls
        for action in (c.prepare,c.state_dict):
            with self.assertRaises(RuntimeError): action()
        self.assertEqual(c.sampler.calls, calls)
        c.finish(optimizer_applied=False)
        with self.assertRaises(RuntimeError): c.finish(optimizer_applied=False)

    def test_incompatible_or_damaged_resume_does_not_mutate_source_rng(self):
        a = ContextCursor(plan(), Sampler(), source_sha256='A'*64)
        a.prepare();a.finish(optimizer_applied=False); state=a.state_dict()
        for kind in ('checksum','source','plan'):
            source=Sampler(seed=7); before=deepcopy(source.rng.bit_generator.state)
            p=ContextPlan(((3,16),),micro_bs=2,base_accum=2,full_length=16) if kind=='plan' else plan()
            b=ContextCursor(p,source,source_sha256=('B' if kind=='source' else 'A')*64)
            value=deepcopy(state)
            if kind=='checksum': value['next_update']=2
            with self.subTest(kind=kind),self.assertRaises(ValueError):b.load_state_dict(value)
            self.assertEqual(before,source.rng.bit_generator.state)

    def test_failed_source_marks_cursor_unresumable(self):
        class Broken(Sampler):
            def __call__(self):
                super().__call__(); raise RuntimeError('source failed after RNG advanced')
        c=ContextCursor(plan(),Broken(),source_sha256='A'*64)
        with self.assertRaisesRegex(RuntimeError,'source failed'):c.prepare()
        for action in (c.state_dict,c.prepare):
            with self.assertRaises(RuntimeError):action()


if __name__ == '__main__':
    unittest.main()
