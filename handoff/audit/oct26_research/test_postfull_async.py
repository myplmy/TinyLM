#!/usr/bin/env python3
"""Synthetic sequence control only: no launcher, model or GPU execution."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("postfull_async",Path(__file__).with_name("continue_after_official.py"))
d=importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)

class Sequence(unittest.TestCase):
 def test_nonzero_stops_without_retry_or_next_job(self):
  calls=[]; records=[]
  def launch(name,cap): calls.append(name); return 9
  self.assertEqual(d.run_steps(("a","b"),launch,lambda:1000,records.append),9)
  self.assertEqual(calls,["a"])
  self.assertEqual(len(records),1)
 def test_time_hold_never_launches(self):
  calls=[]; records=[]
  self.assertEqual(d.run_steps(("a",),lambda *args:calls.append(args),lambda:120,records.append),8)
  self.assertEqual(calls,[])
  self.assertEqual(records[0]["status"],"TIME_HOLD_NOT_RUN")
 def test_production_pause_remains_eight_after_three_completed_steps(self):
  calls=[]; records=[]
  def launch(name,cap): calls.append(name); return 8 if name=="production" else 0
  self.assertEqual(d.run_steps(("a","b","c","production"),launch,lambda:1000,records.append),8)
  self.assertEqual(calls,["a","b","c","production"])
  self.assertEqual([r["actual_exit"] for r in records],[0,0,0,8])

if __name__=="__main__": unittest.main()
