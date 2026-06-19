"""
월별 조직 크레딧 사용량 크로스체크

① dashboards/usage/export-task API (credit_source=organization) 로 월별 합산
② daily_data_organization 파일 기반 월별 합산
두 값을 비교해서 불일치 원인을 찾는다.

사용법:
    python3 -u code/crosscheck_monthly_credits.py

쿠키 갱신:
    브라우저 → chat.khu.ac.kr → 개발자도구 → Network → 요청 헤더 > cookie
    에서 sessionId=... 값을 SESSION_ID에 업데이트
"""

import urllib.request
import urllib.parse
import json
import time
import io
import glob
import pandas as pd
from datetime import date

# ── 설정 ──────────────────────────────────────────────
SESSION_ID   = "5d8e1725-40ee-475a-b0ce-66d6d9383c08"
BASE_URL     = "https://chat.khu.ac.kr"
DATA_DIR     = "/home/user/workspace/chatkhu/data/daily_data_organization"
DAILY_CREDIT_COL = "기간 내 크레딧 사용량 총합"

MONTHS = [
    ("2026-03", "2026-03-01", "2026-03-31"),
    ("2026-04", "2026-04-01", "2026-04-30"),
    ("2026-05", "2026-05-01", "2026-05-31"),
    ("2026-06", "2026-06-01", "2026-06-15"),
]

HEADERS = {
    "cookie": f"sessionId={SESSION_ID}; x-subdomain=chat",
    "subdomain": "chat",
    "accept": "application/json, text/plain, */*",
    "ngrok-skip-browser-warning": "true",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
# ──────────────────────────────────────────────────────


def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def poll_task(task_id: int, interval=2.0, timeout=180) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(interval)
        resp = api_get(f"/api/proxy/tasks/{task_id}/")
        data = resp.get("data", resp)
        if data.get("status") == "completed" and data.get("file"):
            return data["file"]
        if data.get("status") == "failed":
            raise RuntimeError(f"Task {task_id} failed")
    raise TimeoutError(f"Task {task_id} timed out")


def download_csv_text(file_info: dict) -> str:
    file_url = file_info["url"]
    file_name = file_info["name"]
    encoded = urllib.parse.quote(file_url, safe="")
    download_url = (
        f"{BASE_URL}/api/download-media"
        f"?url={encoded}&filename={urllib.parse.quote(file_name)}"
    )
    req = urllib.request.Request(download_url, headers={**HEADERS, "accept": "*/*"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8-sig")


def fetch_dashboard_monthly(start_date: str, end_date: str) -> float:
    """dashboards/usage/export-task API로 기간 내 크레딧 합산 반환.

    응답 CSV 포맷:
      (빈 줄)
      합계,채팅,웹검색,...
      4744855.668,3914683.858,...
      (모델별 상세)
    → '합계' 행 바로 다음 줄 첫 번째 값이 전체 크레딧 총합.
    """
    resp = api_get("/api/proxy/admin/dashboards/usage/export-task/", {
        "response_type": "csv",
        "start_date": start_date,
        "end_date": end_date,
        "credit_source": "organization",
    })
    task_id = resp["data"]["id"]
    file_info = poll_task(task_id)
    csv_text = download_csv_text(file_info)

    lines = [l.strip() for l in csv_text.splitlines()]
    for i, line in enumerate(lines):
        if line.startswith("합계,"):
            # 다음 줄이 실제 값
            if i + 1 < len(lines):
                total_str = lines[i + 1].split(",")[0]
                return float(total_str)
    return 0.0


def sum_daily_org(month_prefix: str) -> float:
    """daily_data_organization 파일에서 월별 합산"""
    files = sorted(glob.glob(f"{DATA_DIR}/member_{month_prefix}-*.csv"))
    if not files:
        return 0.0
    total = 0.0
    for f in files:
        df = pd.read_csv(f, low_memory=False)
        total += df[DAILY_CREDIT_COL].sum()
    return total


def main():
    print("=" * 65)
    print("월별 조직 크레딧 크로스체크")
    print("  ① dashboards/usage API  (credit_source=organization)")
    print("  ② daily_data_organization 파일 합산")
    print("=" * 65)

    results = []
    for month, start, end in MONTHS:
        print(f"\n[{month}] {start} ~ {end}")

        # ① API 호출
        print("  → API 호출 중...", end=" ", flush=True)
        try:
            api_total = fetch_dashboard_monthly(start, end)
            print(f"{api_total:,.0f}")
        except Exception as e:
            print(f"실패: {e}")
            api_total = None

        # ② daily 파일 합산
        daily_total = sum_daily_org(month)
        print(f"  → daily 파일 합산: {daily_total:,.0f}")

        if api_total is not None:
            diff = daily_total - api_total
            ratio = daily_total / api_total if api_total else float("inf")
            print(f"  → 차이 (daily - API): {diff:+,.0f}  (daily/API = {ratio:.3f}x)")

        results.append({
            "월": month,
            "API": api_total,
            "daily_org": daily_total,
        })

    print("\n" + "=" * 65)
    print("요약")
    print(f"{'월':<10} {'API':>15} {'daily_org':>15} {'차이':>15} {'배율':>8}")
    print("-" * 65)
    for r in results:
        api = r["API"]
        daily = r["daily_org"]
        if api:
            diff = daily - api
            ratio = daily / api
            print(f"{r['월']:<10} {api:>15,.0f} {daily:>15,.0f} {diff:>+15,.0f} {ratio:>7.3f}x")
        else:
            print(f"{r['월']:<10} {'(실패)':>15} {daily:>15,.0f}")


if __name__ == "__main__":
    main()
