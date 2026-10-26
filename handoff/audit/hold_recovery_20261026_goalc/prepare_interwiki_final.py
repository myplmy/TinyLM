"""Adopt the independently reviewed four-fragment repair without changing policy."""
from collections import Counter
import copy
import json
from pathlib import Path
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
import final_adoptions
from scripts.p106b_native_text_audit import file_sha, write_json


def main():
    old_path = AUDIT / "root_adoptions_v2.json"
    old = json.loads(old_path.read_text(encoding="utf-8"))
    assert old["root_decisions_approved"]
    document = copy.deepcopy(old)
    ident = "expanded_train:1080124"
    row = next(r for r in document["rows"] if r["id"] == ident)
    before = (ROOT / row["path"]).read_text(encoding="utf-8")
    directory = ROOT / "data_cache/p106b_hold_recovery_v1_20261026_goalc/agents/historical_review/postbuild_residual_v4"
    path = directory / "expanded_train_1080124.txt"
    sidecar = directory / "expanded_train_1080124_hold.md"
    review = directory / "review.md"
    counter = ROOT / "data_cache/p106b_hold_recovery_v1_20261026_goalc/agents/context_controls/counter_interwiki_postbuild_v2.md"
    fragments = [
        "So for example if you wanted to link to the Jedi page on Wookiepedia, you would use",
        "Spanish wikis can be found under",
        "- To request a specific interwiki link for your wiki, please visit this page.",
    ]
    expected = before
    for fragment in fragments:
        assert expected.count(fragment) == 1
        expected = expected.replace(fragment, "")
    assert expected.count("[[Wikia:c:Wiki name:Page title]]or") == 1
    expected = expected.replace("[[Wikia:c:Wiki name:Page title]]or", "[[Wikia:c:Wiki name:Page title]]")
    actual = path.read_text(encoding="utf-8")
    assert actual.split() == expected.split(), "unreviewed content change"
    assert all(fragment not in actual for fragment in fragments)
    assert "[[Wikia:c:Wiki name:Page title]]or" not in actual
    held = sidecar.read_text(encoding="utf-8")
    assert all(fragment in held for fragment in fragments)
    assert "| or |" in held
    counter_text = counter.read_text(encoding="utf-8")
    assert any(ident in line and line.split("|")[2].strip() == "PASS" for line in counter_text.splitlines() if line.count("|") >= 3)
    for required in ("[[w:c:wikiname:pagename]]", "de.<wikiname>.wikia.com.", "[[Wikia:c:Wiki name:Page title]]", "[[w:c:Starwars:Jedi|test]]", "[[fr:fromage]]"):
        assert required in actual, required
    row["superseded_decision"] = {k: row[k] for k in ("path", "sha256", "review", "reason")}
    row.update(path=str(path.relative_to(ROOT)), sha256=file_sha(path),
        sidecar_path=str(sidecar.relative_to(ROOT)), sidecar_sha256=file_sha(sidecar),
        review=str(review.relative_to(ROOT)), independent_review=str(counter.relative_to(ROOT)),
        independent_review_sha256=file_sha(counter),
        reason="교육용 위키 문법과 실제 URL을 보존하고, 없는 예제·Spanish 주소·or 대안·식별 불가 페이지의 네 고아 예고만 별도 보류했다.")
    assert len(document["rows"]) == 453
    assert all(a == b for a, b in zip(old["rows"], document["rows"]) if a["id"] != ident)
    assert Counter(r["decision"] for r in document["rows"]) == Counter(KEEP=54, EDIT=366, HOLD=33)
    preflight = final_adoptions.preflight(document["rows"])
    assert preflight["positive_rows"] == 420 and not preflight["failed_rows"]
    with final_adoptions.revision.revision():
        assert document["source_code_sha256"] == final_adoptions.revision.engine.code_pins()
    document.update(supersedes_adoptions=str(old_path.relative_to(ROOT)),
        supersedes_adoptions_sha256=file_sha(old_path), cache_created=False, training_authorized=False)
    target = AUDIT / "root_adoptions_v3.json"
    write_json(target, document)
    write_json(AUDIT / "root_adoptions_v3_preflight.json", dict(preflight,
        adoptions_path=str(target.relative_to(ROOT)), adoptions_sha256=file_sha(target)))
    write_json(AUDIT / "interwiki_literal_repair_proof_v1.json", dict(
        schema="P106B_INTERWIKI_LITERAL_REPAIR_V1", id=ident, passed=True,
        adoptions_path=str(target.relative_to(ROOT)), adoptions_sha256=file_sha(target),
        before_path=row["superseded_decision"]["path"], before_sha256=row["superseded_decision"]["sha256"],
        after_path=row["path"], after_sha256=row["sha256"],
        held_fragments=fragments + ["or"], sidecar_path=row["sidecar_path"], sidecar_sha256=row["sidecar_sha256"],
        comparison="Only four exact fragments removed; whitespace equivalence permitted in this prose explanation. All other 452 adoption rows and seven production sources unchanged.",
        independent_review=row["independent_review"], independent_review_sha256=file_sha(counter),
        model_loads=0, training_authorized=False))
    print(dict(rows=453, positive_rows=420, failures=0, counts=document["counts"], adopted=ident))


if __name__ == "__main__":
    main()
