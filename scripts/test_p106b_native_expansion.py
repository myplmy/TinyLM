"""Tiny synthetic byte-level BPE and temp-bin CPU tests; real assets untouched."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
import copy
from datetime import datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native_expansion as d


def codec_fixture():
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, processors, trainers
    with d.single_core_environment():
        tok = Tokenizer(models.BPE())
        tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        tok.decoder = decoders.ByteLevel()
        tok.post_processor = processors.ByteLevel(trim_offsets=False)
        rng = random.Random(1337)
        words = [''.join(rng.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(12)) for _ in range(400)]
        text = ' '.join(words) + ' 가나다 한글 바이트 alpha beta KEEP BLOCK café snowman repeated ' * 20
        tok.train_from_iterator([text], trainers.BpeTrainer(vocab_size=384,
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
            special_tokens=['<pad>', '<bos>', '<eos>'], show_progress=False))
        old = json.loads(tok.to_str()); current = copy.deepcopy(old)
        n = len(old['model']['vocab'])
        specials = [dict(id=3 + i, content='<|fixture_' + str(i) + '|>', single_word=False,
            lstrip=False, rstrip=False, normalized=False, special=True) for i in range(32)]
        current['added_tokens'] = current['added_tokens'] + specials
        current['model']['merges'] = current['model']['merges'][:-32]
        current['model']['vocab'] = {token: index if index < 3 else index + 32
            for token, index in old['model']['vocab'].items() if index < n - 32}
        current['model']['vocab'].update({value['content']: value['id'] for value in specials})
        return old, current, d.CodecPair(old, current)


def old_segment(pair, text):
    return pair.old.backend.encode(text, add_special_tokens=False).ids + [d.EOS]


def no_val():
    return d.ValIndex(frozenset(), (), {})


def fixture_host(free_bytes=10**12, label='FIXTURE_HOST_INPUT_NOT_AUTODETECTED'):
    stamp = datetime.now(d.timezone.utc).isoformat()
    path = d.ROOT / 'handoff/audit' / ('host_' + d.sha([stamp, free_bytes])[:16] + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(dict(free_bytes=free_bytes, measured_at=stamp, input_label=label), stream)
    return dict(free_bytes=free_bytes, measured_at=stamp, label=label,
                evidence_path=str(path.relative_to(d.ROOT)))


@contextmanager
def tiny_source(pair, old_config, current_config):
    """Use genuine CLI/receipt functions with only tiny, explicitly patched paths."""
    with tempfile.TemporaryDirectory(prefix='native_expansion_') as temporary:
        root = Path(temporary); cache = root / 'data_cache' / d.TAG
        evidence = root / 'test_result/evidence' / d.TAG
        old_train = root / 'data_cache/legacy/train.bin'
        old_tok = root / 'data_cache/old_tokenizer.json'
        current_val = root / 'data_cache/current/val.bin'
        current_tok = root / 'data_cache/current_tokenizer.json'
        old_ids = old_segment(pair, 'KEEP alpha 가나다') + old_segment(pair, 'BLOCK beta')
        starter = next(index for index, piece in enumerate(pair.old.pieces) if piece == b'\xea')
        old_ids += [starter]
        val_ids = [3, d.EOS] + pair.current.backend.encode('BLOCK beta').ids + [d.EOS, 4]
        old_train.parent.mkdir(parents=True); current_val.parent.mkdir(parents=True)
        old_train.write_bytes(d.ids_bytes(old_ids)); current_val.write_bytes(d.ids_bytes(val_ids))
        old_tok.write_text(json.dumps(old_config, ensure_ascii=False))
        current_tok.write_text(json.dumps(current_config, ensure_ascii=False))
        tok_sha = hashlib.sha256(current_tok.read_bytes()).hexdigest().upper()
        old_meta, current_meta = old_train.parent / 'meta.json', current_val.parent / 'meta.json'
        old_meta.write_text(json.dumps(dict(train=len(old_ids), vocab=pair.layout['vocab'],
            mix_ratio_cfg=[.5, .5], mix_token_frac=[.25, .75])))
        current_meta.write_text(json.dumps(dict(val=len(val_ids), train=19, vocab=pair.layout['vocab'],
            tokenizer_lineage='chat32', tokenizer_sha256=tok_sha,
            mix_ratio_cfg=[.5, .5], mix_token_frac=[.34, .66])))
        (root / 'code.py').write_text('TINY_FIXTURE_ONLY = True\n')
        (root / '.gitignore').write_text('**/data_cache/\n')
        values = dict(ROOT=root, CACHE=cache, EVIDENCE=evidence, OLD_TRAIN=old_train,
            OLD_META=old_meta, OLD_TOKENIZER=old_tok, CURRENT_VAL=current_val,
            CURRENT_META=current_meta, CURRENT_TOKENIZER=current_tok,
            CURRENT_TOKENIZER_SHA=tok_sha, CURRENT_VAL_SHA=d.ids_hash(val_ids),
            EXPECTED_OLD_IDS=len(old_ids), EXPECTED_VAL_IDS=len(val_ids),
            EXPECTED_VOCAB=pair.layout['vocab'], CODE=('code.py',))
        with patch.multiple(d, **values), patch.object(d, 'authority', return_value=100000.), \
             patch.object(d.shutil, 'disk_usage', return_value=SimpleNamespace(free=10**12)):
            yield root, old_ids, val_ids


class CodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.old, cls.current, cls.pair = codec_fixture()

    def test_layout_proves_shift_and_removed32_not_direct_id_compatibility(self):
        layout = d.validate_layout(self.old, self.current)
        self.assertEqual(layout['ordinary_id_shift'], 32)
        self.assertFalse(layout['id_direct_copy_allowed'])
        for literal, index in self.old['model']['vocab'].items():
            if 3 <= index < layout['vocab'] - 32:
                self.assertEqual(self.current['model']['vocab'][literal], index + 32)

    def test_strict_multibyte_and_original_replacement_character_are_lossless(self):
        for text in ('가나다 한글 café snowman ☃', 'a\ufffdb', '', 'ASCII text\nsecond line'):
            converted, proof = self.pair.transform(old_segment(self.pair, text))
            self.assertEqual(self.pair.current.raw(converted[:-1]), text.encode())
            self.assertEqual(proof['body_bytes'], len(text.encode()))
            self.assertEqual(converted[-1], d.EOS)
            self.assertNotIn(d.EOS, converted[:-1])

    def test_old_pad_bos_eos_semantics_and_bytes_are_preserved(self):
        converted, _ = self.pair.transform([0, 1] + old_segment(self.pair, ' text'))
        self.assertEqual(converted[:2], [0, 1])
        self.assertEqual(self.pair.current.raw(converted[:-1]), b'<pad><bos> text')
        self.assertEqual(converted[-1], 2)

    def test_new_reserved_literal_becomes_canonical_special_not_old_numeric_id(self):
        literal = self.current['added_tokens'][3]['content']
        old_ids = old_segment(self.pair, literal)
        converted, proof = self.pair.transform(old_ids)
        self.assertEqual(converted, [3, 2])
        self.assertGreater(len(old_ids), len(converted))
        self.assertEqual(proof['new_special_counts'], {3: 1})

    def test_removed_tail_merge_occurrence_is_observed_and_split_losslessly(self):
        for index in range(self.pair.layout['vocab'] - 32, self.pair.layout['vocab']):
            try:
                text = self.pair.old.raw([index]).decode('utf-8')
            except UnicodeDecodeError: continue
            if self.pair.old.backend.encode(text).ids == [index]:
                converted, proof = self.pair.transform([index, 2])
                self.assertEqual(proof['old_tail_merge_tokens'], 1)
                self.assertGreater(len(converted), 2)
                self.assertEqual(self.pair.current.raw(converted[:-1]), text.encode())
                break
        else: self.fail('synthetic removed tail must have a complete UTF8 token')

    def test_invalid_complete_utf8_errors_without_replacement(self):
        index = next(i for i, piece in enumerate(self.pair.old.pieces) if piece == b'\xea')
        with self.assertRaises(UnicodeDecodeError): self.pair.transform([index, 2])

    def test_canonical_new_eos_from_literal_bytes_is_boundary_error(self):
        vocab = self.old['model']['vocab']
        literal_as_ordinary_byte_tokens = [vocab[char] for char in '<eos>']
        self.assertNotIn(2, literal_as_ordinary_byte_tokens)
        with self.assertRaisesRegex(ValueError, 'introduced EOS2'):
            self.pair.transform(literal_as_ordinary_byte_tokens + [2])

    def test_changed_format_normalization_special_or_shift_is_rejected(self):
        for mutate in (lambda value: value.update(normalizer={'type': 'NFC'}),
                       lambda value: value['model'].update(dropout=.1),
                       lambda value: value['added_tokens'][1].update(content='<wrong>'),
                       lambda value: value['model']['merges'].pop()):
            changed = copy.deepcopy(self.current); mutate(changed)
            with self.assertRaises(ValueError): d.validate_layout(self.old, changed)

    def test_large_segment_invalid_ids_or_multiple_eos_are_errors(self):
        segment = old_segment(self.pair, 'alpha')
        with patch.object(d, 'MAX_SEGMENT_IDS', 1):
            with self.assertRaises(ValueError): self.pair.transform(segment)
        for invalid in ([2, 2], [65535, 2], [True, 2], []):
            with self.assertRaises(ValueError): self.pair.transform(invalid)
        with self.assertRaisesRegex(ValueError, 'byte bound'): self.pair.old.raw(segment, max_bytes=1)


class ExclusionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.old, cls.current, cls.pair = codec_fixture()

    def test_full_and_both_edge_partials_are_conservative_and_disclosed(self):
        index = d.build_val_index([10, 11, 2, 20, 21, 2, 30], self.pair)
        self.assertEqual(index.summary['prefix_partial_ids'], 2)
        self.assertEqual(index.summary['suffix_partial_ids'], 1)
        self.assertEqual(index.summary['complete_eos_segments'], 1)
        self.assertIn('FULL_CANONICAL_EOS_IDS', index.match([20, 21, 2])[0])
        self.assertIn('VAL_PREFIX_PARTIAL_IDS', index.match([35, 10, 11, 2])[0])
        self.assertIn('VAL_SUFFIX_PARTIAL_IDS', index.match([30, 35, 2])[0])
        self.assertEqual(index.match([35, 36, 2])[0], [])

    def test_one_id_partial_is_not_relaxed_and_can_remove_every_segment(self):
        index = d.build_val_index([3, 2], self.pair)
        literal = self.current['added_tokens'][3]['content']
        values = old_segment(self.pair, literal + ' alpha') + old_segment(self.pair, literal + ' beta')
        stats = d.convert_stream(values, self.pair, index)
        self.assertEqual(stats['kept_segments'], 0)
        self.assertEqual(stats['excluded_segments'], 2)
        self.assertEqual(stats['new_kept_ids'], 0)
        self.assertEqual(stats['old_excluded_ids'], len(values))

    def test_odd_byte_match_is_not_an_aligned_token_match(self):
        haystack, needle = d.ids_bytes([0x1201, 0x3456]), d.ids_bytes([0x5612])
        self.assertEqual(d.aligned_match(haystack, needle), (False, 1))
        self.assertEqual(d.aligned_match(haystack + needle, needle), (True, 1))
        with self.assertRaises(ValueError): d.aligned_match(haystack, b'')

    def test_whole_val_without_eos_is_two_edges_not_silently_empty_filter(self):
        index = d.build_val_index([10, 11], self.pair)
        self.assertEqual(len(index.full), 0)
        self.assertEqual(index.summary['prefix_partial_ids'], 2)
        self.assertEqual(len(index.match([10, 11, 2])[0]), 2)

    def test_empty_edges_are_not_empty_substring_patterns(self):
        index = d.build_val_index([2, 20, 2], self.pair)
        self.assertEqual(index.partials, ())
        self.assertEqual(index.summary['suffix_partial_ids'], 0)
        self.assertEqual(index.match([35, 2])[0], [])

    def test_complete_val_must_be_canonical_not_ordinary_spelling_of_new_special(self):
        vocab = self.current['model']['vocab']
        literal = self.current['added_tokens'][3]['content']
        ordinary = [vocab[char] for char in literal]
        with self.assertRaisesRegex(ValueError, 'not canonical'):
            d.build_val_index([2] + ordinary + [2], self.pair)

    def test_duplicate_validation_segments_use_distinct_hash_count_without_new_truth_claim(self):
        index = d.build_val_index([2, 20, 21, 2, 20, 21, 2], self.pair)
        self.assertEqual(index.summary['complete_eos_segments'], 2)
        self.assertEqual(index.summary['unique_complete_id_hashes'], 1)
        self.assertEqual(index.summary['semantic_near_or_pretraining_decontamination'], 'NOT_ESTABLISHED')


class ConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.old, cls.current, cls.pair = codec_fixture()

    def test_incomplete_multibyte_tail_is_counted_excluded_and_never_decoded(self):
        index = next(i for i, piece in enumerate(self.pair.old.pieces) if piece == b'\xea')
        prefix = old_segment(self.pair, '가나다')
        events, kept = [], []
        stats = d.convert_stream(prefix + [index], self.pair, no_val(), on_keep=kept.append, on_event=events.append)
        self.assertEqual(stats['old_input_ids'], len(prefix) + 1)
        self.assertEqual(stats['old_incomplete_tail_ids'], 1)
        self.assertEqual(stats['incomplete_tail_bytes'], 1)
        self.assertEqual(stats['incomplete_tail_utf8'], 'NOT_DECODED_INCOMPLETE')
        self.assertFalse(stats['replacement_repair'])
        self.assertEqual(stats['consumer_old_ids_sha256'], d.ids_hash(prefix + [index]))
        self.assertEqual(hashlib.sha256(b''.join(kept)).hexdigest().upper(), stats['retained_ids_sha256'])
        self.assertTrue(d.recount_audit(events, stats)['tail_seen'])

    def test_prefix_reader_never_reads_past_limit_and_chunk_boundaries_do_not_repair_utf8(self):
        values = old_segment(self.pair, '가나다') + old_segment(self.pair, 'second unseen paragraph')
        class Counted(io.BytesIO):
            consumed = 0
            def read(self, n=-1):
                self.assert_bound = n >= 0
                block = super().read(n); self.consumed += len(block); return block
        stream = Counted(d.ids_bytes(values)); limit = len(values) - 2
        reader = d.UInt16Input(stream, limit, chunk_ids=1)
        stats = d.convert_stream(reader, self.pair, no_val())
        self.assertEqual(stream.consumed, 2 * limit)
        self.assertEqual(stats['old_input_ids'], limit)
        self.assertEqual(stats['consumer_old_ids_sha256'], reader.hexdigest())
        self.assertGreater(stats['old_incomplete_tail_ids'], 0)

    def test_raw_reader_rejects_odd_or_short_extent_and_zero_reads_nothing(self):
        for raw, limit in ((b'\x00', 1), (b'\x00\x00', 2)):
            with self.assertRaises(ValueError): list(d.UInt16Input(io.BytesIO(raw), limit))
        stream = io.BytesIO(b'ignored'); self.assertEqual(list(d.UInt16Input(stream, 0)), [])
        self.assertEqual(stream.tell(), 0)

    def test_all_drop_reasons_are_union_not_double_token_exclusion(self):
        values = old_segment(self.pair, 'alpha'); new, _ = self.pair.transform(values)
        raw = d.ids_bytes(new[:-1])
        index = d.ValIndex(frozenset({(len(new), d.ids_hash(new))}), (('PREFIX', raw), ('SUFFIX', raw)), {})
        stats = d.convert_stream(values, self.pair, index)
        self.assertEqual(stats['excluded_segments'], 1)
        self.assertEqual(stats['old_excluded_ids'], len(values))
        self.assertEqual(len(stats['validation_reason_segments']), 3)

    def test_consumer_ledger_missing_reordered_or_changed_denominator_is_rejected(self):
        events = []; values = old_segment(self.pair, 'alpha') + old_segment(self.pair, 'beta')
        stats = d.convert_stream(values, self.pair, no_val(), on_event=events.append)
        d.recount_audit(events, stats)
        for changed in (events[:-1], list(reversed(events)), [dict(events[0], old_offset=1), events[1]]):
            with self.assertRaises(ValueError): d.recount_audit(changed, stats)
        changed = dict(stats); changed['new_kept_ids'] += 1
        with self.assertRaises(ValueError): d.recount_audit(events, changed)

    def test_statistics_roundtrip_has_stable_string_counter_keys(self):
        values = old_segment(self.pair, self.current['added_tokens'][13]['content'])
        stats = d.convert_stream(values, self.pair, no_val())
        saved = json.loads(json.dumps(stats))
        self.assertEqual(d.sha(saved), d.sha(stats))
        self.assertIn('13', saved['new_special_counts'])


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.old, cls.current, cls.pair = codec_fixture()

    def run_tiny_stages(self, through='readback'):
        reports = {}
        for mode in d.MODES:
            kwargs = dict(max_wall_sec=600)
            if mode == 'budget': kwargs.update(allow_full_scan=True, host=fixture_host())
            if mode == 'build': kwargs.update(allow_full_build=True, draw_ids=10,
                                              host=fixture_host(9 * 10**11))
            with redirect_stdout(io.StringIO()): self.assertEqual(d.worker(mode, **kwargs), 0)
            reports[mode] = d.read_report(mode)
            if mode == through: break
        return reports

    def test_tiny_full_pipeline_roundtrip_preserves_originals_and_entire_consumer(self):
        with tiny_source(self.pair, self.old, self.current) as (_, old_ids, _):
            before = {path: path.read_bytes() for path in
                      (d.OLD_TRAIN, d.OLD_META, d.OLD_TOKENIZER, d.CURRENT_VAL, d.CURRENT_TOKENIZER)}
            reports = self.run_tiny_stages()
            built, final = reports['build'], reports['readback']
            self.assertEqual(built['metrics']['old_input_ids'], len(old_ids))
            self.assertEqual(built['metrics']['old_incomplete_tail_ids'], 1)
            self.assertEqual(built['metrics']['excluded_segments'], 1)
            self.assertEqual(built['metrics']['kept_segments'], 1)
            self.assertEqual(final['last_id'], 2)
            self.assertEqual(final['actual_eos_segments'], 1)
            self.assertEqual(final['full_input_consumer']['old_input_ids'], len(old_ids))
            self.assertEqual(final['source_train_sha256_verified_by_completed_build_stream'], d.ids_hash(old_ids))
            self.assertFalse(final['pool2draw']['existing601m_added'])
            self.assertEqual(final['model_gpu_training'], 'NOT_RUN')
            for path, raw in before.items(): self.assertEqual(path.read_bytes(), raw)
            public = json.dumps(final)
            self.assertNotIn('KEEP alpha', public); self.assertNotIn('BLOCK beta', public)

    def test_source_stage_only_reads_small_config_and_stats_not_bins(self):
        with tiny_source(self.pair, self.old, self.current):
            original = Path.open
            def guarded(path, *args, **kwargs):
                if path in (d.OLD_TRAIN, d.CURRENT_VAL):
                    raise AssertionError('source may not open bins')
                return original(path, *args, **kwargs)
            with patch.object(Path, 'open', guarded):
                snapshot = d.source_stage()
            self.assertEqual(snapshot['status'], 'SOURCE_METADATA_PINNED')
            self.assertEqual(snapshot['source']['bin_hashes'], 'NOT_READ_BY_SOURCE_STAGE')
            self.assertFalse(snapshot['source']['legacy_val_access'])

    def test_pilot_fixed_prefix_consumption_never_whole_source_hashes(self):
        with tiny_source(self.pair, self.old, self.current) as (_, old_ids, _):
            limit = len(old_segment(self.pair, 'KEEP alpha 가나다')) + 2
            self.assertLess(limit, len(old_ids))
            with patch.object(d, 'PILOT_IDS', limit), patch.object(d, 'digest', wraps=d.digest) as hashing:
                reports = self.run_tiny_stages('pilot')
            pilot = reports['pilot']
            self.assertEqual(pilot['prefix_read_ids'], limit)
            self.assertEqual(pilot['prefix_read_bytes'], 2 * limit)
            self.assertEqual(pilot['prefix_sha256'], d.ids_hash(old_ids[:limit]))
            self.assertGreater(pilot['metrics']['old_incomplete_tail_ids'], 0)
            self.assertFalse(any(call.args[0] == d.OLD_TRAIN for call in hashing.call_args_list))

    def test_source_change_blocks_before_codec_or_bin_consumption(self):
        with tiny_source(self.pair, self.old, self.current):
            self.run_tiny_stages('source')
            value = json.loads(d.OLD_META.read_text()); value['changed'] = True
            d.OLD_META.write_text(json.dumps(value))
            with patch.object(d, 'load_pair') as codec:
                with self.assertRaisesRegex(ValueError, 'original source/config'):
                    d.pilot_stage()
            codec.assert_not_called()

    def test_explicit_flags_required_before_whole_hash_or_build(self):
        with patch.object(d, 'digest') as hashing:
            with self.assertRaises(d.Pending): d.budget_stage()
            with self.assertRaises(d.Pending): d.build_stage()
        hashing.assert_not_called()
        phases = d.phase_commands('build')
        self.assertNotIn('--allow-full-build', phases[2][1])

    def test_whitelist_rejects_legacy_val_current_train_and_whole_hash_by_default(self):
        with tiny_source(self.pair, self.old, self.current):
            for forbidden in (d.OLD_TRAIN.parent / 'val.bin', d.CURRENT_VAL.parent / 'train.bin'):
                with self.assertRaisesRegex(ValueError, 'allowlist'): d.read_path(forbidden)
            with self.assertRaisesRegex(ValueError, 'explicit budget'): d.digest(d.OLD_TRAIN)

    def test_whole_build_cannot_reuse_or_overwrite_partial_or_complete_cache(self):
        with tiny_source(self.pair, self.old, self.current):
            self.run_tiny_stages('build'); before = (d.CACHE / 'train.bin').read_bytes()
            with patch.object(d, 'load_pair') as codec:
                with self.assertRaises(FileExistsError):
                    d.build_stage(allow_full_build=True, max_wall_sec=600, host=fixture_host())
            codec.assert_not_called(); self.assertEqual((d.CACHE / 'train.bin').read_bytes(), before)

    def test_readback_rejects_changed_output_hash_or_last_eos(self):
        with tiny_source(self.pair, self.old, self.current):
            self.run_tiny_stages('build')
            path = d.CACHE / 'train.bin'; original = path.read_bytes()
            path.write_bytes(original[:-2] + d.ids_bytes([3]))
            with self.assertRaisesRegex(ValueError, 'last EOS'): d.readback_stage()

    def test_actual_source_sha_mismatch_leaves_partial_bin_but_no_success_metadata(self):
        with tiny_source(self.pair, self.old, self.current):
            reports = self.run_tiny_stages('budget')
            budget = copy.deepcopy(reports['budget']); budget['source_train_sha256'] = 'A' * 64
            original = d.read_report
            with d.single_core_environment(), patch.object(d, 'read_report',
                    side_effect=lambda mode: budget if mode == 'budget' else original(mode)):
                with self.assertRaisesRegex(ValueError, 'whole input reader/consumer SHA'):
                    d.build_stage(allow_full_build=True, max_wall_sec=600, host=fixture_host())
            self.assertTrue((d.CACHE / 'train.bin').exists())
            self.assertFalse((d.CACHE / 'meta.json').exists())
            self.assertFalse((d.CACHE / 'segments/segments_shards_manifest.json').exists())

    def test_writeonce_public_json_limit_and_raw_cache_ignore_guard(self):
        with tiny_source(self.pair, self.old, self.current) as (root, _, _):
            path = d.CACHE / 'fixture.json'; d.write_json(path, {'aggregate': 1})
            with self.assertRaises(FileExistsError): d.write_json(path, {'aggregate': 2})
            with patch.object(d, 'PUBLIC_LIMIT', 64):
                with self.assertRaisesRegex(ValueError, 'below20MB'):
                    d.write_json(d.CACHE / 'too_big.json', {'body': 'X' * 64})
            (root / '.gitignore').write_text('# fixture rule missing\n')
            with self.assertRaisesRegex(ValueError, 'ignore rule'): d.source_snapshot()

    def test_completed_activity_recipe_code_sha_and_bool_types_are_bound(self):
        with tiny_source(self.pair, self.old, self.current):
            report = self.run_tiny_stages('source')['source']
            self.assertEqual(d.sha(report['recipe']), d.sha(d.info()))
            self.assertNotIn('source_pool_policy', report)
            self.assertIsInstance(report['recipe']['source_pool_policy'], str)
            self.assertIsInstance(report['source'], dict)
            changed = copy.deepcopy(report); changed['recipe']['cpu_only'] = 1
            original = d.read_json
            with patch.object(d, 'read_json', side_effect=lambda path: changed if Path(path) ==
                              d.report_path('source') else original(path)):
                with self.assertRaises(d.Pending): d.read_report('source')
            activity = d.read_json(d.activity_path('source')); activity['report_sha256'] = 'OTHER'
            with patch.object(d, 'read_json', side_effect=lambda path: activity if Path(path) ==
                              d.activity_path('source') else original(path)):
                with self.assertRaises(d.Pending): d.read_report('source')

    def test_forecast_does_not_claim_actual_remaining_pool_or_new_information(self):
        pilot = dict(metrics=dict(old_input_ids=100, old_complete_ids=95, new_canonical_ids=110),
            conversion_seconds=2., current_val={'seconds': .1}, audit_sample_encoded_bytes=10000)
        result = d.forecast(pilot, 10000, remaining_seconds=100000, free_bytes=10**12)
        self.assertEqual(result['estimated_unfiltered_canonical_ids'], 11579)
        self.assertTrue(result['actual_retained_pool'].startswith('NOT_BUILT'))
        self.assertEqual(result['headroom_factor'], 2.)
        for kwargs in (dict(remaining_seconds=1, free_bytes=10**12), dict(remaining_seconds=100000, free_bytes=1)):
            with self.assertRaises(d.Pending): d.forecast(pilot, 10000, **kwargs)
        pilot['metrics']['old_complete_ids'] = 0
        with self.assertRaises(d.Pending): d.forecast(pilot, 10000, remaining_seconds=100000, free_bytes=10**12)

    def test_long_incomplete_tail_cannot_inflate_conversion_or_audit_extrapolation_denominator(self):
        pilot = dict(metrics=dict(old_input_ids=1000, old_complete_ids=1000, new_canonical_ids=1100),
            conversion_seconds=10., current_val={'seconds': .1}, audit_sample_encoded_bytes=10000)
        baseline = d.forecast(pilot, 100000, remaining_seconds=100000, free_bytes=10**12)
        pilot['metrics']['old_input_ids'] = 100000  #99k IDs never exercised canonical conversion.
        long_tail = d.forecast(pilot, 100000, remaining_seconds=100000, free_bytes=10**12)
        self.assertEqual(long_tail['estimated_build_seconds'], 2121)
        self.assertEqual(long_tail['estimated_audit_bytes'], 1000000)
        self.assertEqual(long_tail['estimated_build_seconds'], baseline['estimated_build_seconds'])
        self.assertEqual(long_tail['estimated_audit_bytes'], baseline['estimated_audit_bytes'])
        self.assertEqual(long_tail['extrapolation_complete_old_ids'], 1000)

    def test_budget_readback_extrapolation_also_uses_complete_old_ids_not_long_tail(self):
        pilot = dict(source={}, metrics=dict(old_input_ids=100000, old_complete_ids=1000,
            new_canonical_ids=1100), conversion_seconds=10., current_val={'seconds': .1},
            audit_sample_encoded_bytes=10000)
        with patch.object(d, 'read_report', return_value=pilot), patch.object(d, 'verify_source'), \
             patch.object(d, 'host_measurement', return_value={'free_bytes': 10**12}), \
             patch.object(d, 'guest_disk_measurement', return_value={'free_bytes': 10**12}), \
             patch.object(d, 'authority', return_value=100000), patch.object(d, 'EXPECTED_OLD_IDS', 100000), \
             patch.object(d, 'digest', return_value='A' * 64), \
             patch.object(d.time, 'perf_counter', side_effect=[10., 11.]):
            report = d.budget_stage(allow_full_scan=True, host={})
        self.assertEqual(report['forecast']['estimated_readback_seconds'], 200)

    def test_readback_budget_requires_estimate_cap_and_remaining_record_safe_time(self):
        budget = dict(forecast={'estimated_readback_seconds': 1500})
        self.assertEqual(d.validate_readback_budget(budget, 1500, remaining_seconds=1500), 1500)
        for cap, remaining in ((1200, 3000), (1800, 1400), (1800, 1600)):
            with self.subTest(cap=cap, remaining=remaining), self.assertRaises(d.Pending):
                d.validate_readback_budget(budget, cap, remaining_seconds=remaining)
        for invalid in (0, float('nan'), True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                d.validate_readback_budget(dict(forecast={'estimated_readback_seconds': invalid}),
                                          1800, remaining_seconds=3000)

    def test_readback_cap1200_pred1500_holds_before_any_scan_and_records_failed_activity(self):
        with tiny_source(self.pair, self.old, self.current):
            reports = self.run_tiny_stages('build')
            budget = copy.deepcopy(reports['budget']); budget['forecast']['estimated_readback_seconds'] = 1500
            original = d.read_report
            with patch.object(d, 'read_report', side_effect=lambda mode: budget if mode == 'budget' else original(mode)), \
                 patch.object(d, 'authority', return_value=3000), patch.object(d, 'readback_stage') as scan, \
                 redirect_stdout(io.StringIO()):
                code = d.main(['--mode', 'readback', '--worker', '--execute', '--max-wall-sec', '1200'])
            self.assertEqual(code, 8); scan.assert_not_called()
            activity = d.read_json(d.activity_path('readback'))
            self.assertEqual(activity['returncode'], 8); self.assertFalse(activity['complete'])
            self.assertFalse(d.report_path('readback').exists())

    def test_readback_preflight_rechecks_current05z_minus_record_reserve(self):
        with tiny_source(self.pair, self.old, self.current):
            reports = self.run_tiny_stages('build')
            budget = copy.deepcopy(reports['budget']); budget['forecast']['estimated_readback_seconds'] = 1500
            original = d.read_report
            with patch.object(d, 'read_report', side_effect=lambda mode: budget if mode == 'budget' else original(mode)), \
                 patch.object(d, 'authority', return_value=1400) as clock:
                with self.assertRaises(d.Pending): d.preflight('readback', max_wall_sec=1800)
            clock.assert_called_once_with('readback')

    def test_fresh_root_host_measurement_has_utc_and_evidence_sha_but_no_topology_claim(self):
        with tiny_source(self.pair, self.old, self.current):
            value = fixture_host(); stamp = datetime.fromisoformat(value['measured_at'])
            measured = d.host_measurement(value, now=stamp + timedelta(seconds=600))
            self.assertEqual(measured['age_seconds_at_entry'], 600.)
            self.assertEqual(measured['free_bytes'], value['free_bytes'])
            self.assertFalse(measured['runtime_continuous_host_free_guarantee'])
            self.assertIn('NOT_AUTODETECTED', measured['label_scope'])
            self.assertEqual(measured['evidence_sha256'], hashlib.sha256(
                (d.ROOT / value['evidence_path']).read_bytes()).hexdigest().upper())
            for now in (stamp + timedelta(seconds=601), stamp - timedelta(seconds=1)):
                with self.assertRaises(d.Pending): d.host_measurement(value, now=now)
            changed = dict(value); changed['measured_at'] = stamp.replace(tzinfo=None).isoformat()
            with self.assertRaises(ValueError): d.host_measurement(changed, now=stamp)
            with self.assertRaises(d.Pending): d.host_measurement(None)

    def test_guest_logical_and_current_host_are_independent_and_fresh_values_may_differ(self):
        with tiny_source(self.pair, self.old, self.current):
            reports = self.run_tiny_stages('build')
            self.assertEqual(reports['source']['disk']['host'], 'NOT_MEASURED_BY_TOOL')
            self.assertIn('guest logical', reports['pilot']['disk']['guest_logical']['method'])
            old_host = reports['budget']['disk']['host_root_input']['free_bytes']
            new_host = reports['build']['disk']['host_root_input']['free_bytes']
            self.assertNotEqual(old_host, new_host)
            self.assertEqual(old_host, 10**12); self.assertEqual(new_host, 9 * 10**11)
            self.assertIn('NOT_CONTINUOUSLY_OBSERVED', reports['build']['disk']['runtime_host_free'])

    def test_powershell_utc_z_and_seven_fraction_digits_work_on_python310(self):
        for value, expected in (('2026-10-19T14:40:00Z', '2026-10-19T14:40:00+00:00'),
                                ('2026-10-19T14:40:00.1234567Z', '2026-10-19T14:40:00.123456+00:00')):
            self.assertEqual(d.utc_measurement_time(value).isoformat(), expected)
        with self.assertRaises(ValueError): d.utc_measurement_time('2026-10-19T23:40:00+09:00')

    def test_insufficient_host_blocks_whole_hash_and_build_despite_large_guest_free(self):
        with tiny_source(self.pair, self.old, self.current):
            self.run_tiny_stages('pilot')
            with patch.object(d, 'digest', wraps=d.digest) as hashing:
                with self.assertRaisesRegex(d.Pending, 'physical host free'):
                    d.budget_stage(allow_full_scan=True, host=fixture_host(1))
            self.assertFalse(any(call.args[0] == d.OLD_TRAIN for call in hashing.call_args_list))
            with redirect_stdout(io.StringIO()):
                d.worker('budget', max_wall_sec=600, allow_full_scan=True, host=fixture_host())
            with patch.object(d, 'load_pair') as codec:
                with self.assertRaises(d.Pending):
                    d.build_stage(allow_full_build=True, max_wall_sec=600, host=fixture_host(1))
            codec.assert_not_called(); self.assertFalse((d.CACHE / 'train.bin').exists())

    def test_host_fields_are_forwarded_to_each_full_phase_not_inferred_or_reused(self):
        value = dict(free_bytes=100, measured_at='2026-10-19T00:00:00+00:00', label='Z: root input',
                     evidence_path='handoff/audit/root_host_fixture_not_read_here.json')
        for mode in ('budget', 'build'):
            phases = d.phase_commands(mode, host=value)
            for _, command in phases[1:]:
                self.assertIn('--host-free-bytes', command)
                self.assertIn(value['evidence_path'], command)
                self.assertIn(value['measured_at'], command)
        with self.assertRaises(ValueError): d.phase_commands('pilot', host=value)

    def test_everything_excluded_stays_empty_without_repetition_or_threshold_relaxation(self):
        with tiny_source(self.pair, self.old, self.current):
            literal = self.current['added_tokens'][3]['content']
            values = old_segment(self.pair, literal + ' alpha') + old_segment(self.pair, literal + ' beta')
            d.OLD_TRAIN.write_bytes(d.ids_bytes(values))
            meta = json.loads(d.OLD_META.read_text()); meta['train'] = len(values)
            d.OLD_META.write_text(json.dumps(meta))
            with patch.object(d, 'EXPECTED_OLD_IDS', len(values)):
                reports = self.run_tiny_stages()
            self.assertEqual(reports['build']['metrics']['new_kept_ids'], 0)
            self.assertEqual(reports['build']['metrics']['excluded_segments'], 2)
            self.assertEqual(reports['readback']['actual_output_ids'], 0)
            self.assertIsNone(reports['readback']['last_id'])
            self.assertFalse(reports['readback']['actual_cache_usable'])
            self.assertFalse(reports['readback']['pool2draw']['pool2x_admissible'])
            self.assertEqual((d.CACHE / 'train.bin').stat().st_size, 0)

    def test_pool2draw_uses_only_actual_retained_positions(self):
        self.assertTrue(d.pool_for_draw(20, 10)['pool2x_admissible'])
        self.assertFalse(d.pool_for_draw(19, 10)['pool2x_admissible'])
        self.assertEqual(d.pool_for_draw(19)['max_draw_under_pool2x'], 9)
        self.assertIsNone(d.pool_for_draw(0)['pool2x_admissible'])
        for arguments in ((True,), (1, 0), (-1,), (10, 2.5)):
            with self.assertRaises(ValueError): d.pool_for_draw(*arguments)

    def test_deadlines_and_600_second_record_reserve(self):
        self.assertEqual(d.authority('build', now=d.BUILD_STOP - timedelta(seconds=601)), 1)
        self.assertEqual(d.authority('pilot', now=d.END - timedelta(seconds=601)), 1)
        with self.assertRaises(d.Pending): d.authority('build', now=d.BUILD_STOP - timedelta(seconds=600))
        with self.assertRaises(ValueError): d.authority('pilot', now=datetime(2026, 10, 19))

    def test_check_only_reads_code_not_source_and_never_launches_workers(self):
        with patch.object(d, 'source_snapshot') as source, patch.object(d, 'worker') as worker, \
             patch.object(d, 'launch') as launch, patch.object(d, 'load_pair') as codec, \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.main(['--mode', 'build', '--check-only']), 0)
        for spy in (source, worker, launch, codec): spy.assert_not_called()
        metadata = json.loads(output.getvalue().split(' ', 1)[1])
        self.assertTrue(metadata['cpu_only']); self.assertFalse(metadata['gpu'])
        self.assertTrue(metadata['code_complete'])

    def test_phase_commands_preserve_flags_and_no_default_full_build(self):
        phases = d.phase_commands('build', max_wall_sec=600, allow_full_build=True, draw_ids=10)
        self.assertEqual([name for name, _ in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertEqual(phases[1][1][phases[1][1].index('--target-mode') + 1], 'build')
        for _, command in phases[1:]:
            self.assertIn('--allow-full-build', command); self.assertIn('--worker', command)
        for kwargs in (dict(mode='pilot', max_wall_sec=1201), dict(mode='build', allow_full_scan=True),
                       dict(mode='source', draw_ids=10), dict(mode='pilot', max_wall_sec=True)):
            with self.assertRaises(ValueError): d.phase_commands(**kwargs)

    def test_cpu_child_environment_and_timeout_kill_only_owned_group(self):
        process = Mock(pid=4321); process.wait.side_effect = [subprocess.TimeoutExpired('fixture', 1), 0]
        process.poll.return_value = None
        with patch.object(d.subprocess, 'Popen', return_value=process) as popen, \
             patch.object(d.os, 'getpgid', return_value=4321), patch.object(d.os, 'killpg') as kill:
            self.assertEqual(d.launch(['fixture'], 1), 124)
        self.assertEqual(popen.call_args.kwargs['env']['RAYON_NUM_THREADS'], '1')
        self.assertEqual(popen.call_args.kwargs['env']['CUDA_VISIBLE_DEVICES'], '')
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        kill.assert_called_once_with(4321, signal.SIGTERM)

    def test_failed_worker_records_hold_and_never_calls_real_stage(self):
        with tiny_source(self.pair, self.old, self.current):
            with patch.object(d, 'preflight', side_effect=d.Pending('fixture hold')), \
                 patch.object(d, 'source_stage') as stage:
                with self.assertRaises(d.Pending): d.worker('source', max_wall_sec=600)
            stage.assert_not_called()
            activity = d.read_json(d.activity_path('source'))
            self.assertEqual(activity['returncode'], 8); self.assertFalse(activity['complete'])
            self.assertFalse(d.report_path('source').exists())

    def test_termination_guard_restores_previous_handler_normally_and_on_exception(self):
        previous = signal.getsignal(signal.SIGTERM)
        with d.termination_guard(): self.assertIsNot(signal.getsignal(signal.SIGTERM), previous)
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with d.termination_guard(): raise RuntimeError('fixture')
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)

    def test_real_owned_term_unwinds_main_to130_and_preserves_failure_activity_and_handlers(self):
        with tiny_source(self.pair, self.old, self.current):
            previous = signal.getsignal(signal.SIGTERM)
            def terminate_stage():
                try: d.os.kill(d.os.getpid(), signal.SIGTERM)
                finally: d.os.kill(d.os.getpid(), signal.SIGTERM)  #Repeated TERM must not interrupt cleanup.
            with patch.object(d, 'preflight'), patch.object(d, 'source_stage', side_effect=terminate_stage), \
                 redirect_stdout(io.StringIO()) as output:
                code = d.main(['--mode', 'source', '--worker', '--execute', '--max-wall-sec', '600'])
            self.assertEqual(code, 130)
            self.assertIs(signal.getsignal(signal.SIGTERM), previous)
            self.assertIn('INTERRUPTED130', output.getvalue())
            activity = d.read_json(d.activity_path('source'))
            self.assertEqual(activity['returncode'], 130); self.assertFalse(activity['complete'])
            self.assertIsNone(activity['report_path']); self.assertIsNone(activity['report_sha256'])
            self.assertFalse(d.report_path('source').exists())
            self.assertIn('SIGKILL', d.info()['worker_termination'])

    def test_single_core_environment_restores_parent_values(self):
        with patch.dict(d.os.environ, {'RAYON_NUM_THREADS': '7'}):
            with d.single_core_environment():
                self.assertEqual(d.os.environ['RAYON_NUM_THREADS'], '1')
                self.assertEqual(d.os.environ['TOKENIZERS_PARALLELISM'], 'false')
            self.assertEqual(d.os.environ['RAYON_NUM_THREADS'], '7')


if __name__ == '__main__':
    unittest.main()
