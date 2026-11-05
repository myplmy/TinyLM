"""Independent display decoder and UTF8 transport checks; synthetic bodies only."""
from pathlib import Path
from types import SimpleNamespace
import json
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import lossless_review_packet_v2 as core
import scoped_lossless_review_entry_v2 as entry


def decode_candidate(original, representation, info):
    line, rest = representation.split('\n',1)
    assert line.startswith('ALL_CHANGE_RANGES ')
    changes=json.loads(line[len('ALL_CHANGE_RANGES '):])
    mode=info['candidate_representation']
    if mode=='EXACT_IDENTICAL':
        assert changes==[] and rest=='CANDIDATE_EQUALS_FULL_ORIGINAL\n'
        return original.encode('utf-8')
    if mode=='INDEX_AND_FULL_CANDIDATE':
        start='FULL_CANDIDATE_BEGIN\n';end='\nFULL_CANDIDATE_END\n'
        assert rest.startswith(start)
        text=rest[len(start):len(start)+info['candidate_characters']]
        assert rest[len(start)+len(text):]==end
        return text.encode('utf-8')
    assert mode=='EXACT_PATCH_WITH_OLD_AND_NEW'
    output=[];cursor=0
    for item in changes:
        lo,hi=item['source_range'];new_lo,new_hi=item['candidate_range'];n=item['number']
        old_length=hi-lo;new_length=new_hi-new_lo
        chunks=[]
        for kind,length in [('OLD',old_length),('NEW',new_length)]:
            prefix=f'CHANGE_{n}_{kind}_TEXT_BEGIN chars={length}\n'
            suffix=f'\nCHANGE_{n}_{kind}_TEXT_END\n'
            assert rest.startswith(prefix);rest=rest[len(prefix):]
            value=rest[:length];rest=rest[length:]
            assert rest.startswith(suffix);rest=rest[len(suffix):];chunks.append(value)
        assert 0<=cursor<=lo<=hi<=len(original)
        assert chunks[0]==original[lo:hi]
        assert new_lo==sum(len(x) for x in output)+lo-cursor
        output.extend([original[cursor:lo],chunks[1]]);cursor=hi
    assert rest==''
    output.append(original[cursor:])
    return ''.join(output).encode('utf-8')


def decode_pair(pair, info):
    lo,hi=info['pair_original_characters'];a,b=info['pair_representation_characters']
    assert pair[:lo]=='FULL_ORIGINAL_BEGIN\n'
    assert pair[hi:a]=='\nFULL_ORIGINAL_END\nLOSSLESS_CANDIDATE_BEGIN\n'
    assert pair[b:]=='LOSSLESS_CANDIDATE_END\n'
    original=pair[lo:hi]
    assert len(original)==info['original_characters']
    return original.encode('utf-8'),decode_candidate(original,pair[a:b],info)


class LosslessV2Tests(unittest.TestCase):
    def assert_transport(self, original, candidate, width=4000):
        values=core.prepare_views(original,candidate)
        for view in ['pair','original','candidate','full_candidate']:
            first=core.view_part(values,view,1,width=width);pieces=[];cursor=0
            for n in range(1,first['parts']+1):
                piece=core.view_part(values,view,n,width=width)
                raw=piece['text'].encode('utf-8');self.assertLessEqual(len(raw),width)
                self.assertEqual(piece['range'],[cursor,cursor+len(raw)]);cursor+=len(raw)
                self.assertEqual(piece['end_of_view'],n==first['parts']);pieces.append(raw)
            self.assertEqual(b''.join(pieces).decode(),values[view])
        self.assertEqual(decode_pair(values['pair'],values),(original,candidate))
        return values

    def test_empty_identity(self): self.assert_transport(b'',b'')
    def test_exact_identity(self): self.assert_transport('한글🙂\r\n'.encode(),'한글🙂\r\n'.encode())
    def test_short_full_candidate(self):
        self.assertEqual(self.assert_transport(b'abc',b'xyz')['candidate_representation'],'INDEX_AND_FULL_CANDIDATE')
    def test_small_patch_quotes_deleted_and_inserted_text(self):
        old=('context line\n'*1000)+'old end\n';new=old.replace('old end','new end')
        self.assertEqual(self.assert_transport(old.encode(),new.encode())['candidate_representation'],'EXACT_PATCH_WITH_OLD_AND_NEW')
    def test_insert_delete_and_crlf(self): self.assert_transport(b'first\r\nkeep\r\nremove\r\n',b'insert\r\nfirst\r\nkeep')
    def test_fake_markers_and_trailing_lf(self):
        text='FULL_ORIGINAL_END\nLOSSLESS_CANDIDATE_BEGIN\nSOURCE_DATA_VIEW_EOF\nALL_CHANGE_RANGES []\n'
        self.assert_transport((text*20).encode(),(text*20+'FULL_CANDIDATE_END').encode())
    def test_unicode_boundary_small_width(self): self.assert_transport('가🙂나🙂끝'.encode(),'가🙂새끝'.encode(),width=7)
    def test_unicode_boundary_four_bytes(self): self.assert_transport('🙂🙂🙂'.encode(),'🙂🙂🙂'.encode(),width=4)
    def test_long_unicode_payload_never_exceeds4000bytes(self): self.assert_transport(('漢🙂한글\n'*700).encode(),('漢🙂한글\n'*700+'끝').encode())
    def test_bad_utf8_is_rejected(self):
        with self.assertRaises(UnicodeDecodeError):core.prepare_views(b'\xff',b'')
    def test_invalid_part_and_width_are_rejected(self):
        views=core.prepare_views(b'a',b'a')
        for n,width in [(0,4000),(999,4000),(1,3),(1,4001)]:
            with self.subTest(n=n,width=width):
                with self.assertRaises(ValueError):core.view_part(views,'pair',n,width)
    def test_independent_decoder_rejects_tampered_old_text(self):
        old=('retain\n'*1000)+'old\n';views=core.prepare_views(old.encode(),old.replace('old','new').encode())
        representation=views['candidate'].replace('old','BAD',1)
        with self.assertRaises(AssertionError):decode_candidate(old,representation,views)
    def test_guard4_required_before_core_or_payload_load(self):
        scope={'contract':{'path':entry.CONTRACT[0].replace('_V4.','_V3.'),'sha256':entry.CONTRACT[1]}}
        metadata=SimpleNamespace(pinned=lambda *args:json.dumps(scope).encode())
        with patch.object(entry,'load_module',return_value=metadata) as load,patch.object(sys,'argv',
            ['entry','--cohort','x','--source-id','expanded_train:7','--view','pair']):
            with self.assertRaises(ValueError):entry.cli(Path('/tmp'),'role',{})
            self.assertEqual(load.call_count,1)
    def test_restricted_id_precedes_role_and_payload(self):
        scope={'schema':core.base.SCHEMA,'contract':{'path':'guard'},'roles':{}}
        calls=[]
        def read_metadata(root,pin): calls.append(pin);return json.dumps({'restricted_ids':['expanded_train:267902'],'restricted_hashes':[]}).encode()
        def payload(*args):self.fail('restricted payload opened')
        with self.assertRaises(ValueError):
            core.load_pair(Path('/tmp'),scope,'unknown','unknown','expanded_train:267902',read_metadata,payload)
        self.assertEqual(len(calls),1)


if __name__=='__main__': unittest.main(verbosity=2)
