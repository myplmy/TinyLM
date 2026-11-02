"""Quarantine two conflicting birth-year fields without choosing either year."""
from __future__ import annotations

import hashlib
import re
from scripts import p106b_hold_resolution_policy_v26 as baseline

RULE = "EXACT_TWO_BIRTH_YEAR_FIELDS_QUARANTINED_MONTH_DAY_AND_OTHER_FACTS_PRESERVED_V1"
DATE = re.compile(r"(?P<year>[12][0-9]{3})년[ \t]*(?P<month>[0-9]{1,2})월[ \t]*(?P<day>[0-9]{1,2})일")
CATEGORY = re.compile(r"(?m)^[ \t]*(?P<year>[12][0-9]{3})년[ _\t]+출생[ \t]*$")
SPAN = re.compile(r"~|～|∼|–|—|[ \t]+-[ \t]+")
PERSON = re.compile(baseline.v12.BIOGRAPHIC_ROLE.pattern +
    r"|소설가|시인|화가|조각가|감독|성우|교수|언론인|기업인|성직자|문신|무신|백작|인물|사람")
UNCERTAIN = re.compile(r"음력|양력|율리우스|그레고리|기원전|추정|추측|논쟁|불명|미상|불확실|"
                       r"정확하지|확실하지|또는|[?？]|[0-9]년대|약[ \t]*[12][0-9]{3}")
NONLIFE = re.compile(r"재위|재임|임기|재직|활동[ \t]*기간|통치[ \t]*기간")
OTHER_BIRTH = re.compile(r"생년|생일|출생|태어|탄생|\bborn\b|\bbirth\b", re.I)
AGE = re.compile(r"(?:만[ \t]*)?[0-9]{1,3}[ \t]*세[ \t]*(?:때|에|의[ \t]*나이|나이로|였|가[ \t]*되|로[ \t]*사망)")


def _date_valid(match):
    month, day = int(match["month"]), int(match["day"])
    # Calendar choice is not inferred; only dates impossible in any ordinary
    # month are rejected. Explicit calendar qualifications are excluded above.
    return 1 <= month <= 12 and 1 <= day <= (29 if month == 2 else 30 if month in {4, 6, 9, 11} else 31)


def prove(text):
    """Return a source-coordinate deletion proof, never a cache admission."""
    first = baseline.intro(text)
    if not first or not text.lstrip().startswith(first) or not PERSON.search(first):
        return None
    if text.lstrip().startswith(('"', "'", "‘", "“", ">")) or any(token in text for token in ["```", "~~~"]):
        return None
    if baseline.QUOTE_CONTEXT.search(first) or UNCERTAIN.search(first):
        return None
    lead = baseline.v12.INTRO_NAME.match(text)
    if lead is None or baseline.v12.VALUE_NAME.search(lead["name"]):
        return None
    fields = lead["fields"]
    if NONLIFE.search(fields) or any(mark in fields for mark in ["<", ">", "=", "{", "}", "[", "]"]):
        return None
    pieces = list(SPAN.finditer(fields))
    if len(pieces) > 1:
        return None
    left = fields[:pieces[0].start()] if pieces else fields
    dates = list(DATE.finditer(left))
    if len(dates) != 1:
        return None
    born = dates[0]
    prefix, suffix = left[:born.start()].strip(), left[born.end():].strip()
    if suffix or (prefix and (prefix[-1] not in {",", ";"} or re.search(r"[0-9]", prefix))):
        return None
    if not _date_valid(born):
        return None
    if pieces:
        right = fields[pieces[0].end():].strip()
        if right:
            died = DATE.fullmatch(right)
            if died is None or not _date_valid(died):
                return None
    categories = list(CATEGORY.finditer(text))
    if len(categories) != 1:
        return None
    category = categories[0]
    if category["year"] == born["year"] or category.start() <= lead.end():
        return None
    metadata = baseline.separate_metadata_suffix(text)
    if not metadata[2] and baseline.metadata.prove(text) is None:
        return None
    blocks = [block for block in baseline.BLOCK.finditer(text) if block[0].strip()]
    if not blocks or not (blocks[-1].start() <= category.start() < category.end() <= blocks[-1].end()):
        return None
    if baseline.QUOTE_CONTEXT.search(text[max(0, blocks[-1].start() - 400):blocks[-1].start()]):
        return None

    year_lo = lead.start("fields") + born.start("year")
    year_hi = lead.start("fields") + born.end("year") + 1  # The source's 년 suffix.
    while year_hi < len(text) and text[year_hi] in " \t":
        year_hi += 1
    remainder = text[:lead.start("fields")] + text[lead.end("fields"):category.start()] + text[category.end():]
    # Other birth claims or age arithmetic may depend on the disputed year.
    # They require separate source reading and cannot inherit this proof.
    if OTHER_BIRTH.search(remainder) or AGE.search(remainder) or UNCERTAIN.search(remainder):
        return None
    before_category = text[:category.start()]
    cat_lo, cat_hi = category.start(), category.end()
    if cat_hi < len(text) and text[cat_hi] == chr(10):
        cat_hi += 1
    spans = [(year_lo, year_hi, "CONFLICTING_LEAD_BIRTH_YEAR"),
             (cat_lo, cat_hi, "CONFLICTING_TRAILING_BIRTH_CATEGORY")]
    clean = text
    for lo, hi, _ in reversed(spans):
        clean = clean[:lo] + clean[hi:]
    if (not baseline.ordered_deletion(text, clean) or not baseline.code_preserved(text, clean)
            or not baseline.unicode_examples_preserved(text, clean)
            or not baseline.semantic_style_preserved(text, clean)):
        return None
    input_sha = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()
    changes = [dict(reason=RULE, role=role, original=text[lo:hi],
        prepared_candidate_characters=[lo, hi], input_text_sha256=input_sha,
        coordinate_basis="EXACT_FUNCTION_INPUT_NOT_NATIVE_TOKEN_COORDINATES", replacement="")
        for lo, hi, role in spans]
    return dict(candidate=clean, changes=changes,
        proof=dict(kind=RULE, input_text_sha256=input_sha, subject=lead["name"].strip(),
            lead_birth_year=born["year"], category_birth_year=category["year"],
            month_day=born["month"] + "월 " + born["day"] + "일",
            exact_month_day=text[lead.start("fields") + born.start("month"):lead.start("fields") + born.end()],
            birth_year_selected=None, age_recomputed=False, other_text_rewritten=False,
            metadata_boundary_reused=True, removed_fields=2))
