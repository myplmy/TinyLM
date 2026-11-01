"""Current source-structure counters plus all prior policy regressions."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v22 as policy
from scripts import p106b_hold_resolution_structure_v2 as structure
from scripts import test_p106b_hold_resolution_policy_v21 as inherited


class ExplicitSourceStructures(unittest.TestCase):
    def value(self, text):
        return policy.propose(dict(id="expanded_train:987654321", text=text, complete_eos=True, valid_utf8=True))

    def test_python_full_module_repetitions_are_preserved_code(self):
        text = "import sys\n\ndef first():\n    print('same')\n\ndef second():\n    print('same')\n"
        self.assertTrue(structure.complete_source_program(text))
        result = self.value(text)
        self.assertNotIn("MAIN_BODY_REPETITION_REQUIRES_CONTEXT", result["reasons"])
        self.assertEqual(result.get("candidate", result["text"]), text)

    def test_prose_near_a_program_is_not_a_whole_program(self):
        text = "This paragraph announces a program.\nimport sys\nprint()\n"
        self.assertFalse(structure.complete_source_program(text))
        self.assertIn("GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL",
                      policy.structural_reasons(text, {"GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL"}))

    def test_whole_code_can_contain_real_empty_calls_without_deleting_them(self):
        text = "import datetime\nvalue = datetime.date.today()\n"
        result = self.value(text)
        self.assertIn("today()", result.get("candidate", result["text"]))
        self.assertNotIn("UNRESOLVED_FIELD_OR_TITLE", result["reasons"])

    def test_pure_python_names_do_not_masquerade_as_an_actual_program(self):
        self.assertFalse(structure.complete_source_program("First\nSecond\nFirst\n"))

    def test_broken_python_and_unclosed_c_do_not_get_program_proof(self):
        self.assertFalse(structure.complete_source_program("def work(:\n    print()\n"))
        self.assertFalse(structure.complete_source_program("int work(void) { return 0;\n"))

    def test_two_typed_c_functions_keep_repeated_statements(self):
        text = "int first(void) { return 0; }\nint second(void) { return 0; }\n"
        self.assertTrue(structure.complete_source_program(text))
        self.assertFalse(structure.complete_source_program("Unknown prose\n" + text))

    def test_known_include_forms_do_not_require_loading_headers(self):
        for include in ['#include <stdio.h>\n', '#include "local.h"\n']:
            self.assertTrue(structure.complete_source_program(include + "int main(void) { return 0; }\n"))

    def test_program_proof_does_not_clear_actual_biography_or_measurement_risks(self):
        text = "import sys\nprint()\n"
        reasons = {"MAIN_BODY_REPETITION_REQUIRES_CONTEXT", "INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED",
                   "OBSERVED_MISSING_MEASURED_QUANTITY"}
        self.assertEqual(policy.structural_reasons(text, reasons), {
            "INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED", "OBSERVED_MISSING_MEASURED_QUANTITY"})

    def sparse(self):
        return '{| class="wikitable"\n! 항목 !! 첫 값 !! 둘째 값\n|-\n| 가람 || 7 ||\n|-\n| 누리 || || 9\n|}\n'

    def test_explicit_sparse_axes_preserve_every_blank_and_value(self):
        text = self.sparse()
        self.assertFalse(structure.ORIGINAL_FILLED_TABLE([line.strip() for line in text.splitlines()]))
        self.assertTrue(structure.complete_tables_with_explicit_blanks(text))
        result = self.value(text)
        self.assertEqual(result.get("candidate", result["text"]), text)
        self.assertNotIn("BROKEN_TABLE_OR_WIKI_MARKUP", result["reasons"])
        self.assertNotIn("INDEPENDENT_PROSE_NOT_ESTABLISHED", result["reasons"])
        self.assertNotIn("P106B_VALIDATION_ONLY", result.get("candidate", result["text"]))

    def test_unlabelled_rows_and_empty_records_are_not_sparse_record_proof(self):
        self.assertFalse(structure.complete_tables_with_explicit_blanks(self.sparse().replace("| 가람 || 7 ||", "| || 7 ||")))
        self.assertFalse(structure.complete_tables_with_explicit_blanks(self.sparse().replace("| 가람 || 7 ||", "| 가람 || ||")))

    def test_missing_column_and_missing_table_boundary_stay_unproved(self):
        self.assertFalse(structure.complete_tables_with_explicit_blanks(self.sparse().replace("! 항목 !! 첫 값 !! 둘째 값", "! 항목 !! !! 둘째 값")))
        self.assertFalse(structure.complete_tables_with_explicit_blanks(self.sparse().replace("|}", "")))

    def test_unmatched_or_duplicate_axis_and_merged_cells_stay_unproved(self):
        self.assertFalse(structure.complete_tables_with_explicit_blanks(self.sparse().replace("둘째 값", "첫 값")))
        self.assertFalse(structure.complete_tables_with_explicit_blanks(self.sparse().replace("| 가람 || 7 ||", '| rowspan="2" | 가람 || 7 ||')))

    def test_table_proof_does_not_clear_a_repeat_in_outside_prose(self):
        text = "Repeated actual prose.\nRepeated actual prose.\n" + self.sparse()
        self.assertFalse(structure.complete_source_table_body(text))
        self.assertIn("MAIN_BODY_REPETITION_REQUIRES_CONTEXT",
                      policy.structural_reasons(text, {"MAIN_BODY_REPETITION_REQUIRES_CONTEXT"}))

    def test_typed_named_definition_removes_only_its_empty_alias(self):
        text = "힐베르트 공간()은 완비 내적 공간이다.\n"
        clean, changes = policy.typed_initial_alias(text)
        self.assertEqual(clean, "힐베르트 공간은 완비 내적 공간이다.\n")
        self.assertEqual([row["original"] for row in changes], ["()"])

    def test_value_placeholder_function_call_and_parenthesis_teaching_are_not_aliases(self):
        for text in ["공간()은 공간이다.\n", "거리()는 측정값이다.\n", "sprintf()는 출력 함수이다.\n",
                     "특수 공간()은 빈 인수 괄호의 문법을 설명하는 공간이다.\n"]:
            self.assertEqual(policy.typed_initial_alias(text), (text, []))

    def test_a_real_parameter_or_later_call_cannot_borrow_alias_proof(self):
        text = "힐베르트 공간(x)은 완비 내적 공간이다.\n"
        self.assertEqual(policy.typed_initial_alias(text), (text, []))
        fence = chr(96) * 3
        raw = "힐베르트 공간()은 완비 내적 공간이다.\n" + fence + "c\nint work(void) { return step(); }\n" + fence + "\n"
        self.assertFalse(policy.code_preserved(raw, raw.replace("step()", "step")))


if __name__ == "__main__":
    modules, pending = [], [inherited]
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.append(module)
        pending.extend(value for name in ["inherited", "local_inherited", "structure_tests", "preservation_tests"]
                       if (value := getattr(module, name, None)) is not None)
    classes = [ExplicitSourceStructures]
    for module in modules:
        classes += [(inherited.RetainedStyleInsteadOfRenderedLoss if value.__name__ == "SourceValuePreservation" else value)
                    for value in vars(module).values() if isinstance(value, type)
                    and issubclass(value, unittest.TestCase) and value.__module__ == module.__name__]
    classes = list(dict.fromkeys(classes))
    with ExitStack() as stack:
        for module in modules:
            if hasattr(module, "policy"):
                stack.enter_context(patch.object(module, "policy", policy))
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in classes])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
