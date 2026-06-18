"""
CSV 비식별화 스크립트
- member 파일: 이름+이메일 조합으로 고유 ID 생성, id 컬럼 추가 후 이름/이메일 제거
- 다른 member_export 파일: member 파일 참조하여 이름+이메일 → id로 대체 후 원본 컬럼 삭제

파일 실행 
- 상대경로 : 
    cd /home/user/workspace
    python3 chatkhu/code/deidentify.py
- 절대경로 : python3 /home/user/workspace/chatkhu/code/deidentify.py
"""

import csv
import hashlib
import sys
from pathlib import Path

# ===================== 설정 =====================

MEMBER_DIR = Path("chatkhu/data/member")
MEMBER_DEIDENTIFIED_DIR = Path("chatkhu/data/member_deidentified")

INPUT_DIR = Path("chatkhu/data/daily_data")
OUTPUT_DIR = Path("chatkhu/data/daily_data__deidentified")

# ================================================


def make_id(name: str, email: str) -> str:
    """이름+이메일 조합으로 고유 ID 생성 (SHA256 앞 12자리)"""
    raw = f"{name.strip()}|{email.strip().lower()}"
    return "uid_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def process_basic(basic_path: Path, output_dir: Path) -> dict:
    """member 파일에 id 컬럼 추가 후 이름/이메일 제거, id 맵 반환"""
    id_map = {}

    with open(basic_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    for row in rows:
        uid = make_id(row["이름"], row["이메일"])
        id_map[(row["이름"].strip(), row["이메일"].strip().lower())] = uid
        row["id"] = uid
        del row["이름"]
        del row["이메일"]

    out_path = output_dir / basic_path.name
    new_fields = ["id"] + [f for f in fieldnames if f not in ("이름", "이메일")]

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[member] {basic_path.name} → {out_path}  ({len(rows)}명, ID {len(id_map)}개)")
    return id_map


def process_other(file_path: Path, id_map: dict, output_dir: Path):
    """이름+이메일 컬럼을 id로 대체"""
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    not_found = []
    for row in rows:
        key = (row["이름"].strip(), row["이메일"].strip().lower())
        uid = id_map.get(key)
        if uid is None:
            not_found.append(key)
            uid = make_id(*key)  # basic에 없어도 동일 규칙으로 ID 부여
        row["id"] = uid
        del row["이름"]
        del row["이메일"]

    # 컬럼 순서: id를 맨 앞, 이름/이메일 제거
    new_fields = ["id"] + [f for f in fieldnames if f not in ("이름", "이메일")]

    out_path = output_dir / file_path.name

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(rows)

    if not_found:
        print(f"  ⚠ basic 파일에 없는 계정 {len(not_found)}개 (동일 규칙으로 ID 부여):")
        for name, email in not_found[:5]:
            print(f"    - {name} / {email}")
        if len(not_found) > 5:
            print(f"    ... 외 {len(not_found)-5}개")

    print(f"[other] {file_path.name} → {out_path}  ({len(rows)}행)")


def main():
    MEMBER_DEIDENTIFIED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== 비식별화 시작 ===\n")

    if not MEMBER_DIR.exists():
        print(f"[ERROR] member 폴더를 찾을 수 없습니다: {MEMBER_DIR}")
        sys.exit(1)

    member_files = sorted(MEMBER_DIR.glob("*.csv"))
    if not member_files:
        print(f"[ERROR] member 폴더에 CSV 파일이 없습니다: {MEMBER_DIR}")
        sys.exit(1)

    id_map = {}
    for f in member_files:
        id_map.update(process_basic(f, MEMBER_DEIDENTIFIED_DIR))
    print()

    if not INPUT_DIR.exists():
        print(f"[ERROR] input 폴더를 찾을 수 없습니다: {INPUT_DIR}")
        sys.exit(1)

    for f in sorted(INPUT_DIR.glob("*.csv")):
        process_other(f, id_map, OUTPUT_DIR)

    print("\n=== 완료 ===")
    print(f"member 출력: {MEMBER_DEIDENTIFIED_DIR.resolve()}")
    print(f"usage 출력:  {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()