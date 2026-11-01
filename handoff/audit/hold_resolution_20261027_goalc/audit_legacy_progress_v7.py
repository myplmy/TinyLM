"""Snapshot text-review ledgers and mechanically render pinned literal edits.

This is not root semantic approval or cache admission. Historical proposals,
in-flight rows, incomplete reads and exact mechanical failures remain visible.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_text_edits_v2 as edits
from scripts import p106b_hold_resolution_policy_v5 as policy

BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
AUDIT = Path(__file__).resolve().parent
manifest_path = BASE / "legacy_span_review_v2/manifest.json"
document = json.loads(manifest_path.read_bytes().decode("utf-8"))
sources = {row["id"]: row for row in document["rows"]}
ROLES = list(document["assignments"])
ACCEPTED = {"KEEP_SOURCE", "ADOPT_CANDIDATE", "EDIT_TEXT", "EDIT_RECIPE", "EXCLUDE", "NEEDS_ROOT"}
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + str(time.time_ns() % 1_000_000_000)
output = AUDIT / "legacy_progress_v7" / (stamp + ".json")
rendered = BASE / "legacy_rendered_v3"
output.parent.mkdir(exist_ok=True)
records = []
errors = []
review_pins = []
counts = {}


def sha_bytes(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def read_stable(path):
    payload = path.read_bytes()
    if payload != path.read_bytes():
        raise ValueError("IN_FLIGHT_FILE_CHANGED_DURING_SNAPSHOT")
    return payload


def review_order(path):
    match = re.fullmatch(r"review_([0-9]+)(?:_v([0-9]+))?[.]md", path.name)
    return (int(match[1]), int(match[2] or 1)) if match else (0, 0)


def canonical_id(cell, expected):
    explicit = re.search(r"(?:expanded_train|historical_train|validation):[0-9]+", cell)
    if explicit:
        return explicit[0]
    stripped = cell.strip(" `*")
    numeric=re.fullmatch(r"([0-9]+)(?:\s*\(정정\))?", stripped)
    if numeric:
        possible = [ident for ident in expected if ident.rsplit(":", 1)[1] == numeric[1]]
        return possible[0] if len(possible) == 1 else None
    return None


def materialized_text(role_directory, row, status, outputs):
    ident = row["id"]
    original_path = ROOT / row["paths"]["original"]["path"]
    raw = original_path.read_bytes().decode("utf-8")
    if sha_bytes(original_path.read_bytes()) != row["original_text_sha256"]:
        raise ValueError("SOURCE_PACKET_HASH_CHANGED")
    if status in {"KEEP_SOURCE", "ADOPT_CANDIDATE"}:
        label = "original" if status == "KEEP_SOURCE" else "candidate"
        info = row["paths"][label]
        path = ROOT / info["path"]
        data = path.read_bytes()
        if sha_bytes(data) != info["sha256"]:
            raise ValueError("PINNED_REVIEW_BASE_CHANGED")
        return data.decode("utf-8"), dict(kind="PINNED_TEXT_REFERENCE", path=info["path"], sha256=info["sha256"]), raw
    pattern = r"[A-Za-z0-9_]+(?:[.]edits)?[.]md" if status == "EDIT_RECIPE" else r"[A-Za-z0-9_]+[.]txt"
    prefix = ident.replace(":", "_")
    candidates = [name for name in re.findall(pattern, outputs) if re.fullmatch(
        re.escape(prefix) + (r"(?:_v[0-9]+)?[.]edits[.]md" if status == "EDIT_RECIPE" else r"(?:_v[0-9]+)?[.]txt"),name)]
    if not candidates:
        candidates = [ident.replace(":", "_") + (".edits.md" if status == "EDIT_RECIPE" else ".txt")]
    if len(set(candidates)) != 1:
        raise ValueError("AMBIGUOUS_SAVED_OUTPUT_REFERENCE")
    path = role_directory / candidates[0]
    if not path.resolve().is_relative_to(role_directory.resolve()):
        raise ValueError("SAVED_OUTPUT_ESCAPES_AUTHOR_DIRECTORY")
    payload = read_stable(path)
    if status == "EDIT_TEXT":
        return payload.decode("utf-8"), dict(kind="AUTHOR_TEXT", path=str(path.relative_to(ROOT)), sha256=sha_bytes(payload)), raw
    recipe = payload.decode("utf-8")
    base_match = re.search(r"(?m)^base:\s*(original|candidate)\s*$", recipe)
    if not base_match:
        raise ValueError("RECIPE_BASE_HEADER_MISSING")
    label = base_match[1]
    info = row["paths"][label]
    before = (ROOT / info["path"]).read_bytes()
    if sha_bytes(before) != info["sha256"]:
        raise ValueError("RECIPE_BASE_HASH_CHANGED")
    text, proof = edits.apply_recipe(before.decode("utf-8"), recipe, source_id=ident, base=label)
    return text, dict(kind="MECHANICALLY_APPLIED_LITERAL_EDITS_ONLY", path=str(path.relative_to(ROOT)),
                      sha256=sha_bytes(payload), edit_proof=proof), raw


for role in ROLES:
    directory = BASE / "agents" / role / "legacy_span_review_v2"
    expected = set(document["assignments"][role]["ids"])
    latest = {}
    history = {}
    for review in sorted(directory.glob("review_*.md"), key=review_order):
        if not re.fullmatch(r"review_[0-9]+(?:_v[0-9]+)?[.]md", review.name):
            continue
        try:
            payload = read_stable(review)
        except ValueError as exc:
            errors.append(dict(role=role, review=str(review.relative_to(ROOT)), error=str(exc)))
            continue
        digest = sha_bytes(payload)
        review_pins.append(dict(path=str(review.relative_to(ROOT)), sha256=digest))
        header = None
        for number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
            if not line.startswith("|"):
                continue
            cells = [c.strip().strip("`*") for c in line.split("|")[1:-1]]
            if len(cells) < 2:
                continue
            ident = canonical_id(cells[0], expected)
            if ident is None:
                if "ID" in cells[0].upper() or "원문" in cells[0]:
                    header = cells
                continue
            if ident not in expected:
                errors.append(dict(role=role, id=ident, review=str(review.relative_to(ROOT)), error="ROW_OUTSIDE_ASSIGNED_SOURCES"))
                continue
            status = cells[1]
            aliases = {"EXCLUDE 유지":"EXCLUDE","EXCLUDE 제안":"EXCLUDE","EDIT_RECIPE_V2":"EDIT_RECIPE",
                       "REVISE / EDIT_RECIPE":"EDIT_RECIPE","EDIT / 기존 후보 채택":"ADOPT_CANDIDATE",
                       "HOLD":"NEEDS_ROOT", "KEEP_CANDIDATE":"ADOPT_CANDIDATE",
                       "EDIT_RECIPE 유지":"EDIT_RECIPE", "EDIT_TEXT_METADATA_ONLY":"EDIT_TEXT"}
            status = aliases.get(status,status)
            def column(pattern, fallback):
                indexes=[i for i,label in enumerate(header or []) if re.search(pattern,label)]
                return cells[indexes[0]] if indexes and indexes[0]<len(cells) else fallback
            # Some supplemental rows have four cells after an earlier five-cell
            # header. Output names carry their exact source ID; find them across
            # the actual row, never reinterpret a reason as a file column.
            file_pattern=re.escape(ident.replace(":","_"))+r"(?:_v[0-9]+)?(?:[.]edits)?[.](?:md|txt)"
            output_indexes=[i for i,label in enumerate(header or []) if re.search(r"출력|산출물|파일",label)]
            declared=(cells[output_indexes[0]] if len(cells)==len(header or []) and output_indexes else "")
            outputs=(declared if re.search(file_pattern,declared) else
                     next((cell for cell in cells[2:] if re.search(file_pattern,cell))," | ".join(cells[2:])))
            explicit_status=re.match(r"^(KEEP_SOURCE|ADOPT_CANDIDATE|EDIT_TEXT|EDIT_RECIPE|EXCLUDE|NEEDS_ROOT)(?=$|[ ;])",status)
            if explicit_status:
                status=explicit_status[1]
            elif status in {"EDIT","REVISE"}:
                # This only selects a mechanical text/recipe reader for the
                # author's explicit edit proposal. It never approves its body.
                if re.search(file_pattern,outputs):
                    status="EDIT_RECIPE" if ".edits.md" in outputs else "EDIT_TEXT"
            read_scope=column(r"판독|대조 범위","")
            reason=column(r"근거|사유|설명|경계","")
            output_versions=[int(match) for match in re.findall(r"_v([0-9]+)[.]",outputs)]
            explicit_version=max(output_versions,default=1)
            _,review_version=review_order(review)
            rank=(review_order(review)[0],review_version,number,explicit_version)
            record=dict(id=ident,role=role,status=status,original_status=cells[1],read_scope=read_scope,reason=reason,
                        output_references=outputs,review=str(review.relative_to(ROOT)),review_sha256=digest,line=number,
                        root_approved=False,author_version_precedence=list(rank))
            history.setdefault(ident,[]).append(record)
            # A prose-only correction row is retained in history and flagged;
            # it cannot silently replace an explicit authored decision.
            canonical = status in ACCEPTED
            old_canonical = ident in latest and latest[ident]["status"] in ACCEPTED
            if (ident not in latest or canonical and not old_canonical or
                canonical == old_canonical and rank>=tuple(latest[ident]["author_version_precedence"])):
                latest[ident]=record
    for ident, record in latest.items():
        if record["status"] not in ACCEPTED:
            record["mechanical_status"] = "NONCANONICAL_AUTHOR_STATUS_NEEDS_REVIEW"
        elif record["status"] in {"EXCLUDE", "NEEDS_ROOT"}:
            record["mechanical_status"] = "TEXT_ADJUDICATION_NOT_ADMISSION"
        else:
            try:
                text, proof, original = materialized_text(directory, sources[ident], record["status"], record["output_references"])
                data = text.encode("utf-8")
                if not text.strip() or len(data) >= 20_000_000:
                    raise ValueError("EMPTY_OR_OVERSIZE_AUTHOR_BODY")
                digest = sha_bytes(data)
                path = rendered / digest[:2] / (digest + ".txt")
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    if path.read_bytes() != data:
                        raise ValueError("CONTENT_ADDRESSED_BODY_DIFFERS")
                else:
                    with path.open("xb") as f:
                        f.write(data)
                record.update(mechanical_status="MATERIALIZED_DRAFT_NOT_SEMANTIC_APPROVAL",
                              body=str(path.relative_to(ROOT)), clean_text_sha256=digest, proof=proof,
                              code_guard=policy.code_preserved(original, text),
                              unicode_guard=policy.unicode_examples_preserved(original, text))
            except (ValueError, OSError) as exc:
                record["mechanical_status"] = "MECHANICAL_REJECTION_NOT_APPLIED"
                record["mechanical_error"] = str(exc)
        record["author_decision_history"]=[dict(review=item["review"],line=item["line"],status=item["status"],
                                              output_references=item["output_references"],
                                              author_version_precedence=item["author_version_precedence"])
                                           for item in history[ident]]
        records.append(record)
    counts[role] = dict(assigned=len(expected), review_rows=len(latest), remaining_without_row=len(expected-set(latest)),
                       decisions=dict(Counter(record["status"] for record in latest.values())))
value = dict(schema="P106B_TEXT_REVIEW_PROGRESS_SNAPSHOT_V1", status="IN_PROGRESS_NOT_CACHE_ADMISSION",
             manifest_sha256=sha_bytes(manifest_path.read_bytes()), producer_sha256=sha_bytes(Path(__file__).read_bytes()),
             parser_sha256=sha_bytes(Path(edits.__file__).read_bytes()), root_adopted=0, roles=counts, records=records, review_pins=review_pins, snapshot_errors=errors)
with output.open("x", encoding="utf-8") as f:
    json.dump(value, f, ensure_ascii=False, indent=2)
    f.write(chr(10))
print(str(output.relative_to(ROOT)))
print(json.dumps(dict(roles=counts, records=len(records), mechanical=dict(Counter(r["mechanical_status"] for r in records)),
                      mechanical_errors=[dict(id=r["id"], role=r["role"], error=r["mechanical_error"]) for r in records if r.get("mechanical_error")]), ensure_ascii=False))
