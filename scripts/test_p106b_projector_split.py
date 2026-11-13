import unittest
from scripts.p106b_projector_split import split_by_root


class RootSplitContracts(unittest.TestCase):
    def rows(self):return [dict(row_id=str(i)+l,semantic_root_id=f'{i:064x}',language=l)for i in [5,6,10,11]for l in ['ko','en']]
    def test_same_declared_root_siblings_stay_together(self):
        r=split_by_root(self.rows());self.assertEqual(set(r['dev']),{'5ko','5en','10ko','10en'})
    def test_order_does_not_change_membership(self):
        a=split_by_root(self.rows());b=split_by_root(list(reversed(self.rows())))
        for k in a:self.assertEqual(set(a[k]),set(b[k]))
    def test_duplicate_row_is_rejected(self):
        rows=self.rows();rows.append(rows[0])
        with self.assertRaises(ValueError):split_by_root(rows)
    def test_missing_or_malformed_root_is_rejected(self):
        rows=self.rows();rows[0]['semantic_root_id']='unknown'
        with self.assertRaises(ValueError):split_by_root(rows)
    def test_absent_language_or_empty_fold_is_rejected(self):
        for rows in [[],[r for r in self.rows()if r['language']=='ko'],[r for r in self.rows()if r['semantic_root_id'].endswith('6')]]:
            with self.assertRaises(ValueError):split_by_root(rows)


if __name__=='__main__':unittest.main()
