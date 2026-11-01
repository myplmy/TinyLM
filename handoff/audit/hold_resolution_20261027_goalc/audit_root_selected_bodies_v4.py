"""Inspect actual reviewed bodies without granting cache or semantic approval.

Existing code/Unicode/style guards are reused. Restricted parent content is
never inspected: only an explicitly pinned source view is eligible there.
"""
from collections import Counter
from pathlib import Path
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v23 as policy
from scripts import p106b_hold_resolution_literal_guard_v3 as literal
from scripts import p106b_hold_resolution_source_relations_v1 as relations

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "root_selected_body_literals_v4.json"
inv.require(not OUT.exists(), "new body inspection receipt required")
plan_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V8.json"
plan = inv.cache.read(plan_path)
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:1216576",
              "expanded_train:1250821", "expanded_train:15695", "expanded_train:20624", "expanded_train:6030"}
clinical_path = BASE / "clinical_source_view_v1/manifest.json"
clinical = inv.cache.read(clinical_path)
view_paths = [BASE / "limited_biology_views_v2/manifest.json"]
allowed_views = {(clinical["id"], clinical["view"]["path"], clinical["view"]["sha256"])}
for path in view_paths:
    for row in inv.cache.read(path)["rows"]:
        allowed_views.add((row["id"], row["original"]["path"], row["original"]["sha256"]))
cases = literal.load_registry()
numeric = re.compile(r"(?<![A-Za-z0-9_])[-+−]?[0-9]+(?:[.,][0-9]+)*(?:%|°[CF])?")
lexical = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[\u3400-\u9fff]+")
memo = inv.corpus.MEMOS
authored_memo = re.compile(
    r"(?mi)^[ \t]*(?:#{1,6}[ \t]*)?(?:"
    r"(?:[0-9]+[ \t]+)?(?:본문[ \t]*정제|정제[ \t]*본문|수정[ \t]*본문)[ \t]*v[0-9]+|"
    r"(?:이[ \t]*본문|새[ \t]*본문|원문|후보|candidate|TXT|sidecar|hold|검수|편집|보류|정제)"
    r"[^\n]{0,120}(?:보존했|보존하였|분리했|분리하였|저장했|작성했|검수[ \t]*메모|"
    r"편집[ \t]*메모|sidecar|hold)|"
    r"(?:실제[ \t]*)?(?:판독[ \t]*범위|검토[ \t]*결과|수정[ \t]*근거|정제[ \t]*사유))")
texts, records, counts, errors = {}, [], Counter(), []
started = time.monotonic()


def read_pin(path, key):
    if path not in texts:
        payload = (ROOT / path).read_bytes()
        inv.require(inv.sha(payload.decode("utf-8")) == key and inv.file_sha(ROOT / path) == key,
                    "source/body pin changed")
        texts[path] = payload.decode("utf-8"), key
    value, actual = texts[path]
    inv.require(actual == key, "one path is bound to different source pins")
    return value


for source in plan["rows"]:
    ident = source["id"]
    chosen = source["selected"]
    if not chosen.get("body"):
        counts.update(root_text_only_decisions=1)
        continue
    compare = chosen.get("compare_source") or dict(path=chosen.get("source") or source["original_paths"][0],
                                                      sha256=source["original_text_sha256"])
    choices = [dict(body=chosen["body"], clean_text_sha256=chosen["clean_text_sha256"], compare_source=compare,
                    cohort=chosen.get("cohort", "EXISTING_EXACT_ROOT_SELECTION"),
                    review=chosen.get("review") or chosen.get("review_inputs") or chosen.get("evidence"),
                    root_approved=bool(source.get("exact_root_evidence")))]
    for choice in choices:
        compare = choice["compare_source"]
        if ident in restricted:
            inv.require((ident, compare["path"], compare["sha256"]) in allowed_views,
                        "restricted source escaped its exact limited view")
        record = dict(id=ident, cohort=choice["cohort"], compare_source=compare,
                      original_text_sha256=source["original_text_sha256"], body=choice["body"],
                      clean_text_sha256=choice["clean_text_sha256"], review=choice.get("review"),
                      exact_root_selected=choice["root_approved"], cache_admitted=False)
        try:
            raw = read_pin(compare["path"], compare["sha256"])
            clean = read_pin(choice["body"], choice["clean_text_sha256"])
            code_guard = policy.code_preserved(raw, clean)
            exact_literal = False if code_guard else literal.exact_pair_preserved(raw, clean, ident, cases)
            added_numbers = dict(Counter(numeric.findall(clean)) - Counter(numeric.findall(raw)))
            added_words = Counter(lexical.findall(clean)) - Counter(lexical.findall(raw))
            added_memos = (Counter(match[0] for pattern in [memo, authored_memo] for match in pattern.finditer(clean))
                           - Counter(match[0] for pattern in [memo, authored_memo] for match in pattern.finditer(raw)))
            new_pairs = relations.ungrounded_new_link_pairs(raw, clean)
            missing_pairs = relations.missing_source_link_pairs(raw, clean)
            call_losses = policy.proven_source_call_losses(raw, clean)
            plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                            for protected, part in policy.v1.protected_parts(clean)[0])
            fields = Counter(match[0] for match in inv.cache.MISSING_FIELD.finditer(plain))
            wiki_tokens = {token: plain.count(token) for token in ["{{", "}}", "{|", "|}", "[[", "]]", ":en:"] if token in plain}
            record.update(status="ACTUAL_BODY_LITERAL_READBACK_NOT_SEMANTIC_APPROVAL", code_guard=code_guard,
                exact_reviewed_literal_exception=exact_literal, unicode_guard=policy.unicode_examples_preserved(raw, clean),
                semantic_style_guard=policy.semantic_style_preserved(raw, clean),
                ordered_nonwhitespace_deletion_only=policy.ordered_deletion(raw, clean),
                source_function_parentheses_losses=call_losses,
                ungrounded_literal_link_pairs=[dict(target=pair[0], display=pair[1], count=count) for pair, count in sorted(new_pairs.items())],
                missing_source_literal_link_pairs=[dict(target=pair[0], display=pair[1], count=count) for pair, count in sorted(missing_pairs.items())],
                literal_link_diagnostics_are_not_automatic_semantic_verdicts=True,
                introduced_numeric_occurrences=added_numbers,
                introduced_lexical_occurrences=dict(added_words.most_common(60)),
                introduced_lexical_distinct=len(added_words), introduced_lexical_total=sum(added_words.values()),
                introduced_editor_memo_occurrences=dict(added_memos), literal_hole_signals=policy.literal_holes(clean),
                remaining_field_literal_signals=dict(fields), raw_wiki_literal_signals=wiki_tokens,
                source_characters=len(raw), clean_characters=len(clean))
            counts.update(bodies=1)
            counts["source_function_parentheses_loss_flags"] += bool(call_losses)
            counts["ungrounded_literal_link_pair_flags"] += bool(new_pairs)
            counts["missing_source_literal_link_pair_flags"] += bool(missing_pairs)
            counts["code_or_unicode_flags"] += not (record["unicode_guard"] and (code_guard or exact_literal))
            counts["style_flags"] += not record["semantic_style_guard"]
            counts["numeric_flags"] += bool(added_numbers)
            counts["lexical_flags"] += bool(added_words)
            counts["editor_memo_flags"] += bool(added_memos)
            counts["literal_hole_signals"] += bool(record["literal_hole_signals"])
            counts["remaining_field_literal_signals"] += bool(fields)
            counts["raw_wiki_literal_signals"] += bool(wiki_tokens)
        except (ValueError, OSError, UnicodeError) as error:
            record.update(status="BODY_NOT_VALIDATED", error=str(error))
            errors.append(dict(id=ident, body=choice["body"], error=str(error)))
        records.append(record)

paths = [plan_path, clinical_path, *view_paths, Path(__file__)]
result = dict(status="ACTUAL_REVIEWED_BODY_LITERAL_DIAGNOSTICS_NOT_ADMISSION", records=records, counts=dict(counts), errors=errors,
    source_ids=len({row["id"] for row in records}), pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in paths},
    seconds=time.monotonic() - started, restricted_parent_full_content_opened=False,
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "readback receipt needs shards")
inv.write_json(OUT, result)
print(json.dumps(dict(records=len(records), source_ids=result["source_ids"], counts=result["counts"],
                      errors=len(errors), seconds=result["seconds"]), ensure_ascii=False))
