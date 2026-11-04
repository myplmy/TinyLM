from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
HELPER=HERE/'scoped_packet_reader_v1.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest().upper()=='DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6'
s=importlib.util.spec_from_file_location('root12_reader',HELPER);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('source_id');p.add_argument('packet',type=int);a=p.parse_args()
row=m.read_piece(HERE/'SCOPED_ROOT12_CONTEXT_CONTROLS_INPUTS_V1.json','86ADF7F52484EF4D60245019A42180607C3D6FC14D709B92DEF6AE8511B29A1F',ROOT,a.source_id,a.packet,1)
print('APPROVED_PACKET '+json.dumps({k:v for k,v in row.items() if k!='text'},ensure_ascii=False));print(row['text'],end='');print(chr(10)+'END_APPROVED_PACKET')
