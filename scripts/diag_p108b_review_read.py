#!/usr/bin/env python3
"""Read complete Q/A text with exact, earlier-reviewed history references."""
import argparse
import json
from scripts import diag_p108b_geometry as atlas
from scripts.diag_p108b_review_pack import signature


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--start',type=int,required=True)
    parser.add_argument('--count',type=int,default=20);a=parser.parse_args()
    rows=json.loads((atlas.ROOT/'review_request/20261116_P108B_최종원답_v1/SOURCE_ROWS_v1.json').read_text(encoding='utf-8'))['rows']
    by={row['qa_signature']:row for row in rows}
    if not 0<=a.start<len(rows)or not 1<=a.count<=60:raise ValueError('bounded exact review range required')
    for index,row in enumerate(rows[a.start:a.start+a.count],a.start):
        refs=[];history=row['actual_history']
        for position in range(0,len(history),2):
            if history[position]['role']!='user'or history[position+1]['role']!='assistant':raise ValueError('paired actual history required')
            prior=dict(question=history[position]['content'],actual_history=history[:position],answer=history[position+1]['content'])
            previous=by[signature(prior)]
            if int(previous['review_id'][1:])>=index:raise ValueError('history must reference an earlier complete Q/A')
            refs.append(previous['review_id'])
        print(row['review_id']+' '+row['language']+' '+row['family']+' history='+','.join(refs))
        print('Q> '+row['question']);print('A> '+row['answer'])
        print('Expected> '+str(row['expected'])+'; strict='+str(row['exact'])+'; end='+row['generation']['finish_reason'])
        print()


if __name__=='__main__':main()
