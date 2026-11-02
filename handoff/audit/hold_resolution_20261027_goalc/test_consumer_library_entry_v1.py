"""Exercise the actual CLI dispatch boundary and reject recursive legacy aliases."""
from contextlib import contextmanager,redirect_stdout
from pathlib import Path
from unittest.mock import patch
import io
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import consume_guarded_partial_cache_v2_library_v1 as entry


class ConsumerEntry(unittest.TestCase):
    def test_cli_uses_the_library_once_without_mutating_legacy_functions(self):
        before=entry.guarded.previous.verify
        args=['entry','verify','--roster','/tmp/unit_roster','--selection','/tmp/unit_selection','--output-name','unit_fixture']
        with patch.object(sys,'argv',args),patch.object(entry.guarded,'main',side_effect=AssertionError('legacy CLI entered')), \
                patch.object(entry.guarded,'verify',return_value=dict(status='UNIT_FIXTURE_ONLY')) as library, \
                redirect_stdout(io.StringIO()):
            entry.main()
            library.assert_called_once()
        self.assertIs(entry.guarded.previous.verify,before)

    def test_real_library_context_calls_the_original_verifier_once(self):
        calls=[]

        @contextmanager
        def context(selection):
            calls.append(('context',selection))
            yield object()

        def verify(base,roster,output,selection):
            with entry.guarded.previous.runtime(selection):
                calls.append(('verify',output))
                return dict(status='UNIT_FIXTURE_ONLY')

        with patch.object(entry.guarded,'runtime',context),patch.object(entry.guarded.previous,'verify',verify):
            result=entry.consume(None,None,'fixture','selection')
        self.assertEqual(result['status'],'UNIT_FIXTURE_ONLY')
        self.assertEqual(calls,[('context','selection'),('verify','fixture')])

    def test_legacy_recursive_alias_is_rejected_before_consuming_any_data(self):
        with patch.object(entry.guarded.previous,'verify',entry.guarded.verify):
            with self.assertRaisesRegex(ValueError,'legacy CLI verify alias'):
                entry.consume(None,None,None,None)


if __name__=='__main__':
    unittest.main()
