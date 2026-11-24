"""Guard official KoBEST string-target audit without modifying task semantics."""
from types import SimpleNamespace
import unittest
from scripts import diag_p106b_orpo_official as module


class TargetAudit(unittest.TestCase):
    def task(self, gold, name='kobest_copa'):
        return SimpleNamespace(config=SimpleNamespace(task=name), multiple_input=False,
            eval_docs=[{'label': 1}], doc_to_target=lambda doc: gold,
            doc_to_choice=lambda doc: ['앞 문장.', '뒤 문장.'])

    def rows(self):
        return [dict(doc_id=0, filtered_resps=[(-5., False), (-1., True)], acc=1)]

    def test_official_copa_string_maps_to_exact_choice_without_task_mutation(self):
        task = self.task('뒤 문장.')
        result = module.audit_task(task, self.rows(), 1)
        self.assertEqual(result['correct'], 1)
        self.assertEqual(task.doc_to_target({}), '뒤 문장.')

    def test_integer_gold_is_preserved(self):
        self.assertEqual(module.audit_task(self.task(1), self.rows(), 1)['correct'], 1)

    def test_no_fuzzy_string_or_numeric_string_coercion(self):
        for value in ('뒤 문장', '1', '뒤 문장. ', '없는 문장.'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.audit_task(self.task(value), self.rows(), 1)

    def test_bool_is_not_an_integer_label(self):
        with self.assertRaises(ValueError):
            module.audit_task(self.task(True), self.rows(), 1)

    def test_core6_integer_only_contract_is_not_relaxed(self):
        with self.assertRaises(ValueError):
            module.audit_task(self.task('뒤 문장.', 'arc_easy'), self.rows(), 1)


if __name__ == '__main__':
    unittest.main()
