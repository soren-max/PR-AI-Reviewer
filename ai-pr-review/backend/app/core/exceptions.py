"""
Unified exception hierarchy and FastAPI exception handlers.
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception with structured error payload."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self, request_id: str | None = None) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
            "request_id": request_id,
        }


class PRNotFoundError(AppException):
    def __init__(self, detail: str = "Pull Request not found"):
        super().__init__(
            code="PR_NOT_FOUND",
            message=detail,
            status_code=404,
        )


class InvalidPRUrlError(AppException):
    def __init__(self, detail: str = "提供的 URL 不是有效的 GitHub Pull Request 链接"):
        super().__init__(
            code="INVALID_PR_URL",
            message=detail,
            status_code=422,
            details={"expected_pattern": "https://github.com/{owner}/{repo}/pull/{number}"},
        )


class GitHubAPIError(AppException):
    def __init__(self, detail: str = "GitHub API 调用失败", status_code: int = 502):
        super().__init__(
            code="GITHUB_API_ERROR",
            message=detail,
            status_code=status_code,
        )


class LLMAPIError(AppException):
    def __init__(self, detail: str = "LLM API 调用失败", status_code: int = 502):
        super().__init__(
            code="LLM_API_ERROR",
            message=detail,
            status_code=status_code,
        )


class RateLimitError(AppException):
    def __init__(self):
        super().__init__(
            code="RATE_LIMITED",
            message="请求频率超限，请稍后重试",
            status_code=429,
        )


class StateTransitionError(AppException):
    def __init__(self, current: str, target: str):
        super().__init__(
            code="STATE_TRANSITION_INVALID",
            message=f"Cannot transition from {current} to {target}",
            status_code=409,
        )


class ReportParseError(AppException):
    def __init__(self, detail: str = "无法解析 LLM 输出"):
        super().__init__(
            code="REPORT_PARSE_ERROR",
            message=detail,
            status_code=500,
        )


# ---------------------------------------------------------------------------
# FastAPI exception handler
# ---------------------------------------------------------------------------
def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(request_id=getattr(request.state, "request_id", None)),
    )
