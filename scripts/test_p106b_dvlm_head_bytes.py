"""Byte-exact optional mapping and preservation of strict failures; model0."""
import copy,unittest
from scripts import p106b_dvlm_head_bytes as core
from scripts.p106b_dvlm_head import initialization_map
from scripts.p106b_dvlm_pts import AdmissionHold

def raw(vocab,added=()):return dict(model=dict(type='BPE',vocab=vocab),decoder=dict(type='ByteLevel'),added_tokens=list(added))
def initial(student,teacher):
    return initialization_map(student,teacher,decode_student=lambda _: '',
        encode_teacher=lambda _: [],decode_teacher=lambda _: '')

class HeadBytesContracts(unittest.TestCase):
    def test_byte_fragment_is_recovered_without_lossy_unicode_and_original_map_is_unchanged(self):
        student=raw({'a':0,'\u00c3\u00c2':1});teacher=raw({'a':0,'\u00c3':1,'\u00c2':2})
        original=initial(student,teacher);saved=copy.deepcopy(original)
        result=core.extend_invalid_utf8(original,student,teacher,bpe_tokenize=lambda s:[1,2])
        self.assertEqual(original,saved);self.assertTrue(result['complete'])
        self.assertEqual(result['records'][0],saved['records'][0])
        self.assertEqual(result['records'][1]['teacher_ids'],[1,2])
        self.assertEqual(result['changes'][0]['bytes_hex'],'C3C2')
        self.assertFalse(result['adoption']);self.assertFalse(result['HPA_gate_changed'])
    def test_lossy_repair_wrong_order_unknown_empty_and_added_ids_are_rejected(self):
        student=raw({'\u00c3\u00c2':0});teacher=raw({'\u00c3':0,'\u00c2':1,'X':2},[dict(id=2,content='X',special=True)])
        original=initial(student,teacher)
        for ids in ([],[1,0],[0],[99],[2],[True]):
            with self.subTest(ids=ids),self.assertRaises(AdmissionHold):
                core.extend_invalid_utf8(original,student,teacher,bpe_tokenize=lambda s:ids)
    def test_non_utf8_hold_reason_is_not_rescued(self):
        student=raw({'\u00c3\u00c2':0});teacher=raw({'\u00c3':0,'\u00c2':1})
        original=initial(student,teacher);original['records'][0]['reason']='AMBIGUOUS_SHARED_NATIVE_PIECE'
        result=core.extend_invalid_utf8(original,student,teacher,bpe_tokenize=lambda s:self.fail('no rescue'))
        self.assertEqual(result['records'],original['records']);self.assertFalse(result['complete'])
    def test_invalid_utf8_reason_on_valid_text_fails_instead_of_silent_policy_change(self):
        student=raw({'ab':0});teacher=raw({'a':0,'b':1})
        original=initial(student,teacher);original['records'][0]['reason']='UnicodeDecodeError: fabricated'
        with self.assertRaises(AdmissionHold):core.extend_invalid_utf8(original,student,teacher,bpe_tokenize=lambda s:[0,1])
    def test_direct_real_bpe_works_in_encoded_bytelevel_space(self):
        from tokenizers.models import BPE
        student=raw({'\u00c3\u00c2':0});teacher=raw({'\u00c3':0,'\u00c2':1})
        tokenizer=BPE(vocab=teacher['model']['vocab'],merges=[])
        result=core.extend_invalid_utf8(initial(student,teacher),student,teacher,
            bpe_tokenize=lambda spelling:[token.id for token in tokenizer.tokenize(spelling)])
        self.assertEqual(result['records'][0]['teacher_ids'],[0,1]);self.assertTrue(result['complete'])

if __name__=='__main__':unittest.main()
