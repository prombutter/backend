"""
Cloud Run 주입용 env.yaml 생성 — PB-140

배포 워크플로가 env.yaml 을 echo 로 조립하고 있었다. 값 안에 따옴표나 줄바꿈이 하나라도
들어가면 YAML 이 깨지는데, 주입하는 값 대부분이 시크릿이라 로그에서 눈으로 확인할 수
없다. 이스케이프를 파서에 맡긴다.

빈 값은 키 자체를 넣지 않는다. 빈 문자열을 주입하면 코드의 기본값이 덮여서
"미설정이라 기본값" 과 "빈 값으로 설정됨" 이 구분되지 않는다.

사용법: python3 scripts/build_env_yaml.py  (환경변수에서 읽어 ./env.yaml 로 쓴다)
위치: scripts/build_env_yaml.py
"""

import json
import os
import sys

KEYS = [
    "APP_ENV",
    "SECRET_KEY",
    "DATABASE_URL",
    "CORS_ORIGINS",
    "COOKIE_SECURE",
    "COOKIE_SAMESITE",
    "COOKIE_DOMAIN",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_MINUTES",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "OAUTH_TOKEN_KEY",
    "OAUTH_CALLBACK_URL",
    "OAUTH_FRONTEND_REDIRECT",
    "OAUTH_ALLOWED_REDIRECTS",
    "SENDGRID_API_KEY",
    "MAIL_FROM_ADDRESS",
]

# 이것들이 없으면 서비스가 뜨더라도 정상 동작하지 않는다. 배포 전에 멈춘다.
REQUIRED = ["APP_ENV", "SECRET_KEY", "DATABASE_URL", "CORS_ORIGINS"]

# 값이 아니라 조합이 틀리면 브라우저가 쿠키를 조용히 버린다. 주입 시점에 잡는다.
def _validate(values: dict[str, str]) -> list[str]:
    problems = []
    samesite = values.get("COOKIE_SAMESITE", "lax").lower()
    if samesite not in {"lax", "strict", "none"}:
        problems.append(f"COOKIE_SAMESITE 는 lax·strict·none 중 하나여야 합니다 (받은 값: {samesite})")
    secure = values.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes", "on"}
    if samesite == "none" and not secure:
        problems.append("COOKIE_SAMESITE=none 은 COOKIE_SECURE=true 와 함께여야 합니다")
    return problems


def main() -> int:
    values = {k: os.environ.get(k, "").strip() for k in KEYS}
    present = {k: v for k, v in values.items() if v}

    missing = [k for k in REQUIRED if k not in present]
    if missing:
        print(f"::error::필수 환경변수 미설정: {', '.join(missing)}", file=sys.stderr)
        return 1

    problems = _validate(present)
    if problems:
        for p in problems:
            print(f"::error::{p}", file=sys.stderr)
        return 1

    lines = [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in present.items()]
    with open("env.yaml", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # 값은 찍지 않는다. 어떤 키가 들어갔는지만 남긴다.
    print("주입 키: " + ", ".join(present))
    skipped = [k for k in KEYS if k not in present]
    if skipped:
        print("미설정(코드 기본값 사용): " + ", ".join(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
