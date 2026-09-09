import unittest
from scripts.generate_teacher_responses import training_prompt


class TeacherPromptTests(unittest.TestCase):
    def test_reference_not_sent_to_teacher(self):
        raw = {"meta": {"split": "train"},
               "messages": [{"role": "user", "content": "질문"},
                            {"role": "assistant", "content": "정본 비공개 답"}]}
        messages = training_prompt(raw)
        self.assertEqual(messages, [{"role": "user", "content": "질문"}])

    def test_eval_material_not_packaged_as_teacher_train(self):
        with self.assertRaises(ValueError):
            training_prompt({"meta": {"split": "eval"}, "messages": []})
