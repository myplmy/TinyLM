"""Reuse the validated field-page machinery for all remaining other-type pages."""
from pathlib import Path
import re

AUDIT=Path(__file__).resolve().parent
def adapt(source_name,target_name,identity=False):
    text=(AUDIT/source_name).read_text(encoding='utf-8')
    for before,after in [
        ('remaining_field_title_native_proofs_v1','remaining_other_types_native_proofs_v1'),
        ('remaining_field_title_readers_v1','remaining_other_types_readers_v1'),
        ('remaining_field_title_page_','remaining_other_types_page_'),
        ('REMAINING_FIELD_TITLE','REMAINING_OTHER_TYPES'),
        ('SCOPED_CONTEXT_CONTROLS_FIELD_PAGE_','SCOPED_CONTEXT_CONTROLS_OTHER_TYPES_PAGE_'),
        ('read_context_controls_field_page_','read_context_controls_other_types_page_'),
        ('FIELD_OR_TITLE_ROLE_REQUIRES_INDEPENDENT_SOURCE_READING','OTHER_TYPES_REQUIRE_INDEPENDENT_SOURCE_READING'),
        ('ALL_FIELD_PAGES_PREPARED_NOT_CONTENT_REVIEWED','ALL_OTHER_TYPE_PAGES_PREPARED_NOT_CONTENT_REVIEWED'),
        ('ALL_FIELD_READING_LINKS_READY_NOT_CONTENT_READ','ALL_OTHER_TYPE_READING_LINKS_READY_NOT_CONTENT_READ'),
        ('EXACT_FIELD_PAGE_NATIVE_FULL_READING_REQUIRED_NOT_ADMISSION','EXACT_OTHER_TYPE_PAGE_FULL_READING_REQUIRED_NOT_ADMISSION'),
        ('all_field_sources','all_other_type_sources'),
    ]:
        text=text.replace(before,after)
    # Whole numeric literals only: preserve hashes containing the digits36.
    for before,after in [('18237','50162'),('29659','77879'),('36','98')]:
        text=re.sub(r'\b'+before+r'\b',after,text)
    text=text.replace('36페이지','98페이지')
    text=text.replace('필드·제목 유형 전량의 일부 페이지다.','다른 잔여 유형 전량의 일부 페이지다.')
    text=text.replace('필드·제목 관계의 전량 원문 판독','다른 잔여 유형의 전량 문맥 판독')
    text=text.replace('현재 literal 전량 배정을 마친 뒤 총괄이 이 페이지 착수를 알리면 사용한다.',
        '필드·제목36페이지의 자기 모든TASK를 마친 뒤 총괄이 이 다음유형 착수를 알리면 사용한다.')
    text=text.replace('현재 literal TASK072까지 처리하고 남은 좁은 중재를 정확 리뷰로 연결한 뒤, 총괄이 허용한 페이지부터 시작한다.',
        '필드·제목36페이지의 자기 모든TASK와 중재연결을 마친 뒤, 총괄이 허용한 다음유형 페이지부터 시작한다.')
    assert 'remaining_field_title_' not in text and '18237' not in text
    if identity:
        assert 'BCE445B7C4897A75926EAC3618D5EFBC8E5F371EC71D891E1B41966F36F0A588' in text
    compile(text,target_name,'exec')
    with (AUDIT/target_name).open('x',encoding='utf-8') as stream:stream.write(text)
adapt('prepare_remaining_field_title_readers_v1.py','prepare_remaining_other_types_readers_v1.py')
adapt('prepare_remaining_field_title_identity_and_controls_v1.py',
    'prepare_remaining_other_types_identity_and_controls_v1.py',True)
print('other-type reader and exact-input adapters saved; frozen helpers unchanged')
