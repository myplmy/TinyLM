"""Prove the YAML-dict rename does not change official evaluation semantics."""
import ast
import copy
import hashlib
import json
import os
import unittest
from pathlib import Path
from scripts import diag_p108_frozen_edit_official as owner

ROOT=Path(__file__).resolve().parents[1]


class TaskFieldsTests(unittest.TestCase):
    def test_change_is_only_alpha_renaming_of_local_yaml_dictionary(self):
        record=json.loads((ROOT/'handoff/audit/nov16_p108b/SOURCE_ORPO_TASK_FIELDS_v1.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(record['text'].encode('utf-8')).hexdigest().upper(),record['sha256'])
        before=ast.parse(record['text']);after=ast.parse((ROOT/record['path']).read_text(encoding='utf-8'))
        for node in ast.walk(after):
            if isinstance(node,ast.Name)and node.id=='task_fields':node.id='config'
        self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False))

    def test_current_official11_task_specs_and_denominators_match_closed_original(self):
        os.environ.update(owner.official.OFFLINE,HF_EVALUATE_OFFLINE='1')
        tasks,specs,provenance=owner.prepare_tasks()
        closed=json.loads((owner.OUTPUT/'original/report.json').read_text(encoding='utf-8'))
        self.assertEqual(specs,closed['task_specs'])
        self.assertEqual({name:len(task.eval_docs)for name,task in tasks.items()},closed['actual_counts'])
        self.assertEqual(len(tasks),11)


if __name__=='__main__':unittest.main()
