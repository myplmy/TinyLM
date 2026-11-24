"""Generic native down-projection contracts, not pretrained HF evidence."""
from types import SimpleNamespace
import unittest
import torch
from scripts import diag_p108b_hf_canary as d


class HFCanaryTests(unittest.TestCase):
    def test_real_local_config_uses_hidden_activation_not_hidden_act(self):
        path=d.external.ROOT/d.external.REGISTRY['gemma270']['path']/'config.json'
        config=d.external.read_json(path)
        d.validate_config(config)
        self.assertNotIn('hidden_act',config)
        with self.assertRaises(ValueError):d.validate_config(dict(config,hidden_activation='unsupported'))

    def test_all_layers_are_discovered_and_aliasing_is_rejected(self):
        layers=[SimpleNamespace(mlp=SimpleNamespace(down_proj=torch.nn.Linear(5,3,bias=False)))for _ in range(18)]
        body=SimpleNamespace(model=SimpleNamespace(layers=layers))
        self.assertEqual(list(d.modules(body)),list(range(18)))
        layers[-1].mlp.down_proj=layers[0].mlp.down_proj
        with self.assertRaises(ValueError):d.modules(body)

    def test_real_write_and_exception_rollback_preserve_parameter_identity(self):
        module=torch.nn.Linear(5,3,bias=False);original=module.weight.detach().clone();ident=id(module.weight)
        with self.assertRaises(RuntimeError):
            with d.edit(module,torch.ones_like(original)):
                self.assertTrue(torch.equal(module.weight,original+1));raise RuntimeError('evaluation failed')
        self.assertEqual(id(module.weight),ident);self.assertTrue(torch.equal(module.weight,original))


if __name__=='__main__':unittest.main()
