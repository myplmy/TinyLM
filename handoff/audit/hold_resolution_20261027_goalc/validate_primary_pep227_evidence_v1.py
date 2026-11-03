"""Check exact original-token correspondence to already viewed primary examples."""
from pathlib import Path
import ast
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

source_path=inv.BASE/'remaining_literal_full_counter_v1/inputs/expanded_train_1418578_original.txt'
expected='FF0DB57BF072E532257E98ECF9C83A376CCD43BC835036BCA7346955CBD27F68'
assert inv.file_sha(source_path)==expected
text=source_path.read_text(encoding='utf-8')
primary_bank='''def bank_account(initial_balance):
    balance = [initial_balance]
    def deposit(amount):
        balance[0] = balance[0] + amount
        return balance
    def withdraw(amount):
        balance[0] = balance[0] - amount
        return balance
    return deposit, withdraw'''
start=text.index('def bank_account(initial_balance):')
end=text.index('return deposit, withdraw',start)+len('return deposit, withdraw')
raw_bank=text[start:end]
norm=lambda value: ''.join(value.split())
assert norm(primary_bank.replace('[0]',''))==norm(raw_bank)
assert primary_bank.count('[0]')==4
ast.parse(primary_bank)  # Static syntax only; no example code is executed.
primary_tim='''i = 6
def f(x):
    def g():
        print i
    # ...
    # skip to the next page
    # ...
    for i in x:  # ah, i *is* local to f, so this is what g sees
        pass
    g()'''
start=text.index('i = 6 def f(x): def g(): print i')
end=text.index('The call to g()',start)
assert norm(primary_tim)==norm(text[start:end])
old="if attr != '_':"
assert text.count(old)==1
result=dict(status='PRIMARY_EXACT_TOKEN_LINKS_INDEX_RECOVERY_NOT_CLEANED_TEXT',
    original=dict(path=str(source_path.relative_to(ROOT)),sha256=expected),
    primary_url='https://peps.python.org/pep-0227/',
    primary_observation='Official PEP lines137-146 and212-220 and wrapper condition viewed directly',
    bank=dict(original_characters=[text.index('def bank_account(initial_balance):'),
        text.index('return deposit, withdraw')+len('return deposit, withdraw')],
        only_nonwhitespace_change='restore four exact [0] indices on assignment left/right',
        added_index_zeros=4,return_balance_unchanged=True,static_ast_parse=True,
        indentation_columns=[0,4,4,8,8,4,8,8,4]),
    wrapper=dict(only_condition_change='restore attr[0] from the exact primary condition',added_index_zeros=1),
    tim=dict(nonwhitespace_tokens_identical=True,code_comment_preserved=True,
        indentation_columns=[0,0,4,8,4,4,4,4,8,4],python_version='original Python2 print syntax retained'),
    cleaned_source_written=False,example_code_executed=False,
    producer_sha256=inv.file_sha(Path(__file__)),goal_complete=False,training_authorized=False)
output=AUDIT/'PRIMARY_PEP227_EXACT_RECOVERY_EVIDENCE_V1.json'
assert not output.exists()
inv.write_json(output,result)
print(json.dumps(dict(bank_indices=4,wrapper_indices=1,original_bank_tokens_match=True,
    tim_tokens_match=True,code_executed=False)))
