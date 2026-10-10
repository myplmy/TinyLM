"""P093B recovery CPU leaf-operator fixtures, never a checkpoint/model load."""
from __future__ import annotations
import copy
import inspect
import unittest
import torch
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p093b_native_repair as native
from scripts import p093b_calibration_recovery as recovery
from scripts.test_p093b_native_repair import fixtures

class RecoveryTests(unittest.TestCase):
    def setUp(self): torch.set_num_threads(1)

    def test_dev_selection_has_no_test_data_argument(self):
        self.assertNotIn("test_x",inspect.signature(recovery.dev_fit).parameters)
        trials=[{"selected_dev_nrms":.8,"selected_step":20,"test_nrms":1.2},
                {"selected_dev_nrms":.9,"selected_step":1,"test_nrms":.1}]
        self.assertEqual(recovery.select_trial(trials),0)

    def test_snapshot_restore_exact_ownership(self):
        cfg,originals,x,y=fixtures(); shared=native.shared_native(originals,cfg)
        adapters=native.residual_adapters(originals,shared,x,2,cfg)
        state=recovery.snapshot(adapters)
        with torch.no_grad(): adapters[0][0].D.add_(1)
        recovery.restore(adapters,state)
        self.assertTrue(torch.equal(adapters[0][0].D,state[0][0]["D"]))
        with self.assertRaises(ValueError): recovery.restore(adapters,state[:-1])

    def test_dev_fit_restores_selected_state_and_preserves_shared(self):
        cfg,originals,x,y=fixtures(); shared=native.shared_native(originals,cfg)
        adapters=native.residual_adapters(originals,shared,x,2,cfg)
        before=native.native_weight(shared.gate_proj)
        report,state=recovery.dev_fit(shared,adapters,x,y,x,y,lr=1e-4,steps=3,points=(0,1,3))
        self.assertEqual([r["step"] for r in report["curve"]],[0,1,3])
        self.assertTrue(torch.equal(before,native.native_weight(shared.gate_proj)))
        self.assertAlmostEqual(native.measure(shared,x,y,adapters)["nrms"],report["selected_dev_nrms"],places=6)
        self.assertTrue(torch.isfinite(torch.tensor(report["grad_max"])))

    def test_invalid_lr_and_missing_endpoint_fail(self):
        cfg,originals,x,y=fixtures(); shared=native.shared_native(originals,cfg)
        adapters=native.residual_adapters(originals,shared,x,2,cfg)
        for lr,points in ((.1,(0,3)),(1e-3,(1,3))):
            with self.assertRaises(ValueError): recovery.dev_fit(shared,adapters,x,y,x,y,lr=lr,steps=3,points=points)

    def test_half_roundtrip_does_not_claim_half_residency(self):
        cfg,originals,x,y=fixtures(); shared=native.shared_native(originals,cfg)
        adapters=native.residual_adapters(originals,shared,x,2,cfg); before=recovery.snapshot(adapters)
        rounded=recovery.half_storage_roundtrip(adapters)
        self.assertEqual(rounded[0][0].D.dtype,torch.float32)
        self.assertTrue(torch.equal(adapters[0][0].D,before[0][0]["D"]))
        account=recovery.byte_account(rounded)
        self.assertEqual(account["fp16_storage_bytes"]*2,account["fp32_parameter_bytes"])
        self.assertFalse(account["fp16_roundtrip_runtime_saving"])

    def test_native_half_dtype_is_not_transparently_compatible(self):
        with self.assertRaises(RuntimeError):
            torch.nn.functional.linear(torch.ones(2,8),torch.ones(4,8,dtype=torch.float16))

    def test_earliest_tied_dev_endpoint_is_selected(self):
        self.assertEqual(recovery.select_trial([{"selected_dev_nrms":.4,"selected_step":50},
                                               {"selected_dev_nrms":.4,"selected_step":20}]),1)

    def test_checkonly_never_loads_private_or_model(self):
        from scripts import diag_p093b_calibration_recovery as driver
        from unittest.mock import patch
        import io
        with patch.object(sys,"argv",["diag","--mode","capacity_b","--check-only"]), \
             patch.object(driver,"load_observation",side_effect=AssertionError("model/private load")), \
             patch("sys.stdout",new=io.StringIO()):
            self.assertEqual(driver.main(),0)

    def test_precision_negative_prerequisite_is_before_model_loading(self):
        from scripts import diag_p093b_calibration_recovery as driver
        from unittest.mock import patch
        from types import SimpleNamespace
        import tempfile,json
        with tempfile.TemporaryDirectory(prefix="p093b_precision_fixture_") as tmp:
            folder=Path(tmp); (folder/"report.json").write_text(json.dumps({"status":"RECOVERY_CALIBRATION_COMPLETE",
                "input":{"code_sha256":{}},"ranks":[{"rank":32,"local_viable":False},{"rank":64,"local_viable":False}]}))
            with patch.object(driver,"directory",return_value=folder), \
                 patch.object(driver,"load_observation",side_effect=AssertionError("model must not load")):
                report,rc=driver.execute(SimpleNamespace(mode="precision",tag="fixture",max_wall_sec=10),{"code_sha256":{}},folder)
                self.assertEqual(rc,8); self.assertEqual(report["model_loading"],"NOT_RUN")

    def test_actual_answer_prompts_are_explicit_legacy_and_bilingual(self):
        from scripts.diag_p093b_calibration_recovery import PROBES
        self.assertEqual(len(PROBES),8)
        self.assertEqual(sum(name.startswith("ko_") for name,prompt in PROBES),4)
        self.assertFalse(any("<|im_start|>" in prompt for name,prompt in PROBES))

if __name__=="__main__": unittest.main(verbosity=2)
