"""Context-layout checkpoint mechanism, not a complete training dependency seal.

Cache hashes identify bytes, not rights or corpus admission. This helper owns
source/validation/Torch RNG and caller-supplied control state. Model weights and
both optimizer states remain in the trainer's common checkpoint container.
The opt-in trainer bridge is implemented; successful native trainer execution
and GPU numerical reproducibility remain NOT_RUN.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path, PurePath
from types import SimpleNamespace

import numpy as np
import torch

from .context_micro_tokens import MicroTokensCursor

SCHEMA = "P013_CONTEXT_TRAINING_STATE_V1"
BINDING_SCHEMA = "P013_CONTEXT_TRAINING_BINDING_V1"


def validate_trainer_control(control, step, optimizer_updates):
    """NTP trainer control fields; called before model/optimizer mutation."""
    required = {"completed_updates", "best_val", "best_step", "since_improve", "history",
                "n_skip", "gmax", "gpeak", "loss_accumulators"}
    if not isinstance(control, dict) or set(control) != required:
        raise ValueError("complete NTP trainer control state required")
    for key in ("completed_updates", "best_step", "since_improve", "n_skip"):
        if type(control[key]) is not int or control[key] < 0:
            raise ValueError("integer nonnegative trainer control counters required")
    if (control["completed_updates"] != step or not 1 <= control["best_step"] <= step
            or type(optimizer_updates) is not int or not 0 <= optimizer_updates <= step):
        raise ValueError("trainer control/source counters differ")
    for key in ("best_val", "gmax", "gpeak"):
        value = control[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("finite trainer numeric control required")
    accumulators = control["loss_accumulators"]
    if not isinstance(accumulators, dict) or set(accumulators) != {"kd_l", "kd_ce", "kd_n", "no_l", "no_ce", "no_n"}:
        raise ValueError("complete NTP loss accumulators required")
    if (type(accumulators["no_n"]) is not int or accumulators["no_n"] != optimizer_updates
            or type(accumulators["kd_n"]) is not int or accumulators["kd_n"] != 0
            or accumulators["no_n"] + control["n_skip"] != step):
        raise ValueError("NTP optimizer/skip/loss counters differ")
    history = control["history"]
    if not isinstance(history, list) or not history:
        raise ValueError("saved trainer validation history required")
    previous = 0
    best_record = None
    for row in history:
        if (not isinstance(row, dict) or type(row.get("step")) is not int
                or not previous < row["step"] <= step):
            raise ValueError("ordered complete validation history required")
        previous = row["step"]
        if row["step"] == control["best_step"]:
            best_record = row
    if previous != step or best_record is None or best_record.get("val_loss") != control["best_val"]:
        raise ValueError("prospective best/current evaluation state differs")
    _canonical(control)
    return deepcopy(control)


def _canonical(value):
    if type(value) in (type(None), bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("finite checkpoint metadata required")
        return value
    if isinstance(value, (PurePath, torch.dtype, torch.device)):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict) and all(type(k) is str for k in value):
        return {key: _canonical(item) for key, item in value.items()}
    raise ValueError("unsupported context checkpoint metadata type")


def _sha(value):
    return hashlib.sha256(json.dumps(_canonical(value), sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest().upper()


def cache_identity(cache_dir):
    """Hash only the caller-selected existing cache's three exact files."""
    directory = Path(cache_dir).resolve(strict=True)
    files = {}
    for name in ("meta.json", "train.bin", "val.bin"):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("existing regular cache file required: " + name)
        before = path.stat()
        sha = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                sha.update(block)
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("cache changed during identity read")
        files[name] = dict(bytes=after.st_size, sha256=sha.hexdigest().upper())
    result = dict(cache_dir=str(directory), files=files)
    result["identity_sha256"] = _sha(result)
    return result


def runtime_identity(device):
    device = torch.device(device)
    value = dict(device=str(device), torch_version=str(torch.__version__),
                 numpy_version=np.__version__, threads=torch.get_num_threads(),
                 interop_threads=torch.get_num_interop_threads(),
                 float32_matmul_precision=torch.get_float32_matmul_precision(),
                 deterministic_algorithms=torch.are_deterministic_algorithms_enabled())
    if device.type == "cuda":
        if not torch.cuda.is_initialized():
            raise ValueError("owned CUDA device must already be initialized")
        value.update(tf32_matmul=torch.backends.cuda.matmul.allow_tf32,
                     cudnn_tf32=torch.backends.cudnn.allow_tf32,
                     cudnn_deterministic=torch.backends.cudnn.deterministic,
                     cublas_workspace=os.environ.get("CUBLAS_WORKSPACE_CONFIG"))
    elif device.type != "cpu":
        raise ValueError("context state supports CPU or owned CUDA only")
    return value


def make_binding(plan, recipe, cache, device):
    if (not isinstance(cache, dict) or set(cache) != {"cache_dir", "files", "identity_sha256"}
            or cache["identity_sha256"] != _sha({key: item for key, item in cache.items()
                                              if key != "identity_sha256"})):
        raise ValueError("verified cache identity structure required")
    recipe = dict(recipe)
    recipe.pop("resume", None)
    recipe["context_curriculum"] = plan.contract()
    source_dir = Path(__file__).resolve().parent
    names = ("context_training_state.py", "context_micro_tokens.py",
             "context_curriculum.py", "trainer.py")
    if recipe.get("ce_recompute_rows"):
        names += ("recomputed_ce.py",)
    if recipe.get("packed_document_profile"):
        names += ("packed_document_training.py", "indexed_document_source.py", "document_input.py",
                  "document_context_curriculum.py", "hybrid_mntp.py", "../model/visibility.py",
                  "../model/transformer.py", "../model/modules.py", "../config.py")
    pins = {name: hashlib.sha256((source_dir / name).read_bytes()).hexdigest().upper()
            for name in names}
    value = dict(schema=BINDING_SCHEMA, plan=plan.contract(), recipe=_canonical(recipe),
                 cache=_canonical(cache), runtime=runtime_identity(device), sources=pins,
                 source_scope="CONTEXT_MECHANISM_AND_TRAINER_NOT_COMPLETE_DEPENDENCY_CLOSURE")
    value["binding_sha256"] = _sha(value)
    return value


def _rng_tensor(value):
    if (not isinstance(value, torch.Tensor) or value.dtype != torch.uint8
            or value.device.type != "cpu" or value.ndim != 1 or not value.is_contiguous()
            or value.numel() < 1):
        raise ValueError("complete CPU uint8 RNG state vector required")


def _validate_binding(binding):
    if (not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA
            or binding.get("binding_sha256") != _sha({key: item for key, item in binding.items()
                                                     if key != "binding_sha256"})):
        raise ValueError("context binding checksum differs")


def _payload_sha(value):
    meta = {key: item for key, item in value.items()
            if key not in ("cpu_rng", "cuda_rng", "payload_sha256")}
    for key in ("cpu_rng", "cuda_rng"):
        tensor = value[key]
        if tensor is None:
            meta[key + "_sha256"] = None
        else:
            _rng_tensor(tensor)
            meta[key + "_sha256"] = hashlib.sha256(tensor.numpy().tobytes()).hexdigest().upper()
    return _sha(meta)


def capture_training_state(cursor, validation_loader, binding, control):
    _validate_binding(binding)
    device = torch.device(binding["runtime"]["device"])
    if runtime_identity(device) != binding["runtime"]:
        raise ValueError("runtime changed before context checkpoint")
    validation_rng = None
    if binding["recipe"].get("packed_document_profile"):
        if validation_loader is not None:
            raise ValueError("packed validation is recreated from the bound input and fixed seed")
    else:
        if not isinstance(validation_loader.rng.bit_generator, np.random.PCG64):
            raise ValueError("explicit validation PCG64 required")
        validation_rng = deepcopy(validation_loader.rng.bit_generator.state)
    value = dict(schema=SCHEMA, binding=deepcopy(binding), cursor=cursor.state_dict(),
                 validation_rng=validation_rng,
                 cpu_rng=torch.get_rng_state().clone(),
                 cuda_rng=(torch.cuda.get_rng_state(device).clone() if device.type == "cuda" else None),
                 control=_canonical(deepcopy(control)),
                 model_and_optimizer_states="OWNED_BY_COMMON_TRAINER_CONTAINER",
                 elapsed_scope="CURRENT_PROCESS_ONLY;LATEST_CHECKPOINT_SAVE_TIME_NOT_INCLUDED")
    if (type(value["control"].get("completed_updates")) is not int
            or value["control"]["completed_updates"] != cursor.next_update):
        raise ValueError("control step and source cursor differ")
    value["payload_sha256"] = _payload_sha(value)
    return value


def validate_training_state(value, binding, plan, step, *, packed_cursor=None):
    """Validate on disposable generators before model/optimizer load or RNG writes."""
    _validate_binding(binding)
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError("explicit context training checkpoint required")
    if set(value) != {"schema", "binding", "cursor", "validation_rng", "cpu_rng", "cuda_rng",
                      "control", "model_and_optimizer_states", "elapsed_scope", "payload_sha256"}:
        raise ValueError("complete context training schema required")
    if value.get("binding") != binding or binding.get("schema") != BINDING_SCHEMA:
        raise ValueError("context recipe/cache/source/runtime binding differs")
    if type(step) is not int or step < 0 or step > plan.steps:
        raise ValueError("valid common-container step required")
    if value.get("payload_sha256") != _payload_sha(value):
        raise ValueError("context training payload checksum differs")
    if (type(value.get("control", {}).get("completed_updates")) is not int
            or value["control"]["completed_updates"] != step):
        raise ValueError("context control step differs")
    if binding["recipe"].get("packed_document_profile"):
        if packed_cursor is None or value["validation_rng"] is not None:
            raise ValueError("packed cursor and fixed validation recipe required")
        packed_cursor.validate_state_dict(value["cursor"])
        if value["cursor"]["next_update"] != step:
            raise ValueError("packed cursor/common-container step differs")
    else:
        probe_sampler = SimpleNamespace(bs=plan.micro_bs, seq=plan.full_length,
            rng=np.random.Generator(np.random.PCG64(0)))
        probe = MicroTokensCursor(plan, probe_sampler, source_sha256=binding["cache"]["identity_sha256"])
        probe.load_state_dict(value["cursor"])
        if probe.next_update != step:
            raise ValueError("context cursor/common-container step differs")
        val_probe = np.random.Generator(np.random.PCG64(0))
        val_probe.bit_generator.state = deepcopy(value["validation_rng"])
    _rng_tensor(value["cpu_rng"])
    torch.Generator(device="cpu").set_state(value["cpu_rng"])
    device = torch.device(binding["runtime"]["device"])
    if runtime_identity(device) != binding["runtime"]:
        raise ValueError("current runtime differs")
    if device.type == "cpu":
        if value["cuda_rng"] is not None:
            raise ValueError("CPU context checkpoint cannot contain CUDA state")
    else:
        _rng_tensor(value["cuda_rng"])
        if value["cuda_rng"].shape != torch.cuda.get_rng_state(device).shape:
            raise ValueError("owned CUDA RNG format differs")
    _canonical(value["control"])
    return deepcopy(value)


def restore_training_state(value, binding, plan, step, cursor, validation_loader):
    packed = bool(binding["recipe"].get("packed_document_profile"))
    checked = validate_training_state(value, binding, plan, step, packed_cursor=cursor if packed else None)
    if packed:
        if validation_loader is not None:
            raise ValueError("packed validation is recreated from the bound input and fixed seed")
    elif not isinstance(validation_loader.rng.bit_generator, np.random.PCG64):
        raise ValueError("validation loader PCG64 required")
    cursor.load_state_dict(checked["cursor"])
    if not packed:
        validation_loader.rng.bit_generator.state = deepcopy(checked["validation_rng"])
    torch.set_rng_state(checked["cpu_rng"])
    if checked["cuda_rng"] is not None:
        torch.cuda.set_rng_state(checked["cuda_rng"], device=binding["runtime"]["device"])
    return deepcopy(checked["control"])
