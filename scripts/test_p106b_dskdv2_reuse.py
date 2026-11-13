import copy
import unittest
from scripts.p106b_dskdv2_reuse import reusable


class ReuseContracts(unittest.TestCase):
    def row(self):return dict(semantic_root_id='root',source_row_sha256='source',record_sha256='record',language='ko',packed=dict(text='text',student=dict(ids=[1,2],labels=[-100,2],turn_ids=[0,1])),teacher=dict(ids=[3,4]))
    def test_same_original_source_can_reuse_despite_new_inventory_id(self):
        a=self.row();b=copy.deepcopy(a);a['row_id']='new';b['row_id']='old';self.assertTrue(reusable(a,b))
    def test_different_root_is_not_reused(self):
        a=self.row();b=self.row();b['semantic_root_id']='different';self.assertFalse(reusable(a,b))
    def test_changed_source_with_same_root_is_rejected(self):
        a=self.row();b=self.row();b['source_row_sha256']='changed'
        with self.assertRaises(ValueError):reusable(a,b)
    def test_changed_teacher_input_is_rejected(self):
        a=self.row();b=self.row();b['teacher']['ids']=[3,5]
        with self.assertRaises(ValueError):reusable(a,b)
    def test_changed_student_owner_is_rejected(self):
        a=self.row();b=self.row();b['packed']['student']['turn_ids'][1]=2
        with self.assertRaises(ValueError):reusable(a,b)
    def test_incomplete_identity_is_rejected(self):
        with self.assertRaises(ValueError):reusable({},self.row())


if __name__=='__main__':unittest.main()
