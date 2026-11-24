"""Check real route cache lifecycle using the existing small CPU fixture."""
import unittest
import torch
from scripts import test_p106b_weight_route as fixture
from scripts import p106b_weight_route as routes
from scripts import diag_p108b_boundary_gpu as driver


class BoundaryRouteTests(unittest.TestCase):
    def test_actual_config_field_and_unapproved_native_modes_are_checked_before_gpu(self):
        from tinylm.config import TMTConfig
        cfg=TMTConfig(n_middle=10,tie_mlp=False,mlp_group=1)
        self.assertFalse(driver.native_config(cfg,'float')['mtp_aux'])
        cfg.mtp_aux=True
        with self.assertRaises(ValueError):driver.native_config(cfg,'float')
        cfg.mtp_aux=False
        with self.assertRaises(ValueError):driver.native_config(cfg,'ternary')

    def test_refresh_after_acceptance_exposes_updated_weights_in_eval(self):
        model=fixture.Mini().eval();x=torch.ones(1,2)
        with routes.weight_route(model,'float')as route:
            driver.refresh_route(model,route);before=model(x).clone()
            with torch.no_grad():model.a.weight.add_(.1)
            with self.assertRaises(RuntimeError):model(x)
            driver.refresh_route(model,route);after=model(x)
            self.assertFalse(torch.equal(before,after));self.assertTrue(model._quant_frozen)

    def test_train_refresh_removes_frozen_cache_and_preserves_gradients(self):
        model=fixture.Mini().eval()
        with routes.weight_route(model,'float')as route:
            driver.refresh_route(model,route);model.train();driver.refresh_route(model,route)
            self.assertFalse(model._quant_frozen);model(torch.ones(1,2)).sum().backward()
            self.assertIsNotNone(model.a.weight.grad);self.assertIsNotNone(model.b.weight.grad)


if __name__=='__main__':unittest.main()
