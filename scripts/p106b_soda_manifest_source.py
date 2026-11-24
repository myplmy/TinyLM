"""Walk sealed SODA-shaped shards while preserving prepared and held source rows."""

from bisect import bisect_right
from dataclasses import dataclass
import hashlib
import itertools
import json
from pathlib import Path

from scripts.p106b_public_refill import english_specs
from scripts.p106b_shards import verify
from scripts.p106b_soda_candidate_wire import PreparedDialogue, prepare_source, teacher_payload


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def source_spec_sha256(spec: dict) -> str:
    if type(spec) is not dict or spec not in english_specs():
        raise ValueError("use an existing source specification")
    return digest(canonical(spec))


@dataclass(frozen=True)
class SourceRow:
    index: int
    shard: str
    row_in_shard: int
    raw_sha256: str
    next_cursor: dict
    prepared: PreparedDialogue | None


@dataclass(frozen=True)
class SourceRequest:
    row: SourceRow
    request_sha256: str | None
    _payload_json: bytes | None

    @property
    def payload(self):
        return json.loads(self._payload_json) if self._payload_json is not None else None


class ManifestSodaSource:
    """Read one sealed version. The caller owns when to persist the next cursor."""

    def __init__(self, manifest_path: Path, expected_sha256: str, source_spec: dict):
        manifest_path = Path(manifest_path)
        if manifest_path.is_symlink() or manifest_path.parent.is_symlink():
            raise ValueError("use an explicit regular manifest and directory")
        if type(source_spec) is not dict:
            raise ValueError("use an existing source specification")
        self._spec = source_spec.copy()
        self.source_spec_sha256 = source_spec_sha256(self._spec)
        self.directory = manifest_path.parent
        raw = manifest_path.read_bytes()
        self.manifest_sha256 = digest(raw)
        if self.manifest_sha256 != expected_sha256:
            raise ValueError("manifest identity differs")
        manifest = json.loads(raw)
        lineage = manifest.get("lineage", {})
        if type(lineage) is not dict:
            raise ValueError("invalid source lineage in the manifest")
        self.source_spec_bound = "source_spec_sha256" in lineage
        if self.source_spec_bound and lineage["source_spec_sha256"] != self.source_spec_sha256:
            raise ValueError("manifest source specification differs")
        verify(self.directory,manifest)
        self._shards = manifest["shards"]
        self._ends = tuple(itertools.accumulate(s["rows"] for s in self._shards))
        if not self._ends or self._ends[-1] != manifest["rows"]:
            raise ValueError("no complete source rows")
        self._cached_shard = -1
        self._cached_rows = ()

    def start(self):
        return self._cursor(0)

    def _cursor(self, index):
        return dict(manifest_sha256=self.manifest_sha256, source_spec_sha256=self.source_spec_sha256,
                    next_row=index)

    def _index(self, cursor, expected_keys):
        if (type(cursor) is not dict or set(cursor) != expected_keys
                or cursor["manifest_sha256"] != self.manifest_sha256
                or type(cursor["next_row"]) is not int or not 0 <= cursor["next_row"] <= self._ends[-1]):
            raise ValueError("cursor is outside this sealed source")
        return cursor["next_row"]

    def bind_legacy_cursor(self, cursor, *, verified_source_spec):
        """Recover a two-field cursor using its independently established source spec."""
        index = self._index(cursor, {"manifest_sha256", "next_row"})
        if source_spec_sha256(verified_source_spec) != self.source_spec_sha256:
            raise ValueError("verified legacy source specification differs")
        return self._cursor(index)

    def _load(self, index):
        if index != self._cached_shard:
            desc = self._shards[index]
            path = self.directory / desc["path"]
            if path.is_symlink() or not path.is_file():
                raise ValueError("sealed shard replaced")
            with path.open("rb") as stream:
                raw = stream.read(desc["bytes"]+1)
            if len(raw) != desc["bytes"] or digest(raw) != desc["sha256"]:
                raise ValueError("sealed shard bytes differ")
            self._cached_rows = tuple(raw[:-1].split(b"\n"))
            self._cached_shard = index
        return self._cached_rows

    def read_next(self, cursor):
        """Return a proposed successor with its source evidence. EOF returns None."""
        if self.source_spec_bound and type(cursor) is dict and set(cursor) == {"manifest_sha256", "next_row"}:
            cursor = self.bind_legacy_cursor(cursor, verified_source_spec=self._spec)
        index = self._index(cursor, {"manifest_sha256", "source_spec_sha256", "next_row"})
        if cursor["source_spec_sha256"] != self.source_spec_sha256:
            raise ValueError("cursor source specification differs")
        shard = bisect_right(self._ends,index)
        if shard == len(self._ends):
            return None
        offset = index - (self._ends[shard-1] if shard else 0)
        line = self._load(shard)[offset]
        row = json.loads(line)
        try:
            prepared = prepare_source(row,self._spec)
        except ValueError:
            prepared = None
        return SourceRow(index,self._shards[shard]["path"],offset,digest(line+b"\n"),
            self._cursor(index+1),prepared)

    def read_request(self, cursor, language, profile, seed, *, history=()):
        """Prepare the existing teacher wire without dispatching it or advancing a cursor."""
        if not self.source_spec_bound:
            raise ValueError("teacher request needs a manifest-bound source specification")
        row = self.read_next(cursor)
        if row is None:
            return None
        if row.prepared is None:
            return SourceRequest(row, None, None)
        payload = teacher_payload(row.prepared, language, profile, seed, history=history)
        receipt = dict(next_cursor=row.next_cursor, row_sha256=row.raw_sha256, payload=payload)
        return SourceRequest(row, digest(canonical(receipt)), canonical(payload))
