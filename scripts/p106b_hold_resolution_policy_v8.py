#!/usr/bin/env python3
"""Literal syntax, real lyric repetition and source-observed surface markup.

Only complete presentation constructs are rendered. Teaching examples, code,
encoding demonstrations, populated tables, reference names and every actual
Unicode glyph remain literal. Missing table values are not reconstructed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re
from types import SimpleNamespace
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v7 as previous
from scripts import p106b_source_cleanup as presentation

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V8_LITERAL_SYNTAX_AND_LYRICS"
v6, v4, v2, v1 = previous.previous, previous.v4, previous.v2, previous.v1
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions
ORIGINAL_INTRO = previous.intro
ORIGINAL_REPETITION = previous.structured_repetition
SYNTAX_TOPIC = re.compile(
    r"\b(?:HTML|XML|DocBook|SGML|XHTML|Unicode|UTF-?[0-9]+|ASCII|ISO-?8859|"
    r"encoding|markup|syntax|tag|entity|entities|transcription|regex|regexp|"
    r"Python|Lisp|JavaScript|PHP|Matlab|Octave|programming|source code)\b|"
    r"프로그래밍|구문|문법|전사\s*기호|유니코드|태그|인코딩|정규\s*표현식", re.I)
ESTABLISHMENT = re.compile(r"설립되었다[.!?。]?$|개관하였다[.!?。]?$|개관했다[.!?。]?$", re.M)
INSTITUTION = re.compile(r"미술관|박물관|기념관|연구소|재단|기업|공원|사찰|기관|학교")
KIND = re.compile(r"(?:의\s*일종|한\s*종류|종류\s*중\s*하나)")
LINK = re.compile(r"(?<!\[)\[\[([^\[\]|:\n]+)\]\](?!\])")
LYRIC_LABELS = {v1.normalize_heading(x) for x in ["가사", "노랫말", "lyrics", "후렴", "가사 원문"]}
REFERENCE_LABELS = {v1.normalize_heading(x) for x in ["참조", "참조 자료", "관련 항목"]}
SCORE_SECTION = re.compile(r"^(?:연도별\s*(?:타격|수비|투구)\s*성적|통산\s*기록|주요\s*기록|시청률)$")
LEGEND = re.compile(r"^(?:굵은\s*글씨는\s*(?:시즌|통산)\s*최고\s*성적[.!。]?|"
                    r"파란색.*최저\s*시청률.*빨간색.*최고\s*시청률[.!。]?)$")
ORPHAN_REFERENCE_CLOSE = re.compile(r"^[ \t]*</ref>[ \t]*\}\}[ \t]*(?:\r?\n)?$")
IMAGE_DOWNLOAD = re.compile(r"^[ \t]*Download\s+TIF\s+for\s+Image\s+[0-9]+[ \t]*(?:\r?\n)?$", re.I)
EMPTY_IMAGE_ROW = re.compile(r"^[ \t]*\|[ |\t]*\|[ \t]*(?:\r?\n)?$")
BOOK_CONTEXT = re.compile(r"저서|저작|책(?:을|은|는|에서|이다)|도서|출판|서적|읽었|\b(?:book|novel|author)\b", re.I)
CALL_CONTEXT = re.compile(v6.CALL_CONTEXT.pattern + r"|\b(?:code snippet|code example|split|isnumeric|callable)\b", re.I)
TEACHING_FRAME = re.compile(r"\b(?:HTML|XML|DocBook|SGML|Unicode|UTF-?[0-9]+|ASCII|encoding|"
                            r"syntax|programming|regular expressions?|code examples?|code snippets?)\b|"
                            r"프로그래밍|구문|문법|전사\s*기호|유니코드|태그|인코딩|정규\s*표현식", re.I)


def intro(text):
    found = ORIGINAL_INTRO(text)
    if found is not None:
        return found
    for match in v4.v3.PARAGRAPH.finditer(text):
        paragraph = match[0].strip()
        if v4.v3.SUBJECT.search(paragraph) and (
                INSTITUTION.search(paragraph) and ESTABLISHMENT.search(paragraph)
                or KIND.search(paragraph) and re.search(r"[.!?。]$", paragraph)):
            return paragraph
        if chr(10) in paragraph or re.search(r"[.!?。]$", paragraph):
            break
    return None


def protected_lines(text):
    parts, opened = v1.protected_parts(text)
    masked = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                     for protected, part in parts)
    return masked.splitlines(keepends=True), opened


def surface(text):
    """Remove only explicitly empty extraction/UI records with local evidence."""
    plain_lines, opened = protected_lines(text)
    if opened:
        return text, []
    lines = text.splitlines(keepends=True)
    changes, remove = [], set()
    syntax = bool(SYNTAX_TOPIC.search(text))
    identified = intro(text) is not None
    image_page = any(IMAGE_DOWNLOAD.fullmatch(line) for line in plain_lines)
    for i, line in enumerate(plain_lines):
        if identified and not syntax and ORPHAN_REFERENCE_CLOSE.fullmatch(line):
            remove.add(i)
            changes.append(dict(reason="ORPHAN_CLOSED_REFERENCE_TEMPLATE_WITH_NO_NAME_OR_VALUE",
                                line=i+1, original=lines[i]))
        elif image_page and (IMAGE_DOWNLOAD.fullmatch(line) or EMPTY_IMAGE_ROW.fullmatch(line)):
            remove.add(i)
            changes.append(dict(reason="IMAGE_DOWNLOAD_UI_OR_EMPTY_IMAGE_LAYOUT_ROW",
                                line=i+1, original=lines[i]))
    entries = [i for i,line in enumerate(plain_lines) if line.strip() and i not in remove]
    known = v4.LABELS | previous.EXTRA_LABELS | REFERENCE_LABELS
    for n,index in enumerate(entries):
        if not SCORE_SECTION.fullmatch(plain_lines[index].strip()):
            continue
        end = n+1
        while end < len(entries):
            following = plain_lines[entries[end]].strip()
            if (v1.normalize_heading(following) in known or SCORE_SECTION.fullmatch(following)
                    or v2.METADATA_YEAR.fullmatch(following) or v4.CATEGORY_LINE.fullmatch(following)):
                break
            end += 1
        content = entries[n+1:end]
        # Any actual row, number, link or explanatory sentence defeats this
        # proof. Only the exact source legend without a single data row is held.
        if content and all(LEGEND.fullmatch(plain_lines[i].strip()) for i in content):
            for i in [index]+content:
                remove.add(i)
                changes.append(dict(reason="EMPTY_SPORT_RECORD_SECTION_AND_UNATTACHED_LEGEND",
                                    line=i+1, original=lines[i]))
    return "".join(line for i,line in enumerate(lines) if i not in remove), changes


def render_presentation(text):
    parts, opened = v1.protected_parts(text)
    if opened:
        return text, []
    result, changes = [], []
    # The original module normalizes NFC before splitting. Its normalizer is
    # replaced locally so no literal Unicode or protected code is normalized.
    identity = SimpleNamespace(normalize=lambda form, value: value)
    for protected, part in parts:
        if protected or SYNTAX_TOPIC.search(part):
            result.append(part)
            continue
        fixed = part
        if presentation.TAG_PATTERN.search(fixed):
            with patch.object(presentation, "unicodedata", identity):
                rendered, counts, warnings = presentation.clean_text(fixed, "unknown")
            if rendered != fixed:
                changes.append(dict(reason="BALANCED_PRESENTATION_ONLY_ORIGINAL_HELPER_NO_NFC",
                                    counts=counts, warnings=warnings))
                fixed = rendered
        def link(match):
            value = match[1]
            if not value.strip() or re.search(r"[={}<>\\]", value):
                return match[0]
            changes.append(dict(reason="COMPLETE_UNALIASED_TEXT_LINK_RETAIN_LITERAL_LABEL",
                                original=match[0], replacement=value))
            return value
        fixed = LINK.sub(link, fixed)
        result.append(fixed)
    return "".join(result), changes


def structured_repetition(text):
    if ORIGINAL_REPETITION(text):
        return True
    parts, _ = v1.protected_parts(text)
    plain = "".join(part for protected,part in parts if not protected)
    lines = [line.strip() for line in plain.splitlines() if line.strip()]
    frequency = Counter(line for line in lines if len(line)>=6)
    duplicates = {line for line,count in frequency.items() if count>1
                  and v1.normalize_heading(line) not in v4.LABELS | REFERENCE_LABELS}
    contexts = defaultdict(list)
    context = "MAIN"
    for line in lines:
        label = v1.normalize_heading(line)
        if label in LYRIC_LABELS:
            context = "SOURCE_LYRICS"
        elif label in v4.APPENDICES | REFERENCE_LABELS:
            context = "APPENDIX"
        elif label in previous.SECTION_CONTEXT | v4.LABELS:
            context = "MAIN"
        if line in duplicates:
            contexts[line].append(context)
    # Preserve every actual refrain. A repeated sentence outside the explicit
    # lyric/appendix section is never released by the presence of a lyrics label.
    return bool(contexts) and all(all(value in {"SOURCE_LYRICS","APPENDIX"}
                                            for value in values) for values in contexts.values())


def literal_tag_context(text):
    """Prove that every angle construct is an actual retained teaching token."""
    plain = "".join(part for protected,part in v1.protected_parts(text)[0] if not protected)
    matches = list(v1.GENERIC_TAG.finditer(plain))
    if not matches or "<!--" in plain:
        return False
    for match in matches:
        lo = plain.rfind(chr(10)+chr(10),0,match.start())+2
        if lo==1:
            lo=0
        hi = plain.find(chr(10)+chr(10),match.end())
        paragraph = plain[lo:hi if hi!=-1 else len(plain)]
        preceding = plain[max(0,lo-512):lo]
        if TEACHING_FRAME.search(paragraph) or (TEACHING_FRAME.search(preceding)
                and v6.CALL_CONTEXT.search(plain[:min(len(plain),2048)])):
            continue
        if not (BOOK_CONTEXT.search(paragraph) and not re.search(r"[/=]",match[0])
                and not re.fullmatch(r"(?i)</?(?:b|i|em|strong|br|div|span|p|ul|ol|li|h[1-6])>",match[0])):
            return False
    return True


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"]=="validation:0":
        return dict(previous.propose(row,individual_hold),rules=RULES)
    prepared, changes = surface(original)
    prepared, rendered = render_presentation(prepared)
    changes += rendered
    with v2.v2.LOCK, patch.object(previous,"intro",intro), \
            patch.object(previous,"structured_repetition",structured_repetition), \
            patch.object(v6,"CALL_CONTEXT",CALL_CONTEXT), \
            patch.object(previous,"EXTRA_APPENDICES",previous.EXTRA_APPENDICES | REFERENCE_LABELS):
        result = previous.propose(dict(row,text=prepared),False)
    final = result.get("candidate",result["text"])
    risks = set(result["reasons"]) if result["decision"]=="PENDING" else set()
    if "MARKUP_OR_TRANSCRIPTION_REQUIRES_CONTEXT" in risks and literal_tag_context(final):
        risks.discard("MARKUP_OR_TRANSCRIPTION_REQUIRES_CONTEXT")
    if not code_preserved(original,final) or not unicode_examples_preserved(original,final):
        risks.add("CODE_OR_UNICODE_GUARD")
    changes += result["changes"]
    if risks:
        return dict(decision="PENDING",text=original,candidate=final,reasons=sorted(risks),
                    changes=changes,rules=RULES)
    return dict(decision="EDIT" if final!=original else "KEEP",text=final,
                reasons=["SOURCE_PRESENTATION_AND_LITERAL_CONTEXT_RETAINED"],changes=changes,rules=RULES)

