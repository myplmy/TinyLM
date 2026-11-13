"""Opt-in hard-ternary CE/ALM bridge; not the original GSQ PTQ recipe.

Reuse P093B's binary Gumbel core and the existing ALM loss. No files, model
loading, downloads or default model changes occur on import. Backward must
finish inside one realization when layer/head checkpointing can recompute.
"""
from contextlib import ExitStack, contextmanager
import math

import torch
from torch import nn

from scripts.p093b_native_repair import GSQProjection
from tinylm.model.ternary import TLinear, ternary_g
from tinylm.train import alm


class GSQBank(GSQProjection):
    def __init__(self, master, group, cfg, *, logit_strength=1.0):
        if master.dtype != torch.float32 or not bool(torch.isfinite(master).all()):
            raise ValueError('finite FP32 master required')
        if not math.isfinite(logit_strength) or logit_strength <= 0:
            raise ValueError('positive finite logit strength required')
        native = ternary_g(master.detach(), group, cfg).detach()
        super().__init__(native, group, cfg)
        # Direct scales preserve initial numerical values without log/exp error.
        del self.log_scale
        shaped = native.reshape(self.out_f, -1, group)
        self.scale = nn.Parameter(shaped.abs().amax(-1, keepdim=True).clamp_min(1e-8))
        with torch.no_grad():
            self.mask_logit.copy_(torch.where(shaped != 0, logit_strength, -logit_strength))
            self.sign_logit.copy_(torch.where(shaped > 0, logit_strength,
                                            torch.where(shaped < 0, -logit_strength, 0.)))

    def matrix(self):
        if not bool(torch.isfinite(self.scale).all()) or bool(self.scale.le(0).any()):
            raise FloatingPointError('positive finite GSQ scales required; project after an update')
        mask = self._binary(self.mask_logit)
        sign = 2 * self._binary(self.sign_logit) - 1
        return (mask * sign * self.scale).reshape(self.out_f, self.in_f)

    def bound(self):
        with torch.no_grad():
            for parameter in self.parameters():
                if not bool(torch.isfinite(parameter).all()):
                    raise FloatingPointError('nonfinite GSQ parameter')
            self.mask_logit.clamp_(-12, 12)
            self.sign_logit.clamp_(-12, 12)
            self.scale.clamp_min_(1e-8)

    def code_scale(self):
        if self.training:
            raise ValueError('deterministic eval required for export')
        code = ((self.mask_logit >= 0).to(torch.int8)
                * (2 * (self.sign_logit >= 0).to(torch.int8) - 1))
        return code.detach().clone(), self.scale.detach().clone()


class STEBank(nn.Module):
    def __init__(self, master, group, cfg):
        super().__init__()
        self.master = nn.Parameter(master.detach().clone())
        self.group, self.cfg = group, cfg

    def matrix(self):
        return ternary_g(self.master, self.group, self.cfg)


class ObjectiveBridge:
    """One bank per physical weight, including the tied embedding/main head."""
    def __init__(self, model, arm, *, logit_strength=1.0):
        if arm not in ('ste', 'gsq'):
            raise ValueError('ste or gsq required')
        if (getattr(model, '_emb_fmt', None) is not None
                or getattr(model, '_quant_frozen', False)
                or getattr(model, '_p102a_quant_update', None) is not None
                or getattr(model, '_unpack_cache', False)
                or getattr(model.cfg, 'sparse34', False)
                or getattr(model.cfg, 'mtp_aux', False)
                or getattr(model.cfg, 'use_ternary_kernel', False)):
            raise ValueError('unpacked native hard-ternary training path required')
        self.model, self.arm = model, arm
        self.banks = nn.ModuleDict()
        self.masters, self.groups, self.aliases = {}, {}, {}
        self.bindings = []
        self._by_id = {}
        self._installed = self._active = self._backward_done = False
        self._current = None

        def bank_for(name, parameter, cfg):
            group = int(cfg.micro_group) or parameter.shape[1]
            if (parameter.ndim != 2 or parameter.shape[1] % group
                    or parameter.dtype != torch.float32 or parameter.grad is not None):
                raise ValueError('clean FP32 matrix and dividing group required')
            if id(parameter) in self._by_id:
                key = self._by_id[id(parameter)]
                if self.groups[key] != group:
                    raise ValueError('shared weight has incompatible groups')
                self.aliases[key].append(name)
                return key
            key = 'weight_' + str(len(self.banks)).zfill(4)
            factory = (lambda: GSQBank(parameter, group, cfg, logit_strength=logit_strength)
                       if arm == 'gsq' else STEBank(parameter, group, cfg))
            self.banks[key] = factory()
            self.masters[key], self.groups[key], self.aliases[key] = parameter, group, [name]
            self._by_id[id(parameter)] = key
            return key

        for name, module in model.named_modules():
            if isinstance(module, TLinear):
                if (module.use_mode or module.connectivity_mask is not None
                        or module._i8 is not None or module._lut_codes is not None
                        or 'forward' in module.__dict__):
                    raise ValueError('mode, sparse, packed or overridden TLinear requires another contract')
                self.bindings.append((module, bank_for(name + '.weight', module.weight, module.cfg)))
        self.embedding = bank_for('emb.weight/input_and_main_head', model.emb.weight, model.cfg)
        self.embedding_up = (bank_for('emb_up.weight/input_and_main_head', model.emb_up.weight, model.cfg)
                             if model.emb_up is not None else None)
        devices = {parameter.device for parameter in self.masters.values()}
        if len(devices) != 1:
            raise ValueError('one model device required')
        self.device = next(iter(devices))

    def parameters_for_optimizer(self):
        originals = set(self._by_id)
        values = list(self.banks.parameters()) + [
            p for p in self.model.parameters() if p.requires_grad and id(p) not in originals]
        unique = {id(p): p for p in values if p.requires_grad}
        if len(unique) != len(values):
            raise ValueError('optimizer must own each trainable value exactly once')
        return list(unique.values())

    def _weight(self, key):
        if not self._active:
            raise RuntimeError('an explicit realization is required')
        return self._current[key]

    @contextmanager
    def installed(self):
        if self._installed:
            raise RuntimeError('bridge is already installed')
        flags = {key: p.requires_grad for key, p in self.masters.items()}
        original_clear = self.model.clear_quant

        def clear():
            if self._active:
                raise RuntimeError('cannot clear caches during a realization')
            return original_clear()
        self._installed = True
        try:
            for p in self.masters.values():
                p.requires_grad_(False)
            with ExitStack() as stack:
                from unittest.mock import patch
                stack.enter_context(patch.object(self.model, 'refresh_quant', lambda: None))
                stack.enter_context(patch.object(self.model, 'clear_quant', clear))
                stack.enter_context(patch.object(self.model, '_emb_w', lambda: self._weight(self.embedding)))
                if self.embedding_up is not None:
                    stack.enter_context(patch.object(self.model, '_emb_up_w',
                        lambda: self._weight(self.embedding_up)))
                yield self
        finally:
            self._installed = False
            for key, p in self.masters.items():
                p.requires_grad_(flags[key])

    @contextmanager
    def realization(self, seed, *, backward_expected=None):
        if not self._installed or self._active:
            raise RuntimeError('one installed, nonnested realization required')
        if type(seed) is not int or not 0 <= seed < 2**63:
            raise ValueError('bounded integer seed required')
        expected = (self.model.training and torch.is_grad_enabled()
                    if backward_expected is None else backward_expected)
        self.banks.train(self.model.training)
        devices = [] if self.device.type == 'cpu' else [self.device.index]
        with torch.random.fork_rng(devices=devices):
            torch.random.default_generator.manual_seed(seed)
            if self.device.type == 'cuda':
                torch.cuda.default_generators[self.device.index].manual_seed(seed)
            matrices = {key: bank.matrix() for key, bank in self.banks.items()}
        failed = False
        self._active, self._backward_done, self._current = True, False, matrices
        try:
            with ExitStack() as stack:
                from unittest.mock import patch
                for module, key in self.bindings:
                    stack.enter_context(patch.object(module, '_wq', matrices[key]))
                yield self
        except BaseException:
            failed = True
            raise
        finally:
            self._active, self._current = False, None
            if expected and not self._backward_done and not failed:
                raise RuntimeError('backward must finish inside the realization; use bridge.backward')

    def loss_terms(self, x, targets, chunks=(), *, temperature=100., head_chunk=64):
        if not self._active:
            raise RuntimeError('loss requires an active realization')
        hidden = self.model(x, return_hidden=True)
        nll, mask = alm.target_nll(self.model, hidden, targets, chunk=head_chunk)
        kl, count = alm.chunk_kl(nll, mask, chunks, temperature=temperature)
        return dict(ce_sum=nll.sum(), ce_targets=int(mask.sum()), kl_sum=kl,
                    kl_chunks=count, nll=nll, supervised=mask)

    @staticmethod
    def normalized_loss(terms, weight):
        return alm.normalized_loss(terms['ce_sum'], terms['ce_targets'],
            terms['kl_sum'], terms['kl_chunks'], weight=weight)

    def backward(self, loss):
        if not self._active or self._backward_done:
            raise RuntimeError('one backward per active realization required')
        loss.backward()
        self._backward_done = True

    def project(self):
        if self._active:
            raise RuntimeError('project only after closing the realization')
        if self.arm == 'gsq':
            for bank in self.banks.values():
                bank.bound()

    def inventory(self):
        return dict(arm=self.arm, physical_banks=len(self.banks),
            tlinear_objects=len(self.bindings),
            aliases=self.aliases, master_elements=sum(p.numel() for p in self.masters.values()),
            frozen_original_bytes=sum(p.numel() * p.element_size() for p in self.masters.values()),
            bank_parameter_bytes=sum(p.numel() * p.element_size() for p in self.banks.parameters()),
            optimizer_trainable_bytes=sum(p.numel() * p.element_size() for p in self.parameters_for_optimizer()),
            scope='training tensors only; excludes gradients, moments, sampling graph and activations',
            packed_deployment=False, general_intelligence_claim=False)
