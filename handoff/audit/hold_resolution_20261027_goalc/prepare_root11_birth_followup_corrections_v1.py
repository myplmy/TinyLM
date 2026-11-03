"""Reuse exact role-copy guards for two observed birth-profile preservation defects."""
from pathlib import Path
import ast
import sys

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
source=AUDIT/'prepare_root11_1018113_correction_v1.py'
template=source.read_text(encoding='utf-8')
records={row['id']:row for row in inv.cache.read(AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V10.json')['records']}
notes={
 '1031233': '양하영의원문에는살아있는사람분류가실제로있는데ROOT11선택문에서삭제됐다. 상충출생연도1962/1961은양쪽모두원형sidecar에분리한상태를유지하고살아있는사람분류는원래그대로복원한다. 현재생존을외부검증한것이아니라원문주장을보존하는것이다. 원래6월14일·데뷔/작품·날짜·학력·수상·귀속은보존한다. 원문의실제기사제목/URL/출판사/저자/날짜/확인날짜가있는서지행은값을바꾸지않고읽을수있는서지구조로정리할수있다. 값없는쪽항목만분리하고날짜와확인날짜를합치지않는다. 없는한자명을추정하지않는다.',
 '1052119': '강지용의원문실제한자명姜志勇이출생연도분리과정에서함께삭제됐다. 그정확한이름을복원한다. 도입1952년과분류1968년은서로상충하는데선택문이1952만지우고1968을남겨한값을고른모양이됐다. 어느연도가참인지선택하지말고두해당출생연도표시만원형sidecar로분리한다. 원래8월27일·출생지·직업·살아있는사람/다른학력·경력·원문법률보도값·날짜와학교명/분류는원문대로유지한다. 외부정치인조사나사실정정은하지않는다.',
}
for digits,note in notes.items():
    record=records['expanded_train:'+digits]
    guide=chr(10).join(['# ROOT11 출생프로필 '+digits+' 의미보존 보완','',
        '지정역할legacy_review, 지정ID expanded_train:'+digits+' 하나다. 이폴더readonly원문/선택본문과새working/TXT/MD만허용한다. 기존입력/캐시/선택본문/리뷰는덮거나삭제하지않는다.',
        '코드/시험/통계/해시/웹/Git/모델/GPU/다른역할/보호자료는금지다. 실제정제본문은Luna가새버전으로만작성한다.','',
        '총괄이원문/기존선택문전부와전체diff를실제읽었다. 보완범위는아래뿐이다.',note,'',
        'expanded_train_'+digits+'_original.txt / expanded_train_'+digits+'_selected_root11.txt 는읽기전용이고 expanded_train_'+digits+'_working_v1.txt 만새작업용이다.',
        '새본문/원형sidecar/전체diff를실제로읽고 review_001.md 에정확ID/REVISE_TEXT/판독범위/실제TXT이름/구체사유를5열로연결한다. 첫리뷰뒤기존파일을덮지않는다. 이보완뒤기존field/other순차큐를계속한다.',''])
    class Adapt(ast.NodeTransformer):
        def visit_Constant(self,node):
            if not isinstance(node.value,str):return node
            if node.value.startswith('# ROOT11의 1018113 독립 의미검토 보완'):value=guide
            else:
                value=node.value.replace('1018113',digits).replace('semantic_field_counter_v1','remaining_birth_full_counter_v1')
                value=value.replace('context_latin','legacy_review').replace('root11_ordered_corrections_v1','root11_birth_'+digits+'_correction_v1')
                value=value.replace('8F07F8FDDC939027E280B2F32162C5ADEE7BD18C9D7B5674A20CBE92B7073E04',record['clean_text_sha256'])
                if node.value=='538c0c':value='7c7b99'
            return ast.copy_location(ast.Constant(value=value),node)
    tree=Adapt().visit(ast.parse(template));ast.fix_missing_locations(tree)
    exec(compile(tree,str(source),'exec'),{'__file__':__file__,'__name__':'exact_birth_profile_copy_publisher'})
