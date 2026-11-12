"""Exercise the observed oversized group without any second payload read."""
import json
from pathlib import Path
import sys
import unittest

AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
import multi_source_lossless_review_entry_v2 as revised
import multi_source_lossless_review_entry_v1 as old
from test_multi_source_lossless_review_entry_v1 import GroupReaderTests, short_fixture, Fixture


def end(value):
    return json.loads(value.splitlines()[-1].split(' ', 1)[1])


class PrefixBackoffTests(unittest.TestCase):
    def test_short_packets_have_identical_frames_and_headers(self):
        packets, result = short_fixture().run()
        value = revised.render(packets, result)
        self.assertEqual(value, old.render(packets, result))
        self.assertEqual(end(value)['completed_pair_ids'], result['returned_ids'])

    def test_large_group_returns_truthful_prefix_without_more_source_reads(self):
        fixture = short_fixture();packets, result = fixture.run()
        for index, packet in enumerate(packets):
            packet['header']['fixture_unique_metadata'] = str(index) + 'x'*6000
        with self.assertRaises(ValueError):old.render(packets, result)
        before = list(fixture.loads)
        value = revised.render(packets, result);summary = end(value)
        self.assertLessEqual(len(value.encode()), old.MAX_OUTPUT_BYTES)
        self.assertEqual(fixture.loads, before)
        count = summary['source_pairs_returned']
        self.assertLess(count, 5)
        self.assertEqual(summary['not_returned_ids'], result['requested_ids'][count:])
        self.assertEqual(summary['source_pairs_loaded'], 5)
        self.assertEqual(summary['prepared_but_not_returned_ids'], result['requested_ids'][count:])
        self.assertEqual(summary['completed_pair_ids'], result['requested_ids'][:count])

    def test_long_source_backoff_preserves_native_next_part(self):
        raw = ('한글🙂 문서. '*4000).encode();fixture = Fixture({'expanded_train:1':(raw,raw)})
        packets, result = fixture.run();packets[0]['header']['fixture_metadata'] = 'x'*8000
        with self.assertRaises(ValueError):old.render(packets,result)
        value = revised.render(packets,result);summary = end(value)
        self.assertEqual(summary['completed_pair_ids'], [])
        self.assertLess(summary['continuations'][0]['next_part'], 4)
        self.assertEqual(fixture.loads, ['expanded_train:1'])
        self.assertEqual(len(packets[0]['pieces']), 3)

    def test_single_oversized_header_is_still_rejected_before_print(self):
        packets, result = short_fixture(1).run();packets[0]['header']['fixture_metadata'] = 'x'*old.MAX_OUTPUT_BYTES
        with self.assertRaises(ValueError):revised.render(packets,result)


if __name__ == '__main__':unittest.main()
