"""Read-only compact status. Completed reports take precedence over progress ticks."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).parent

def load(path):
    try:return json.loads(path.read_text()) if path.is_file() else None
    except (OSError,ValueError):return None

def progress(path):
    if not path.is_file():return 0
    values=[]
    for line in path.read_bytes()[-20000:].decode(errors='replace').splitlines():
        try:item=json.loads(line)
        except ValueError:continue
        if type(item) is dict and 'completed' in item:values.append(item['completed'])
    return max(values,default=0)

def state(folder,total=None,progress_log=None):
    value=load(folder/'report.json')
    if value and 'final_exit' in value:
        return '실행종료'+str(value['actual_rows'])+'/'+str(total)+'(코드'+str(value['final_exit'])+')'
    if folder.exists():
        n=progress(progress_log) if progress_log else 0
        return '단계진행'+(str(n)+'/'+str(total) if total else '')
    return '대기'

def main():
    gsm=ROOT/'test_result/evidence/p106b_gsm8k_nvml_v1_20261101'
    falcon=ROOT/'test_result/evidence/p106b_falcon_mmlu_v3_20261101'
    parts=[]
    for model,alias,suffix in [('native595-q','Native','Wa'),('new595-broad-q','Broad','Wb')]:
        name='P106B_Stage8z'+suffix+'_gsm8k_'+('native' if alias=='Native' else 'broad')+'_full_controller_stdout_v1.log'
        parts.append('GSM8K '+alias+' '+state(gsm/model/'full',1319,AUDIT/name))
    for shot in (0,5):
        folder=falcon/('shot'+str(shot))
        parts.append('Falcon'+str(shot)+' 비용:'+state(folder/'cost',114)+'/전량:'+state(folder/'full',14042))
    errors,closed=[],[]
    log=AUDIT/'COMPLETED_BENCHMARK_CPU_CONTROLLER_v4.log'
    if log.is_file():
        for line in log.read_text().splitlines():
            try:value=json.loads(line)
            except ValueError:continue
            if value.get('event') not in ('CPU_ROOT_FINISHED','CPU_ROOT_REUSED'):continue
            record=value['record']
            if record['status']=='ROOT_ERROR':errors.append(value['name'])
            elif record['actual_exit']==0:closed.append(value['name'])
    print(json.dumps(dict(message='; '.join(parts),cpu_root_errors=errors,cpu_root_closed=closed),ensure_ascii=False))

if __name__=='__main__':main()
