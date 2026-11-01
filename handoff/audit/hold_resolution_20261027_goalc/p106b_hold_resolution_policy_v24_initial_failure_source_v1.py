"""An empty alias never proves the rest of a formal article is complete."""
import re
from scripts import p106b_hold_resolution_policy_v23 as previous
from scripts import p106b_hold_resolution_policy_v22 as names

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V24_ALIAS_SCOPE_AND_OBSERVED_ENGLISH_FORMAL_ROLES"
ALIAS_BODY = "FIRST_TYPED_EMPTY_ALIAS_DOES_NOT_PROVE_THE_REMAINING_FORMAL_BODY"
ENGLISH_ROLE = "OBSERVED_ENGLISH_FORMAL_ROLE_WITHOUT_ITS_ARGUMENT_OR_SYMBOL"
MISSING_ROLE = re.compile(
    r"(?i)\bpoints[ \t]+with[ \t]+[.]|"
    r"\bwhere[ \t]*,[ \t]+and[ \t]+are[ \t]+not[ \t]+yet[ \t]+known")


def __getattr__(name):
    return getattr(previous, name)


def unchecked_body_after_named_alias(text):
    _, aliases = names.typed_initial_alias(text)
    if not aliases:
        return False
    match = names.TYPED_ALIAS.match(text)
    first_line = text[match.end():].split(chr(10), 1)[0]
    ending = re.search(r"[.!?。](?:[ \t]|\Z)", first_line)
    assert ending is not None
    # This is a structural scope, not an arbitrary character or paragraph cap.
    return bool(text[match.end() + ending.end():].strip())


def observed_formal_holes(text):
    values = previous.observed_formal_holes(text)
    if previous.structure.complete_source_program(text):
        return values
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                    for protected, part in previous.v1.protected_parts(text)[0])
    values += [dict(reason=ENGLISH_ROLE, literal=match[0], source_characters=[match.start(), match.end()])
               for match in MISSING_ROLE.finditer(plain)
               if not previous.QUOTE_CONTEXT.search(plain[max(0, match.start() - 400):match.end()])]
    return values


def literal_holes(text):
    reasons = set(previous.literal_holes(text))
    reasons.update(row["reason"] for row in observed_formal_holes(text))
    return sorted(reasons)


def propose(row, individual_hold=False):
    value = previous.propose(row, individual_hold)
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(value, rules=RULES)
    clean = value.get("candidate", value["text"])
    reasons = set(value["reasons"]) if value["decision"] == "PENDING" else set()
    reasons.update(row["reason"] for row in observed_formal_holes(clean))
    if unchecked_body_after_named_alias(row["text"]):
        reasons.add(ALIAS_BODY)
    if reasons:
        return dict(value, decision="PENDING", text=row["text"], candidate=clean,
                    reasons=sorted(reasons), rules=RULES)
    return dict(value, rules=RULES)
