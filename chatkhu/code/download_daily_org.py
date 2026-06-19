"""
chatkhu 일별 멤버 사용량 스냅샷 다운로드 — 조직 제공 크레딧 전용

기존 download_daily.py와 동일한 방식이나, 아래 두 가지 차이:
  1. credit_source=organization 파라미터 추가 → 개인 구매 크레딧 제외
  2. START_DATE: 베타 오픈 시점인 2025-11-01부터

사용법:
    python3 -u code/download_daily_org.py

쿠키 갱신:
    브라우저 → chat.khu.ac.kr → 개발자도구 → Network → 아무 요청의
    Request Headers > cookie 에서 sessionId=... 값을 SESSION_ID에 업데이트
"""

import urllib.request
import urllib.parse
import json
import time
import os
from datetime import date, timedelta

# ── 설정 ──────────────────────────────────────────────
SESSION_ID    = "5d8e1725-40ee-475a-b0ce-66d6d9383c08"
START_DATE    = date(2025, 11, 1)    # 베타 오픈 시점
END_DATE      = date(2026, 6, 15)
OUTPUT_DIR    = "/home/user/workspace/chatkhu/data/daily_data_organization"
BASE_URL      = "https://chat.khu.ac.kr"
POLL_INTERVAL = 2.0    # 초
POLL_TIMEOUT  = 180    # 최대 대기 초
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


def create_export_task(day: date):
    ds = day.strftime("%Y-%m-%d")
    return api_get("/api/proxy/admin/members/export-task/", {
        "response_type": "csv",
        "start_date": ds,
        "end_date": ds,
        "credit_source": "organization",   # 조직 제공 크레딧만
    })


def poll_task(task_id: int) -> dict:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        resp = api_get(f"/api/proxy/tasks/{task_id}/")
        data = resp.get("data", resp)
        status = data.get("status")
        file_info = data.get("file")
        if status == "completed" and file_info:
            return file_info
        if status == "failed":
            raise RuntimeError(f"Task {task_id} failed: {resp}")
    raise TimeoutError(f"Task {task_id} timed out after {POLL_TIMEOUT}s")


def download_file(file_info: dict, output_path: str):
    file_url = file_info["url"]
    file_name = file_info["name"]
    encoded = urllib.parse.quote(file_url, safe="")
    download_url = (
        f"{BASE_URL}/api/download-media"
        f"?url={encoded}&filename={urllib.parse.quote(file_name)}"
    )
    req = urllib.request.Request(download_url, headers={**HEADERS, "accept": "*/*"})
    with urllib.request.urlopen(req, timeout=120) as r:
        content = r.read()
    with open(output_path, "wb") as f:
        f.write(content)
    return len(content)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    days = []
    cur = START_DATE
    while cur <= END_DATE:
        days.append(cur)
        cur += timedelta(days=1)

    total = len(days)
    print(f"총 {total}일 ({START_DATE} ~ {END_DATE}) 조직 크레딧 스냅샷 다운로드 시작", flush=True)
    print(f"출력: {OUTPUT_DIR}\n", flush=True)

    success, skip, fail = 0, 0, 0
    t_start = time.time()

    for i, day in enumerate(days, 1):
        ds = day.strftime("%Y-%m-%d")
        out_path = os.path.join(OUTPUT_DIR, f"member_{ds}.csv")

        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            print(f"[{i:3}/{total}] {ds} — 스킵 (이미 존재)", flush=True)
            skip += 1
            continue

        t0 = time.time()
        try:
            task_resp = create_export_task(day)
            task_id = task_resp["data"]["id"]
            file_info = poll_task(task_id)
            size = download_file(file_info, out_path)
            elapsed = time.time() - t0
            done = success + skip + 1
            remaining = total - done
            eta = (time.time() - t_start) / done * remaining if done > 0 else 0
            print(
                f"[{i:3}/{total}] {ds} — 완료 "
                f"({size/1024:.0f}KB, {elapsed:.1f}s, 잔여 약 {eta/60:.0f}분)",
                flush=True,
            )
            success += 1

        except Exception as e:
            print(f"[{i:3}/{total}] {ds} — 실패: {e}", flush=True)
            fail += 1
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e):
                print("\n세션 만료 의심 — SESSION_ID 갱신 후 재실행하세요.", flush=True)
                break

        time.sleep(0.3)

    print(f"\n완료: 성공 {success}, 스킵 {skip}, 실패 {fail}", flush=True)
    print(f"파일 위치: {OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
