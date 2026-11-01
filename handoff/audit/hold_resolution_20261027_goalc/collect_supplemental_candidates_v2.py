"""Snapshot supplemental full-text reviews without silently picking a cohort.

All explicit author rows and literal recipes remain source/hash-linked. A
different body for the same source is a visible root conflict, never resolved
by filename size, mtime or an automatic highest body-version heuristic.
"""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_text_edits_v2 as edits
from scripts import p106b_hold_resolution_recipe_frame_v1 as frame

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "supplemental_candidates_snapshot_v2.json"
inv.require(not OUT.exists(), "new immutable supplemental snapshot required")
archive_dir = AUDIT / "supplemental_review_archive_v1"
rendered_dir = BASE / "supplemental_rendered_v1"
groups = ["policy_counter_review_v1", "remaining_structure_context_v1",
          "policy_v10_literal_counter_v1", "policy_v11_literal_counter_v1",
          "contextual_residual_v11_v1", "policy_v12_literal_counter_v1", "policy_v13_literal_counter_v1",
          "formal_source_second_review_v1"]
records, errors, review_pins, input_pins = [], [], [], {}


def digest(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def stable(path):
    payload = path.read_bytes()
    inv.require(payload == path.read_bytes(), "author file changed during snapshot")
    return payload


def save_content(directory, payload, suffix):
    key = digest(payload)
    path = directory / key[:2] / (key + suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        inv.require(path.read_bytes() == payload, "content-addressed artifact differs")
    else:
        with path.open("xb") as stream:
            stream.write(payload)
    return str(path.relative_to(ROOT)), key


def review_rank(path):
    match = re.fullmatch(r"review(?:_([0-9]+))?(?:_v([0-9]+))?[.]md", path.name)
    inv.require(match is not None, "unrecognized explicit review filename")
    return int(match[1] or 0), int(match[2] or 1)


def ident(cell):
    cell = cell.strip(" `*")
    matches = re.findall(r"(?:expanded_train|historical_train|validation)[:_][0-9]+", cell)
    if len(matches) == 1:
        return matches[0].replace("_train_", "_train:").replace("validation_", "validation:")
    if re.fullmatch(r"[0-9]+(?:\s+[(（][^()（）]*[)）])?", cell):
        return "expanded_train:" + re.match(r"[0-9]+", cell)[0]
    return None


def decisions(directory, expected):
    found = {}
    for review in sorted(directory.glob("review*.md"), key=review_rank):
        payload = stable(review)
        saved, key = save_content(archive_dir, payload, ".md")
        pin = dict(path=str(review.relative_to(ROOT)), sha256=key, archive=saved)
        review_pins.append(pin)
        header = None
        for number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
            if not line.startswith("|"):
                continue
            cells = [cell.strip().strip("`*") for cell in line.split("|")[1:-1]]
            if len(cells) < 2:
                continue
            key_id = ident(cells[0])
            if key_id is None:
                if "ID" in cells[0].upper():
                    header = cells
                continue
            if key_id not in expected:
                errors.append(dict(id=key_id, review=pin, error="ROW_OUTSIDE_ASSIGNED_COHORT"))
                continue
            status = {"ACCEPT_CANDIDATE": "ADOPT_CANDIDATE", "REVISE_TEXT": "EDIT_TEXT"}.get(cells[1], cells[1])
            columns = {label: cells[index] for index, label in enumerate(header or []) if index < len(cells)}
            scope = next((value for label, value in columns.items() if "판독" in label or "대조 범위" in label), "")
            reason = next((value for label, value in columns.items() if "근거" in label or "사유" in label), "")
            row = dict(id=key_id, decision=status, original_status=cells[1], read_scope=scope, reason=reason,
                       review=pin, line=number, review_text=line,
                       body_references=sorted(set(re.findall(re.escape(key_id.replace(":", "_")) +
                                              r"(?:_v[0-9]+)?(?:[.]edits)?[.](?:txt|md)", line))),
                       author_precedence=[*review_rank(review), number], root_approved=False)
            found[key_id] = row
    return found


def materialize(row, source_row, directory):
    status = row["decision"]
    paths = {label: source_row[label] for label in ["original", "candidate"]}
    for pin in paths.values():
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "pinned source/candidate differs")
    row["original"] = paths["original"]
    if status in {"EXCLUDE", "NEEDS_ROOT"}:
        row["status"] = "TEXT_ADJUDICATION_NOT_ADMISSION"
        return
    if status in {"KEEP_SOURCE", "ADOPT_CANDIDATE"}:
        chosen = paths["original" if status == "KEEP_SOURCE" else "candidate"]
        row.update(status="PINNED_BODY_NOT_ROOT_ADMISSION", body=chosen["path"], clean_text_sha256=chosen["sha256"])
        return
    inv.require(status in {"EDIT_TEXT", "EDIT_RECIPE"}, "unknown authored status")
    references = [name for name in row["body_references"]
                  if name.endswith(".edits.md" if status == "EDIT_RECIPE" else ".txt")]
    inv.require(len(references) == 1, "explicit authored body reference missing or ambiguous")
    path = directory / references[0]
    payload = stable(path)
    if status == "EDIT_RECIPE":
        canonical, compiler_proof = frame.canonicalize(payload.decode("utf-8"), source_id=row["id"], paths=paths, root=ROOT)
        before = ROOT / paths[compiler_proof["base"]]["path"]
        text, proof = edits.apply_recipe(before.read_bytes().decode("utf-8"), canonical,
                                        source_id=row["id"], base=compiler_proof["base"])
        payload = text.encode("utf-8")
        row["literal_edit_proof"] = dict(compiler=compiler_proof, application=proof,
                                         recipe_path=str(path.relative_to(ROOT)), recipe_sha256=inv.file_sha(path))
    inv.require(payload.strip() and len(payload) < 20_000_000, "empty or oversized authored body")
    body, key = save_content(rendered_dir, payload, ".txt")
    row.update(status="MATERIALIZED_BODY_NOT_ROOT_ADMISSION", body=body, clean_text_sha256=key,
               author_output=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)))


for group in groups:
    manifest_path = BASE / group / "manifest.json"
    manifest = inv.cache.read(manifest_path)
    input_pins[str(manifest_path.relative_to(ROOT))] = inv.file_sha(manifest_path)
    sources = {row["id"]: dict(row, **row.get("paths", {})) for row in manifest["rows"]}
    for role, assigned in manifest["assignments"].items():
        assigned = assigned["ids"] if isinstance(assigned, dict) else assigned
        directory = BASE / "agents" / role / group
        choices = decisions(directory, set(assigned))
        for key_id in assigned:
            if key_id not in choices:
                errors.append(dict(id=key_id, group=group, role=role, error="NO_SAVED_REVIEW_ROW"))
                continue
            row = dict(choices[key_id], cohort=group, role=role, manifest=str(manifest_path.relative_to(ROOT)))
            try:
                materialize(row, sources[key_id], directory)
            except (ValueError, OSError) as exc:
                row.update(status="MECHANICAL_REJECTION_NOT_APPLIED", error=str(exc))
                errors.append(dict(id=key_id, group=group, role=role, error=str(exc)))
            records.append(row)

# The clinical reviewer was explicitly limited to this view. The full original
# linkage is retained, while excluded technical lines are not reopened here.
clinical_manifest = BASE / "clinical_source_view_v1/manifest.json"
clinical = inv.cache.read(clinical_manifest)
input_pins[str(clinical_manifest.relative_to(ROOT))] = inv.file_sha(clinical_manifest)
directory = BASE / "agents/context_latin/clinical_source_review_v1"
clinical_choice = decisions(directory, {clinical["id"]})[clinical["id"]]
row = dict(clinical_choice, cohort="clinical_source_review_v1", role="context_latin",
           original=clinical["original"], compare_source=clinical["view"],
           restricted_original_lines_separately_unadmitted=clinical["separately_unadmitted_original_line_range"])
materialize(row, dict(original=clinical["view"], candidate=clinical["view"]), directory)
row["original"] = clinical["original"]
records.append(row)

by_source = defaultdict(list)
for row in records:
    by_source[row["id"]].append(row)
conflicts = []
for key_id, values in by_source.items():
    bodies = {row["clean_text_sha256"] for row in values if row.get("body")}
    if len(bodies) > 1 or any(row["decision"] == "NEEDS_ROOT" for row in values):
        conflicts.append(dict(id=key_id, proposals=[dict(cohort=row["cohort"], decision=row["decision"],
                             body=row.get("body"), clean_text_sha256=row.get("clean_text_sha256"), review=row["review"])
                             for row in values]))
result = dict(status="SUPPLEMENTAL_AUTHORED_PROVENANCE_NOT_ADMISSION", records=records,
              counts=dict(Counter(row["status"] for row in records)), errors=errors, conflicts=conflicts,
              unique_ids=len(by_source), proposal_records=len(records), review_pins=review_pins,
              input_pins=input_pins, producer_sha256=inv.file_sha(Path(__file__)), root_adopted=0,
              goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "snapshot needs sharding")
inv.write_json(OUT, result)
print(json.dumps(dict(records=len(records), unique_ids=len(by_source), counts=result["counts"], errors=errors,
                      conflicts=[row["id"] for row in conflicts]), ensure_ascii=False))

