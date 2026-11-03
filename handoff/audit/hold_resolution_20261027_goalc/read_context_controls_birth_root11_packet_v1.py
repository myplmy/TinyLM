"""Emit one complete, bounded packet using the existing role/byte guards."""
from pathlib import Path
import argparse, hashlib, importlib.util, json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
HELPER=HERE/'scoped_packet_reader_v1.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest().upper()=='DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6'
spec=importlib.util.spec_from_file_location('fixed_birth_reader',HELPER)
reader=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
parser=argparse.ArgumentParser()
parser.add_argument('--source-id',required=True)
parser.add_argument('--packet',type=int,required=True)
args=parser.parse_args()
registry=HERE/'SCOPED_CONTEXT_CONTROLS_BIRTH_ROOT11_INPUTS_V1.json'
expected='888805F2167F655D16334E6EC8F318BD155BCC4AA700FD71DEBE0FF781F2AF87'
first=reader.read_piece(registry,expected,ROOT,args.source_id,args.packet,1)
assert first['total_characters']<=4000 and first['pieces']<=2
parts=[first]+[reader.read_piece(registry,expected,ROOT,args.source_id,args.packet,n) for n in range(2,first['pieces']+1)]
assert parts[-1]['packet_complete'] and parts[0]['characters'][0]==0
assert all(a['characters'][1]==b['characters'][0] for a,b in zip(parts,parts[1:]))
assert parts[-1]['characters'][1]==first['total_characters']
metadata={k:v for k,v in parts[-1].items() if k!='text'}
print('APPROVED_COMPLETE_PACKET '+json.dumps(metadata,ensure_ascii=False))
print(''.join(p['text'] for p in parts),end='')
print(chr(10)+'END_APPROVED_COMPLETE_PACKET')
