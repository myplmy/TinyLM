"""Transmit existing fixed-scale G4 edits into the sealed compact text runtime."""

import argparse
from contextlib import ExitStack
import ctypes
from datetime import datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p109_g4_text_avx2_lookup as fast
from scripts import p108_native_scale as editing
from scripts.p108_shared_ternary_edit import physical_down_owners
from tinylm.data.prepare import load_tokenizer
from tinylm.model.lut import pack_trits, unpack_trits


base, tile, text_exec, bytelevel = fast.base, fast.tile, fast.text_exec, fast.bytelevel
ROOT, ORIGIN = base.ROOT, base.prior.ORIGIN
PACK = base.prior.embedding.PACK
TAG = "p108_g4_compact_fixed_edit_text_v1_20261119"
OUT = fast.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
PLAN = ROOT / "test_plan/P108_직접가중치-방향수리와-학습개입.md"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
PACKETS = ROOT / "test_result/evidence/p108_g4_packed_cuda_joint_v1_20261119/report.json"
OFFSETS = ROOT / "handoff/audit/research_20261118_01a1e647/G4_FIXED_EDIT_NATIVE_CODE_OFFSETS_v1.json"
ARMS = ("single", "split")


def gate(reserve=0):
    if (END - datetime.now(END.tzinfo)).total_seconds() <= reserve or (OUT / "STOP").exists():
        raise TimeoutError("User 177 time window or local stop reached")


def pinned_binary(path, expected):
    handle = Path(path)
    if (not handle.is_absolute() or not handle.is_relative_to("/tmp") or handle.is_symlink()
            or not handle.is_file() or base.SHA(handle) != expected):
        raise ValueError("The original verified local binary is required")
    return handle


def contract():
    eprof = base.READ(text_exec.OUT / "profile.json")
    early = base.READ(text_exec.OUT / "report.json")
    previous = base.READ(fast.OUT / "report.json")
    fprof = base.READ(fast.OUT / "profile.json")
    if (previous["profile_sha256"] != base.SHA(fast.OUT / "profile.json")
            or early["profile_sha256"] != base.SHA(text_exec.OUT / "profile.json")
            or previous["artifact"] != early["source"] or not early["same_pid_exec"]
            or not all(case["within_si"] and case["exact"] for case in previous["runs"])):
        raise ValueError("The original complete comparable compact requests are required")
    for source in (fprof["sources"], eprof["pins"]["candidate"]["sources"]):
        if any(base.SHA(ROOT / p) != sealed for p, sealed in source.items()):
            raise ValueError("A previously sealed model or native runtime source differs")
    y = base.READ(PACKETS)
    offset = base.READ(OFFSETS)
    if (not y["head_pass"] or not y["exact_same_scale"] or y["checkpoint_sha256"] != ORIGIN.PARENT_SHA
            or offset["source_sha256"] != base.SHA(PACKETS)
            or any(offset["cases"][arm]["packed_bytes_touched"] != count for arm, count in (("single",1),("split",2)))):
        raise ValueError("The actual prevalidated fixed-scale packets are required")
    comp = base.READ(fast.OUT / "compiler.json")
    pretok_comp = base.READ(tile.OUT / "compiler.json")
    executable = pinned_binary(comp["binary"], comp["sha256"])
    row_audit = pinned_binary(comp["audit"], comp["audit_sha256"])
    pretok = pinned_binary(pretok_comp["binary"], pretok_comp["sha256"])
    tokprof = base.READ(bytelevel.OUT / "profile.json")
    text_source = base.SHA(bytelevel.TOK)
    if (text_source != tokprof["source_sha256"]
            or eprof["tokenizer_profile"] != base.SHA(bytelevel.OUT / "profile.json")
            or eprof["tokenizer_reference"] != base.SHA(bytelevel.OUT / "report.json")
            or base.SHA(ORIGIN.PARENT) != ORIGIN.PARENT_SHA):
        raise ValueError("The original byte-level tokenizer and source checkpoint must match")
    locations = (PACKETS, OFFSETS, PLAN, Path(__file__).resolve(), fast.OUT / "profile.json",
                 fast.OUT / "report.json", fast.OUT / "compiler.json", text_exec.OUT / "report.json",
                 text_exec.OUT / "profile.json", tile.OUT / "compiler.json",
                 bytelevel.OUT / "profile.json", bytelevel.OUT / "report.json", bytelevel.TOK,
                 ROOT / "scripts/p108_native_scale.py", ROOT / "scripts/p108_shared_ternary_edit.py",
                 ROOT / "tinylm/model/lut.py", ROOT / "scripts/p014e_packed_g128.py")
    return dict(tag=TAG, approval=177, end=END.isoformat(), time_limit_seconds=240,
                refs={p.relative_to(ROOT).as_posix():base.SHA(p) for p in locations},
                parent_sha256=ORIGIN.PARENT_SHA, model=early["source"], candidate=eprof["pins"]["candidate"],
                cpu=eprof["cpu"], binary=str(executable), binary_sha256=comp["sha256"],
                audit=str(row_audit), audit_sha256=comp["audit_sha256"],
                pretokenized=str(pretok), pretokenized_sha256=pretok_comp["sha256"],
                short_seed=64136, logit_atol=base.MAX_LOGIT_DELTA,
                text_cases=["english","korean"], text_tokens=1017, generated=base.GEN)


def verify(profile):
    if profile != contract():
        raise ValueError("The sealed exact source and planned inputs differ")


def prepare():
    gate()
    profile = contract()
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    base.WRITE(PROFILE, profile)
    if base.READ(PROFILE) != profile or torch.cuda.is_initialized():
        raise ValueError("An identical JSON readback and isolated CPU are required")
    print("G4_COMPACT_FIXED_EDIT_PREFLIGHT", profile["binary_sha256"][:12], profile["cpu"], flush=True)


def seal(fd):
    fcntl.fcntl(fd, base.prior.DEPLOY.F_ADD_SEALS, base.prior.DEPLOY.SEALS)
    assert fcntl.fcntl(fd, base.prior.DEPLOY.F_GET_SEALS) == base.prior.DEPLOY.SEALS


def changed_bytes(reference, edited, size):
    positions = []
    for start in range(0, size, 1 << 20):
        count = min(size-start, 1 << 20)
        a, b = (np.frombuffer(os.pread(fd, count, start), dtype=np.uint8) for fd in (reference, edited))
        if len(a) != count or len(b) != count:
            raise ValueError("Sealed files differ in size")
        positions.extend((start+np.flatnonzero(a != b)).tolist())
    return positions


def edited_codes(model, clean, packets, checks, lookup):
    overrides = []
    for index, data in packets.items():
        layer = int(index)
        target = editing.unpack(clean[layer], data)
        expected = PACK.pack_weight(target, data["group"])
        packed = model.layers[layer].mlp[0].down_proj
        updated = packed.packed_codes.clone()
        patch_offsets = []
        for entry in checks:
            if entry["physical_layer"] != layer:
                continue
            row, group, byte = (entry[k] for k in ("row", "group_index", "group_byte"))
            word = unpack_trits(updated[row,group,byte].reshape(1), 5)
            for digit, code in entry["edited_trits"]:
                word[digit] = code
            packed_word, _ = pack_trits(word)
            updated[row,group,byte] = packed_word.item()
            patch_offsets.append(entry["physical_packed_code_byte_offset"])
            restored = np.empty(packed.in_f, dtype=np.float32)
            row_id = ctypes.c_int64(row)
            status = lookup(updated.data_ptr(), packed.group_scales.data_ptr(), ctypes.byref(row_id),
                            restored.ctypes.data, 1, packed.out_f, packed.in_f, packed.group)
            if status or not np.array_equal(restored, target[row].numpy()):
                raise ValueError("Compiled AVX2 row does not restore the independently edited tensor")
        got = torch.nonzero(updated.flatten() != packed.packed_codes.flatten()).flatten().tolist()
        if (got != sorted(patch_offsets) or not torch.equal(updated, expected["codes"])
                or not torch.equal(packed.group_scales, expected["scales"])):
            raise ValueError("Exact physical byte patch differs from complete reference re-encoding")
        overrides.append((packed, updated))
    return overrides


def text_request(binary, fds, text, reference, tok, index, arm, language):
    with ExitStack() as stack:
        extra = [base.memfile(f"p108_g4_text_{index}_{part}") for part in range(3)]
        for handle in extra:
            stack.callback(os.close, handle)
        args = (*fds, *extra)
        command = [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(ROOT / text_exec.SCRIPT),
                   "encode", binary, *map(str,args)]
        start = perf_counter()
        call = subprocess.run(command, input=text, capture_output=True, timeout=55, pass_fds=args, cwd=ROOT)
        elapsed = perf_counter()-start
        if call.returncode:
            print(call.stderr.decode("utf-8", "replace"), flush=True)
            call.check_returncode()
        observed = json.loads(call.stdout)
    base.WRITE(OUT / f"raw_{index}.json", observed)
    native = observed["native"]
    if (observed["encoding"]["ids"] != reference["encoding"]["ids"]
            or len(observed["encoding"]["ids"]) != 1017
            or observed["encoding"]["pid"] != observed["native_pid"]
            or observed["decoding"]["pid"] != observed["native_pid"]
            or observed["decoding"]["text"] != tok.decode(native["ids"],skip_special_tokens=True)
            or any(native[k] != reference["native"][k] for k in ("model_bytes","kv_bytes","scratch_bytes"))):
        raise ValueError("Full text request differs in tokenization, resource geometry or decoding")
    peak = max(
        *(native[s][key] for s in ("before","loaded","prefilled","complete") for key in ("rss","vm_hwm")),
        *(value for name in ("encoding","decoding") for stage in ("startup","loaded","complete")
          for value in observed[name][stage].values()),
    )
    row = dict(arm=arm, language=language, observed_peak_bytes=peak, within_40mb=peak<=40_000_000,
               native_seconds=sum(native["seconds"]), wall_seconds=elapsed, ids=native["ids"],
               same_as_original_ids=native["ids"]==reference["native"]["ids"],
               same_pid=True, parsed_decoding_equal=True)
    print("G4_COMPACT_EDIT_TEXT", row, flush=True)
    return row


@torch.inference_mode()
def actual():
    gate(240)
    profile = base.READ(PROFILE)
    verify(profile)
    os.sched_setaffinity(0, {profile["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    model, step = ORIGIN.load_model()
    assert step == profile["candidate"]["checkpoint_step"]
    owners = physical_down_owners(model)
    clean = {i: owners[i].module._wq.detach().clone() for i in (2,6)}
    payload = PACK.export_payload(model, provenance={"tag":TAG}, head_rows=base.prior.embedding.HEAD_ROWS)
    del model
    model = PACK.load_payload(payload)
    del payload
    model.quantize_embedding("int8")
    model.cfg.emb_chunk = base.prior.embedding.HEAD_ROWS
    tokenizer = load_tokenizer("ko-en",32768)
    short = torch.randint(35,32768,(base.SHORT,),generator=torch.Generator().manual_seed(profile["short_seed"])).tolist()
    lookup = ctypes.CDLL(profile["audit"]).p014e_cpu_lookup
    lookup.argtypes = [ctypes.c_void_p]*4 + [ctypes.c_int64]*4
    lookup.restype = ctypes.c_int
    packet, offsets = base.READ(PACKETS)["geometry"]["packets"], base.READ(OFFSETS)["cases"]
    codec = bytelevel.wire(json.loads(bytelevel.TOK.read_bytes()))
    tok_info = base.READ(bytelevel.OUT / "profile.json")
    if [sha256(x).hexdigest().upper() for x in codec] != [v["sha256"] for v in tok_info["files"]["split_model"]]:
        raise ValueError("The existing proven tokenizer pieces differ")
    prompts = base.READ(bytelevel.OUT / "report.json")["runs"]["split_model"][0]["outputs"]
    previous = {d["case"]:d for d in base.READ(text_exec.OUT / "report.json")["runs"]}
    evidence, requests = {}, []
    with ExitStack() as stack:
        def fd(name):
            handle = base.memfile(name)
            stack.callback(os.close, handle)
            return handle

        base_fd = fd("p108_g4_unedited")
        weight_bytes = profile["candidate"]["model_tensor_bytes"]
        source = base.model_blob(model, base_fd, weight_bytes)
        if source != profile["model"]:
            raise ValueError("The original compact artifact differs from the earlier measured model")
        unedited, _ = base.short_oracle(model, short, tokenizer)
        tokenize = [fd("p108_g4_vocab"), fd("p108_g4_merges")]
        for k, payload in zip(tokenize,codec,strict=True):
            text_exec.store(k,payload)
            seal(k)
        for arm in ARMS:
            gate(20)
            model_fd = fd("p108_g4_" + arm)
            adjusted = edited_codes(model, clean, packet[arm], offsets[arm]["checks"], lookup)
            with ExitStack() as patch_scope:
                for layer, codes in adjusted:
                    patch_scope.enter_context(patch.object(layer,"packed_codes",codes))
                sealed = base.model_blob(model, model_fd, weight_bytes)
                oracle, ids = base.short_oracle(model, short, tokenizer)
            changed = changed_bytes(base_fd,model_fd,source["artifact_bytes"])
            if len(changed) != offsets[arm]["packed_bytes_touched"] or sealed["artifact_bytes"] != source["artifact_bytes"]:
                raise ValueError("Only the expected bytes may change in the actual sealed deployment artifact")
            native, scores = base.run_native(Path(profile["pretokenized"]),model_fd,short,scores=True)
            maximum = float(np.max(np.abs(scores-oracle.numpy())))
            effect = float(torch.max(torch.abs(oracle-unedited)))
            if native["ids"] != ids or maximum > profile["logit_atol"] or effect == 0.:
                raise ValueError("Deployed short test did not preserve the edited oracle and actual effect")
            evidence[arm]=dict(blob=sealed,changed_serialized_byte_offsets=changed,
                               short_native_ids=native["ids"],short_oracle_ids=ids,
                               torch_native_max_abs_logit_delta=maximum, short_edit_logit_effect=effect,
                               packed_reencode_equal=True, compiled_rows_equal=True)
            base.WRITE(OUT / (arm+"_transfer.json"),evidence[arm])
            print("G4_COMPACT_EDIT_TRANSFER",arm,changed,maximum,effect,flush=True)
            for language in profile["text_cases"]:
                result = text_request(profile["binary"],(model_fd,*tokenize),
                                      prompts[language]["decoded"].encode("utf-8"),previous[language],
                                      tokenizer,len(requests),arm,language)
                requests.append(result)
    verify(profile)
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU-only request unexpectedly initialized CUDA")
    peak = max(row["observed_peak_bytes"] for row in requests)
    base.WRITE(OUT / "report.json",dict(profile_sha256=base.SHA(PROFILE),source=source,arms=evidence,
                                      requests=requests,peak_bytes=peak,within_40mb=peak<=40_000_000,
                                      checkpoint_writes=0,cuda_initialized=False,all_native_fds_closed=True))
    print("G4_COMPACT_EDIT_RESULT",peak,len(requests),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","actual"))
    args=parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("This deployment experiment is CPU-only")
    (prepare if args.phase == "prepare" else actual)()


if __name__ == "__main__":
    main()
