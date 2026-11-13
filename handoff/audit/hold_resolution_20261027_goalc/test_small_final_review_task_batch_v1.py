"""Check complete dual views, pre-I/O scope gates and bounded deferrals."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock,patch
import copy
import json
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import small_final_review_task_batch_v1 as current
import lossless_review_packet_v3 as actual


class SmallFinalTaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.role='legacy_review';self.cohort='remaining_field_title_page_016_counter_v1'
        self.folder=self.root/actual.base.DATA_ROOT/'agents'/self.role/self.cohort;self.folder.mkdir(parents=True)
        self.inputs=self.root/actual.base.DATA_ROOT/'test_inputs';self.inputs.mkdir()
        self.contexts={};self.items=[]
        for ordinal in range(12,17):
            ident='expanded_train:'+str(ordinal);source=('이름'+str(ordinal)+'()은 본문이다.'+chr(10)*2+'각주'+chr(10)).encode('utf-8');final=('이름'+str(ordinal)+'은 본문이다.'+chr(10)).encode('utf-8')
            original=self.inputs/(str(ordinal)+'.txt');original.write_bytes(source);name='expanded_train_'+str(ordinal)+'_edited_v1.txt';(self.folder/name).write_bytes(final)
            pin=dict(path=str(original.relative_to(self.root)),sha256=actual.base.digest(source))
            self.contexts[ident]=dict(source_id=ident,role=self.role,cohort=self.cohort,original=pin,candidate=dict(pin))
            self.items.append((ident,name,actual.base.digest(final)))
        self.core=SimpleNamespace(base=actual.base,require=actual.require,ordered_anchors=actual.ordered_anchors,
            resolve_assignment=lambda _root,_scope,_role,_cohort,ident,_reader:copy.deepcopy(self.contexts[ident]))
        self.contract=dict(restricted_ids=[],restricted_hashes=['F'*64],trusted_metadata={})

    def collect(self,items=None,read=None):
        return current.collect(self.root,self.role,self.cohort,items or self.items,self.core,{},None,self.contract,read)

    def test_five_small_finals_and_all_changes_are_complete(self):
        packets,result=self.collect();self.assertEqual(len(packets),5)
        for packet in packets:
            self.assertTrue(packet['exact_final_byte_reconstruction'])
            self.assertEqual(packet['views']['final'].encode('utf-8'),(self.root/packet['final']['path']).read_bytes())
            self.assertTrue(packet['views']['changes'].endswith('ALL_EXACT_CHARACTER_CHANGES_END'+chr(10)))
        output=current.render(self.role,self.cohort,packets,result,{})
        end=json.loads(output.splitlines()[-1].split(' ',1)[1])
        self.assertEqual(len(end['completed_final_and_all_changes_ids']),5)
        self.assertEqual(output.count('SOURCE_DATA_VIEW_EOF'),10)
        self.assertLessEqual(len(output.encode('utf-8')),18000)

    def test_all_ids_and_three_sha_gates_precede_payload_reads(self):
        for field in ['original','candidate']:
            self.contexts[self.items[-1][0]][field]['sha256']='F'*64;read=Mock()
            with self.assertRaises(ValueError):self.collect(read=read)
            read.assert_not_called()
            self.contexts[self.items[-1][0]][field]['sha256']=self.contexts[self.items[-1][0]]['original' if field=='candidate' else 'candidate']['sha256']
        items=list(self.items);items[-1]=(*items[-1][:2],'F'*64);read=Mock()
        with self.assertRaises(ValueError):self.collect(items,read)
        read.assert_not_called()

    def test_duplicate_ids_and_foreign_output_are_rejected_before_reads(self):
        for items in [[self.items[0],self.items[0]],[(self.items[0][0],'expanded_train_999_final.txt',self.items[0][2])]]:
            read=Mock()
            with self.assertRaises(ValueError):self.collect(items,read)
            read.assert_not_called()

    def test_large_final_is_deferred_without_source_or_final_payload_read(self):
        ident,name,_=self.items[0];raw=('가'*2000).encode('utf-8');(self.folder/name).write_bytes(raw);read=Mock()
        packets,result=self.collect([(ident,name,actual.base.digest(raw))],read)
        self.assertEqual(packets,[]);read.assert_not_called()
        self.assertFalse(result['deferred'][0]['payload_pair_loaded'])

    def test_budget_deferral_prints_no_partial_view_or_false_eof(self):
        with patch.object(current,'MAX_BODY_BYTES',1):packets,result=self.collect([self.items[0]])
        output=current.render(self.role,self.cohort,packets,result,{})
        self.assertNotIn('SOURCE_DATA_VIEW_EOF',output)
        end=json.loads(output.splitlines()[-1].split(' ',1)[1]);self.assertEqual(end['completed_final_and_all_changes_ids'],[])
        self.assertEqual(end['prepared_but_not_returned_ids'],[self.items[0][0]])

    def test_changed_final_sha_fails_before_any_print(self):
        items=[(*self.items[0][:2],'A'*64)]
        with self.assertRaises(ValueError):self.collect(items)

    def test_render_cap_uses_whole_packets_only(self):
        packets,result=self.collect()
        with patch.object(current,'MAX_OUTPUT_BYTES',4000):output=current.render(self.role,self.cohort,packets,result,{})
        end=json.loads(output.splitlines()[-1].split(' ',1)[1]);count=len(end['completed_final_and_all_changes_ids'])
        self.assertLess(count,5);self.assertEqual(output.count('SOURCE_DATA_VIEW_EOF'),count*2)
        self.assertLessEqual(len(output.encode('utf-8')),4000)


if __name__=='__main__':unittest.main()
