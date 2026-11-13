"""In-memory CPU contracts. No real checkpoint deletion or model execution."""
from collections import OrderedDict
import copy
import io
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import torch

from scripts import checkpoint_optimizer_archive as codec
from scripts import cleanup_optimizer_archive as cleaner


def fixture():
    storage = torch.arange(12, dtype=torch.float32)
    model = OrderedDict(weight=storage.reshape(3, 4), tied=storage.reshape(3, 4),
                        transposed=storage.reshape(3, 4).T)
    model._metadata = {'': {'version': 1}}
    return dict(model=model, cfg=dict(dim=4, name='original'), step=17,
        opt=dict(state={0:dict(exp_avg=torch.ones(12), exp_avg_sq=torch.ones(12)*2)}),
        opt_muon=dict(momentum=torch.ones(12)*3),
        training_only_auxiliary=dict(mtp=torch.arange(4, dtype=torch.bfloat16)),
        tokenizer_sha256='A'*64, metadata=(None, True, 7, -0., b'original'))


def roundtrip(value):
    stream = io.BytesIO()
    torch.save(value, stream)
    stream.seek(0)
    return torch.load(stream, map_location='cpu', weights_only=True)


class ArchiveTests(unittest.TestCase):
    def test_only_optimizer_root_fields_removed(self):
        original = fixture()
        retained, removed = codec.retained_payload(original)
        self.assertEqual(removed, ['opt', 'opt_muon'])
        self.assertEqual(set(retained), set(original)-set(removed))
        self.assertIn('training_only_auxiliary', retained)
        self.assertIn('opt', original)

    def test_ordered_root_attributes_preserved(self):
        original = OrderedDict(fixture())
        original.extra = dict(version=2)
        retained, _ = codec.retained_payload(original)
        self.assertIs(type(retained), OrderedDict)
        self.assertEqual(retained.extra, original.extra)
        self.assertEqual(codec.fingerprint(retained), codec.fingerprint(roundtrip(retained)))

    def test_retained_graph_roundtrip_bytes_views_and_aliases(self):
        retained, _ = codec.retained_payload(fixture())
        result = roundtrip(retained)
        self.assertEqual(codec.fingerprint(retained), codec.fingerprint(result))
        self.assertEqual(result['model']['weight'].untyped_storage()._cdata,
                         result['model']['tied'].untyped_storage()._cdata)
        self.assertEqual(result['model']._metadata, retained['model']._metadata)

    def test_fingerprint_detects_tensor_mutation(self):
        retained, _ = codec.retained_payload(fixture())
        result = roundtrip(retained)
        result['model']['weight'][0, 0] += 1
        self.assertNotEqual(codec.fingerprint(retained), codec.fingerprint(result))

    def test_fingerprint_detects_lost_alias(self):
        retained, _ = codec.retained_payload(fixture())
        result = roundtrip(retained)
        result['model']['tied'] = result['model']['tied'].clone()
        self.assertNotEqual(codec.fingerprint(retained), codec.fingerprint(result))

    def test_fingerprint_detects_metadata_and_dtype_changes(self):
        retained, _ = codec.retained_payload(fixture())
        result = roundtrip(retained)
        result['cfg']['dim'] = 8
        self.assertNotEqual(codec.fingerprint(retained), codec.fingerprint(result))
        result = roundtrip(retained)
        result['training_only_auxiliary']['mtp'] = result['training_only_auxiliary']['mtp'].float()
        self.assertNotEqual(codec.fingerprint(retained), codec.fingerprint(result))

    def test_signed_zero_and_nan_tensor_bits_survive(self):
        value = dict(values=torch.tensor([0, -2147483648, 2143289345], dtype=torch.int32).view(torch.float32),
                     positive_zero=0., negative_zero=-0., special=float('nan'))
        self.assertEqual(codec.fingerprint(value), codec.fingerprint(roundtrip(value)))
        other = dict(value, negative_zero=0.)
        self.assertNotEqual(codec.fingerprint(value), codec.fingerprint(other))

    def test_metadata_counts_combined_optimizer_and_preserves_shared_storage(self):
        original = fixture()
        original['opt']['same_model'] = original['model']['weight']
        stream = io.BytesIO()
        torch.save(original, stream)
        stream.seek(0)
        meta = codec.metadata(stream)
        self.assertEqual(meta['optimizer_fields'], ['opt', 'opt_muon'])
        self.assertEqual(meta['optimizer_exclusive_bytes'], 3*12*4)

    def test_reject_optimizer_free_and_incomplete_checkpoint(self):
        with self.assertRaises(ValueError):codec.retained_payload(dict(model={}, cfg={}, step=1))
        with self.assertRaises(ValueError):codec.retained_payload(dict(model={}, opt={}))

    def test_scope_forbids_extra_paths_fields_and_dense_deletion(self):
        scope = dict(schema='TINYLM_USER110_OPTIMIZER_CLEANUP_SCOPE_V1',
            archives=[dict(name='fixture_'+str(i)+'.pt') for i in range(184)],
            remove_root_fields=['opt', 'opt_muon'],
            smoke_sessions=['nov01_adaptive_training_v1', 'nov04_p108_p107_v2'],
            smoke_exclude=['tiny_synthetic_2M_dense.pt', 'tiny_synthetic_2M_dense_best.pt'],
            p107=['runs/isolated/p107_session_disk_v1_20261101/boundary_u2',
                  'runs/isolated/p107_document_cli_v1_20261104/boundary_u1'])
        self.assertEqual(len(cleaner.validate_scope(scope)), 184)
        for mutate in (lambda x:x['archives'].append(x['archives'][0]),
                       lambda x:x['archives'][0].update(name='../raw_log.txt'),
                       lambda x:x.update(remove_root_fields=['model']),
                       lambda x:x.update(smoke_exclude=[])):
            altered = copy.deepcopy(scope);mutate(altered)
            with self.assertRaises(ValueError):cleaner.validate_scope(altered)

    def test_corrupt_stage_never_replaces_original(self):
        original = fixture()
        corrupted, _ = codec.retained_payload(roundtrip(original))
        corrupted['model']['weight'][0, 0] += 1
        stage = Mock();stage.exists.return_value = True
        source = Mock();record = Mock();record.exists.return_value = False
        row = dict(path='runs/ckpt/fixture.pt', stage_path='runs/ckpt/fixture_stage.pt',
                   metadata=dict(optimizer_fields=['opt', 'opt_muon']))
        with patch.object(cleaner, 'safe', side_effect=[source, stage]), \
             patch.object(cleaner, 'record_path', return_value=record), \
             patch.object(cleaner, 'check_ref'), patch.object(cleaner, 'host_guard'), \
             patch.object(codec, 'load_cpu', side_effect=[original, corrupted]), \
             patch.object(cleaner.os, 'replace') as replacement:
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                cleaner.convert(row)
            replacement.assert_not_called()

    def test_safe_rejects_parent_escape(self):
        for path in ('../raw_log.txt', '/tmp/fixture.pt', 'runs/../raw_log.txt'):
            with self.assertRaises(ValueError):cleaner.safe(path)

    def test_metadata_reader_rejects_executable_globals(self):
        reader = codec.MetadataOnly(io.BytesIO())
        with self.assertRaises(ValueError):reader.find_class('os', 'system')
        encoder = reader.find_class('_codecs', 'encode')
        self.assertEqual(encoder('original', 'latin1'), b'original')
        with self.assertRaises(ValueError):encoder('original', 'arbitrary-codec')


if __name__ == '__main__':
    torch.set_num_threads(1)
    unittest.main(verbosity=2)
