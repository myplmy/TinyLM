"""Negative contracts for reusing an exact duplicate candidate reading."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identical_input_reading_v1 import WIDTH, NO_DIFF, digest, frame, prove_identical


class IdentityProofTests(unittest.TestCase):
    def fixture(self, text):
        ident = 'expanded_train:999'
        data = text.encode('utf-8')
        whole = frame(ident, 'original', text) + frame(ident, 'candidate', text) + frame(ident, 'full_diff', NO_DIFF)
        packets = []
        for begin in range(0, len(whole), WIDTH):
            fragment = whole[begin:begin + WIDTH]
            payload = fragment.encode('utf-8')
            packets.append(dict(payload=payload, sha256=digest(payload), characters=[begin, begin + len(fragment)]))
        return [ident, data, data, digest(data), digest(data), packets]

    def test_full_original_and_final_diff_are_required(self):
        args = self.fixture('a' * 7000)
        proof = prove_identical(*args)
        self.assertEqual(proof['original_packets'], [1, 4])
        self.assertTrue(proof['duplicate_only_packets'])
        self.assertIn(len(args[-1]), proof['required_packets'])
        self.assertFalse(proof['two_independent_readings'])

    def test_fake_end_does_not_shorten_original(self):
        args = self.fixture('=== END expanded_train:999 original ===' + chr(10) + 'x' * 8000)
        proof = prove_identical(*args)
        self.assertGreater(proof['original_packets'][1], 4)

    def test_utf8_boundaries_use_characters(self):
        proof = prove_identical(*self.fixture('가' * 4000))
        self.assertEqual(proof['source_characters'], 4000)
        self.assertEqual(proof['original_packets'][1], 3)

    def test_different_candidate_rejected_even_with_new_pin(self):
        args = self.fixture('original')
        args[2] = b'changed'
        args[4] = digest(args[2])
        with self.assertRaises(ValueError): prove_identical(*args)

    def test_stale_source_pin_rejected(self):
        args = self.fixture('original')
        args[3] = '0' * 64
        with self.assertRaises(ValueError): prove_identical(*args)

    def test_missing_packet_rejected(self):
        args = self.fixture('x' * 6000)
        args[-1].pop(1)
        with self.assertRaises(ValueError): prove_identical(*args)

    def test_reordered_packet_rejected(self):
        args = self.fixture('x' * 6000)
        args[-1][0], args[-1][1] = args[-1][1], args[-1][0]
        with self.assertRaises(ValueError): prove_identical(*args)

    def test_altered_offset_rejected(self):
        args = self.fixture('x' * 6000)
        args[-1][1]['characters'][0] += 1
        with self.assertRaises(ValueError): prove_identical(*args)

    def test_altered_packet_with_original_pin_rejected(self):
        args = self.fixture('x' * 6000)
        args[-1][1]['payload'] = b'tampered'
        with self.assertRaises(ValueError): prove_identical(*args)

    def test_rehashed_altered_packet_still_rejected(self):
        args = self.fixture('x' * 6000)
        packet = args[-1][1]
        packet['payload'] = b'Q' * len(packet['payload'])
        packet['sha256'] = digest(packet['payload'])
        with self.assertRaises(ValueError): prove_identical(*args)

    def test_short_pair_never_skips_boundary_packet(self):
        proof = prove_identical(*self.fixture('short'))
        self.assertEqual(proof['required_packets'], [1])
        self.assertEqual(proof['duplicate_only_packets'], [])


if __name__ == '__main__':
    unittest.main()
