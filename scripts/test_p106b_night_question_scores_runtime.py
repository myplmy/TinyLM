"""Synthetic lifecycle/storage/budget contracts, never real model assets."""
from pathlib import Path
import copy
import tempfile
import unittest
from datetime import timedelta
from unittest.mock import patch
from scripts import diag_p106b_night_question_scores as d
from scripts.test_p106b_night_question_scores import cases,Tokenizer


def pairs():
    result=[]
    for language in ('ko','en'):
        rows=cases(language)
        for row in rows:row['root']=language+'_'+row['root']
        c=d.source.method.census(rows)['bundles'][0]
        result.append(dict(source_bundle_id=c['bundle_id'],source_definition_sha256=d.qa.data.sha(c),source_cases=rows))
    return result


def events(wire):
    result=[]
    for b in wire:
        for c in b['bundle']['cells']:
            r=d.method._event(c,[-2.]*(c['content_token_count']+1))
            r.update(source_bundle_id=b['source_bundle_id'],actual_x_tokens=len(c['x']),forward_precision='FP32_MATH')
            result.append(r)
    return result


class RuntimeTests(unittest.TestCase):
    def test_info_fields_do_not_collide_with_results(self):
        with patch.object(d.qa.data,'digest',return_value='A'*64):r=d.info()
        reserved={'status','cuda_initialized','wire','manifest','cost_bundle_ids','phase','endpoint','summary',
                  'input_report_sha256','directory','compute_seconds','whole_seconds','peak_reserved_mib'}
        self.assertFalse(set(r)&reserved)
        self.assertEqual(r['endpoints'],['base_qa','unique32k'])
        self.assertFalse(r['semantic_cross_answer_negatives_certified']);self.assertEqual(r['updates'],0)

    def test_all_cells_exact_source_mapping_and_wire_roundtrip(self):
        original=pairs();before=copy.deepcopy(original);wire=d.build_wire(original,Tokenizer())
        self.assertEqual(original,before);self.assertEqual(d.wire_summary(wire)['cells'],8)
        with tempfile.TemporaryDirectory(prefix='p106b_score_wire_') as folder,patch.object(d,'FROZEN',Path(folder)):
            manifest=d.save_wire(wire)
            self.assertEqual(d.restore_wire(manifest),wire)
            with self.assertRaises(FileExistsError):d.save_wire(wire)

    def test_definition_hash_and_duplicate_bundle_rejected(self):
        original=pairs();bad=copy.deepcopy(original);bad[0]['source_definition_sha256']='B'*64
        with self.assertRaises(ValueError):d.build_wire(bad,Tokenizer())
        with self.assertRaises(ValueError):d.build_wire(original+original,Tokenizer())

    def test_synthetic_prepare_then_read_source_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix='p106b_score_lifecycle_') as folder:
            root=Path(folder)
            with patch.object(d,'FROZEN',root/'source'),patch.object(d,'EVIDENCE',root/'evidence'),\
                    patch.object(d,'LOCAL',root/'local'),patch.object(d,'COUNTS',{'ko':1,'en':1}),\
                    patch.object(d,'read_sources',return_value=({},pairs())),\
                    patch.object(d.qa.data,'digest',return_value='A'*64),\
                    patch('tokenizers.Tokenizer.from_file',return_value=Tokenizer()):
                self.assertEqual(d.prepare(),0)
                frozen,wire=d.read_inputs()
                self.assertEqual(frozen['wire']['cells'],8)
                self.assertEqual(d.wire_summary(wire),frozen['wire'])
                self.assertEqual(len(frozen['cost_bundle_ids']),2)
                self.assertFalse(frozen['cuda_initialized'])

    def test_recount_checks_actual_source_shape_and_precision(self):
        wire=d.build_wire(pairs(),Tokenizer());raw=events(wire)
        self.assertEqual(d.recount(raw,wire,None)['cells'],8)
        for field,value in (('source_bundle_id','wrong'),('actual_x_tokens',0),('forward_precision','BF16')):
            bad=copy.deepcopy(raw);bad[0][field]=value
            with self.assertRaises(ValueError):d.recount(bad,wire,None)

    def test_summary_excludes_individual_records(self):
        wire=d.build_wire(pairs(),Tokenizer());report=d.recount(events(wire),wire,None)
        result=d.compact(report)
        self.assertNotIn('outcomes',result);self.assertEqual(result['overall']['bundles'],2)
        self.assertFalse(result['quality_pass_declared'])

    def test_budget_uses_actual_finite_cost_and_includes_load_reserve(self):
        r=dict(phase='cost',compute_seconds=2.,whole_seconds=12.,measured_bundles=2)
        self.assertEqual(d.forecast(r,110),225.)
        for key,value in (('compute_seconds',0),('compute_seconds',float('nan')),('compute_seconds',float('inf')),
                ('whole_seconds',float('nan')),('whole_seconds',1.),('measured_bundles',True),('phase','full')):
            with self.assertRaises(ValueError):d.forecast(dict(r,**{key:value}),110)

    def test_runtime_has_no_training_or_checkpoint_save(self):
        text=(d.ROOT/'scripts/diag_p106b_night_question_scores.py').read_text()
        for value in ('optimizer.step(', 'torch.save(', '.backward(', 'hf_hub_download('):self.assertNotIn(value,text)

    def test_gpu_deadline_recomputed_after_source_and_idle_checks(self):
        self.assertEqual(d.gpu_seconds(600,d.qa.TRAIN_STOP-timedelta(seconds=300)),299)
        self.assertEqual(d.gpu_seconds(100,d.qa.TRAIN_STOP-timedelta(seconds=300)),100)
        for now in (d.qa.TRAIN_STOP,d.qa.TRAIN_STOP-timedelta(seconds=119)):
            with self.assertRaises(ValueError):d.gpu_seconds(600,now)
        for cap in (True,0,601):
            with self.assertRaises(ValueError):d.gpu_seconds(cap)
        text=(d.ROOT/'scripts/diag_p106b_night_question_scores.py').read_text()
        self.assertIn('idle_before_gpu();seconds=gpu_seconds(seconds)',text)
        self.assertIn('probe.e.train.deadline(training=True)',text)


if __name__=='__main__':unittest.main()
