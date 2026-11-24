"""Guard the catalog's evidence routing and replaceable local snapshot."""

from argparse import Namespace
from contextlib import closing, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import research_catalog as catalog
from scripts.check_result_conditions import META_FIELDS, REQUIRED_FIELDS


def signature():
    data = {name: ("SAME", "SAME") for name in REQUIRED_FIELDS}
    data.update(eval_dataset=("VAL_A", "VAL_B"), tokenizer=("TOK_A", "TOK_B"),
                permitted_claim=("DESCRIPTIVE_ONLY", "DESCRIPTIVE_ONLY"))
    matched = sorted(set(data) - META_FIELDS - {"eval_dataset", "tokenizer"})
    data.update(matched_axes=(",".join(matched), ",".join(matched)),
                changed_axes=("eval_dataset,tokenizer", "eval_dataset,tokenizer"),
                unmeasured_axes=("NONE", "NONE"), not_run_claims=("NONE", "NONE"))
    return "\n".join([
        "<!-- TINYLM_CONDITION_SIGNATURE_V1 id=sample -->",
        "| field | arm_a | arm_b | evidence |", "|---|---|---|---|",
        *(f"| {field} | {a} | {b} | sealed |" for field, (a, b) in data.items()),
        "<!-- /TINYLM_CONDITION_SIGNATURE_V1 -->",
    ])


class ResearchCatalogTest(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.db = self.root / catalog.DB_PATH
        self.result = "test_result/109_20261124000000_P109-summary.md"
        self.write(catalog.ONTOLOGY, json.dumps({"version": 1, "concepts": [
            {"id": "pair", "label": "한영 대응", "aliases": ["한영대응"]},
        ]}))
        self.write(self.result, "# 결과\n\n<a id='finding'></a>\n\n## 교과 결과\n\n"
                   "한영 대응 32,768쌍을 사용했고 실제 비중만 바뀌었다.\n"
                   "~~~\n# 예시 속의 헤딩\n~~~\n" + signature() + "\n")
        self.write("test_plan/P109_plan.md", "# 계획\n\n[결과](../" + self.result + "#finding)\n")
        (self.root / "test_plan" / "외부.md").symlink_to(
            self.write("datasets/TinyDataset/secret.md", "# 검색 대상 밖\n"))
        catalog.refresh(self.root, self.db)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def find(self, query="", **options):
        args = dict(query=query, kind=None, project=None, claim=None, dataset=None, tokenizer=None,
                    origin=None, preset=None, decision=None, limit=10)
        args.update(options)
        with closing(catalog.open_index(self.db)) as db:
            return catalog.search(db, Namespace(**args))

    def write_review(self, fragment="finding"):
        self.write(catalog.METHOD_REVIEWS, "\n".join([
            "# 방법론 적용 판정", "", '<a id="case"></a>', "", "## 한영 대응", "",
            catalog.REVIEW_HEADER, "|---|---|---|", "| GPT 주도 실험 | P109C v2 | 적용 |",
            "| 사용자 실행 보고 | P109C v3 | 미검토 |", "",
            f"[원결과](../../{self.result}#{fragment})", "",
        ]))

    def test_search_aliases_and_explicit_links(self):
        hits = self.find("한영대응 32,768쌍 비중", project="P109")
        self.assertEqual([(row["heading"], row["anchor"]) for row in hits], [("교과 결과", "finding")])
        self.assertEqual(self.find("검색 대상 밖"), [])
        with closing(catalog.open_index(self.db)) as db:
            inbound = catalog.related(db, self.result + "#finding", 5)
            self.assertEqual([(row["relation"], row["path"]) for row in inbound],
                             [("cited_by", "test_plan/P109_plan.md")])

    def test_show_reads_the_current_section_and_continuation(self):
        with closing(catalog.open_index(self.db)) as db:
            first = catalog.show(db, self.root, self.result + "#finding", 2)
            self.assertEqual(first["text"], "## 교과 결과\n")
            self.assertEqual(first["next_line"], first["end_line"] + 1)
            second = catalog.show(db, self.root, f"{self.result}:{first['next_line']}", 2)
            self.assertIn("한영 대응 32,768쌍", second["text"])
            self.assertFalse(second["stale"])

            path = self.root / self.result
            original = path.read_text(encoding="utf-8")
            self.write(self.result, "# 앞에 추가한 기록\n\n" + original)
            shifted = catalog.show(db, self.root, self.result + "#finding", 2)
            self.assertEqual(shifted["line"], first["line"] + 2)
            self.assertEqual(shifted["text"], first["text"])
            self.assertTrue(shifted["stale"])
            with self.assertRaises(ValueError):
                catalog.show(db, self.root, self.result + "#absent", 2)
            with self.assertRaises(ValueError):
                catalog.show(db, self.root, "datasets/TinyDataset/secret.md", 2)

            path.unlink()
            path.symlink_to(self.root / "datasets/TinyDataset/secret.md")
            with self.assertRaises(ValueError):
                catalog.show(db, self.root, self.result, 2)

    def test_artifact_paths_use_only_direct_local_references_in_the_current_section(self):
        report = self.write("test_result/evidence/p109/report.json", "{}\n")
        self.write("test_result/109_log_case.txt", "receipt\n")
        alias = report.with_name("alias.json")
        alias.symlink_to(self.root / "datasets/TinyDataset/secret.md")
        self.write(self.result, "\n".join([
            "# 결과", "", '<a id="finding"></a>', "", "## 검증할 절", "",
            "[보고](evidence/p109/report.json) [같은 보고](evidence/p109/report.json#row)",
            "[감사 예정 경로](../handoff/audit/not-transferred.json)",
            "[원로그](109_log_case.txt) [가중치](evidence/p109/model.pt)",
            "[보호 데이터](../datasets/TinyDataset/secret.md) [별칭](evidence/p109/alias.json)",
            "[외부](https://example.com/report.json)",
            "~~~", "[실행 예시](evidence/p109/example.json)", "~~~", "",
            "## 다른 절", "[다른 근거](evidence/p109/other.json)", "",
        ]))
        with closing(catalog.open_index(self.db)) as db:
            results = catalog.artifact_paths(db, self.root, self.result + "#finding", 10)
            self.assertTrue(results["stale"])
            self.assertEqual(results["count"], 3)
            self.assertEqual(results["artifacts"], [
                {"path": "test_result/evidence/p109/report.json", "source_line": 7, "present": True},
                {"path": "handoff/audit/not-transferred.json", "source_line": 8, "present": False},
                {"path": "test_result/109_log_case.txt", "source_line": 9, "present": True},
            ])
            by_line = catalog.artifact_paths(db, self.root, f"{self.result}:13", 1)
            self.assertEqual(by_line["count"], 3)
            self.assertEqual(by_line["artifacts"], results["artifacts"][:1])
        output = StringIO()
        argv = ["research_catalog", "--json", "artifacts", self.result + "#finding"]
        with patch.object(catalog, "ROOT", self.root), patch("sys.argv", argv), redirect_stdout(output):
            self.assertEqual(catalog.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), results)

    def test_filters_use_one_arm_and_reject_damaged_signatures(self):
        self.assertEqual(len(self.find(dataset="VAL_A", tokenizer="TOK_A")), 1)
        self.assertEqual(self.find(dataset="VAL_A", tokenizer="TOK_B"), [])
        self.assertEqual(self.find(claim="DIRECT_PAIRED"), [])
        doc = self.root / self.result
        self.write(self.result, doc.read_text(encoding="utf-8") + signature())
        catalog.refresh(self.root, self.db)
        self.assertEqual(self.find(dataset="VAL_A"), [])
        self.assertTrue(self.find("한영대응"))

    def test_staleness_and_failed_rebuild_preserve_previous_search(self):
        self.write(self.result, "# 새로운 표기\n")
        old_hits = self.find("한영대응")
        catalog.check_sources(self.root, old_hits)
        self.assertTrue(all(row["stale"] for row in old_hits))
        good_terms = (self.root / catalog.ONTOLOGY).read_text(encoding="utf-8")
        self.write(catalog.ONTOLOGY, '{"version":99}')
        with self.assertRaises(ValueError):
            catalog.refresh(self.root, self.db)
        self.assertEqual(self.find("한영대응"), [{k: v for k, v in hit.items() if k != "stale"} for hit in old_hits])
        self.write(catalog.ONTOLOGY, good_terms)
        catalog.refresh(self.root, self.db)
        self.assertEqual(self.find("한영대응"), [])
        self.assertEqual(len(self.find("새로운 표기")), 1)

    def test_existing_unowned_database_is_preserved(self):
        other = self.root / "runs/other.sqlite3"
        with closing(sqlite3.connect(other)) as db:
            db.execute("CREATE TABLE own(note TEXT)")
        before = other.read_bytes()
        with self.assertRaises(ValueError):
            catalog.refresh(self.root, other)
        self.assertEqual(other.read_bytes(), before)

    def test_review_filters_use_one_row_and_the_cases_cited_project(self):
        self.write_review()
        self.assertEqual(catalog.refresh(self.root, self.db)["method_review"], 2)
        hits = self.find("한영대응", project="p109", origin="사용자 실행 보고", preset="p109c v3", decision="미검토")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["anchor"], "case")
        self.assertEqual(hits[0]["method_reviews"], [
            {"origin": "사용자 실행 보고", "preset": "P109C v3", "decision": "미검토"},
        ])
        self.assertEqual(self.find(preset="P109C v2", origin="사용자 실행 보고"), [])
        self.assertEqual(self.find(preset="P109C v3", decision="적용"), [])
        self.assertEqual(self.find(project="P107", preset="P109C v3"), [])
        self.assertFalse(any(row["path"] == catalog.METHOD_REVIEWS.as_posix() for row in self.find(project="P109")))

    def test_review_migration_and_failed_rebuild_are_atomic(self):
        with closing(catalog.open_index(self.db, writable=True)) as db, db:
            db.execute("DROP TABLE method_review")
            db.execute("PRAGMA user_version = 1")
        self.write_review(fragment="missing-anchor")
        with self.assertRaisesRegex(ValueError, "실제 결과 근거"):
            catalog.refresh(self.root, self.db)
        with closing(catalog.open_index(self.db)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='method_review'").fetchone())
        self.write_review()
        self.assertEqual(catalog.refresh(self.root, self.db)["method_review"], 2)
        expected = self.find(preset="P109C v2")

        original = (self.root / catalog.METHOD_REVIEWS).read_text(encoding="utf-8")
        self.write(catalog.METHOD_REVIEWS, original.replace("| 적용 |", "| 성공 |"))
        with self.assertRaisesRegex(ValueError, "판정 행의 값"):
            catalog.refresh(self.root, self.db)
        self.assertEqual(self.find(preset="P109C v2"), expected)


if __name__ == "__main__":
    unittest.main()
