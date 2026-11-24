"""Run the native NTP trainer with an explicit, resumable P109 visit policy."""

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys
from unittest.mock import patch

from scripts import diag_p109_warm_visit_routes as warm
from scripts import p070b_cla_routes as cla
from scripts import p078_route_training as prior
from tinylm.model import TiedMLPTransformer
from tinylm.train.context_micro_tokens import MicroTokensCursor


ROOT = Path(__file__).resolve().parents[1]
POLICIES = ('uniform_r2', 'balanced_count', 'second_shuffle_r2')
RECIPE_KEY = 'p109_train_visit_policy'
SOURCES = (
    'scripts/p109_train_visit_policy.py', 'scripts/p070b_cla_routes.py',
    'scripts/p078_route_training.py', 'scripts/diag_p109_warm_visit_routes.py',
    'tinylm/config.py', 'tinylm/cli.py', 'tinylm/data/loader.py',
    'tinylm/model/transformer.py', 'tinylm/model/modules.py', 'tinylm/model/ternary.py',
)


def route_for(cfg, owners, policy, seed, index, steps):
    if policy not in POLICIES or type(index) is not int or not 0 <= index < steps:
        raise ValueError('registered P109 policy and absolute update in the declared horizon required')
    if policy == 'balanced_count':
        repeat = prior.bounded_count(prior.Policy(policy, seed), index, steps, 'train')
        return tuple(cla.schedule(cfg, owners, 'uniform', repeat))
    route = cla.schedule(cfg, owners, 'uniform', 2)
    if policy == 'second_shuffle_r2':
        key = int(prior.sha([warm.SHUFFLE_IDENTITY, seed, index])[:16], 16)
        first = cfg.n_prelude
        second = first + cfg.n_middle
        end = second + cfg.n_middle
        permutation = cla.schedule(cfg, owners, 'shuffle', 1, key)
        route[second:end] = permutation[first:second]
        cla.trace(cfg, owners, route)
    return tuple(route)


class RoutedG4(TiedMLPTransformer):
    def __init__(self, cfg):
        if ((cfg.n_prelude, cfg.n_middle, cfg.n_coda, cfg.mlp_group, cfg.cla_group) != (2, 12, 2, 4, 2)
                or cfg.mlp_split or not cfg.tie_mlp
                or cfg.train_repeat != 2.0 or cfg.infer_repeat != 1.0 or cfg.repeat_mode != 'uniform'
                or cfg.repeat_kv_reuse or cfg.reuse_attn_on_dup or cfg.repeat_embed_reinject or cfg.mtp_aux):
            raise ValueError('P109 requires the 16-layer G4·CLA2 R2 geometry')
        super().__init__(cfg)
        self.training_route = None
        self.training_forwards = 0

    def visit_schedule(self):
        if self.training and self.training_route is not None:
            return list(self.training_route)
        return super().visit_schedule()

    def forward(self, *args, **kwargs):
        if self.training:
            if self.training_route is None:
                raise RuntimeError('training forward requires an active update route')
            self.training_forwards += 1
        return super().forward(*args, **kwargs)


def source_pins():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest().upper() for name in SOURCES}


def validate_output_paths(trainer, args):
    tag = args['tag']
    if not tag or tag in ('dense', 'tied') or not re.fullmatch(r'[a-zA-Z0-9_]+', tag):
        raise ValueError('P109 requires an explicit distinct experiment tag')
    amount = args['n_tokens']
    tokens = args['tokstr'] or (f'{int(amount) // 1_000_000}M' if amount >= 1_000_000 else str(int(amount)))
    name = f"{args['preset']}_{args['data']}_{tokens}_{tag}"
    output = trainer.LOGS / (name + '.json')
    checkpoint = trainer.CKPT / (name + '.pt')
    best = trainer.CKPT / (name + '_best.pt')
    if (output.exists() or any(path.is_symlink() for path in (output, checkpoint, best))
            or (not args['resume'] and (checkpoint.exists() or best.exists()))):
        raise FileExistsError('existing result or checkpoint requires a distinct P109 run tag')


def run_native(policy, native_args, *, build_model=None):
    """Call the standard CLI inside one owned process; return its actual route accounting."""
    if policy not in POLICIES or not native_args or native_args[0] != 'train':
        raise ValueError('explicit P109 policy and a native train command required')
    from tinylm import cli
    import tinylm.train as train_package
    from tinylm.train import context_micro_tokens, context_training_state, trainer

    standard_train = train_package.train
    standard_binding = context_training_state.make_binding
    if build_model is None:
        build_model = RoutedG4
    pins = source_pins()
    model = None
    receipts = []
    policy_binding = None

    def build_routed(cfg):
        nonlocal model
        if model is not None:
            raise RuntimeError('P109 expects one native training model')
        model = build_model(cfg)
        return model

    def bind_route(plan, recipe, cache, device):
        # The native context binding rejects changed recipes before loading weights.
        return standard_binding(plan, dict(recipe, **{RECIPE_KEY: policy_binding}), cache, device)

    class RoutedCursor(MicroTokensCursor):
        def prepare(self):
            if model is None or model.training_route is not None:
                raise RuntimeError('one unfinished training route is allowed at a time')
            route = route_for(model.cfg, model.owner, policy, policy_binding['seed'],
                              self.next_update, self.plan.steps)
            update = super().prepare()
            model.training_route = route
            model.training_forwards = 0
            return update

        def finish(self, *, optimizer_applied):
            route = model.training_route
            if route is None or model.training_forwards != len(self._pending.batches):
                raise RuntimeError('P109 must execute every micro through the selected route')
            result = super().finish(optimizer_applied=optimizer_applied)
            receipts.append(dict(index=result['update'], visits=len(route),
                                 route_sha256=cla.route_sha(model.cfg, model.owner, route),
                                 draw_tokens=result['executed_input_tokens'], optimizer_applied=optimizer_applied))
            model.training_route = None
            return result

    def checked_train(*args, **kwargs):
        nonlocal policy_binding
        bound = inspect.signature(standard_train).bind(*args, **kwargs)
        bound.apply_defaults()
        options = bound.arguments
        if ((options['preset'], options['arch'], options['train_repeat'], options['repeat_mode'])
                != ('m100s12_g4', 'tied', 2.0, 'uniform')
                or options['compile_']):
            raise ValueError('P109 visit experiment requires eager m100s12_g4 tied R2')
        fixed = f"{options['steps']}:{options['seq']}"
        if options['context_curriculum'] not in (None, fixed):
            raise ValueError('P109 compares fixed input tokens and context at every update')
        options['context_curriculum'] = fixed
        validate_output_paths(trainer, options)
        policy_binding = dict(schema='P109_VISIT_POLICY_NTP_V1', policy=policy, seed=options['seed'],
                              steps=options['steps'], eval_route='uniform_r2', sources=pins)
        return standard_train(*bound.args, **bound.kwargs)

    with (patch.object(sys, 'argv', ['tinylm', *native_args]),
          patch.object(train_package, 'train', checked_train),
          patch.object(trainer, 'TiedMLPTransformer', build_routed),
          patch.object(context_micro_tokens, 'MicroTokensCursor', RoutedCursor),
          patch.object(context_training_state, 'make_binding', bind_route)):
        cli.main()
    if not receipts or receipts[-1]['index'] + 1 != policy_binding['steps'] or pins != source_pins():
        raise RuntimeError('P109 route run did not close at its unchanged declared horizon')
    return dict(policy=policy_binding, updates=receipts,
                layer_token_visits=sum(row['draw_tokens'] * row['visits'] for row in receipts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', required=True, choices=POLICIES)
    parser.add_argument('native', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.native[1:] if args.native[:1] == ['--'] else args.native
    receipt = run_native(args.policy, command)
    print('P109_NATIVE_VISIT_RECEIPT', json.dumps(receipt, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
