"""Do not treat a completely missing content axis as optional sparse cells."""
import re
from scripts import p106b_hold_resolution_policy_v24 as previous
from scripts import p106b_hold_resolution_structure_v2 as structure

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V25_COMPLETE_MISSING_TABLE_AXES_REMAIN_UNRESOLVED"
COLUMN_REASON = "DECLARED_CONTENT_TABLE_COLUMN_HAS_NO_ACTUAL_VALUES"
OPTIONAL_METADATA = re.compile(r"(?:ISBN(?:-?(?:10|13))?|비고|참고사항|특기사항|주석|remarks|notes)", re.I)


def __getattr__(name):
    return getattr(previous, name)


def missing_table_axes(text):
    if structure.complete_source_program(text):
        return []
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                    for protected, part in previous.v1.protected_parts(text)[0])
    values = []
    for match in structure.TABLE_BLOCK.finditer(plain):
        if previous.QUOTE_CONTEXT.search(plain[max(0, match.start() - 400):match.start()]):
            continue
        lines = [line.strip() for line in match[0].splitlines()]
        if not structure.explicit_sparse_wiki_table(lines):
            continue
        headers = [line for line in lines[1:-1] if line.startswith("!")]
        if len(headers) != 1:
            continue
        header = [cell.strip() for cell in headers[0][1:].split("!!")]
        rows = [[cell.strip() for cell in line[1:].split("||")] for line in lines[1:-1]
                if line.startswith("|") and not line.startswith(("|-", "|+", "|}"))]
        if not rows or any(len(row) != len(header) for row in rows):
            continue
        for column in range(1, len(header)):
            if not any(row[column] for row in rows) and not OPTIONAL_METADATA.fullmatch(header[column]):
                values.append(dict(reason=COLUMN_REASON, column=column, header=header[column],
                    row_labels=[row[0] for row in rows], source_table_characters=[match.start(), match.end()],
                    blank_is_not_interpreted_as_zero_or_not_applicable=True))
    return values


def observed_formal_holes(text):
    return previous.observed_formal_holes(text) + missing_table_axes(text)


def literal_holes(text):
    values = set(previous.literal_holes(text))
    if missing_table_axes(text):
        values.add(COLUMN_REASON)
    return sorted(values)


def propose(row, individual_hold=False):
    value = previous.propose(row, individual_hold)
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(value, rules=RULES)
    clean = value.get("candidate", value["text"])
    reasons = set(value["reasons"]) if value["decision"] == "PENDING" else set()
    if missing_table_axes(clean):
        reasons.add(COLUMN_REASON)
    if ("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in reasons
            and any(change["reason"] == previous.QUARANTINE for change in value["changes"])
            and previous.separate_metadata_suffix(clean)[2]):
        reasons.add("PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE")
    if reasons:
        return dict(value, decision="PENDING", text=row["text"], candidate=clean,
                    reasons=sorted(reasons), rules=RULES)
    return dict(value, rules=RULES)
