#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from tokenizers import Tokenizer
from scripts import diag_p106b_original_qa3_runtime_v2 as c


class Consumers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r,cls.rows,cls.labels=c.frozen.read_course()
        cls.tok=Tokenizer.from_file(str(c.training.data.TOKENIZER))

    def test_all_actual_train_development_and_native_consumers(self):
        observation,dev=c.validate_consumers(self.r,self.rows,self.labels)
        self.assertEqual(observation['train_label_count'],3072)
        self.assertEqual(observation['train_lookup_per_epoch'],dict(first=[3072]*4,three=[3072]*4))
        self.assertEqual(len(dev),512);self.assertEqual(observation['original_producer_messages'],640)
        self.assertEqual([observation['development_counts'][k]['rows'] for k in ('dev_natural_three','dev_code','dev_fiction')],[246,640,1024])
        self.assertFalse(observation['cuda_initialized']);self.assertTrue(observation['native']['reader_verified'])

    def test_wrong_producer_dev_list_reproduces_original_failure(self):
        b=c.prior.data.binding
        with self.assertRaisesRegex(ValueError,'exact approved producer'):
            c.prior.data.known_contract(self.rows['dev_code'],self.tok,b.approved_questions('dev'))

    def test_question_and_trusted_metadata_mutation_rejected(self):
        altered=copy.deepcopy(self.rows['dev_code']);altered[0]['messages'][0]['content'][0]['text']+=' changed'
        with self.assertRaisesRegex(ValueError,'original640'):c.development_labels(altered,self.tok)
        altered=copy.deepcopy(self.rows['dev_code']);altered[0]['meta']['first_value']='untrusted'
        with self.assertRaisesRegex(ValueError,'untrusted producer metadata'):c.development_labels(altered,self.tok)

    def test_train_label_mutation_rejected_before_cuda(self):
        altered=copy.deepcopy(self.labels);key=next(iter(altered));altered[key]['bit']^=1
        with self.assertRaisesRegex(ValueError,'unchanged train3072'):c.validate_consumers(self.r,self.rows,altered)

    def test_new_outputs_preserved_old_dataset(self):
        self.assertEqual(c.CORPUS,c.frozen.CORPUS);self.assertNotEqual(c.TAG,c.frozen.TAG)
        self.assertNotEqual(c.EVIDENCE,c.frozen.EVIDENCE);self.assertFalse(c.info()['formal_train_ready'])

    def test_hash_serialization_mismatch_is_not_a_missing_label(self):
        row=self.rows['dev_code'][0]
        self.assertNotEqual(c.factory.sha(row['messages']),c.conversation_signature(row['messages']))
        self.assertEqual(len(c.development_labels(self.rows['dev_code'],self.tok)),512)


if __name__=='__main__':unittest.main()
