"""Check exact late repairs and distinguish source-readback false claims."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import write_json, file_sha
from scripts import p106b_hold_policy_v3 as policy
from scripts.p106b_hold_policy_v2 import conflicting_birth_year


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adoptions", type=Path, required=True)
    parser.add_argument("--receipt-name", required=True)
    args = parser.parse_args()
    assert args.receipt_name.isascii() and args.receipt_name.replace("_", "").isalnum()
    document = json.loads(args.adoptions.read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in document["rows"]}
    checks = []
    def record(ident, passed, note):
        row = rows[ident]
        path = ROOT / row["path"]
        checks.append(dict(id=ident, passed=bool(passed), path=row["path"], sha256=file_sha(path), check=note))
    for number in [1415117, 950001, 1389144, 1170731, 384984, 783522]:
        ident = "expanded_train:" + str(number)
        row = rows[ident]
        old = (ROOT / row["superseded_decision"]["path"]).read_text(encoding="utf-8")
        new = (ROOT / row["path"]).read_text(encoding="utf-8")
        expected = old
        if number == 1415117:
            expected = old.replace("[[deacon]", "deacon")
        if number == 950001:
            expected = "".join(line for line in old.splitlines(keepends=True) if line.strip() != "<p>")
        if number == 1389144:
            expected = old.replace("</ref>", "")
        if number == 1170731:
            expected = old.replace("あんべ まさひろ<ref>이름은 아베가 아니라 안베。</ref>", "あんべ まさひろ(이름은 아베가 아니라 안베。)").replace("레몬'''", "레몬")
        if number == 384984:
            expected = "".join(line for line in old.replace("망고 항공()", "망고 항공").splitlines(keepends=True) if line.strip() != "각주")
        if number == 783522:
            expected = old.replace("[하와이 원주민]]는", "하와이 원주민은").replace("[[훌라], [빠니오로]]", "훌라, 빠니오로").replace("[호쿠레아 | 호쿠레아 호]", "호쿠레아(호쿠레아 호)")
            expected = "".join(line for line in expected.splitlines(keepends=True) if line.strip() != "각주")
        passed = new.split() == expected.split() if number == 384984 else new.strip() == expected.strip()
        record(ident, passed, "Only specified wrapper/empty-label changes; 384984 additionally permits empty-line whitespace only")
    for ident, years, required in [
        ("expanded_train:1008442", ["1979년", "1981년"], ["Holly Elissa Dignard"]),
        ("expanded_train:995468", ["1984년", "1982년"], ["Matt Lauria"]),
        ("validation:44", ["1424년", "1425년"], ["Jean II de Lorraine", "1470년 12월 16일 사망", "독살", "1471년"]),
    ]:
        text = (ROOT / rows[ident]["path"]).read_text(encoding="utf-8")
        record(ident, all(year not in text for year in years) and all(s in text for s in required), "Conflicting birth years not selected; explicit names, death date, other dates and uncertainty preserved")
    base = ROOT / "data_cache/p106b_hold_recovery_v1_20261026_goalc"
    old = base / "agents/context_controls/postbuild_residual_v1/validation_44.txt"
    expected = "".join(line for line in old.read_text(encoding="utf-8").splitlines(keepends=True) if line.strip() != "1425년 출생")
    record("validation:44", (ROOT / rows["validation:44"]["path"]).read_text(encoding="utf-8") == expected, "v2 removes one remaining birth category line only")
    frozen = {r["id"]: r for r in json.loads((base / "postbuild_v1_candidates.json").read_text())["rows"]}
    for ident in ["expanded_train:995468", "expanded_train:783522"]:
        item = frozen[ident]
        record(ident, file_sha(ROOT / item["path"]) == item["sha256"], "Earlier counterreview's source text did not change after its SHA was frozen")
    sentences = ["이와같은 일본인 이민이 문제가 되어서 미국에서는 일본인 이민자 몰아내기운동으로 일어났다.", "1907년에는 항공금지령이 선포되어 다음해인 1908년에는 미일간 행정처치로서 아메리카에 가는 일본인노동자의 여행제한을 푸는 미일신사협정이 체결되었다."]
    old = (base / "agents/historical_review/initial/expanded_train_783522.txt").read_text(encoding="utf-8")
    new = (ROOT / rows["expanded_train:783522"]["path"]).read_text(encoding="utf-8")
    record("expanded_train:783522", all(old.count(s) == new.count(s) == 1 for s in sentences), "Two allegedly missing sentences were already present once in the initial and final bodies; no duplicate insertion")
    birth_flags, changes = [], []
    for row in document["rows"]:
        if row["decision"] == "HOLD":
            continue
        text = (ROOT / row.get("path", row["original_path"])).read_text(encoding="utf-8")
        if conflicting_birth_year(text):
            birth_flags.append(row["id"])
        result = policy.propose(dict(id=row["id"], text=text, complete_eos=True, valid_utf8=True), dict(reasons=[], manual_hold=False))
        if result["changes"]:
            changes.append(dict(id=row["id"], changes=result["changes"]))
    assert set(birth_flags) == {"expanded_train:912185", "expanded_train:998546"}
    assert [r["id"] for r in changes] == ["expanded_train:783522"]
    failed = [r["id"] for r in checks if not r["passed"]]
    report = dict(schema="P106B_POSTBUILD_LITERAL_REPAIR_PROOF_V1", checks=checks, failed=failed,
        remaining_birth_guard_signals=birth_flags, remaining_format_rule_suggestions=changes,
        remaining_suggestions_are_reviewed_source_structure_exceptions=True,
        source_adoptions_sha256=file_sha(args.adoptions), source_script_sha256=file_sha(Path(__file__)),
        semantic_scope="Exact late changes and specified fields, not full factual verification")
    write_json(Path(__file__).with_name(args.receipt_name + ".json"), report)
    print(dict(checks=len(checks), failed=failed, birth_false_positives=birth_flags, format_exceptions=[r["id"] for r in changes]))


if __name__ == "__main__":
    main()
