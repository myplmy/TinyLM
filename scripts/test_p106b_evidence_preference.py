#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
import torch
from tokenizers import Tokenizer
from scripts import p106b_evidence_preference as m
from scripts import p101a_sft_mtp_data as data


class Pairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if data.digest(data.TOKENIZER)!=data.TOK_SHA:raise ValueError('actual tokenizer changed')
        cls.tok=Tokenizer.from_file(str(data.TOKENIZER))

    def test_all_families_conditions_languages(self):
        modes=set()
        for g in m.previous.graphs(4,'train'):
            for lang in ('ko','en'):
                for c in range(4):
                    p=m.make_pair(g,lang,c,0,self.tok);modes.add(p['mode'])
                    self.assertEqual(p['chosen']['messages'][0],p['rejected']['messages'][0])
                    self.assertNotEqual(p['chosen']['messages'][1],p['rejected']['messages'][1])
        self.assertEqual(modes,{'UNNECESSARY_CLARIFICATION','UNSUPPORTED_ASSERTION'})

    def test_no_eval_graph_training(self):
        with self.assertRaises(ValueError):m.make_pair(m.previous.graphs(4,'test')[0],'ko',0,0,self.tok)

    def test_hidden_missing_fact_not_in_prompt(self):
        g=m.previous.graphs(4,'train')[0];p=m.make_pair(g,'en',0,0,self.tok)
        meta=p['chosen']['meta'];self.assertFalse(meta['query_sufficient'])
        self.assertNotIn(meta['omitted_key'],meta['first_available_keys'])

    def test_positive_and_negative_assistant_masks(self):
        from tinylm.train.mtp_sft import encode_record
        g=m.previous.graphs(4,'train')[0]
        for p in (m.make_pair(g,'ko',0,0,self.tok),m.make_pair(g,'en',1,1,self.tok)):
            for side in ('chosen','rejected'):
                r=encode_record(p[side],self.tok);self.assertGreater(r.targets,0)
                self.assertEqual({s for y,s in zip(r.y,r.segments) if y!=-100},{1})
                self.assertLessEqual(r.x_tokens,1024)

    def test_balanced_frozen_graph_selection(self):
        graphs=m.previous.graphs(16,'train');a=m.select_graphs(graphs,8,'tag')
        self.assertEqual(a,m.select_graphs(list(reversed(graphs)),8,'tag'))
        self.assertEqual(len({m.previous.neutral(g) for g in a}),8)

    def test_fresh_test_excludes_two_previous_cohorts(self):
        primary=m.previous.base.graphs(128,'test');excluded={m.previous.neutral(g) for g in primary}
        old=m.previous.graphs(128,'test',exclude=excluded);new=m.fresh_test(old,'tag')
        self.assertEqual(len(new),128)
        self.assertFalse({m.previous.neutral(g) for g in old}&{m.previous.neutral(g) for g in new})
        self.assertFalse(excluded&{m.previous.neutral(g) for g in new})

    def test_zero_beta_gradient_and_odds_direction(self):
        x=torch.tensor([-1.,-2.],requires_grad=True);main=x.square().sum();pref=m.odds.preference_loss(x[:1],x[1:]).sum()
        self.assertTrue(torch.equal(torch.autograd.grad(main+0.*pref,x,retain_graph=True)[0],torch.autograd.grad(main,x,retain_graph=True)[0]))
        gc,gr=torch.autograd.grad(pref,x)[0];self.assertLessEqual(gc,0);self.assertGreaterEqual(gr,0)

    def test_no_repeat_penalty_or_generic_text_admission(self):
        self.assertEqual(m.ARMS,{'sft_only':0.,'orpo010':.1})
        with self.assertRaises((KeyError,TypeError,ValueError)):m.make_pair({'split':'train'},'ko',0,0,self.tok)

    def test_visible_alias_keeps_two_distinct_producer_negatives(self):
        import copy
        p=m.make_pair(m.previous.graphs(4,'train')[0],'ko',0,0,self.tok);other=copy.deepcopy(p)
        other['root']='B'*64
        for side in ('chosen','rejected'):other[side]['meta']['semantic_root_id']=other['root']
        other['rejected']['messages'][-1]['content']=[dict(type='text',text='another unsupported candidate')]
        index=m.index_pairs([p,other]);self.assertEqual(len(index),2)
        self.assertEqual(index[p['root']]['chosen']['messages'],index[other['root']]['chosen']['messages'])
        with self.assertRaises(ValueError):m.index_pairs([p,p])


if __name__=='__main__':unittest.main()
