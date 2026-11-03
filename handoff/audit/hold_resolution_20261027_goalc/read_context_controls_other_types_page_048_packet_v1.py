from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
HELPER=HERE/'scoped_packet_reader_v1.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest().upper()=='DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6'
spec=importlib.util.spec_from_file_location('assigned_input_reader',HELPER)
reader=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
parser=argparse.ArgumentParser()
parser.add_argument('--source-id',required=True)
parser.add_argument('--packet',type=int,required=True)
parser.add_argument('--piece',type=int,required=True)
args=parser.parse_args()
row=reader.read_piece(HERE/'SCOPED_CONTEXT_CONTROLS_OTHER_TYPES_PAGE_048_INPUTS_V1.json','680D0D1BBFEE04FEE610A2E740E6001553A746DB4DD48251B572C74F7687F8D1',ROOT,args.source_id,args.packet,args.piece)
print('APPROVED_PACKET_PIECE '+json.dumps({k:v for k,v in row.items() if k!='text'},ensure_ascii=False))
print(row['text'],end='')
print(chr(10)+'END_APPROVED_PACKET_PIECE')
