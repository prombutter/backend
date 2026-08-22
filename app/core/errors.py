"""
도메인 에러 + 에러 응답 형식 — PB-72

확정 정책: 에러 응답 body에 error_code(ERR-*/WARN-*) + 사용자 문구(message)를 담는다.
- AppError: 라우터에서 직접 올리는 도메인 에러(409 중복, 404 없음 등).
- validation_error_handler: Pydantic/경로 파라미터 검증 실패(422)도 같은 형식으로 통일.

main.py에서 두 핸들러를 등록한다.
※ PB-67(auth)의 기존 HTTPException(detail=...)는 그대로 두어(스코프 밖) 응답 형식이
   섞여 있다. 전역 통일은 후속 과제.

위치: app/core/errors.py
"""

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


from typing import Any

class AppError(Exception):
    """error_code를 담아 던지는 커스텀 에러. app_error_handler가 JSON으로 변환한다."""

    def __init__(self, status_code: int, error_code: str, message: str, detail: Any = None) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.detail = detail
        super().__init__(message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    content = {"error_code": exc.error_code, "message": exc.message}
    if exc.detail is not None:
        content["detail"] = exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # details = 개발자용 원인 목록(FastAPI 기본 형식), message = 사용자용 문구
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "ERR-VAL-001",
            "message": "입력값을 확인해 주세요.",
            "detail": jsonable_encoder(exc.errors()),
        },
    )
