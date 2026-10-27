"""CPU-only default-reference equivalence, no checkpoint or real corpus.

The historical source is a byte-pinned audit copy, never an active replacement.
"""
from pathlib import Path
import ast
import copy
import hashlib
import json
import os
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OMP_NUM_THREADS'] = '1'
import tinylm
import torch
from tinylm.train import mtp_sft as current

OLD_SHA = 'EF508EC83AA16FE37674516A77A3E5B43D69545C05E52E8C6AC34765255BC657'
NEW_SHA = 'D700B91EAFCC03B1834B865B89D9CEC32BBB8F4936386BB7FB5A37C521799D9D'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class ReferenceOnly(ast.NodeTransformer):
    def __init__(self):
        self.removed_branches = 0
        self.removed_arguments = 0

    def visit_If(self, node):
        target = ast.parse("ce_backend != 'reference'", mode='eval').body
        if ast.dump(node.test) == ast.dump(target):
            assert not node.orelse
            self.removed_branches += 1
            return None
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name == 'components':
            assert node.args.args[-1].arg == 'ce_backend'
            assert ast.literal_eval(node.args.defaults[-1]) == 'reference'
            node.args.args.pop()
            node.args.defaults.pop()
            self.removed_arguments += 1
        return self.generic_visit(node)


class ToyHead(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.heads = torch.nn.ModuleList([torch.nn.Linear(7, 19) for _ in range(4)])

    def _head_logits(self, hidden):
        return self.heads[0](hidden)

    def mtp_aux_logits(self, hidden, horizon):
        return self.heads[horizon-1](hidden)


def main():
    started = time.perf_counter()
    torch.set_num_threads(1)
    old_path = Path(__file__).with_name('p078_mtp_reference_legacy.source')
    new_path = ROOT/'tinylm/train/mtp_sft.py'
    assert sha(old_path) == OLD_SHA and sha(new_path) == NEW_SHA
    old_tree = ast.parse(old_path.read_text())
    transform = ReferenceOnly()
    new_tree = transform.visit(ast.parse(new_path.read_text()))
    assert (transform.removed_branches, transform.removed_arguments) == (2, 1)
    assert ast.dump(old_tree) == ast.dump(new_tree), 'reference-only complete module AST differs'
    legacy = types.ModuleType('p078_historical_mtp_reference')
    sys.modules[legacy.__name__] = legacy
    exec(compile(old_path.read_text(), str(old_path), 'exec'), legacy.__dict__)
    rows = []
    for batch, length in ((2, 9), (1, 1), (2, 5)):
        for horizons in ((), (2, 3, 4)):
            for checkpoint_heads in (False, True):
                for chunk in (2, 8):
                    torch.manual_seed(1337+batch+length)
                    original = ToyHead()
                    old_model, new_model = copy.deepcopy(original), copy.deepcopy(original)
                    features = torch.randn(batch, length, 7)
                    old_h, new_h = features.clone().requires_grad_(), features.clone().requires_grad_()
                    y = torch.randint(0, 19, (batch, length))
                    segments = torch.ones_like(y)
                    if length > 1:
                        segments[:, :2] = 0
                        y[:, :2] = -100
                        segments[:, length//2:] = 2
                        y[segments == 0] = -100
                    args = dict(horizons=horizons, chunk=chunk, checkpoint_heads=checkpoint_heads)
                    old_sums, old_counts = legacy.components(old_model, old_h, y, segments, **args)
                    new_sums, new_counts = current.components(new_model, new_h, y, segments, **args)
                    assert old_counts == new_counts
                    assert all(torch.equal(old_sums[h], new_sums[h]) for h in old_sums)
                    sum(old_sums.values()).backward()
                    sum(new_sums.values()).backward()
                    assert torch.equal(old_h.grad, new_h.grad)
                    compared = 1
                    for old_p, new_p in zip(old_model.parameters(), new_model.parameters()):
                        assert (old_p.grad is None) == (new_p.grad is None)
                        if old_p.grad is not None:
                            assert torch.equal(old_p.grad, new_p.grad)
                            compared += 1
                    rows.append(dict(batch=batch, length=length, horizons=list(horizons),
                        checkpoint_heads=checkpoint_heads, chunk=chunk, counts=old_counts,
                        exact_loss_equal=True, exact_gradient_equal=True, gradient_tensors=compared))
    assert not torch.cuda.is_initialized()
    assert sha(old_path) == OLD_SHA and sha(new_path) == NEW_SHA
    result = dict(schema='P078_REFERENCE_SOURCE_CPU_EQUIVALENCE_V1',
        old_source=str(old_path.relative_to(ROOT)), old_sha256=OLD_SHA,
        current_source='tinylm/train/mtp_sft.py', current_sha256=NEW_SHA,
        normalized_complete_module_ast_equal=True,
        normalization='ONLY_TWO_NON_REFERENCE_BRANCHES_AND_DEFAULT_REFERENCE_ARGUMENT',
        cases=rows, cases_count=len(rows), cpu_threads=torch.get_num_threads(),
        cuda_initialized=False, real_model_loads=0, real_corpus_reads=0,
        optimizer_steps=0, checkpoint_writes=0, original_sources_unchanged=True,
        torch_version=torch.__version__, seconds=time.perf_counter()-started,
        claim='DEFAULT_REFERENCE_NUMERICAL_EQUIVALENCE_ON_TOY; NOT_CURRENT_MODEL_QUALITY_OR_HISTORICAL_RERUN')
    output=Path(__file__).with_name('p078_reference_equivalence_v1.json')
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
        stream.write(chr(10))
    print(json.dumps({k:result[k] for k in ('cases_count','seconds','normalized_complete_module_ast_equal','cuda_initialized')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
