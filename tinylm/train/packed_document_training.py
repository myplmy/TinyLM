"""File-bound packed NTP input, update cursor and fixed holdout evaluation."""

from contextlib import contextmanager
from dataclasses import dataclass, fields
from hashlib import sha256
import math
import os
import stat
from tempfile import NamedTemporaryFile

import torch

from . import document_input as envelope
from .context_curriculum import ContextPlan
from .context_training_state import _sha as binding_sha
from .document_context_curriculum import causal_loss_sum, regroup_document_context
from .indexed_document_source import IndexLimits, IndexedDocumentInput, _root, _stamp, load_indexed_document_input


INPUT_SCHEMA = "P013_PACKED_DOCUMENT_PROFILE_V1"
CURSOR_SCHEMA = "P013_PACKED_DOCUMENT_CURSOR_V1"


@contextmanager
def _open_regular(path):
    path = _root(path)
    if ".." in path.parts or any(item.is_symlink() for item in (*reversed(path.parents), path)):
        raise ValueError("packed training requires an explicit unlinked input path")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size <= 0:
            raise ValueError("packed training input must be a nonempty regular file")
        yield path, stream, info
        if _stamp(os.fstat(stream.fileno())) != _stamp(info):
            raise ValueError("packed training input changed during read")


def _profile(path):
    with _open_regular(path) as (path, stream, info):
        if info.st_size > envelope.MAX_META_BYTES:
            raise ValueError("bounded regular packed document profile required")
        raw = stream.read(envelope.MAX_META_BYTES + 1)
        if len(raw) != info.st_size:
            raise ValueError("packed document profile changed during read")
    return path, raw, envelope._json(raw)


def load_packed_parent(path, *, read_weights):
    """Bind a cooldown parent by its exact bytes; resume restores its own checkpoint."""
    with _open_regular(path) as (path, stream, info):
        checksum = sha256()
        for block in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(block)
        state = None
        if read_weights:
            stream.seek(0)
            state = torch.load(stream, map_location="cpu", weights_only=True)
    return dict(path=str(path), bytes=info.st_size, sha256=checksum.hexdigest().upper()), state


def _check_splits(train, validation):
    for field in ("source_id", "declared_source_sha256", "token_sha256"):
        left = {getattr(record, field) for record in train.records}
        if any(getattr(record, field) in left for record in validation.records):
            raise ValueError(f"train and validation share document identity: {field}")


@dataclass(frozen=True)
class PackedDocumentInput:
    train: IndexedDocumentInput
    validation: IndexedDocumentInput
    validation_batches: int
    identity: dict

    def cursor(self, plan, *, seed):
        if self.validation.contract["tokens"] <= plan.full_length:
            raise ValueError("validation must fill at least one full packed window")
        stream = self.train.as_source(batch=plan.micro_bs, length=plan.full_length, micros=plan.base_accum,
                                      vocab=self.train.contract["vocab_size"], seed=seed, packed=True)
        return PackedDocumentCursor(plan, stream)


def load_packed_document_profile(profile_path):
    path, raw, profile = _profile(profile_path)
    required = {"schema", "input_root", "tokenizer", "train", "validation", "validation_batches"}
    if (not isinstance(profile, dict) or not required <= set(profile) <= required | {"index_limits"}
            or profile["schema"] != INPUT_SCHEMA or type(profile["validation_batches"]) is not int
            or not 1 <= profile["validation_batches"] <= 50):
        raise ValueError("complete packed document profile with 1 to 50 fixed validation batches required")
    tokenizer = profile["tokenizer"]
    if (not isinstance(tokenizer, dict) or set(tokenizer) != {"path", "bytes", "sha256", "vocab_size"}
            or type(tokenizer["vocab_size"]) is not int or tokenizer["vocab_size"] < 2):
        raise ValueError("explicit tokenizer file and vocabulary required")
    limits = profile.get("index_limits", {})
    if not isinstance(limits, dict) or set(limits) - {field.name for field in fields(IndexLimits)}:
        raise ValueError("unknown document index limits")
    limits = IndexLimits(**limits)
    root = profile["input_root"]
    token_ref = {key: item for key, item in tokenizer.items() if key != "vocab_size"}
    envelope.read_bound(path.parent, token_ref, root, limit=envelope.MAX_SHARD_BYTES)
    options = dict(allowed_root=root, tokenizer_sha256=tokenizer["sha256"],
                   vocab_size=tokenizer["vocab_size"], allow_admitted=True, limits=limits)
    train = load_indexed_document_input(path.parent, profile["train"], split="train", **options)
    validation = load_indexed_document_input(path.parent, profile["validation"], split="val", **options)
    _check_splits(train, validation)
    files = dict(profile=dict(path=path.name, bytes=len(raw), sha256=envelope.sha256(raw)),
                 tokenizer=tokenizer, train=train.contract, validation=validation.contract)
    identity = dict(cache_dir=str(path.parent), files=files)
    identity["identity_sha256"] = binding_sha(identity)
    return PackedDocumentInput(train, validation, profile["validation_batches"], identity)


def save_packed_checkpoint(path, state):
    """Publish a complete checkpoint while preserving the previous file on failure."""
    with NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
        torch.save(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stream.name, path)


class PackedDocumentCursor:
    def __init__(self, plan, source):
        self.plan, self.source = plan, source
        self.signature = envelope.canonical_sha(dict(plan=plan.contract(), source=source.contract))
        self.next_update = self.optimizer_updates = self.valid_targets = 0
        self._pending = None

    def prepare(self):
        if self._pending is not None:
            raise RuntimeError("finish the current packed update first")
        length = self.plan.length_at(self.next_update)
        previous = self.source.state_dict()
        windows = self.source.next_update()
        try:
            self._pending = regroup_document_context(windows, self.plan, length, vocab_size=self.source.vocab)
        except BaseException:
            self.source.load_state_dict(previous)
            raise
        return self._pending

    def finish(self, *, optimizer_applied):
        if self._pending is None or type(optimizer_applied) is not bool:
            raise RuntimeError("complete prepared packed update required")
        self.valid_targets += self._pending.target_count
        self.next_update += 1
        self.optimizer_updates += int(optimizer_applied)
        self._pending = None

    def state_dict(self):
        if self._pending is not None or self.source.cursor != self.next_update:
            raise RuntimeError("packed state requires a complete update boundary")
        saved = self.source.state_dict()
        saved["rng"] = saved["rng"].numpy().tobytes().hex()
        return dict(schema=CURSOR_SCHEMA, signature=self.signature, next_update=self.next_update,
                    optimizer_updates=self.optimizer_updates, valid_targets=self.valid_targets, source=saved)

    def validate_state_dict(self, state):
        fields = {"schema", "signature", "next_update", "optimizer_updates", "valid_targets", "source"}
        if (not isinstance(state, dict) or set(state) != fields or state["schema"] != CURSOR_SCHEMA
                or state["signature"] != self.signature):
            raise ValueError("packed cursor source or plan differs")
        step, updates, targets = (state[key] for key in ("next_update", "optimizer_updates", "valid_targets"))
        if (any(type(value) is not int for value in (step, updates, targets))
                or not 0 <= updates <= step <= self.plan.steps
                or not step <= targets <= step * self.plan.tokens_per_update):
            raise ValueError("invalid packed cursor update or target counts")
        source = state["source"]
        if (not isinstance(source, dict) or source.get("cursor") != step or not isinstance(source.get("rng"), str)
                or len(source["rng"]) != 2 * self.source.rng.get_state().numel()):
            raise ValueError("packed source counter or RNG differs")
        decoded = dict(source, rng=torch.tensor(list(bytes.fromhex(source["rng"])), dtype=torch.uint8, device="cpu"))
        self.source.validate_state_dict(decoded)
        return decoded

    def load_state_dict(self, state):
        if self._pending is not None or self.next_update:
            raise RuntimeError("packed state restore requires a fresh cursor")
        self.source.load_state_dict(self.validate_state_dict(state))
        self.next_update, self.optimizer_updates, self.valid_targets = (
            state[key] for key in ("next_update", "optimizer_updates", "valid_targets"))


@torch.no_grad()
def evaluate_packed_documents(model, packet, plan, device):
    """Recreate the same holdout draws and count all valid targets once."""
    width = plan.full_length
    validation_plan = ContextPlan(((1, width),), plan.micro_bs, 1, width)
    stream = packet.validation.as_source(batch=plan.micro_bs, length=width, micros=1,
                                         vocab=packet.validation.contract["vocab_size"], seed=99, packed=True)
    prior_anneal = model.cfg.quant_anneal
    training = model.training
    dtype = torch.bfloat16 if torch.device(device).type == "cuda" else None
    model.set_anneal(1.)
    model.eval()
    try:
        model.freeze_quant()
        loss_sum, targets = 0., 0
        for _ in range(packet.validation_batches):
            update = regroup_document_context(stream.next_update(), validation_plan, width, vocab_size=stream.vocab)
            loss_sum += float(causal_loss_sum(model, update.batches[0], device, autocast_dtype=dtype))
            targets += update.target_count
    finally:
        model.clear_quant()
        model.train(training)
        model.set_anneal(prior_anneal)
    loss = loss_sum / targets
    return dict(val_loss=loss, ppl=math.exp(min(loss, 20)), val_valid_targets=targets,
                val_batches=packet.validation_batches)
