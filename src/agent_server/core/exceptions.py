from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..utils.log_util import build_logger

logger = build_logger("global_exception_handler")


# ------------------ 业务异常: 继承自 HTTPException，所以 FastAPI 能直接处理 ------------------

class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class AlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Unauthorized access"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

# ------------------ 全局兜底: 捕获所有未被处理的异常 ------------------

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 使用 loguru 记录详细的异常信息，包括堆栈跟踪
    logger.exception(f"Unhandled exception at {request.url.path}: {exc}")
    # 向客户端返回一个通用的、安全的错误信息
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )