#!/usr/bin/env python3
"""Shared contracts for Stage 2-10 corpus generation, packaging, and audit."""
from __future__ import annotations

import hashlib
import functools
import json
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

try:
    import regex as _regex
except ImportError:  # pragma: no cover - surfaced as a clear runtime gate.
    _regex = None


CONTROLLED_RELATIONS = (
    "is_a",
    "subclass_of",
    "part_of",
    "classification",
    "boundary",
    "contrast",
    "comparison",
    "function",
    "role",
    "process",
    "state",
    "attribute",
    "other",
)
CONTROLLED_SET = frozenset(CONTROLLED_RELATIONS)
RECORDS_PER_FILE = 150
VAL_TRUE_PER_FILE = 18
GENERATOR_KIND = "semantic_composition_generator"

FILENAME_RE = re.compile(
    r"stage(?P<stage>\d+)_\((?P<slot>\d+)\)(?P<slug>[a-z0-9_]+)"
    r"_high_density_(?P<split>train|val)_(?P<version>v\d{2,})\.json"
)
ID_RANGE_RE = re.compile(
    r"(?P<prefix>S(?:10|[2-9])-[A-Z]+[HV])-(?P<first>\d{5})"
    r" ~ (?P=prefix)-(?P<last>\d{5})"
)
RESERVATION_ID_RE = re.compile(
    r"S(?P<stage>10|[2-9])-A(?P<area>\d{2})-(?P<split>[TV])-(?P<seq>\d{3,})"
)
UNICODE_ESCAPE_RE = re.compile(rb"\\u[0-9a-fA-F]{4}")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
BPE_PATTERN_TEXT = r"'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"
KNOWN_GRAMMAR_PATTERNS: Mapping[str, re.Pattern[str]] = {
    "duplicate_value_noun": re.compile(r"값\s+값"),
    "duplicated_condition_suffix": re.compile(r"때일\s+때"),
    "finite_predicate_before_suffix": re.compile(
        r"(?:한다|된다|낸다|고른다|찾는다|잰다|맡는다|적는다)\s+뒤"
    ),
    # Regression signatures reported during independent generator review.
    "plain_subject_wa": re.compile(r"관찰\s+표본와"),
    "plain_hazard_ga": re.compile(r"초반\s+사실\s+망각가"),
}


class ContractError(ValueError):
    """A canonical ledger/source/corpus invariant failed."""


@dataclass(frozen=True)
class AreaContract:
    stage: int
    number: int
    slot: int
    slug: str
    packet_type: str
    code: str
    name: str
    learning_goal: str
    error_suppression_axis: str
    train_id_prefix: str
    val_id_prefix: str
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    stage: int
    area_number: int
    slot: int
    slug: str
    split: str
    version: str
    filename: str
    id_range: str
    id_prefix: str
    id_first: int
    id_last: int
    record_count: int
    concept_family: str
    domain: str
    semantic_axis: str
    status: str
    raw: Mapping[str, Any]

    @property
    def version_number(self) -> int:
        return int(self.version[1:])


@dataclass(frozen=True)
class Ledger:
    path: Path
    sha256: str
    raw: Mapping[str, Any]
    areas: Mapping[tuple[int, int], AreaContract]
    reservations: tuple[Reservation, ...]
    by_id: Mapping[str, Reservation]


@dataclass(frozen=True)
class SourceRow:
    primary: str
    concepts: tuple[str, ...]
    text: str
    relations: tuple[str, ...]
    other_type: str | None
    unseen_relation: bool | None
    provenance: Mapping[str, Any] | None
    authoring: Mapping[str, Any] | None
    line_number: int

    @property
    def relation_set(self) -> tuple[str, ...]:
        return tuple(sorted(self.relations))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalized_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in value if ch.isalnum())


def canonical_json_bytes(value: Any, *, indent: int | None = 2) -> bytes:
    kwargs: dict[str, Any] = {"ensure_ascii": False}
    if indent is None:
        kwargs["separators"] = (",", ":")
    else:
        kwargs["indent"] = indent
    return (json.dumps(value, **kwargs) + "\n").encode("utf-8")


def format_version(number: int) -> str:
    if number < 1:
        raise ContractError(f"version must be positive: {number}")
    return f"v{number:02d}" if number < 100 else f"v{number}"


def _require_text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{location}: expected non-empty string")
    return value.strip()


def load_ledger(path: Path) -> Ledger:
    """Load and exhaustively validate the current central reservation ledger."""
    path = path.resolve()
    raw_bytes = path.read_bytes()
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise ContractError(f"{path}: UTF-8 BOM is not canonical")
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{path}: cannot parse UTF-8 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{path}: top-level ledger must be an object")
    if tuple(data.get("controlled_relations", ())) != CONTROLLED_RELATIONS:
        raise ContractError(f"{path}: controlled_relations is not the canonical 13-label list")

    stage_defs = data.get("stage_definitions")
    if not isinstance(stage_defs, list):
        raise ContractError(f"{path}: stage_definitions must be an array")
    areas: dict[tuple[int, int], AreaContract] = {}
    seen_slugs: set[tuple[int, str]] = set()
    for sidx, stage_raw in enumerate(stage_defs):
        location = f"{path}:stage_definitions[{sidx}]"
        if not isinstance(stage_raw, dict):
            raise ContractError(f"{location}: expected object")
        stage = int(stage_raw.get("stage", -1))
        if stage not in range(2, 11):
            raise ContractError(f"{location}: invalid stage {stage}")
        raw_areas = stage_raw.get("areas")
        if not isinstance(raw_areas, list) or not raw_areas:
            raise ContractError(f"{location}: areas must be a non-empty array")
        for aidx, area_raw in enumerate(raw_areas):
            aloc = f"{location}.areas[{aidx}]"
            if not isinstance(area_raw, dict):
                raise ContractError(f"{aloc}: expected object")
            number = int(area_raw.get("curriculum_area_number", -1))
            slot = int(area_raw.get("file_area_slot", -1))
            slug = _require_text(area_raw.get("slug"), f"{aloc}.slug")
            key = (stage, number)
            if key in areas:
                raise ContractError(f"{aloc}: duplicate Stage/area {key}")
            if (stage, slug) in seen_slugs:
                raise ContractError(f"{aloc}: duplicate Stage/slug {(stage, slug)}")
            seen_slugs.add((stage, slug))
            focus = area_raw.get("relation_focus", [])
            if not isinstance(focus, list) or any(x not in CONTROLLED_SET for x in focus):
                raise ContractError(f"{aloc}: relation_focus contains an uncontrolled label")
            # relation_focus is deliberately not stored as a generation constraint.
            areas[key] = AreaContract(
                stage=stage,
                number=number,
                slot=slot,
                slug=slug,
                packet_type=_require_text(area_raw.get("packet_type"), f"{aloc}.packet_type"),
                code=_require_text(area_raw.get("code"), f"{aloc}.code"),
                name=_require_text(area_raw.get("name"), f"{aloc}.name"),
                learning_goal=_require_text(area_raw.get("learning_goal"), f"{aloc}.learning_goal"),
                error_suppression_axis=_require_text(
                    area_raw.get("error_suppression_axis"), f"{aloc}.error_suppression_axis"
                ),
                train_id_prefix=_require_text(area_raw.get("train_id_prefix"), f"{aloc}.train_id_prefix"),
                val_id_prefix=_require_text(area_raw.get("val_id_prefix"), f"{aloc}.val_id_prefix"),
                raw=area_raw,
            )
    if {stage for stage, _ in areas} != set(range(2, 11)):
        raise ContractError(f"{path}: stage definitions must cover Stage 2 through 10")

    raw_rows = data.get("reservations")
    if not isinstance(raw_rows, list):
        raise ContractError(f"{path}: reservations must be an array")
    reservations: list[Reservation] = []
    seen: dict[str, set[str]] = {
        "reservation_id": set(),
        "filename": set(),
        "concept_family": set(),
        "normalized_family": set(),
        "id_range": set(),
    }
    required = {
        "reservation_id", "stage", "curriculum_area_number", "file_area_slot",
        "area_slug", "split", "version", "filename", "id_range",
        "record_count", "concept_family", "domain", "semantic_axis", "status",
    }
    for index, row in enumerate(raw_rows):
        location = f"{path}:reservations[{index}]"
        if not isinstance(row, dict) or not required <= set(row):
            missing = sorted(required - set(row) if isinstance(row, dict) else required)
            raise ContractError(f"{location}: missing keys {missing}")
        reservation_id = _require_text(row["reservation_id"], f"{location}.reservation_id")
        stage = int(row["stage"])
        area_number = int(row["curriculum_area_number"])
        area = areas.get((stage, area_number))
        if area is None:
            raise ContractError(f"{location}: unknown Stage/area {(stage, area_number)}")
        slot = int(row["file_area_slot"])
        slug = _require_text(row["area_slug"], f"{location}.area_slug")
        split = _require_text(row["split"], f"{location}.split")
        version = _require_text(row["version"], f"{location}.version")
        filename = _require_text(row["filename"], f"{location}.filename")
        id_range = _require_text(row["id_range"], f"{location}.id_range")
        record_count = int(row["record_count"])
        concept_family = _require_text(row["concept_family"], f"{location}.concept_family")
        domain = _require_text(row["domain"], f"{location}.domain")
        semantic_axis = _require_text(row["semantic_axis"], f"{location}.semantic_axis")
        status = _require_text(row["status"], f"{location}.status")
        if split not in {"train", "val"}:
            raise ContractError(f"{location}: split must be train or val")
        if record_count != RECORDS_PER_FILE:
            raise ContractError(f"{location}: record_count must be {RECORDS_PER_FILE}")
        if split == "val" and int(row.get("unseen_relation_target_records", -1)) != VAL_TRUE_PER_FILE:
            raise ContractError(f"{location}: val unseen target must be {VAL_TRUE_PER_FILE}")
        if slot != area.slot or slug != area.slug:
            raise ContractError(f"{location}: reservation area projection mismatch")

        version_match = re.fullmatch(r"v(\d{2,})", version)
        if not version_match:
            raise ContractError(f"{location}: invalid version {version!r}")
        version_number = int(version_match.group(1))
        if version != format_version(version_number):
            raise ContractError(f"{location}: non-canonical version padding {version!r}")
        filename_match = FILENAME_RE.fullmatch(filename)
        if not filename_match:
            raise ContractError(f"{location}: invalid filename {filename!r}")
        projected = filename_match.groupdict()
        if (
            int(projected["stage"]) != stage
            or int(projected["slot"]) != slot
            or projected["slug"] != slug
            or projected["split"] != split
            or projected["version"] != version
        ):
            raise ContractError(f"{location}: filename fields differ from reservation")

        rid_match = RESERVATION_ID_RE.fullmatch(reservation_id)
        expected_split_code = "T" if split == "train" else "V"
        if not rid_match or (
            int(rid_match.group("stage")) != stage
            or int(rid_match.group("area")) != area_number
            or rid_match.group("split") != expected_split_code
            or int(rid_match.group("seq")) != version_number
        ):
            raise ContractError(f"{location}: reservation_id/version projection mismatch")

        range_match = ID_RANGE_RE.fullmatch(id_range)
        if not range_match:
            raise ContractError(f"{location}: invalid id_range {id_range!r}")
        id_prefix = range_match.group("prefix")
        id_first = int(range_match.group("first"))
        id_last = int(range_match.group("last"))
        expected_prefix = area.train_id_prefix if split == "train" else area.val_id_prefix
        expected_first = (version_number - 1) * RECORDS_PER_FILE + 1
        expected_last = version_number * RECORDS_PER_FILE
        if id_prefix != expected_prefix or (id_first, id_last) != (expected_first, expected_last):
            raise ContractError(f"{location}: id range does not follow ledger area/version")
        if domain not in concept_family or semantic_axis not in concept_family:
            raise ContractError(f"{location}: concept_family does not project domain and semantic_axis")

        unique_values = {
            "reservation_id": reservation_id,
            "filename": filename,
            "concept_family": concept_family,
            "normalized_family": normalized_key(concept_family),
            "id_range": id_range,
        }
        for label, value in unique_values.items():
            if value in seen[label]:
                raise ContractError(f"{location}: duplicate {label}: {value!r}")
            seen[label].add(value)
        reservations.append(
            Reservation(
                reservation_id=reservation_id,
                stage=stage,
                area_number=area_number,
                slot=slot,
                slug=slug,
                split=split,
                version=version,
                filename=filename,
                id_range=id_range,
                id_prefix=id_prefix,
                id_first=id_first,
                id_last=id_last,
                record_count=record_count,
                concept_family=concept_family,
                domain=domain,
                semantic_axis=semantic_axis,
                status=status,
                raw=row,
            )
        )

    groups: dict[tuple[int, int, str], list[Reservation]] = {}
    for row in reservations:
        groups.setdefault((row.stage, row.area_number, row.split), []).append(row)
    for key, rows in groups.items():
        rows.sort(key=lambda item: item.version_number)
        actual = [item.version_number for item in rows]
        expected = list(range(1, len(rows) + 1))
        if actual != expected:
            raise ContractError(f"{path}: non-contiguous versions for {key}: {actual[:10]}...")
        area_raw = areas[(key[0], key[1])].raw
        declared_name = "train_files" if key[2] == "train" else "val_files"
        if declared_name in area_raw and int(area_raw[declared_name]) != len(rows):
            raise ContractError(
                f"{path}: {key} has {len(rows)} rows but area declares {area_raw[declared_name]}"
            )

    ordered = tuple(
        sorted(
            reservations,
            key=lambda item: (
                0 if item.split == "train" else 1,
                item.stage,
                item.area_number,
                item.version_number,
            ),
        )
    )
    by_id = {item.reservation_id: item for item in ordered}
    return Ledger(path, sha256_bytes(raw_bytes), data, areas, ordered, by_id)


def source_path(workspace: Path, reservation: Reservation) -> Path:
    return (
        workspace
        / f"stage{reservation.stage}_highdensity_dataset"
        / "sources"
        / reservation.split
        / f"{Path(reservation.filename).stem}.source.jsonl"
    )


def legacy_psv_path(workspace: Path, reservation: Reservation) -> Path:
    return source_path(workspace, reservation).with_suffix(".psv")


def corpus_path(workspace: Path, reservation: Reservation) -> Path:
    return (
        workspace
        / f"stage{reservation.stage}_highdensity_dataset"
        / reservation.split
        / reservation.filename
    )


def existing_source_path(workspace: Path, reservation: Reservation) -> Path | None:
    canonical = source_path(workspace, reservation)
    legacy = legacy_psv_path(workspace, reservation)
    paths = [path for path in (canonical, legacy) if path.exists()]
    if len(paths) > 1:
        raise ContractError(f"{reservation.reservation_id}: both JSONL and legacy PSV source exist")
    return paths[0] if paths else None


def _validate_authoring(authoring: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(authoring, dict):
        raise ContractError(f"{location}: authoring must be an object")
    required = {"domain_slice", "semantic_move", "discourse_form"}
    if not required <= set(authoring):
        raise ContractError(f"{location}: authoring missing {sorted(required - set(authoring))}")
    for key in required:
        _require_text(authoring[key], f"{location}.{key}")
    return authoring


def validate_source_object(
    obj: Any,
    *,
    split: str,
    location: str,
    line_number: int,
    require_generator_provenance: bool = False,
) -> SourceRow:
    if not isinstance(obj, dict):
        raise ContractError(f"{location}: source row must be an object")
    allowed = {
        "primary", "concept", "concepts", "text", "relations", "other_type",
        "unseen_relation", "provenance", "authoring",
    }
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ContractError(f"{location}: unknown source keys {unknown}")
    if ("primary" in obj) == ("concept" in obj):
        raise ContractError(f"{location}: use exactly one of primary or legacy concept")
    primary = _require_text(obj.get("primary", obj.get("concept")), f"{location}.primary")
    text = _require_text(obj.get("text"), f"{location}.text")
    if CONTROL_RE.search(text):
        raise ContractError(f"{location}: text contains a control character")
    concepts_raw = obj.get("concepts", [primary])
    if not isinstance(concepts_raw, list) or not concepts_raw:
        raise ContractError(f"{location}: concepts must be a non-empty array")
    concepts = tuple(_require_text(value, f"{location}.concepts") for value in concepts_raw)
    if concepts[0] != primary:
        raise ContractError(f"{location}: concepts[0] must equal primary")
    if len(concepts) != len(set(concepts)):
        raise ContractError(f"{location}: concepts contain duplicates")
    missing_literals = [concept for concept in concepts if concept not in text]
    if missing_literals:
        raise ContractError(f"{location}: concepts missing literally from text: {missing_literals}")

    relations_raw = obj.get("relations")
    if not isinstance(relations_raw, list):
        raise ContractError(f"{location}: relations must be an array")
    relations = tuple(_require_text(value, f"{location}.relations") for value in relations_raw)
    if not 2 <= len(relations) <= 5:
        raise ContractError(f"{location}: relations length must be 2 through 5")
    if len(relations) != len(set(relations)):
        raise ContractError(f"{location}: relations contain duplicates")
    uncontrolled = sorted(set(relations) - CONTROLLED_SET)
    if uncontrolled:
        raise ContractError(f"{location}: uncontrolled relations {uncontrolled}")
    other_type_raw = obj.get("other_type")
    other_type = None if other_type_raw is None else _require_text(other_type_raw, f"{location}.other_type")
    if ("other" in relations) != (other_type is not None):
        raise ContractError(f"{location}: other_type must be present iff relations contains other")

    if split == "val":
        unseen = obj.get("unseen_relation")
        if type(unseen) is not bool:
            raise ContractError(f"{location}: unseen_relation must be boolean")
    else:
        if "unseen_relation" in obj:
            raise ContractError(f"{location}: train source must not contain unseen_relation")
        unseen = None

    provenance = obj.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        raise ContractError(f"{location}: provenance must be an object")
    if require_generator_provenance:
        if not provenance or provenance.get("method") != GENERATOR_KIND:
            raise ContractError(f"{location}: missing {GENERATOR_KIND} provenance")
        if provenance.get("manual_semantic_review") is not False:
            raise ContractError(f"{location}: generated rows must begin with manual_semantic_review=false")
        evidence = provenance.get("relation_evidence")
        if not isinstance(evidence, dict) or set(evidence) != set(relations):
            raise ContractError(f"{location}: relation_evidence keys must exactly match relations")
        for relation, item in evidence.items():
            if not isinstance(item, dict):
                raise ContractError(f"{location}: relation_evidence[{relation}] must be an object")
            span = item.get("span")
            bank_key = item.get("bank_key")
            if (
                not isinstance(span, list)
                or len(span) != 2
                or any(type(value) is not int for value in span)
                or not 0 <= span[0] < span[1] <= len(text)
            ):
                raise ContractError(f"{location}: invalid relation evidence span for {relation}")
            _require_text(bank_key, f"{location}.relation_evidence[{relation}].bank_key")
            if f"/{relation}/" not in bank_key:
                raise ContractError(f"{location}: bank key does not identify relation {relation}")
    authoring_raw = obj.get("authoring")
    authoring = _validate_authoring(authoring_raw, f"{location}.authoring") if authoring_raw is not None else None
    return SourceRow(primary, concepts, text, relations, other_type, unseen, provenance, authoring, line_number)


def read_jsonl_source(
    path: Path,
    *,
    split: str,
    require_generator_provenance: bool = False,
) -> list[SourceRow]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ContractError(f"{path}: UTF-8 BOM is not canonical")
    if UNICODE_ESCAPE_RE.search(raw):
        raise ContractError(f"{path}: contains a JSON Unicode escape; write literal UTF-8")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{path}: invalid UTF-8: {exc}") from exc
    rows: list[SourceRow] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise ContractError(f"{path}:{line_number}: blank lines are not canonical JSONL")
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        rows.append(
            validate_source_object(
                obj,
                split=split,
                location=f"{path}:{line_number}",
                line_number=line_number,
                require_generator_provenance=require_generator_provenance,
            )
        )
    _validate_source_file(rows, path=path, split=split)
    return rows


def read_psv_source(path: Path, *, split: str) -> list[SourceRow]:
    lines = path.read_text(encoding="utf-8").splitlines()
    expected = (
        "concept|relations|other_type|unseen_relation|text"
        if split == "val"
        else "concept|relations|other_type|text"
    )
    if not lines or lines[0] != expected:
        raise ContractError(f"{path}: legacy PSV header mismatch")
    width = 5 if split == "val" else 4
    rows: list[SourceRow] = []
    for line_number, line in enumerate(lines[1:], 2):
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) != width:
            raise ContractError(f"{path}:{line_number}: expected {width} PSV columns")
        concept, relation_text, other_text = cells[:3]
        obj: dict[str, Any] = {
            "concept": concept,
            "text": cells[-1],
            "relations": [value.strip() for value in relation_text.split(",") if value.strip()],
            "other_type": other_text or None,
        }
        if split == "val":
            if cells[3] not in {"true", "false"}:
                raise ContractError(f"{path}:{line_number}: invalid PSV unseen_relation")
            obj["unseen_relation"] = cells[3] == "true"
        rows.append(
            validate_source_object(
                obj,
                split=split,
                location=f"{path}:{line_number}",
                line_number=line_number,
            )
        )
    _validate_source_file(rows, path=path, split=split)
    return rows


def read_source(
    path: Path,
    *,
    split: str,
    require_generator_provenance: bool = False,
) -> list[SourceRow]:
    if path.name.endswith(".source.jsonl"):
        return read_jsonl_source(
            path,
            split=split,
            require_generator_provenance=require_generator_provenance,
        )
    if path.name.endswith(".source.psv"):
        if require_generator_provenance:
            raise ContractError(f"{path}: legacy PSV cannot carry generator provenance")
        return read_psv_source(path, split=split)
    raise ContractError(f"{path}: unsupported source extension")


def _validate_source_file(rows: Sequence[SourceRow], *, path: Path, split: str) -> None:
    if len(rows) != RECORDS_PER_FILE:
        raise ContractError(f"{path}: expected {RECORDS_PER_FILE} rows, got {len(rows)}")
    for label, values in (
        ("primary concept", [row.primary for row in rows]),
        ("text", [row.text for row in rows]),
    ):
        if len(values) != len(set(values)):
            raise ContractError(f"{path}: duplicate {label} within source file")
    if split == "val":
        true_count = sum(row.unseen_relation is True for row in rows)
        if true_count != VAL_TRUE_PER_FILE:
            raise ContractError(f"{path}: expected {VAL_TRUE_PER_FILE} unseen true rows, got {true_count}")


def source_row_to_object(row: SourceRow) -> dict[str, Any]:
    obj: dict[str, Any] = {
        "primary": row.primary,
        "text": row.text,
        "relations": list(row.relations),
        "other_type": row.other_type,
    }
    if len(row.concepts) > 1:
        obj["concepts"] = list(row.concepts)
    if row.unseen_relation is not None:
        obj["unseen_relation"] = row.unseen_relation
    if row.authoring is not None:
        obj["authoring"] = row.authoring
    if row.provenance is not None:
        obj["provenance"] = row.provenance
    return obj


def source_jsonl_bytes(rows: Sequence[SourceRow]) -> bytes:
    parts = [canonical_json_bytes(source_row_to_object(row), indent=None) for row in rows]
    return b"".join(parts)


def build_corpus_payload(
    reservation: Reservation,
    area: AreaContract,
    rows: Sequence[SourceRow],
) -> dict[str, Any]:
    if len(rows) != RECORDS_PER_FILE:
        raise ContractError(f"{reservation.reservation_id}: source row count mismatch")
    records: list[dict[str, Any]] = []
    for offset, row in enumerate(rows):
        record: dict[str, Any] = {
            "id": f"{reservation.id_prefix}-{reservation.id_first + offset:05d}",
            "type": area.packet_type,
            "split": reservation.split,
            "text": row.text,
            "concepts": list(row.concepts),
            "relations": list(row.relations),
        }
        if reservation.split == "val":
            record["unseen_relation"] = row.unseen_relation
        records.append(record)
    has_generated_provenance = any(
        row.provenance and row.provenance.get("method") == GENERATOR_KIND
        for row in rows
    )
    design_note = (
        f"{reservation.domain} 영역의 {reservation.semantic_axis} 의미축을 다룬다. "
        "semantic composition 산출물은 record별 수동 의미 검토 전까지 직접 작성으로 간주하지 않는다."
        if has_generated_provenance
        else (
            f"{reservation.domain} 영역의 {reservation.semantic_axis} 의미축을 다룬다. "
            "primary concept·text·relations를 record별로 직접 작성한 canonical source를 포장했다."
        )
    )
    payload: dict[str, Any] = {
        "dataset_name": (
            f"Korean AI Curriculum — Stage {reservation.stage} {area.name} "
            f"High-Density {'Validation' if reservation.split == 'val' else 'Train'} "
            f"150 {reservation.version}"
        ),
        "version": str(reservation.version_number),
        "purpose": area.learning_goal,
        "split": reservation.split,
        "record_count": RECORDS_PER_FILE,
        "range": reservation.id_range,
        "concept_family": reservation.concept_family,
        "design_note": design_note,
    }
    if reservation.split == "val":
        payload["generalization_slice"] = {
            "basis": "해당 Stage train에서 개별 label은 관측됐지만 정렬 relation-set은 미관측인 조합",
            "unseen_records": VAL_TRUE_PER_FILE,
            "total_records": RECORDS_PER_FILE,
            "ratio": VAL_TRUE_PER_FILE / RECORDS_PER_FILE,
        }
    payload["records"] = records
    return payload


def atomic_create(path: Path, data: bytes) -> str:
    """Create ``path`` without replacing an existing file.

    Existing identical bytes are an idempotent resume success.  Existing
    different bytes are a hard error, which protects pilots and user edits.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing != data:
            raise ContractError(f"refusing to overwrite non-identical existing file: {path}")
        return "existing-identical"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise ContractError(f"concurrent non-identical file appeared: {path}")
            return "existing-identical"
        return "created"
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_replace_generated(path: Path, data: bytes) -> None:
    """Atomically replace a generated checkpoint/report, never corpus/source."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def select_reservations(
    ledger: Ledger,
    *,
    stages: set[int] | None = None,
    areas: set[int] | None = None,
    split: str | None = None,
    reservation_ids: set[str] | None = None,
    limit: int | None = None,
) -> list[Reservation]:
    if reservation_ids:
        unknown = sorted(reservation_ids - set(ledger.by_id))
        if unknown:
            raise ContractError(f"unknown reservation IDs: {unknown}")
    rows = [
        row
        for row in ledger.reservations
        if (not stages or row.stage in stages)
        and (not areas or row.area_number in areas)
        and (split is None or row.split == split)
        and (not reservation_ids or row.reservation_id in reservation_ids)
    ]
    if limit is not None:
        rows = rows[:limit]
    return rows


def sorted_relation_set(relations: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(relations))


def validate_validation_relations(
    *,
    rows: Sequence[SourceRow],
    train_labels: set[str],
    train_sets: set[tuple[str, ...]],
    location: str,
) -> None:
    true_count = 0
    for index, row in enumerate(rows, 1):
        missing_labels = sorted(set(row.relations) - train_labels)
        if missing_labels:
            raise ContractError(f"{location}:{index}: val labels absent from Stage train: {missing_labels}")
        relation_set = row.relation_set
        if row.unseen_relation:
            true_count += 1
            if relation_set in train_sets:
                raise ContractError(f"{location}:{index}: unseen true relation-set was observed in train")
        elif relation_set not in train_sets:
            raise ContractError(f"{location}:{index}: unseen false relation-set was not observed in train")
    if true_count != VAL_TRUE_PER_FILE:
        raise ContractError(f"{location}: expected {VAL_TRUE_PER_FILE} unseen true rows, got {true_count}")


def word_tokens(text: str) -> tuple[str, ...]:
    return tuple(TOKEN_RE.findall(unicodedata.normalize("NFKC", text).casefold()))


def ngrams(tokens: Sequence[str], size: int) -> Iterator[tuple[str, ...]]:
    for index in range(len(tokens) - size + 1):
        yield tuple(tokens[index:index + size])


def normalized_text(text: str) -> str:
    return " ".join(word_tokens(text))


def template_fingerprint(primary: str, text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold().replace(primary.casefold(), "<primary>")
    normalized = re.sub(r"\d+(?:[.,]\d+)*", "<num>", normalized)
    normalized = re.sub(r"[0-9a-z가-힣]+", "<lex>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _has_final_consonant(value: str) -> bool | None:
    for ch in reversed(value.strip()):
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            return (code - 0xAC00) % 28 != 0
        if ch.isalnum():
            return None
    return None


def particle_for(value: str, pair: str) -> str:
    if pair == "로/으로":
        last = value[-1] if value else ""
        if "가" <= last <= "힣":
            jong = (ord(last) - 0xAC00) % 28
            return "로" if jong in (0, 8) else "으로"
        return "로"
    options = {
        "은/는": ("은", "는"),
        "이/가": ("이", "가"),
        "을/를": ("을", "를"),
        "과/와": ("과", "와"),
    }
    if pair not in options:
        raise ValueError(pair)
    final = _has_final_consonant(value)
    return options[pair][0] if final is not False else options[pair][1]


def attach_particle(value: str, pair: str) -> str:
    return value + particle_for(value, pair)


COPULAR_I_PREFIXES = (
    "이다",
    "이며",
    "이고",
    "이지만",
    "이므로",
    "이어서",
    "이라",
    "이라고",
    "이라는",
    "이란",
    "이라도",
    "이든",
    "이든지",
    "이었다",
    "이었으며",
    "이었고",
    "이자",
    "이니",
    "이니까",
)


def _is_copular_i(text: str, noun_end: int) -> bool:
    """Return true when noun-final ``이`` begins a copular ending, not 이/가."""
    return any(text.startswith(prefix, noun_end) for prefix in COPULAR_I_PREFIXES)


def dynamic_particle_mismatches(text: str, values: Iterable[str]) -> list[str]:
    """Find a wrong Korean particle attached to a known generated noun slot."""
    findings: list[str] = []
    for value in sorted({item for item in values if item}, key=len, reverse=True):
        for pair in ("은/는", "이/가", "을/를", "과/와", "로/으로"):
            expected = particle_for(value, pair)
            for candidate in pair.split("/"):
                if candidate == expected:
                    continue
                needle = f"{value}{candidate}"
                offset = 0
                while True:
                    index = text.find(needle, offset)
                    if index < 0:
                        break
                    if pair == "이/가" and candidate == "이" and _is_copular_i(text, index + len(value)):
                        offset = index + len(needle)
                        continue
                    following = text[index + len(needle): index + len(needle) + 1]
                    # ``noun + 이다`` is a copula, not a mismatched 이/가
                    # attachment (for example ``결과 상태이다``).
                    if not (pair == "이/가" and candidate == "이" and following == "다"):
                        findings.append(f"{value!r}+{candidate!r}; expected {expected!r}")
                    offset = index + len(needle)
    return findings


def known_grammar_findings(text: str) -> list[str]:
    return [name for name, pattern in KNOWN_GRAMMAR_PATTERNS.items() if pattern.search(text)]


def primary_particle_mismatches(primary: str, text: str) -> list[str]:
    findings: list[str] = []
    offset = 0
    while True:
        index = text.find(primary, offset)
        if index < 0:
            break
        following = text[index + len(primary): index + len(primary) + 1]
        for pair in ("은/는", "이/가", "을/를", "과/와"):
            if following in pair.split("/"):
                if pair == "이/가" and following == "이" and _is_copular_i(text, index + len(primary)):
                    continue
                expected = particle_for(primary, pair)
                if following != expected:
                    findings.append(f"{primary!r} followed by {following!r}; expected {expected!r}")
        offset = index + len(primary)
    for bad in ("은는", "는은", "이가", "가이", "을를", "를을", "과와", "와과", "그 그"):
        if bad in text:
            findings.append(f"suspicious sequence {bad!r}")
    return findings


def _bytes_to_unicode() -> dict[int, str]:
    byte_values = list(range(ord("!"), ord("~") + 1))
    byte_values += list(range(ord("¡"), ord("¬") + 1))
    byte_values += list(range(ord("®"), ord("ÿ") + 1))
    unicode_values = byte_values[:]
    extra = 0
    for byte in range(256):
        if byte not in byte_values:
            byte_values.append(byte)
            unicode_values.append(256 + extra)
            extra += 1
    return dict(zip(byte_values, map(chr, unicode_values)))


class ByteLevelBPECounter:
    """Exact counter for the repository's GPT-2-style ByteLevel BPE JSON."""

    def __init__(self, tokenizer_path: Path) -> None:
        if _regex is None:
            raise ContractError("the Python 'regex' package is required for exact tokenizer gating")
        payload = json.loads(tokenizer_path.read_text(encoding="utf-8"))
        pre = payload.get("pre_tokenizer", {})
        model = payload.get("model", {})
        if model.get("type") != "BPE" or pre.get("type") != "ByteLevel":
            raise ContractError(f"unsupported tokenizer structure: {tokenizer_path}")
        if pre.get("add_prefix_space") or not pre.get("use_regex"):
            raise ContractError(f"unsupported ByteLevel options: {tokenizer_path}")
        self.path = tokenizer_path
        self.encoder = _bytes_to_unicode()
        self.ranks = {tuple(pair): rank for rank, pair in enumerate(model["merges"])}
        self.pattern = _regex.compile(BPE_PATTERN_TEXT)

    @functools.lru_cache(maxsize=300_000)
    def bpe(self, token: str) -> tuple[str, ...]:
        word = tuple(token)
        if len(word) <= 1:
            return word
        while True:
            pairs = {(word[index], word[index + 1]) for index in range(len(word) - 1)}
            pair = min(pairs, key=lambda value: self.ranks.get(value, 10**12))
            if pair not in self.ranks:
                break
            first, second = pair
            merged: list[str] = []
            index = 0
            while index < len(word):
                try:
                    found = word.index(first, index)
                except ValueError:
                    merged.extend(word[index:])
                    break
                merged.extend(word[index:found])
                index = found
                if index < len(word) - 1 and word[index] == first and word[index + 1] == second:
                    merged.append(first + second)
                    index += 2
                else:
                    merged.append(word[index])
                    index += 1
            word = tuple(merged)
            if len(word) == 1:
                break
        return word

    def count(self, text: str) -> int:
        total = 0
        for piece in self.pattern.findall(text):
            encoded = "".join(self.encoder[value] for value in piece.encode("utf-8"))
            total += len(self.bpe(encoded))
        return total
