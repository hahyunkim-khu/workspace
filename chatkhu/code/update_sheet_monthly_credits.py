"""
breakdown_v2 시트 F9:F12에 월별 조직 크레딧 사용량 (전체) 업데이트

데이터 출처: dashboards/usage/export-task?credit_source=organization
→ 실제 조직 크레딧 풀 차감액만 집계한 정확한 값 (members/export 대비 개인 구매 크레딧 제외)

시트 구조:
  breakdown_v2 시트
  F9  = 2026-03 전체 크레딧 이용량  (수식 =L9+R9+X9 를 값으로 덮어씀)
  F10 = 2026-04
  F11 = 2026-05
  F12 = 2026-06 (1-15일)
  G열 (인당 크레딧) / 4행 (가중평균) 은 F 참조 수식이므로 자동 재계산됨

사용법:
    python3 -u code/update_sheet_monthly_credits.py

쿠키 갱신:
    브라우저 → chat.khu.ac.kr → 개발자도구 → Network → 요청 헤더 > cookie
    에서 sessionId=... 값을 SESSION_ID에 업데이트

Google 인증:
    MCP 토큰 파일 사용: ~/.workspace-mcp/hahyunkim@khu.ac.kr.json
"""

import json
import time
import urllib.parse
import urllib.request

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ── ChatKHU API 설정 ───────────────────────────────────
SESSION_ID = "5d8e1725-40ee-475a-b0ce-66d6d9383c08"
BASE_URL   = "https://chat.khu.ac.kr"

# (월 레이블, 시작일, 종료일, 쓸 셀 주소)
MONTHS = [
    ("2026-03", "2026-03-01", "2026-03-31", "F9"),
    ("2026-04", "2026-04-01", "2026-04-30", "F10"),
    ("2026-05", "2026-05-01", "2026-05-31", "F11"),
    ("2026-06", "2026-06-01", "2026-06-15", "F12"),
]

# ── Google Sheets 설정 ─────────────────────────────────
SPREADSHEET_ID = "1uJmPUHpxsbMn4YFOnCc0tTmKlUaHjC2ViUuApC7PXFE"
SHEET_NAME     = "breakdown_v2"
MCP_TOKEN_FILE = "/home/user/.workspace-mcp/hahyunkim@khu.ac.kr.json"
# ──────────────────────────────────────────────────────

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


def fetch_org_credits(start_date: str, end_date: str) -> float:
    """dashboards/usage/export-task로 기간 내 조직 크레딧 합계 반환.

    CSV 응답 포맷:
      합계,채팅,웹검색,...
      4744855.668,...
    → '합계,' 헤더 바로 다음 줄 첫 번째 값이 전체 크레딧 합계.
    """
    resp = api_get("/api/proxy/admin/dashboards/usage/export-task/", {
        "response_type": "csv",
        "start_date": start_date,
        "end_date": end_date,
        "credit_source": "organization",
    })
    task_id  = resp["data"]["id"]
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(2)
        data = api_get(f"/api/proxy/tasks/{task_id}/")["data"]
        if data["status"] == "completed" and data["file"]:
            fi     = data["file"]
            enc    = urllib.parse.quote(fi["url"], safe="")
            dl_url = (
                f"{BASE_URL}/api/download-media"
                f"?url={enc}&filename={urllib.parse.quote(fi['name'])}"
            )
            req2 = urllib.request.Request(dl_url, headers={**HEADERS, "accept": "*/*"})
            with urllib.request.urlopen(req2, timeout=120) as r:
                text = r.read().decode("utf-8-sig")
            lines = [l.strip() for l in text.splitlines()]
            for i, line in enumerate(lines):
                if line.startswith("합계,") and i + 1 < len(lines):
                    return float(lines[i + 1].split(",")[0])
            raise ValueError("합계 행을 찾을 수 없음")
        if data["status"] == "failed":
            raise RuntimeError(f"Task {task_id} failed")
    raise TimeoutError(f"Task {task_id} timed out")


def get_worksheet():
    """MCP 토큰으로 gspread 인증 후 워크시트 반환"""
    with open(MCP_TOKEN_FILE) as f:
        d = json.load(f)
    creds = Credentials(
        token=d["token"], refresh_token=d["refresh_token"],
        token_uri=d["token_uri"], client_id=d["client_id"],
        client_secret=d["client_secret"], scopes=d["scopes"],
    )
    creds.refresh(Request())
    gc = gspread.authorize(creds)
    return gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)


def main():
    print("=" * 60)
    print("breakdown_v2 시트 월별 조직 크레딧 업데이트")
    print("  출처: dashboards/usage/export-task?credit_source=organization")
    print("=" * 60)

    ws = get_worksheet()

    for month, start, end, cell in MONTHS:
        print(f"[{month}] {start} ~ {end}  API 호출 중...", end=" ", flush=True)
        credits = fetch_org_credits(start, end)
        print(f"{credits:,.0f}  →  {cell} 쓰기...", end=" ", flush=True)
        ws.update([[round(credits)]], cell)
        print("완료")

    print("\n최종 확인 (F9:F12):")
    for row, (month, *_) in zip(ws.get("F9:F12"), MONTHS):
        print(f"  {month}: {row[0]}")


if __name__ == "__main__":
    main()
