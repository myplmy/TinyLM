"""Optional LR/session boundary around the existing adaptive trainer."""
from __future__ import annotations

import copy
import math
from .anneal_schedule import lr_factor


class HybridTrainingSession:
    def __init__(self, trainer, *, total_updates, warmup_updates=0, schedule='stable', decay_fraction=.2):
        if (type(total_updates) is not int or total_updates<1 or type(warmup_updates) is not int
                or not 0<=warmup_updates<total_updates or schedule not in ('stable','cosine','wsd','decay')
                or type(decay_fraction) not in (int,float) or not math.isfinite(decay_fraction)
                or not 0<decay_fraction<=1):
            raise ValueError('명시한 전체 학습률 스케줄 계약이 필요합니다')
        self.trainer=trainer
        self.contract=dict(total_updates=total_updates,warmup_updates=warmup_updates,
            schedule=schedule,decay_fraction=float(decay_fraction))
        self.base_lrs=[[float(g['lr']) for g in o.param_groups] for o in trainer.optimizers]
        if any(not math.isfinite(lr) or lr<=0 for group in self.base_lrs for lr in group):
            raise ValueError('각 optimizer group의 양수 기준 LR이 필요합니다')
        self.active,self.dirty=False,False

    @property
    def cursor(self):
        return self.trainer.cursor

    def update(self):
        if self.active or self.dirty or self.cursor>=self.contract['total_updates']:
            raise ValueError('정상 완료 경계·남은 스케줄 또는 전체 복원이 필요합니다')
        self.active=True
        try:
            c=self.contract
            factor=lr_factor(self.cursor,c['warmup_updates'],c['total_updates'],c['schedule'],c['decay_fraction'])
            lrs=[]
            for optimizer,initial in zip(self.trainer.optimizers,self.base_lrs):
                if len(optimizer.param_groups)!=len(initial):
                    raise ValueError('실행 중 optimizer group이 바뀌었습니다')
                values=[]
                for group,base in zip(optimizer.param_groups,initial):
                    group['lr']=base*factor
                    values.append(group['lr'])
                lrs.append(values)
            row=self.trainer.update()
            row['schedule_lrs']=lrs
            return row
        except BaseException:
            self.dirty=True
            raise
        finally:
            self.active=False

    def state_dict(self):
        if self.active or self.dirty:
            raise ValueError('정상 완료 세션만 저장할 수 있습니다')
        return dict(schema='P107_HYBRID_SESSION_V1',contract=copy.deepcopy(self.contract),
            base_lrs=copy.deepcopy(self.base_lrs),trainer=self.trainer.state_dict())

    def load_state_dict(self,state):
        if self.active:
            raise ValueError('진행 중 세션은 복원할 수 없습니다')
        if (state.get('schema')!='P107_HYBRID_SESSION_V1' or state.get('contract')!=self.contract
                or state.get('base_lrs')!=self.base_lrs
                or type(state.get('trainer',{}).get('cursor')) is not int
                or not 0<=state['trainer']['cursor']<=self.contract['total_updates']):
            raise ValueError('다른 전체 스케줄·기준 LR·cursor입니다')
        self.dirty=True
        self.trainer.load_state_dict(state['trainer'])
        self.dirty=False
