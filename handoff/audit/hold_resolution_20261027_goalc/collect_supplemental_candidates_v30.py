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
from scripts import p106b_hold_resolution_recipe_frame_v3 as frame
from scripts import p106b_hold_resolution_review_safeguards_v2 as safeguards

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "supplemental_candidates_snapshot_v30.json"
inv.require(not OUT.exists(), "new immutable supplemental snapshot required")
archive_dir = AUDIT / "supplemental_review_archive_v1"
rendered_dir = BASE / "supplemental_rendered_v1"
groups = ["policy_counter_review_v1", "remaining_structure_context_v1",
          "policy_v10_literal_counter_v1", "policy_v11_literal_counter_v1",
          "contextual_residual_v11_v1", "policy_v12_literal_counter_v1", "policy_v13_literal_counter_v1",
          "formal_source_second_review_v1", "style_value_counter_v1", "materialized_text_repairs_v2",
          "policy_v14_literal_counter_v1", "authored_postsignal_review_v1", "exclusion_second_review_v1",
          "policy_v15_literal_counter_v1", "secondary_body_counter_v1", "remaining_context_v14_v1", "policy_v16_literal_counter_v1", "policy_v16_literal_counter_v2", "automatic_partial_counter_v1", "limited_biology_views_v2", "authored_literal_counter_v3",
          "remaining_candidate_context_v16_v1", "policy_v17_literal_counter_v1", "policy_v17_literal_counter_v2", "policy_v17_literal_counter_v4", "root_mediation_context_v1",
          "root_selected_signal_counter_v1", "retracted_review_counter_v1", "remaining_candidate_context_v17_v1", "policy_v18_literal_counter_v1", "repeat_context_counter_v1", "remaining_candidate_context_v19_v1", "legacy_incident_counter_v1", "policy_v20_literal_counter_v1", "root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1"]
records, errors, review_pins, input_pins = [], [], [], {}
retracted_history = []
coverage = {}
reassignment_path = AUDIT / "AUTHOR_REASSIGNMENTS_V1.json"
reassignment_rows = inv.cache.read(reassignment_path)["rows"]
reassignments, reassigned_history = {}, []
for row in reassignment_rows:
    inv.require(row.get("root_approved") is True and row.get("old_derivatives_unadmitted") is True,
                "unapproved author reassignment")
    key = row["from_cohort"], row["from_role"], row["id"]
    inv.require(key not in reassignments, "repeated author reassignment")
    replacement_path = ROOT / row["replacement_manifest"]
    inv.require(inv.file_sha(replacement_path) == row["replacement_manifest_sha256"],
                "replacement assignment changed")
    replacement = inv.cache.read(replacement_path)
    pair = [item for item in replacement["rows"] if item["id"] == row["id"]]
    inv.require(len(pair) == 1 and pair[0]["original"]["sha256"] == row["original_text_sha256"]
                and row["id"] in replacement["assignments"][row["to_role"]],
                "replacement assignment has another source or owner")
    reassignments[key] = row
input_pins[str(reassignment_path.relative_to(ROOT))] = inv.file_sha(reassignment_path)
binding_path = AUDIT / "AUTHOR_REVIEW_EXPLICIT_BINDINGS_V1.json"
bindings = inv.cache.read(binding_path)["rows"]
input_pins[str(binding_path.relative_to(ROOT))] = inv.file_sha(binding_path)
retractions_path = AUDIT / "AUTHOR_REVIEW_RETRACTIONS_V1.json"
retractions = inv.cache.read(retractions_path)["rows"]
input_pins[str(retractions_path.relative_to(ROOT))] = inv.file_sha(retractions_path)
for withdrawal in retractions:
    inv.require(inv.file_sha(ROOT / withdrawal["review"]) == withdrawal["review_sha256"],
                "withdrawn original review changed; preserve its recorded history")


views_path = BASE / "root_selected_signal_counter_v2/reading_views_manifest_v1.json"
views_manifest = inv.cache.read(views_path)
inv.require(inv.file_sha(ROOT / views_manifest["source_manifest"]["path"]) == views_manifest["source_manifest"]["sha256"],
            "reading views refer to another assignment")
input_pins[str(views_path.relative_to(ROOT))] = inv.file_sha(views_path)
input_pins["scripts/p106b_hold_resolution_review_safeguards_v1.py"] = inv.file_sha(ROOT / "scripts/p106b_hold_resolution_review_safeguards_v1.py")
extra_views_path = BASE / "remaining_unreviewed_context_v20_v1/reading_views_manifest_v1.json"
extra_views = inv.cache.read(extra_views_path)
inv.require(inv.file_sha(ROOT / extra_views["source_manifest"]["path"]) == extra_views["source_manifest"]["sha256"],
            "new reading views refer to another assignment")
input_pins[str(extra_views_path.relative_to(ROOT))] = inv.file_sha(extra_views_path)
input_pins["scripts/p106b_hold_resolution_review_safeguards_v2.py"] = inv.file_sha(ROOT / "scripts/p106b_hold_resolution_review_safeguards_v2.py")
views_manifest = dict(rows=views_manifest["rows"] + extra_views["rows"])
unparsed_review_history, invalid_task_rows = [], []
strict_task_cohorts = {"root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1"}


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
    match = re.fullmatch(r"review(?:_([0-9]+))?(?:_v([0-9]+)|_root_addendum_v([0-9]+))?[.]md", path.name)
    inv.require(match is not None, "unrecognized explicit review filename")
    # A named root addendum explicitly supersedes its own source row only.
    # Other cohorts are still unresolved conflicts, never ranked by this key.
    return int(match[1] or 0), bool(match[3]), int(match[3] or match[2] or 1)


def ident(cell):
    cell = cell.strip(" `*")
    matches = re.findall(r"(?:expanded_train|historical_train|validation)[:_][0-9]+", cell)
    if len(matches) == 1:
        return matches[0].replace("_train_", "_train:").replace("validation_", "validation:")
    if re.fullmatch(r"[0-9]+(?:\s+[(（][^()（）]*[)）])?", cell):
        return "expanded_train:" + re.match(r"[0-9]+", cell)[0]
    return None


def review_entries(payload, allow_sections=False):
    """Read explicit table rows and saved labelled per-ID Markdown sections.

    Section recovery retains its actual source line span and raw Markdown.
    It never turns narrative prose mentioning an ID into a decision.
    """
    lines = payload.decode("utf-8").splitlines()
    entries = []
    header = None
    for number, line in enumerate(lines, 1):
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
        entries.append(dict(number=number, end=number, cells=cells, header=header,
                            raw=line, format="EXPLICIT_MARKDOWN_TABLE"))
    if not allow_sections:
        return entries
    section = None

    def finish(end):
        if section is None:
            return
        fields = section["fields"]
        if "판정" not in fields:
            return
        status = fields["판정"].strip(" `*.")
        inv.require(status in {"ACCEPT_CANDIDATE", "ADOPT_CANDIDATE", "REVISE_TEXT", "EDIT_TEXT",
                    "EDIT_RECIPE", "KEEP_SOURCE", "EXCLUDE", "NEEDS_ROOT", "HOLD"},
                    "unrecognized explicit prose review status")
        scope = next((value for label, value in fields.items()
                      if "범위" in label and label != "정확 출력"), "")
        output = fields.get("정확 출력", fields.get("출력", fields.get("산출물", "")))
        reason = next((value for label, value in fields.items() if "근거" in label or "사유" in label), "")
        inv.require(scope and output and reason, "explicit prose review lacks required fields")
        entries.append(dict(number=section["start"], end=end,
            cells=[section["id"], status, scope, output, reason],
            header=["ID", "판정", "실제 판독 범위", "출력", "근거"],
            raw=chr(10).join(lines[section["start"] - 1:end]),
            format="EXPLICIT_LABELLED_MARKDOWN_SECTION"))

    for number, line in enumerate(lines, 1):
        heading = re.match(r"^#{1,6}[ \t]+(?:ID[ \t]+)?(.+?)[ \t]*$", line)
        if heading:
            finish(number - 1)
            key_id = ident(heading[1])
            section = dict(id=key_id, start=number, fields={}) if key_id else None
            continue
        field = re.match(r"^-[ \t]+([^:：]+)[:：][ \t]*(.*)$", line)
        if section is not None and field:
            label = field[1].strip(" `*")
            inv.require(label not in section["fields"], "explicit prose review repeats a field")
            section["fields"][label] = field[2]
    finish(len(lines))
    return sorted(entries, key=lambda row: row["number"])


def decisions(directory, expected):
    found = {}
    explicit = {row["batch"]: row for row in bindings
                if row["role"] == directory.parent.name and row["cohort"] == directory.name}
    for row in explicit.values():
        chosen = ROOT / row["path"]
        inv.require(chosen.parent == directory and inv.file_sha(chosen) == row["sha256"],
                    "explicit author review binding changed or left its assigned directory")
    def bound_rank(path):
        batch, root_addendum, version = review_rank(path)
        chosen = explicit.get(batch)
        matched = bool(chosen and str(path.relative_to(ROOT)) == chosen["path"])
        return batch, root_addendum, matched, version
    for review in sorted(directory.glob("review*.md"), key=bound_rank):
        payload = stable(review)
        saved, key = save_content(archive_dir, payload, ".md")
        pin = dict(path=str(review.relative_to(ROOT)), sha256=key, archive=saved)
        review_pins.append(pin)
        try:
            entries = review_entries(payload, allow_sections=directory.name == "root_selected_signal_counter_v1")
        except ValueError as exc:
            errors.append(dict(review=pin, group=directory.name, role=directory.parent.name,
                               error="INVALID_REVIEW_SYNTAX_NOT_EVIDENCE", detail=str(exc)))
            entries = []
        parsed_ids = {ident(entry["cells"][0]) for entry in entries}
        unsupported = safeguards.unparsed_declared_review_ids(payload, parsed_ids, expected)
        for missing_id in sorted(unsupported):
            historical = dict(id=missing_id, review=pin, group=directory.name, role=directory.parent.name,
                              error="EXPLICIT_NEW_REVIEW_NOT_PARSED_OLDER_BODY_MUST_NOT_FALL_BACK")
            unparsed_review_history.append(historical)
            found[missing_id] = dict(id=missing_id, decision="NEEDS_ROOT", original_status="UNPARSED_EXPLICIT_REVIEW",
                read_scope="", reason=historical["error"], review=pin, line=1, review_line_end=len(payload.decode("utf-8").splitlines()),
                review_source_format="UNPARSED_DECLARATION_IS_MISSING_EVIDENCE_ONLY", review_text="",
                body_references=[], declared_output_cell="", body_reference_scope="NO_PARSED_BODY_REFERENCE",
                author_precedence=[*review_rank(review), 0], root_approved=False)
        for entry in entries:
            number, line, cells, header = entry["number"], entry["raw"], entry["cells"], entry["header"]
            key_id = ident(cells[0])
            inv.require(key_id is not None, "parsed explicit review lost its source ID")
            if key_id not in expected:
                errors.append(dict(id=key_id, review=pin, error="ROW_OUTSIDE_ASSIGNED_COHORT"))
                continue
            if directory.name in strict_task_cohorts:
                batch = review_rank(review)[0]
                task_path = directory / ("TASK_" + str(batch).zfill(3) + ".md")
                inv.require(task_path.is_file(), "new explicit review has no assigned TASK")
                input_pins[str(task_path.relative_to(ROOT))] = inv.file_sha(task_path)
                if not safeguards.review_row_matches_task(key_id, task_path.read_text(encoding="utf-8")):
                    invalid_task_rows.append(dict(id=key_id, review=pin, line=number, review_text=line,
                        task=str(task_path.relative_to(ROOT)), error="REVIEW_ROW_IS_NOT_IN_THIS_TASK_SOURCE_LIST",
                        invalid_as_review_evidence=True))
                    continue
            withdrawn = [row for row in retractions if row["id"] == key_id
                         and row["role"] == directory.parent.name
                         and row["cohort"] == directory.name
                         and row["review"] == pin["path"]
                         and row["review_sha256"] == pin["sha256"]]
            if withdrawn:
                inv.require(len(withdrawn) == 1, "duplicate exact author retraction")
                retracted_history.append(dict(id=key_id, review=pin, line=number,
                    review_text=line, invalid_as_review_evidence=True,
                    reason=withdrawn[0]["reason"]))
                continue
            # A raw source pipe quoted in the last rationale column is data,
            # not a new semantic column. Keep its exact literal text there.
            if header and len(cells) > len(header):
                cells = cells[:len(header) - 1] + ["|".join(cells[len(header) - 1:])]
            status = {"ACCEPT_CANDIDATE": "ADOPT_CANDIDATE", "REVISE_TEXT": "EDIT_TEXT", "HOLD": "NEEDS_ROOT"}.get(cells[1], cells[1])
            columns = {label: cells[index] for index, label in enumerate(header or []) if index < len(cells)}
            scope = next((value for label, value in columns.items() if "판독" in label or "대조 범위" in label or label == "실제 범위"), "")
            reason = next((value for label, value in columns.items() if "근거" in label or "사유" in label), "")
            pattern = re.escape(key_id.replace(":", "_")) + r"(?:_v[0-9]+)?(?:[._]edits(?:_v[0-9]+)?)?[.](?:txt|md)"
            if directory.name in {"authored_postsignal_review_v1", "exclusion_second_review_v1"}:
                # The assignment explicitly allowed source_ID_vN.txt. This is
                # an exact expected-ID filename, never a body-version guess.
                pattern += r"|source_" + re.escape(key_id.rsplit(":", 1)[1]) + r"(?:_v[0-9]+)?[.]txt"
            if directory.name == "root_selected_signal_counter_v1" and directory.parent.name == "historical_review":
                # Two actual outputs were saved under bare numeric names.
                # Accept only this exact source ID explicitly named in its
                # review output cell. Never guess the highest body version.
                pattern += (r"|(?<![A-Za-z0-9_])" + re.escape(key_id.rsplit(":", 1)[1])
                            + r"_v[0-9]+[.]txt")
            output_cell = next((value for label, value in columns.items() if label in {"출력", "정확 출력", "산출물"}), line)
            row = dict(id=key_id, decision=status, original_status=cells[1], read_scope=scope, reason=reason,
                       review=pin, line=number, review_text=line,
                       review_line_end=entry["end"], review_source_format=entry["format"],
                       body_references=sorted(set(re.findall(pattern, output_cell))),
                       declared_output_cell=output_cell,
                       body_reference_scope="EXPLICIT_OUTPUT_COLUMN" if output_cell != line else "FULL_ROW_WITHOUT_OUTPUT_HEADER",
                       author_precedence=[*review_rank(review), number], root_approved=False)
            found[key_id] = row
    return found


def exact_assigned_input_reference(cell, reference, chosen):
    """Resolve an ACCEPT/KEEP input name against its exact TASK pin.

    A basename equal to the assigned input is not a missing authored output.
    An explicit path must identify that same input, never a different folder.
    A differently versioned authored filename still requires an actual file.
    """
    if reference != Path(chosen["path"]).name:
        return False
    paths = re.findall(r"(?:(?:[A-Za-z][A-Za-z0-9+.-]*://)?(?:/|[A-Za-z0-9_.-]+/))[^\s`<>|()]*[.]txt", cell)
    if paths:
        return set(paths) <= {chosen["path"], str(ROOT / chosen["path"])}
    return True


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
        references = [name for name in row["body_references"] if name.endswith(".txt")]
        inv.require(len(references) <= 1, "accept/keep row explicitly names multiple different bodies")
        if references:
            named = directory / references[0]
            if named.exists():
                payload = stable(named)
                key = digest(payload)
                row["explicit_accept_body"] = dict(path=str(named.relative_to(ROOT)), sha256=key)
                inv.require(key == chosen["sha256"],
                            "EXPLICIT_ACCEPT_OR_KEEP_BODY_DIFFERS_FROM_ASSIGNED_TEXT")
            else:
                inv.require(exact_assigned_input_reference(row["declared_output_cell"], references[0], chosen),
                            "named accept body is neither an actual authored file nor its exact assigned input")
                row["explicit_accept_assigned_input"] = dict(chosen,
                    binding="EXACT_ASSIGNED_INPUT_PATH_OR_BASENAME_PIN_NOT_A_NEW_BODY_FILE")
        row.update(status="PINNED_BODY_NOT_ROOT_ADMISSION", body=chosen["path"], clean_text_sha256=chosen["sha256"])
        return
    inv.require(status in {"EDIT_TEXT", "EDIT_RECIPE"}, "unknown authored status")
    references = [name for name in row["body_references"]
                  if (bool(re.search(r"[._]edits(?:_v[0-9]+)?[.]md$", name)) if status == "EDIT_RECIPE" else name.endswith(".txt"))]
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
    collisions = safeguards.partial_reading_view_collisions(row["id"], digest(payload), views_manifest)
    inv.require(not collisions, "AUTHOR_BODY_MATCHES_A_PARTIAL_READING_VIEW_NOT_A_FULL_CANDIDATE")
    body, key = save_content(rendered_dir, payload, ".txt")
    row.update(status="MATERIALIZED_BODY_NOT_ROOT_ADMISSION", body=body, clean_text_sha256=key,
               author_output=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)))


for group in groups:
    manifest_path = BASE / group / "manifest.json"
    manifest = inv.cache.read(manifest_path)
    input_pins[str(manifest_path.relative_to(ROOT))] = inv.file_sha(manifest_path)
    coverage[group] = dict(expected=0, saved=0, awaiting_review=0, explicitly_reassigned=0)
    sources = {row["id"]: dict(row, **row.get("paths", {})) for row in manifest["rows"]}
    for role, assigned in manifest["assignments"].items():
        assigned = assigned["ids"] if isinstance(assigned, dict) else assigned
        coverage[group]["expected"] += len(assigned)
        directory = BASE / "agents" / role / group
        active = {ident for ident in assigned if (group, role, ident) not in reassignments}
        choices = decisions(directory, active) if active else {}
        for key_id in assigned:
            if (group, role, key_id) in reassignments:
                reassigned = reassignments[group, role, key_id]
                inv.require(sources[key_id]["original"]["sha256"] == reassigned["original_text_sha256"],
                            "reassigned old source identity differs")
                reassigned_history.append(reassigned)
                coverage[group]["explicitly_reassigned"] += 1
                continue
            if key_id not in choices:
                coverage[group]["awaiting_review"] += 1
                errors.append(dict(id=key_id, group=group, role=role, error="NO_SAVED_REVIEW_ROW"))
                continue
            coverage[group]["saved"] += 1
            row = dict(choices[key_id], cohort=group, role=role, manifest=str(manifest_path.relative_to(ROOT)))
            try:
                materialize(row, sources[key_id], directory)
                limited = sources[key_id].get("restricted_parent_metadata_only")
                if limited is not None:
                    row["compare_source"] = sources[key_id]["original"]
                    row["original"] = limited
                    row["restricted_parent_not_opened_or_copied"] = True
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
              coverage=coverage, retracted_history=retracted_history,
              unparsed_review_history=unparsed_review_history,
              invalid_task_rows=invalid_task_rows, invalid_task_rows_skipped=len(invalid_task_rows),
              active_unparsed_review_rows=[dict(id=row["id"], cohort=row["cohort"], review=row["review"])
                    for row in records if row.get("original_status") == "UNPARSED_EXPLICIT_REVIEW"],
              explicitly_reassigned_source_assignments=reassigned_history,
              invalid_retracted_rows_skipped=len(retracted_history),
              goal_complete=False, training_authorized=False)
inv.require(len(retracted_history) == len(retractions) == 3,
            "exact withdrawn rows were not all retained and excluded as evidence")
inv.require(len(reassigned_history) == len(reassignments) == 2,
            "both interrupted assignments require exact replacement provenance")
for detail in coverage.values():
    inv.require(detail["expected"] == detail["saved"] + detail["awaiting_review"] + detail["explicitly_reassigned"],
                "review assignment conservation differs")
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "snapshot needs sharding")
inv.write_json(OUT, result)
print(json.dumps(dict(records=len(records), unique_ids=len(by_source), counts=result["counts"], errors=errors,
                      conflicts=[row["id"] for row in conflicts], coverage=coverage,
                      invalid_retracted_rows_skipped=len(retracted_history)), ensure_ascii=False))




