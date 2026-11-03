# 120798 원형 보류

register_taxonomy 예고·깨진 설정 및 그 직접 의존 조각:

> Here is an example for the registration of a "people" taxonomy: "people", "post", "label" => __('People' ),'rewrite' => array('slug' =>'person'),'assign_terms' =>'edit_guides','edit_terms' =>'publish_guides' ); add_action('init','people Here_init' ); the taxonomy "people" is define. It' is designed to work for postings, and a write slot is designed to turn the web address into '/person/' instead of '/people/'.
> This allows any of the users with the edit_guides function to associate the taxonomy with a contribution, and any of the users with the publish_guides function to generate new taxonomy elements.
> Here, you can

설정 예의 시작/인수 경계와 add_action 호출이 손상돼 있다. 그 설정을 근거로 한 직접 결과·권한 귀속은 새 코드나 관계로 고치지 않고 이 원형 묶음에 보존했다. 완결된 API 이름, 실제 권한 이름 및 taxonomy 기능 설명은 본문에서 유지했다.

깨진 WP_Query 예시 묶음:

> To create a mailing lists for example where "Bob" is included as a "Person" taxonomy, we use: $query = new WP_Query('person' =>'bob' ) ); or, for more sophisticated arguments: Taxonomy' => Person', Field' => Slug', Terms' => Bob'); $query = new WP_Query( $args);

두 호출 모두 표기/구조가 손상되어 있으므로 인수, 따옴표, 괄호, 분류값을 복원하지 않았다. 앞의 명명된 `wp_set_object_terms()`·`wp_tag_cloud()`·`the_terms()`·`get_terms()` 정보와 완결된 `wp_set_object_terms( 123, 'Bob', 'Person')` 호출은 보존했다.

고립된 문자열 꼬리:

> ';

깨진 설정/인용의 잔여로 보이는 원형만 보존했으며 새 의미를 붙이지 않았다.
