"""
credit_source=organization 파라미터가 members/export-task의
`기간 내 크레딧 사용량 총합` 컬럼에 영향을 주는지 검증

동일한 날짜로 파라미터 있을 때 / 없을 때 두 파일을 다운로드해서 비교:
  - 멤버 수 차이 → 목록 필터링 효과 여부
  - 기간 내 크레딧 사용량 총합 합계 차이 → 사용량 컬럼 필터 효과 여부
  - 개인 구매 크레딧 있는 유저의 총합값 비교

사용법:
    python3 -u code/verify_credit_source_param.py
"""

import csv
import io
import json
import time
import urllib.parse
import urllib.request

SESSION_ID = "5d8e1725-40ee-475a-b0ce-66d6d9383c08"
BASE_URL   = "https://chat.khu.ac.kr"
TEST_DATE  = "2026-05-09"   # 이미 member_*.csv 있어서 세 번째 결과와도 비교 가능

HEADERS = {
    "cookie": f"sessionId={SESSION_ID}; x-subdomain=chat",
    "subdomain": "chat",
    "accept": "application/json, text/plain, */*",
    "ngrok-skip-browser-warning": "true",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def download_member_csv(date_str: str, with_credit_source: bool) -> list[dict]:
    params = {
        "response_type": "csv",
        "start_date": date_str,
        "end_date": date_str,
    }
    if with_credit_source:
        params["credit_source"] = "organization"

    label = "WITH credit_source=organization" if with_credit_source else "WITHOUT credit_source"
    print(f"\n[{label}] export-task 요청 중...", flush=True)

    resp    = api_get("/api/proxy/admin/members/export-task/", params)
    task_id = resp["data"]["id"]
    print(f"  task_id: {task_id}", flush=True)

    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(2)
        data = api_get(f"/api/proxy/tasks/{task_id}/")["data"]
        if data["status"] == "completed" and data["file"]:
            fi     = data["file"]
            enc    = urllib.parse.quote(fi["url"], safe="")
            dl_url = (f"{BASE_URL}/api/download-media"
                      f"?url={enc}&filename={urllib.parse.quote(fi['name'])}")
            req2 = urllib.request.Request(dl_url, headers={**HEADERS, "accept": "*/*"})
            with urllib.request.urlopen(req2, timeout=120) as r:
                text = r.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            rows   = list(reader)
            print(f"  완료: {len(rows)}행", flush=True)
            return rows
        if data["status"] == "failed":
            raise RuntimeError(f"Task {task_id} failed")
    raise TimeoutError(f"Task {task_id} timed out")


def summarize(rows: list[dict], label: str):
    col_total    = "기간 내 크레딧 사용량 총합"
    col_personal = "개인 구매 크레딧"
    col_identity = "신분"
    col_per_use  = "개인 구매 크레딧 사용량"

    total_sum  = sum(float(r.get(col_total, 0) or 0)    for r in rows)
    users_with_personal = [r for r in rows if float(r.get(col_personal, 0) or 0) > 0]

    from collections import defaultdict
    by_id = defaultdict(float)
    for r in rows:
        by_id[r.get(col_identity, "")] += float(r.get(col_total, 0) or 0)

    print(f"\n  {'=== ' + label + ' ==='}")
    print(f"  총 멤버 수: {len(rows)}")
    print(f"  기간 내 크레딧 사용량 총합 합계: {total_sum:,.3f}")
    print(f"  개인 구매 크레딧 보유 유저 수: {len(users_with_personal)}")
    print("  신분별 총합:")
    for ident in ["학생", "교수", "교직원"]:
        print(f"    {ident}: {by_id[ident]:>12,.3f}")
    return total_sum, len(rows), users_with_personal


def compare_with_existing(rows_with: list[dict]):
    """이미 다운로드된 member_*.csv와 WITH 결과를 비교"""
    import os
    existing = f"/home/user/workspace/chatkhu/data/daily_data_organization/member_{TEST_DATE}.csv"
    if not os.path.exists(existing):
        print(f"\n  [기존 파일 없음] {existing}")
        return
    with open(existing) as f:
        existing_rows = list(csv.DictReader(f))
    col = "기간 내 크레딧 사용량 총합"
    ex_sum  = sum(float(r.get(col, 0) or 0) for r in existing_rows)
    new_sum = sum(float(r.get(col, 0) or 0) for r in rows_with)
    print(f"\n  [기존 파일 vs WITH 재다운로드 비교]")
    print(f"  기존 파일 합계: {ex_sum:,.3f}")
    print(f"  신규 WITH 합계: {new_sum:,.3f}")
    print(f"  일치 여부: {'✅ 일치' if abs(ex_sum - new_sum) < 1 else '❌ 불일치'}")


def main():
    print("=" * 60)
    print(f"credit_source 파라미터 효과 검증  ({TEST_DATE})")
    print("=" * 60)

    rows_with    = download_member_csv(TEST_DATE, with_credit_source=True)
    rows_without = download_member_csv(TEST_DATE, with_credit_source=False)

    sum_with,    cnt_with,    pu_with    = summarize(rows_with,    "credit_source=organization 있음")
    sum_without, cnt_without, pu_without = summarize(rows_without, "credit_source=organization 없음")

    print("\n" + "=" * 60)
    print("비교 결과")
    print("=" * 60)
    print(f"  멤버 수 차이:   {cnt_with} vs {cnt_without}  ({'동일' if cnt_with == cnt_without else '다름 → 목록 필터 있음'})")
    print(f"  총합 차이:      {sum_with:,.3f} vs {sum_without:,.3f}")
    ratio = sum_with / sum_without if sum_without else float("inf")
    print(f"  총합 비율:      {ratio:.4f}")

    if abs(sum_with - sum_without) < 1:
        print("\n  결론: credit_source 파라미터가 총합 컬럼에 영향 없음")
        print("        → `기간 내 크레딧 사용량 총합` = 조직+개인 혼합 (org-only 분해 불가)")
    else:
        print(f"\n  결론: credit_source 파라미터가 총합 컬럼에 영향 있음! (비율 {ratio:.4f}x)")
        print("        → WITH 버전이 org-only일 가능성 검토 필요")

    compare_with_existing(rows_with)

    print(f"\n  dashboard API 기준값 (2026-05 전체): 8,255,840 (member합산) vs 6,021,805 (org-only API)")
    print("  위 비율 참고해 해석할 것")


if __name__ == "__main__":
    main()
