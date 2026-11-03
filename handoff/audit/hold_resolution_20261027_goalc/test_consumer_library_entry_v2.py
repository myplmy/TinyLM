"""Check adapter4 dispatch and each historic recursive-alias boundary before data I/O."""
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import io
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import consume_guarded_partial_cache_v3_library_v1 as entry

class ConsumerEntry(unittest.TestCase):
    def test_cli_dispatches_once_without_entering_legacy_cli(self):
        modules=[entry.guarded.previous,entry.guarded.previous.previous,entry.guarded.previous.first]
        before=[module.verify for module in modules]
        args=['entry','verify','--roster','/tmp/unit_roster','--selection','/tmp/unit_selection','--output-name','unit_fixture']
        with patch.object(sys,'argv',args),patch.object(entry.guarded,'main',side_effect=AssertionError('legacy CLI entered')), \
                patch.object(entry.guarded,'verify',return_value=dict(status='UNIT_FIXTURE_ONLY')) as library, \
                redirect_stdout(io.StringIO()):
            entry.main();library.assert_called_once()
        self.assertEqual([module.verify for module in modules],before)

    def test_direct_entry_delegates_exact_arguments_once(self):
        with patch.object(entry.guarded,'verify',return_value={'status':'UNIT_FIXTURE_ONLY'}) as library:
            result=entry.consume('base','roster','output','selection')
        library.assert_called_once_with('base','roster','output','selection')
        self.assertEqual(result,{'status':'UNIT_FIXTURE_ONLY'})

    def check_alias(self,module):
        with patch.object(module,'verify',entry.guarded.verify):
            with self.assertRaisesRegex(ValueError,'legacy CLI verify alias'):
                entry.consume(None,None,None,None)

    def test_reject_adapter3_alias(self):self.check_alias(entry.guarded.previous)
    def test_reject_adapter2_alias(self):self.check_alias(entry.guarded.previous.previous)
    def test_reject_original_cli_alias(self):self.check_alias(entry.guarded.previous.first)

if __name__=='__main__':unittest.main()
