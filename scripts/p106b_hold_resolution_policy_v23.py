"""Fresh observed formal-role holes and source-proved empty structure leaves."""
import re
from scripts import p106b_hold_resolution_policy_v22 as previous
from scripts import p106b_hold_resolution_empty_structures_v1 as empty
from scripts import p106b_hold_resolution_structure_v2 as structure

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V23_OBSERVED_FORMAL_ROLES_AND_EMPTY_SOURCE_STRUCTURES"
FORMAL_ROLE = re.compile(
    r"(?m)^[ \t]*여기서[ \t]+(?:은|는)[ \t]+(?:(?:주어진|정해진)[ \t]+)?"
    r"(?:계수|상수)(?:들)?(?:이다|이[고며]|다)|"
    r"^[ \t]*여기서[ \t]+에[ \t]+따라[ \t]+(?:미분[ \t]*)?방정식")
ROLE_REASON = "OBSERVED_KOREAN_FORMAL_ROLE_WITHOUT_A_SYMBOL"


def __getattr__(name):
    return getattr(previous, name)


def observed_formal_holes(text):
    if structure.complete_source_program(text):
        return []
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                    for protected, part in previous.v1.protected_parts(text)[0])
    return [dict(reason=ROLE_REASON, literal=match[0], source_characters=[match.start(), match.end()])
            for match in FORMAL_ROLE.finditer(plain)
            if not previous.QUOTE_CONTEXT.search(plain[max(0, match.start() - 400):match.end()])]


def literal_holes(text):
    reasons = set(previous.literal_holes(text))
    if observed_formal_holes(text):
        reasons.add(ROLE_REASON)
    return sorted(reasons)


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    prepared, emptied = empty.clean_empty_structures(original)
    value = previous.propose(dict(row, text=prepared), False)
    clean = value.get("candidate", value["text"])
    reasons = set(value["reasons"]) if value["decision"] == "PENDING" else set()
    reasons.update(literal_holes(clean))
    changes = emptied + value["changes"]
    if previous.code_preserved(original, clean) and previous.unicode_examples_preserved(original, clean):
        reasons.discard("CODE_OR_UNICODE_GUARD")
    else:
        reasons.add("CODE_OR_UNICODE_GUARD")
    if not previous.semantic_style_preserved(original, clean):
        reasons.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not previous.ordered_deletion(original, clean):
        reasons.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    if ("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in reasons
            and any(change["reason"] == previous.QUARANTINE for change in changes)
            and previous.separate_metadata_suffix(clean)[2]):
        reasons.add("PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE")
    if reasons:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(reasons), changes=changes, rules=RULES)
    return dict(decision="EDIT" if original != clean else "KEEP", text=clean,
        reasons=["PROVED_EMPTY_SOURCE_STRUCTURES_ONLY_WITH_ALL_REMAINING_GUARDS"], changes=changes, rules=RULES)
