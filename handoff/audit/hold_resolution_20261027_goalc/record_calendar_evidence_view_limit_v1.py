"""Record the PDF screenshot timeout without discarding parsed primary rows."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
out=HERE/'CALENDAR_171249_EVIDENCE_VIEW_LIMIT_V1.json'
with out.open('x',encoding='utf-8') as stream:
    json.dump(dict(status='PARSED_PRIMARY_DATE_ROW_AND_SEPARATE_FIXED_PAGE_CHECKED_SCREENSHOT_FAILED',
        primary_pdf='https://jcdp.jp/wp-content/uploads/2020/08/2ed3543cba5c5b37bc7fe917711255ef.pdf',
        zero_based_page=145,printed_date_pair=['1725-03-29','享保10年2月15日'],
        parsed_header_checked=True,parsed_target_row_checked=True,
        screenshot_attempted=True,screenshot_succeeded=False,screenshot_failure='TimeoutError',
        secondary_fixed_page='https://ja.wikipedia.org/w/index.php?title=佐竹義都&oldid=106250221',
        calendar_conversion_executed=False,whole_biography_verified=False,
        goal_complete=False,training_authorized=False),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print('달력 원문 텍스트 대조와 이미지 도구 실패를 분리 기록')
