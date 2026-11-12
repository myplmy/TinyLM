"""Re-run value counterexamples and reject a stale unchanged terminal body."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import verify_event_metadata_literal_delta_v2 as verifier
import test_event_metadata_literal_delta_v1 as inherited


class TerminalEventLiteralTests(inherited.EventLiteralTests):
    def setUp(self):
        binding=patch.object(inherited,'evaluate',verifier.evaluate)
        binding.start()
        self.addCleanup(binding.stop)

    def test_same_body_with_empty_heading_is_not_an_edit(self):
        source=self.source()
        result=verifier.evaluate(source,source)
        self.assertFalse(result['guards']['actual_empty_footer_removal'])
        self.assertFalse(result['eligible_narrow_literal_delta'])


if __name__=='__main__':
    unittest.main(verbosity=2)
