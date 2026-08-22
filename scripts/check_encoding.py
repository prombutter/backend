"""
소스 파일 인코딩 검사 — 모든 텍스트 파일은 BOM 없는 UTF-8 이어야 한다.

배경: app/core/utils.py 가 UTF-16 으로 저장되어 파이썬이 import 하지 못했고,
      SyntaxError: source code string cannot contain null bytes 로
      CI 테스트 18건이 한 번에 실패했다. 같은 일이 반복되지 않도록 배포 전에 막는다.

사용법: python scripts/check_encoding.py
        문제가 있으면 파일 목록을 출력하고 종료 코드 1 을 반환한다.

위치: scripts/check_encoding.py
"""

import subprocess
import sys

# 검사 대상 확장자 (이미지·PDF 같은 진짜 바이너리는 제외)
TEXT_SUFFIXES = (
    ".py", ".md", ".txt", ".yml", ".yaml", ".toml",
    ".sql", ".json", ".cfg", ".ini", ".sh", ".env.example",
)

BOMS = {
    b"\xef\xbb\xbf": "UTF-8 BOM",
    b"\xff\xfe": "UTF-16 LE BOM",
    b"\xfe\xff": "UTF-16 BE BOM",
}


def tracked_text_files() -> list[str]:
    """git 이 추적 중인 파일 중 검사 대상 확장자만 고른다."""
    out = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, check=True
    ).stdout
    names = [n.decode("utf-8", "surrogateescape") for n in out.split(b"\0") if n]
    return [n for n in names if n.endswith(TEXT_SUFFIXES)]


def check(path: str) -> str | None:
    """문제가 있으면 사유 문자열, 없으면 None 을 돌려준다."""
    with open(path, "rb") as f:
        raw = f.read()

    for bom, label in BOMS.items():
        if raw.startswith(bom):
            return f"{label} 로 시작함"

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return f"UTF-8 로 읽을 수 없음 ({e.reason}, {e.start} 번째 바이트)"

    return None


def main() -> int:
    problems = [(p, r) for p in tracked_text_files() if (r := check(p))]

    if not problems:
        print("인코딩 검사 통과 — 모든 텍스트 파일이 BOM 없는 UTF-8 입니다.")
        return 0

    print("인코딩 검사 실패 — 아래 파일을 BOM 없는 UTF-8 로 다시 저장해 주세요.\n")
    for path, reason in problems:
        print(f"  {path}: {reason}")
    print("\n예시:  iconv -f UTF-16LE -t UTF-8 <파일> > tmp && mv tmp <파일>")
    return 1


if __name__ == "__main__":
    sys.exit(main())
