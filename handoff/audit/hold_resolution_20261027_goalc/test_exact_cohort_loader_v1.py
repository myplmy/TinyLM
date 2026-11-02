"""Definition reuse must never execute historical collection or default calls."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cohort_collector',HERE/'collect_exact_cohort_reviews_v1.py')
collector=importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class LoaderSafety(unittest.TestCase):
    def test_actual_functions_load_without_historical_top_level(self):
        env=collector.load_reused(HERE/'collect_supplemental_candidates_v63.py',{})
        self.assertEqual(set(env)-{'__builtins__'},set(collector.REUSED))

    def test_top_level_raise_never_executes(self):
        code='raise RuntimeError("historical collection must not run")'+chr(10)
        code+=chr(10).join('def '+name+'(): return 7' for name in collector.REUSED)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.py'
            path.write_text(code)
            env=collector.load_reused(path,{})
            self.assertEqual(env['digest'](),7)

    def test_default_call_and_decorator_are_rejected_before_execution(self):
        for definition in ('def digest(value=trap()): return value',
                           '@trap()'+chr(10)+'def digest(): return 1'):
            code=definition+chr(10)+chr(10).join('def '+name+'(): return 7' for name in collector.REUSED if name!='digest')
            called=[]
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'fixture.py'
                path.write_text(code)
                with self.assertRaises(ValueError):
                    collector.load_reused(path,{'trap':lambda:called.append(True)})
            self.assertEqual(called,[])


if __name__=='__main__':unittest.main()
