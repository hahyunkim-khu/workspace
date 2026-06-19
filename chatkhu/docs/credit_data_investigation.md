# 크레딧 데이터 집계 조사 결과

작성일: 2026-06-19

---

## 배경

구글 시트에 입력된 월별 조직 크레딧 사용량과 관리자 대시보드 API 응답값이 불일치하는 문제를 조사.

**시트에 입력된 값 (원인 불명, 코드 유실)**
| 월 | 시트 값 |
|---|---|
| 2026-03 | 2,701,559 |
| 2026-04 | 3,868,085 |
| 2026-05 | 4,796,119 |
| 2026-06 (1~15일) | 5,587,799 |

---

## API 엔드포인트 두 가지

### ① `dashboards/usage/export-task`
```
GET /api/proxy/admin/dashboards/usage/export-task/
    ?response_type=csv&start_date=...&end_date=...&credit_source=organization
```
- **조직 크레딧 풀에서 실제 차감된 금액만** 집계
- 기간 내 총합 (org only) 제공
- 유저별·신분별 분류 **불가**

### ② `members/export-task`
```
GET /api/proxy/admin/members/export-task/
    ?response_type=csv&start_date=...&end_date=...&credit_source=organization
```
- `credit_source=organization` 파라미터는 **조직 소속 유저를 필터**할 뿐
- `기간 내 크레딧 사용량 총합` 컬럼 = **조직 크레딧 + 개인 구매 크레딧 포함**
- 유저별·신분별(학생/교수/교직원) 분류 **가능**
- `개인 구매 크레딧 사용량` 컬럼 = 누적값 (기간 필터 무관하게 항상 전체 누적)

---

## 크로스체크 결과

`code/crosscheck_monthly_credits.py` 실행 결과 (2026-06-19 기준):

| 월 | 대시보드 API (org only) | daily_data_organization 합산 | 차이 | 배율 |
|---|---|---|---|---|
| 2026-03 | 2,682,479 | 3,191,114 | +508,635 | 1.190x |
| 2026-04 | 5,703,663 | 7,390,463 | +1,686,800 | 1.296x |
| 2026-05 | 6,021,805 | 8,263,270 | +2,241,465 | 1.372x |
| 2026-06 (1~15) | 4,744,856 | 6,591,029 | +1,846,173 | 1.389x |

**daily_data_organization이 일관되게 더 크고, 격차가 시간이 갈수록 커짐.**

---

## 원인 분석

`daily_data_organization` 파일은 `members/export-task` API로 생성됨.
이 API의 `기간 내 크레딧 사용량 총합`에는 개인 구매 크레딧이 포함됨.

검증 (개인 크레딧 보유 유저 샘플):
| 유저 | 기간내 총합 | 개인 크레딧 사용량 | org 추정 |
|---|---|---|---|
| hjung159@naver.com | 188,960 | 178,841 | ~10,119 |
| abcwow102@naver.com | 128,174 | 128,160 | ~14 |

→ 개인 크레딧 사용량이 큰 유저일수록 daily 파일의 총합이 org 실사용보다 크게 나옴.
→ 차이(~620만)가 전체 기간 개인 구매 크레딧 사용량(6,891,727)과 근사.

---

## 데이터 조합 가능성

| 필요한 값 | 방법 | 가능 여부 |
|---|---|---|
| 월별 조직 크레딧 합계 | 대시보드 API | ✅ 가능 |
| 전체 기간 신분별 org 크레딧 | member_export 총합 - 개인크레딧사용량, 신분별 groupby | ✅ 가능 (단, 전체기간 합산만) |
| 월별 신분별 org 크레딧 | 현재 두 API 조합으로 | ❌ 불가 |

**`개인 구매 크레딧 사용량`이 항상 누적값**이므로, 월 단위 export에서도 해당 월의 개인 크레딧만 분리할 수 없음.
(검증: 2026-03 월 단위 export의 `개인 구매 크레딧 사용량` = 전체기간 값과 동일)

---

## 관련 코드

- `code/download_daily_org.py` — `members/export-task` 일별 스냅샷 다운로드
- `code/crosscheck_monthly_credits.py` — 대시보드 API vs daily_data_organization 월별 비교

---

## 결론 및 권장 사항

1. **월별 조직 크레딧 합계** → `dashboards/usage/export-task?credit_source=organization` 사용 (현재 `crosscheck_monthly_credits.py`가 이 역할)
2. **신분별 org 크레딧 월 분리** → 현재 불가. 별도 API 또는 로그 기반 데이터 필요
3. **daily_data_organization 파일은 org only 집계에 사용 불가** (개인 크레딧 포함)
4. 시트에 들어간 기존 값의 출처·계산 방식 불명 (코드 유실). 대시보드 API 값으로 교체 권장
