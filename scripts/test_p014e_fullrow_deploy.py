"""Pure CPU admission/pairing contracts, no model/checkpoint/GPU tests."""
from copy import deepcopy
from pathlib import Path
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p014e_fullrow_deploy as full


def control():
    rows=[]
    for variant in full.prior.VARIANTS:
        for tile in full.shape.TILES:
            rows.append(dict(variant=variant,tile_rows=tile,original_allclose=tile==4096,all_exact=tile==4096,
                             all_argmax_equal=True,model_released=True,cleanup=dict(allocated_bytes=0,reserved_bytes=0),
                             logits=[dict(exact_equal=tile==4096,max_abs=0 if tile==4096 else 7.6e-6) for _ in range(16)]))
    return dict(status="CONTROLLED_SHAPES_MEASURED_NOT_ADOPTED",exit_code=0,rows=rows)


class FullRowContract(unittest.TestCase):
    def test_requires_both_formats_exact_not_just_matching_top1(self):
        self.assertEqual(full.exact_shape_admission(control())["tile_rows"],4096)
        for kind in ("missing","exact","retained","cleanup","history"):
            data=deepcopy(control())
            if kind=="missing":data["rows"].pop()
            elif kind=="exact":data["rows"][-1]["all_exact"]=False
            elif kind=="retained":data["rows"][-1]["model_released"]=False
            elif kind=="cleanup":data["rows"][-1]["cleanup"]["allocated_bytes"]=1
            else:data["rows"][0]["original_allclose"]=True
            with self.assertRaises(ValueError):full.exact_shape_admission(data)

    def test_full_ids_metadata_case_order_and_count_required(self):
        value=dict(records=[dict(workload=str(i),observed=dict(generated_ids=[1,2],metadata=dict(finish_reason="EOS"))) for i in range(4)],
                   answers=[dict(case=dict(id=i),generation=dict(generated_ids=[1,4],metadata=dict(finish_reason="STOP_SEQUENCE"))) for i in range(4)])
        self.assertTrue(full.pairs_equal(value,deepcopy(value)))
        for kind in ("id","stop","order","missing"):
            bad=deepcopy(value)
            if kind=="id":bad["records"][0]["observed"]["generated_ids"]=[1,3]
            elif kind=="stop":bad["answers"][0]["generation"]["metadata"]["finish_reason"]="MAX_NEW"
            elif kind=="order":bad["records"].reverse()
            else:bad["records"].pop()
            with self.assertRaises(ValueError):full.pairs_equal(bad,value)


if __name__=="__main__":unittest.main()
