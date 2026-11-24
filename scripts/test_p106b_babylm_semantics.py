"""Official decoder/mask/order/2-versus5-candidate rank contracts; model0."""
import argparse
from collections import Counter,defaultdict
from pathlib import Path
import unittest
from scripts import p106b_babylm_semantics as core

SOURCE=Path(__file__).resolve().parents[1]/'data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp/source/strict/evaluation_pipeline/sentence_zero_shot'

class CharacterProcessor:
    def __call__(self,*,text,return_offsets_mapping):
        return dict(input_ids=[1]+[ord(c)%71+2 for c in text],attention_mask=[1]*(len(text)+1),
            offset_mapping=[[0,0]]+[[i,i+1] for i in range(len(text))])

def entity():return dict(input_prefix='The answer is ',options=['apple','stone','paper','wood','water'],numops=1)

class BabyLMSemanticContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        cls.torch=torch
    def official(self):return core.load_official(SOURCE,self.torch,device='cpu')[0]
    def test_author_entity_skip_is_exact_and_comps_keeps_original_join(self):
        official=self.official();raw=entity();raw['options'][1]='nothing here'
        self.assertEqual(core.decode(official,'entity_tracking',raw,'regular.jsonl'),[])
        raw['options'][1]='Nothing here'
        self.assertEqual(len(core.decode(official,'entity_tracking',raw,'regular.jsonl')),1)
        row=core.decode(official,'comps',dict(prefix_acceptable='ab',prefix_unacceptable='ef',property_phrase='cd'),'comps_base.jsonl')[0]
        self.assertEqual(row['sentences'],['ab cd','ef cd']);self.assertEqual(row['completions'],['cd','cd'])
    def test_original_getitem_and_collate_shift_only_the_completion_mask(self):
        official=self.official()
        row=core.decode(official,'comps',dict(prefix_acceptable='ab',prefix_unacceptable='ef',property_phrase='cd'),'comps_base.jsonl')[0]
        item=core.processed_item(official,CharacterProcessor(),row)
        self.assertEqual(item[1]['sentence_0_phrase_mask'].tolist(),[0,0,0,0,1,1])
        batch=official['get_causal_collate_fn'](0)([item])[1]
        self.assertEqual(batch['sentence_0_phrase_mask'].tolist(),[[0,0,0,1,1]])
        self.assertEqual(batch['sentence_0_targets'][0,-2:].tolist(),item[1]['sentence_0_tokens'][-2:].tolist())
    def test_original_phrase_mask_keeps_a_token_that_overlaps_the_suffix_boundary(self):
        official=self.official()
        row=core.decode(official,'comps',dict(prefix_acceptable='ab',prefix_unacceptable='ef',property_phrase='cd'),'comps_base.jsonl')[0]
        class MergedProcessor:
            def __call__(self,**kwargs):return dict(input_ids=[1,2,3],attention_mask=[1,1,1],offset_mapping=[[0,0],[0,4],[4,5]])
        item=core.processed_item(official,MergedProcessor(),row)
        self.assertEqual(item[1]['sentence_0_phrase_mask'].tolist(),[0,1,1])
    def test_variable_candidates_only_split_adjacent_batches_without_reordering(self):
        records=[dict(index=i,decoded=dict(sentences=['a']*n)) for i,n in enumerate((2,2,5,5,2))]
        batches=list(core.contiguous_batches(records,size=8))
        self.assertEqual([[r['index'] for r in batch] for batch in batches],[[0,1],[2,3],[4]])
    def test_original_two_and_five_candidate_rank_rng_and_prediction_fields(self):
        torch=self.torch
        for task in core.TASKS:
            with self.subTest(task=task):
                official=self.official();args=argparse.Namespace(task=task,images_path=None,save_predictions=True)
                if task=='comps':
                    row=core.decode(official,task,dict(prefix_acceptable='ab',prefix_unacceptable='ef',property_phrase='cd'),'comps_base.jsonl')[0]
                else:row=core.decode(official,task,entity(),'regular.jsonl')[0]
                records=[dict(decoded=row,trace=dict(line=i+1)) for i in range(2)]
                items=[core.processed_item(official,CharacterProcessor(),row) for _ in records]
                raw=[item[0] for item in items];labels=[item[2] for item in items]
                metas=[item[3] for item in items];uids=[item[4] for item in items]
                stats={1.:{}};official['update_subset_to_stats'](stats,metas);pred={1.:defaultdict(list)}
                n=len(row['sentences']);scores={1.:[torch.tensor([-float(i+1),-1.],dtype=torch.float32) for i in range(n)]}
                events=[];torch.manual_seed(1337)
                with core.RankAudit(official,torch,task=task,sink=events.append) as audit:
                    audit.set_batch(records,items);official['rank_and_evaluate'](args,stats,scores,raw,labels,metas,uids,pred)
                _accuracies,average=official['process_results'](args,stats)
                summary=audit.summary(average[1.],expected_by_uid=dict(Counter(uids)))
                self.assertEqual(summary['rows'],2);self.assertEqual(summary['exact_ties'],1)
                self.assertEqual(len(events[0]['native_inputs']),n)
                expected_field='sentences' if task=='comps' else 'completions'
                self.assertEqual(pred[1.][uids[0]][0]['pred'],row[expected_field][0])
    def test_independent_audit_rejects_an_incorrect_original_prediction_string(self):
        torch=self.torch;official=self.official();original_rank=official['rank_and_evaluate']
        def corrupt(*args):
            original_rank(*args);next(iter(args[-1][1.].values()))[0]['pred']='CORRUPTED'
        official['rank_and_evaluate']=corrupt
        row=core.decode(official,'entity_tracking',entity(),'regular.jsonl')[0]
        item=core.processed_item(official,CharacterProcessor(),row)
        args=argparse.Namespace(task='entity_tracking',images_path=None,save_predictions=True)
        stats={1.:{}};official['update_subset_to_stats'](stats,[item[3]])
        scores={1.:[torch.tensor([-float(i+1)],dtype=torch.float32) for i in range(5)]}
        with core.RankAudit(official,torch,task='entity_tracking') as audit:
            audit.set_batch([dict(decoded=row,trace=dict(line=1))],[item])
            with self.assertRaisesRegex(ValueError,'prediction/string'):
                official['rank_and_evaluate'](args,stats,scores,[item[0]],[item[2]],[item[3]],[item[4]],{1.:defaultdict(list)})

if __name__=='__main__':unittest.main()
