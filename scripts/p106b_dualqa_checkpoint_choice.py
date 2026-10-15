"""DEV-only checkpoint choice; no data, model or TEST access."""
import math
RULE='MIN_SOURCE_DEV_CE_EPOCH1_TO4_EARLY_TIE_V1'


def choose(report):
    if report['status']!='TRAINED_NEW_SOURCE_TEST_PENDING' or report['updates']!=176:
        raise ValueError('complete four-epoch course required')
    history=report['history']
    if sorted(h['epoch'] for h in history)!=[1,2,3,4]:raise ValueError('all four unique epochs required')
    for h in history:
        if h['updates']!=44*h['epoch'] or not math.isfinite(h['dev']['source_ce']) or h['dev']['source_ce']<=0:
            raise ValueError('finite source DEV CE and exact epoch steps required')
    best=min(history,key=lambda h:(h['dev']['source_ce'],h['epoch']))
    return dict(rule=RULE,epoch=best['epoch'],updates=best['updates'],source_dev_ce=best['dev']['source_ce'],
        checkpoint=best['checkpoint'],checkpoint_sha256=best['checkpoint_sha256'],
        final4epoch_stays_primary=True,selected_by_test=False,
        selection_scope='teacher-forced DEV source CE only; not free-answer or world truth')
