"""Prove wrong IDs, tampering and path escapes cannot emit source contents."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('scoped_reader',HERE/'scoped_packet_reader_v1.py')
reader=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ScopedReaderTests(unittest.TestCase):
    def fixture(self, directory, relative='packets/one.txt'):
        root=Path(directory);(root/'packets').mkdir()
        packet=root/'packets/one.txt';packet.write_text('가나다ABC'*1001,encoding='utf-8')
        data=dict(allowed_packet_directory='packets',sources={'fixture:one':[
            dict(path=relative,sha256=reader.sha(packet.read_bytes()))]})
        registry=root/'registry.json';registry.write_text(json.dumps(data),encoding='utf-8')
        return root,packet,registry,reader.sha(registry.read_bytes())

    def test_all_pieces_reconstruct_exact_unicode_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory)
            pieces=[reader.read_piece(r,h,root,'fixture:one',1,n) for n in range(1,5)]
            self.assertEqual(''.join(p['text'] for p in pieces),packet.read_text())
            self.assertEqual([p['packet_complete'] for p in pieces],[False,False,False,True])

    def test_unknown_id_is_rejected_before_any_packet_open(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory);opened=[]
            original=Path.read_bytes
            def guarded(path):
                opened.append(path)
                return original(path)
            with patch.object(Path,'read_bytes',guarded):
                with self.assertRaises(ValueError):reader.read_piece(r,h,root,'other:role',1,1)
            self.assertEqual(opened,[r])

    def test_changed_registry_is_rejected_before_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory);r.write_text('{}')
            with self.assertRaises(ValueError):reader.read_piece(r,h,root,'fixture:one',1,1)

    def test_changed_packet_cannot_emit_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory);packet.write_text('altered')
            with self.assertRaises(ValueError):reader.read_piece(r,h,root,'fixture:one',1,1)

    def test_outside_registry_path_is_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory,'../private.txt')
            with self.assertRaises(ValueError):reader.read_piece(r,h,root,'fixture:one',1,1)

    def test_symlink_even_inside_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory,'packets/link.txt')
            (root/'packets/link.txt').symlink_to(packet)
            with self.assertRaises(ValueError):reader.read_piece(r,h,root,'fixture:one',1,1)

    def test_out_of_range_packet_and_piece_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory)
            for packet_number,piece in [(0,1),(2,1),(1,0),(1,99)]:
                with self.assertRaises(ValueError):reader.read_piece(r,h,root,'fixture:one',packet_number,piece)

    def test_symlink_registry_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory)
            link=root/'registry_link.json';link.symlink_to(r)
            with self.assertRaises(ValueError):reader.read_piece(link,h,root,'fixture:one',1,1)

    def test_symlink_packet_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root,packet,r,h=self.fixture(directory)
            (root/'directory_link').symlink_to(root/'packets',target_is_directory=True)
            data=json.loads(r.read_text());data['allowed_packet_directory']='directory_link'
            data['sources']['fixture:one'][0]['path']='directory_link/one.txt'
            r.write_text(json.dumps(data));h=reader.sha(r.read_bytes())
            with self.assertRaises(ValueError):reader.read_piece(r,h,root,'fixture:one',1,1)


if __name__=='__main__':unittest.main()
