"""Read-only bounded FP32 teacher-feature windows, not a model or full trainer.

Declared identities are not corpus rights, tokenizer alignment or admission.
Limits describe reader-owned arrays and metadata, not process RSS, OS cache or
arrays retained by callers. No full75M writer or online coexistence is provided.
"""
from __future__ import annotations

import ast
from bisect import bisect_right
import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

import numpy as np

SCHEMA = "P106B_TEACHER_FEATURE_WINDOW_V1"
STATE_SCHEMA = "P106B_TEACHER_FEATURE_WINDOW_CURSOR_V1"
RESUME_SCOPE = "ORDERED_FEATURE_SOURCE_ONLY_NOT_MODEL_OPTIMIZER_OR_RNG"
HEADER_CAP = 4096


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest().upper()


def _integer(value, label, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError("feature window invalid integer: " + label)


def _fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)


@dataclass(frozen=True)
class FeatureBatch:
    values: np.ndarray
    row_ids: tuple
    positions: tuple
    rows: dict
    start: int
    stop: int


class FeatureWindow:
    """One source array plus one prepared copied batch; explicit finish boundary.

    Only flat caller-selected NPY files inside the exact regular root are read.
    Files must stay immutable while cached. Reopening rechecks their whole SHA;
    cached reuse checks inode/size/mtime. Consumers own returned copies and must
    apply their own retention/runtime memory policy and complete backward before
    recording a full training checkpoint. This cursor owns no training state.
    """
    def __init__(self, records, *, root, identities, split, hidden_width=1024, batch_positions=128,
                 max_feature_bytes=4*1024**2, max_window_payload_bytes=256*1024**2,
                 max_batch_bytes=512*1024, max_metadata_bytes=8*1024**2,
                 max_records=1024, max_positions=65536):
        options = dict(hidden_width=hidden_width, batch_positions=batch_positions,
            max_feature_bytes=max_feature_bytes, max_window_payload_bytes=max_window_payload_bytes,
            max_batch_bytes=max_batch_bytes, max_metadata_bytes=max_metadata_bytes,
            max_records=max_records, max_positions=max_positions)
        for key, value in options.items():
            _integer(value, key)
        if sys.byteorder != "little":
            raise ValueError("feature window currently requires a little-endian host")
        if split not in ("train", "dev", "test", "calibration"):
            raise ValueError("feature window explicit single split required")
        keys = {"teacher_sha256", "tokenizer_sha256", "mapping_sha256", "data_sha256"}
        if (not isinstance(identities, dict) or set(identities) != keys
                or any(not isinstance(v, str) or re.fullmatch("[0-9A-F]{64}", v) is None for v in identities.values())):
            raise ValueError("feature window explicit declared identity SHA values required")
        if not isinstance(records, (list, tuple)) or not 0 < len(records) <= max_records:
            raise ValueError("feature window bounded nonempty record list required")
        raw = _canonical(records).encode("utf-8")
        if len(raw) > max_metadata_bytes:
            raise ValueError("feature window metadata quota exceeded")
        rows = json.loads(raw)
        seen, ends, count, payload = set(), [], 0, 0
        required = {"row_id", "semantic_root_id", "split", "feature_file", "feature_sha256", "teacher_tokens", "positions"}
        for row in rows:
            if not isinstance(row, dict) or not required <= row.keys() or row["split"] != split:
                raise ValueError("feature window complete same-split row required")
            for key in ("row_id", "semantic_root_id"):
                if not isinstance(row[key], str) or not 0 < len(row[key]) <= 256:
                    raise ValueError("feature window bounded source identifiers required")
            if row["row_id"] in seen:
                raise ValueError("feature window duplicate row ID")
            seen.add(row["row_id"])
            filename = row["feature_file"]
            if (not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,155}\.npy", filename)
                    or ".." in filename):
                raise ValueError("feature window exact flat relative NPY name required")
            if not isinstance(row["feature_sha256"], str) or not re.fullmatch("[0-9A-F]{64}", row["feature_sha256"]):
                raise ValueError("feature window whole file SHA required")
            _integer(row["teacher_tokens"], "teacher_tokens")
            size = row["teacher_tokens"] * hidden_width * 4
            if size > max_feature_bytes:
                raise ValueError("feature window single feature payload quota exceeded")
            payload += size
            if payload > max_window_payload_bytes:
                raise ValueError("feature window total input payload quota exceeded")
            positions = row["positions"]
            if not isinstance(positions, list):
                raise ValueError("feature window explicit ordered selected positions required")
            for position in positions:
                if (not isinstance(position, dict)
                        or type(position.get("teacher_predictor_raw_index")) is not int
                        or not 0 <= position["teacher_predictor_raw_index"] < row["teacher_tokens"]):
                    raise ValueError("feature window original teacher predictor index required")
            count += len(positions)
            if count > max_positions:
                raise ValueError("feature window selected position quota exceeded")
            ends.append(count)
        if not count or batch_positions * hidden_width * 4 > max_batch_bytes:
            raise ValueError("feature window nonempty selection and bounded batch payload required")
        directory = Path(root).absolute()
        if not directory.is_dir() or directory.is_symlink() or directory.resolve(strict=True) != directory:
            raise ValueError("feature window existing unlinked exact root required")
        self._root, self._rows, self._ends = directory, rows, ends
        self._options, self._total = options, count
        self._contract = dict(schema=SCHEMA, root=str(directory), identities=copy.deepcopy(identities), split=split,
            records=rows, options=options, selected_positions=count, input_payload_bytes=payload,
            implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
            identity_scope="DECLARED_IDENTITIES_AND_PER_OPEN_VERIFIED_FILES_NOT_CORPUS_ADMISSION")
        self.window_sha256 = _sha(self._contract)
        self._offset = self._batches = 0
        self._pending = self._feature = self._feature_key = self._feature_stat = None
        self._broken = False
        self.stats = dict(files_opened=0, bytes_hashed=0, payload_bytes_read=0,
            maximum_feature_array_bytes=0, maximum_prepared_batch_bytes=0)

    @property
    def contract(self):
        return copy.deepcopy(self._contract)

    def _read_feature(self, row):
        path = self._root / row["feature_file"]
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("feature window unlinked regular feature file required")
        key = (row["feature_file"], row["feature_sha256"], row["teacher_tokens"])
        if key == self._feature_key:
            if _fingerprint(info) != self._feature_stat:
                raise ValueError("feature window cached source file changed")
            return self._feature
        self._feature = self._feature_key = self._feature_stat = None
        expected_payload = row["teacher_tokens"] * self._options["hidden_width"] * 4
        if not expected_payload < info.st_size <= expected_payload + HEADER_CAP + 12:
            raise ValueError("feature window file size outside declared header/payload bound")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            self.stats["files_opened"] += 1
            before = os.fstat(stream.fileno())
            if _fingerprint(before) != _fingerprint(info):
                raise ValueError("feature window source changed before open")
            prefix = stream.read(8)
            if len(prefix) != 8 or prefix[:6] != b"\x93NUMPY" or prefix[6:] not in (b"\x01\x00", b"\x02\x00"):
                raise ValueError("feature window NPY1/2 only; compressed/pickle formats forbidden")
            width = 2 if prefix[6] == 1 else 4
            length_bytes = stream.read(width)
            if len(length_bytes) != width:
                raise ValueError("feature window incomplete header length")
            length = struct.unpack("<H" if width == 2 else "<I", length_bytes)[0]
            if not 0 < length <= HEADER_CAP:
                raise ValueError("feature window NPY header quota exceeded before payload allocation")
            header_bytes = stream.read(length)
            if len(header_bytes) != length or not header_bytes.endswith(b"\n"):
                raise ValueError("feature window incomplete bounded NPY header")
            try:
                header = ast.literal_eval(header_bytes.decode("latin1"))
            except (ValueError, SyntaxError, RecursionError) as exc:
                raise ValueError("feature window literal NPY header required") from exc
            expected_shape = (row["teacher_tokens"], self._options["hidden_width"])
            if (not isinstance(header, dict) or set(header) != {"descr", "fortran_order", "shape"}
                    or header["descr"] != "<f4" or header["fortran_order"] is not False
                    or not isinstance(header["shape"], tuple) or any(type(d) is not int for d in header["shape"])
                    or header["shape"] != expected_shape):
                raise ValueError("feature window exact C-order little-endian FP32 shape required")
            offset = stream.tell()
            if before.st_size != offset + expected_payload:
                raise ValueError("feature window exact NPY payload size required")
            digest = hashlib.sha256()
            stream.seek(0)
            for block in iter(lambda: stream.read(1024**2), b""):
                digest.update(block)
                self.stats["bytes_hashed"] += len(block)
            if digest.hexdigest().upper() != row["feature_sha256"]:
                raise ValueError("feature window full file SHA differs")
            stream.seek(offset)
            array = np.fromfile(stream, dtype="<f4", count=expected_payload // 4).reshape(expected_shape)
            self.stats["payload_bytes_read"] += array.nbytes
            for start in range(0, len(array), 64):
                if not bool(np.isfinite(array[start:start+64]).all()):
                    raise ValueError("feature window finite original FP32 rows required")
            if _fingerprint(os.fstat(stream.fileno())) != _fingerprint(before):
                raise ValueError("feature window source changed during read")
        if _fingerprint(path.lstat()) != _fingerprint(before):
            raise ValueError("feature window source path changed during read")
        self._feature, self._feature_key, self._feature_stat = array, key, _fingerprint(before)
        self.stats["maximum_feature_array_bytes"] = max(self.stats["maximum_feature_array_bytes"], array.nbytes)
        return array

    def prepare(self):
        if self._broken or self._pending is not None:
            raise RuntimeError("feature window finish current batch or restore a fresh reader")
        if self._offset == self._total:
            raise StopIteration("feature window complete")
        stop = min(self._offset + self._options["batch_positions"], self._total)
        values = np.empty((stop-self._offset, self._options["hidden_width"]), dtype=np.float32)
        ids, positions, metadata = [], [], {}
        try:
            for local, global_index in enumerate(range(self._offset, stop)):
                row_index = bisect_right(self._ends, global_index)
                start = self._ends[row_index-1] if row_index else 0
                row = self._rows[row_index]
                position = row["positions"][global_index-start]
                # Do not keep a local view/reference to a previous full array
                # while the next file is allocated.
                values[local] = self._read_feature(row)[position["teacher_predictor_raw_index"]]
                ids.append(row["row_id"])
                positions.append(copy.deepcopy(position))
                if row["row_id"] not in metadata:
                    metadata[row["row_id"]] = copy.deepcopy({k:v for k,v in row.items() if k != "positions"})
            values.flags.writeable = False
            self._pending = FeatureBatch(values, tuple(ids), tuple(positions), metadata, self._offset, stop)
            self.stats["maximum_prepared_batch_bytes"] = max(self.stats["maximum_prepared_batch_bytes"], values.nbytes)
            return self._pending
        except BaseException:
            self._broken = True
            self._feature = self._feature_key = self._feature_stat = None
            raise

    def finish(self):
        if self._broken or self._pending is None:
            raise RuntimeError("feature window one complete prepared source batch required")
        self._offset = self._pending.stop
        self._batches += 1
        self._pending = None

    def state_dict(self):
        if self._broken or self._pending is not None:
            raise RuntimeError("feature window source state requires a complete healthy batch boundary")
        value = dict(schema=STATE_SCHEMA, window_sha256=self.window_sha256, next_position=self._offset,
            committed_batches=self._batches, resume_scope=RESUME_SCOPE)
        value["state_sha256"] = _sha(value)
        return value

    def load_state_dict(self, value):
        if self._broken or self._pending is not None or self._offset or self._batches:
            raise RuntimeError("feature window restore requires a fresh healthy reader")
        value = copy.deepcopy(value)
        if not isinstance(value, dict) or set(value) != {"schema", "window_sha256", "next_position", "committed_batches", "resume_scope", "state_sha256"}:
            raise ValueError("feature window exact source cursor schema required")
        checksum = value.pop("state_sha256")
        if (checksum != _sha(value) or value["schema"] != STATE_SCHEMA
                or value["window_sha256"] != self.window_sha256 or value["resume_scope"] != RESUME_SCOPE):
            raise ValueError("feature window source/window/schema identity differs")
        offset, batches = value["next_position"], value["committed_batches"]
        _integer(offset, "next_position", 0); _integer(batches, "committed_batches", 0)
        maximum = (self._total + self._options["batch_positions"] - 1) // self._options["batch_positions"]
        if batches > maximum or offset != min(batches * self._options["batch_positions"], self._total):
            raise ValueError("feature window only exact batch boundaries are resumable")
        self._offset, self._batches = offset, batches
