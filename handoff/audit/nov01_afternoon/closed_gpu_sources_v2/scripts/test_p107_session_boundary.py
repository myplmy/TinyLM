"""CPU document boundaries and complete scheduled disk-resume equivalence."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
import json
import random
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
from tinylm.train.document_source import ExplicitDocumentSource
from tinylm.train.hybrid_session import HybridTrainingSession
from tinylm.train.boundary_store import save_new,load_complete
from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer
from scripts.test_p107_adaptive_training import ToyAttention

torch.set_num_threads(1)


def source():
    return ExplicitDocumentSource([torch.arange(35,64),torch.tensor([40,41,42]),torch.arange(36,62)],
        ['explicit-a','explicit-b','explicit-c'],batch=2,length=16,micros=4,vocab=64,seed=23)


def session(schedule='cosine'):
    torch.manual_seed(1337);random.seed(1337);np.random.seed(1337)
    data=source();model=ToyAttention()
    config=PolicyConfig(64,.5,.2,2,'keep',23,34,13,data.corpus_sha256,'B'*64)
    trainer=AdaptiveMNTPTrainer(model,[torch.optim.AdamW(model.parameters(),lr=.001)],data,
        policy_config=config,mode='adaptive',masked_micros=2,signature='C'*64,
        collect_ids=lambda logits,targets:logits.argmax(-1).cpu())
    return HybridTrainingSession(trainer,total_updates=7,warmup_updates=2,schedule=schedule)


class SessionBoundaryTests(unittest.TestCase):
    def assert_tree(self,a,b):
        self.assertEqual(type(a),type(b))
        if isinstance(a,torch.Tensor):self.assertTrue(torch.equal(a,b))
        elif isinstance(a,dict):
            self.assertEqual(set(a),set(b))
            for key in a:self.assert_tree(a[key],b[key])
        elif isinstance(a,(tuple,list)):
            self.assertEqual(len(a),len(b))
            for x,y in zip(a,b):self.assert_tree(x,y)
        else:self.assertEqual(a,b)

    def test_explicit_boundaries_and_pad(self):
        data=source();seen_short=False
        for _ in range(12):
            for tokens,docs in data.next_update():
                for row,ids in zip(tokens,docs):
                    valid=ids>=0
                    index=int(ids[0]);self.assertTrue(bool((ids[valid]==index).all()))
                    document=data.documents[index]
                    sequence=row[valid]
                    self.assertTrue(any(torch.equal(document[i:i+len(sequence)],sequence)
                        for i in range(len(document)-len(sequence)+1)))
                    if index==1:
                        seen_short=True;self.assertEqual(int(valid.sum()),3)
                        self.assertTrue(bool((row[~valid]==0).all()))
        self.assertTrue(seen_short)

    def test_source_input_copy_and_resume(self):
        original=torch.arange(35,64)
        data=ExplicitDocumentSource([original],['a'],batch=1,length=8,micros=2,vocab=64,seed=1)
        original.fill_(1)
        self.assertEqual(int(data.documents[0][0]),35)
        data.next_update();saved=data.state_dict();expected=data.next_update()
        data.load_state_dict(saved);self.assert_tree(expected,data.next_update())

    def test_changed_document_or_invalid_rng_rejected(self):
        data=source();state=data.state_dict();state['signature']='D'*64
        with self.assertRaises(ValueError):data.load_state_dict(state)
        state=data.state_dict();state['rng']=torch.ones(3)
        with self.assertRaises((TypeError,RuntimeError)):data.load_state_dict(state)
        self.assertEqual(data.cursor,0)

    def test_wrong_input_or_reserved_mask_refused(self):
        for values in [torch.tensor([35,13,36]),torch.tensor([35.,36.,37.]),torch.tensor([35,36])]:
            with self.assertRaises(ValueError):
                ExplicitDocumentSource([values],['a'],batch=1,length=8,micros=2,vocab=64,seed=1)

    def test_scheduled_disk_resume_exact_including_dropout(self):
        current=session();current.update();current.update()
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'snapshot'
            saved=current.state_dict();manifest=save_new(saved,target,part_bytes=1024)
            self.assertGreater(len(manifest['parts']),1)
            loaded=load_complete(target);self.assert_tree(saved,loaded)
            expected=[current.update() for _ in range(3)];end=current.state_dict()
            resumed=session();resumed.load_state_dict(loaded)
            actual=[resumed.update() for _ in range(3)]
            for left,right in zip(expected,actual):
                for key in ('update','loss','masked_targets','causal_targets','schedule_lrs'):
                    self.assertEqual(left[key],right[key])
            self.assert_tree(end,resumed.state_dict())

    def test_schedule_mismatch_rejected_before_state_copy(self):
        current=session();current.update();saved=current.state_dict()
        other=session('wsd');before=other.state_dict()
        with self.assertRaises(ValueError):other.load_state_dict(saved)
        self.assert_tree(before,other.state_dict())

    def test_partial_optimizer_requires_full_session_restore(self):
        current=session();state=current.state_dict()
        opt=current.trainer.optimizers[0]
        def failed():
            with torch.no_grad():next(current.trainer.model.parameters()).add_(1)
            raise RuntimeError('partial optimizer')
        with patch.object(opt,'step',side_effect=failed):
            with self.assertRaises(RuntimeError):current.update()
        self.assertTrue(current.dirty)
        with self.assertRaises(ValueError):current.state_dict()
        current.load_state_dict(state);current.update()
        self.assertFalse(current.dirty)

    def test_completed_schedule_cannot_continue(self):
        current=session();current.contract['total_updates']=1
        current.contract['warmup_updates']=0
        current.update()
        with self.assertRaises(ValueError):current.update()

    def test_directory_collision_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'snapshot'
            manifest=save_new({'known':torch.arange(5)},target)
            with self.assertRaises(FileExistsError):save_new({'wrong':1},target)
            self.assertTrue(torch.equal(load_complete(target)['known'],torch.arange(5)))
            self.assertEqual(json.loads((target/'manifest.json').read_text()),manifest)

    def test_corruption_and_partial_storage_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'snapshot';save_new({'x':torch.arange(800)},target,part_bytes=1024)
            part=target/'part_000000.bin';raw=part.read_bytes()
            part.write_bytes(bytes([raw[0]^1])+raw[1:])
            with self.assertRaises(ValueError):load_complete(target)
            other=Path(tmp)/'partial';other.mkdir();(other/'part_000000.bin').write_bytes(b'partial')
            with self.assertRaises(ValueError):load_complete(other)

    def test_manifest_cannot_redirect_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'snapshot';save_new({'x':1},target)
            path=target/'manifest.json';data=json.loads(path.read_text())
            data['parts'][0]['path']='../outside'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):load_complete(target)


if __name__=='__main__':unittest.main()
