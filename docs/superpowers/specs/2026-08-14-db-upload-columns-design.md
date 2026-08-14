# DB 적재용 Excel 시트 설계

## 목적

현재 임베딩 통합문서의 원본 시트와 표시명을 보존하면서 PostgreSQL 및 Supabase에 바로 적재하기 쉬운 영문 `snake_case` 구조를 추가한다.

## 적용 방식

- 기존 `Total 150`, `DB 135`, `Test 15` 시트는 변경하지 않는다.
- `DB Upload 135`와 `Test Upload 15` 시트를 추가한다.
- DB 적재 시트에는 두 번째 빈 행을 제거하고 헤더 다음 행부터 데이터가 이어지게 한다.
- `DB Upload 135`에는 DB 등록용 135건, `Test Upload 15`에는 검증용 15건만 포함한다.
- 날짜와 본문 등의 원본 값은 유지한다.
- 기존에 정규화한 종결 상태값 `closed`는 그대로 유지한다.
- 임베딩은 PostgreSQL `pgvector`로 변환하기 쉬운 `[값,값,...]` 문자열 형식을 유지한다.

## 컬럼 매핑

| 기존 컬럼 | DB 적재용 컬럼 |
|---|---|
| Case ID | case_id |
| Customer name | customer_name |
| Country | country |
| VOC Type | voc_type |
| VOC Subtype | voc_subtype |
| Priority | priority |
| Customer Request | customer_request |
| Original Mail Body | original_mail_body |
| Responsible Dept. | responsible_departments |
| Received | received_at |
| First Response | first_response_at |
| Containment | containment_at |
| 5D Root Cause Action | root_cause_action_5d_at |
| Customer Reply | customer_reply_at |
| Final Status | final_status |
| Delay Stage | delay_stage |
| Delay Reason | delay_reason |
| Auto Close | auto_close |
| Reactivated | reactivated |
| 6D Due | due_6d_at |
| 6D Result | result_6d |
| Full Response History | full_response_history |
| customer_request_embedding | customer_request_embedding |
| original_mail_body_embedding | original_mail_body_embedding |

## 검증 기준

- 두 적재 시트의 컬럼 수가 각각 24개인지 확인한다.
- 데이터 건수가 각각 135건과 15건인지 확인한다.
- `case_id`가 비어 있거나 중복되지 않았는지 확인한다.
- 두 임베딩 컬럼의 모든 값이 384차원인지 확인한다.
- 오류 수식이나 잘린 핵심 헤더가 없는지 렌더링으로 확인한다.

## 제외 범위

- 이 단계에서는 부서 목록을 별도 관계형 테이블로 분리하지 않는다.
- `Y/N` 값을 Boolean으로 변환하지 않는다.
- VOC 유형, 우선순위 등 범주값을 별도 코드 테이블로 치환하지 않는다.
