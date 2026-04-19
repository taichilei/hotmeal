"""
@File       : exceptions.py
@Date       : 2025-03-01 (或当前日期)
@Description: Defines custom exception classes for the HotMeal API.
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms
@Version    : 1.0.
@Copyright  : Copyright © 2025. All rights reserved.
"""

import logging
from http import HTTPStatus

from .error_codes import ErrorCode

logger = logging.getLogger(__name__)


# ======================
# Custom Exceptions
# ======================

class APIException(Exception):
    """
    自定义 API 异常的基类。
    允许关联错误消息、HTTP 状态码和自定义错误码。
    """

    def __init__(self,
                 message: str = "API exception occurred",
                 http_status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
                 error_code: int | None = ErrorCode.INTERNAL_SERVER_ERROR.value,
                 error_tag: str | None = None,
                 original_exception=None):
        self.message = message
        # 确保 http_status_code 有默认值
        self.http_status_code = http_status_code if http_status_code is not None else HTTPStatus.INTERNAL_SERVER_ERROR
        # 确保 error_code 有默认值
        self.error_code = error_code if error_code is not None else ErrorCode.INTERNAL_SERVER_ERROR.value
        self.error_tag = error_tag  # 存储 error_tag
        self.original_exception = original_exception
        # 在异常的字符串表示中包含错误码和消息
        super().__init__(f"Code {self.error_code}: {message}")

    def to_response_dict(self):
        """
        提供一个适合错误处理器使用的字典表示。
        (这个方法可能不是必须的，因为错误处理器可以直接访问属性)
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "http_code": self.http_status_code,
            "error_tag": self.error_tag
        }


# --- Specific Exception Types ---


class AuthError(APIException):
    """认证或授权相关错误的通用异常。"""

    def __init__(self, message="认证或授权错误",
                 error_code: int | None = ErrorCode.AUTH_ERROR.value,
                 http_status_code: int = HTTPStatus.UNAUTHORIZED,  # 默认为 401
                 error_tag: str | None = None):
        super().__init__(message, http_status_code=http_status_code, error_code=error_code,
                         error_tag=error_tag)
        logger.error(f"[{type(self).__name__} Raised] Code {error_code}: {message}")


class AuthenticationError(AuthError):  # 继承自 AuthError 可能更合适
    """专用于认证失败的异常 (例如，无效凭证、令牌缺失)。"""

    def __init__(self, message: str = "身份认证失败",
                 error_code: int | None = ErrorCode.UNAUTHORIZED.value,  # 使用更具体的 20003
                 http_status_code: int = HTTPStatus.UNAUTHORIZED,  # 状态码 401
                 error_tag: str | None = None):
        super().__init__(message, error_code=error_code, http_status_code=http_status_code,
                         error_tag=error_tag)
        # 日志记录已在 AuthError 中处理


class AuthorizationError(AuthError):  # 继承自 AuthError 可能更合适
    """专用于授权失败的异常 (例如，权限不足)。"""

    def __init__(self, message: str = "权限不足",
                 error_code: int | None = ErrorCode.FORBIDDEN.value,  # 使用更具体的 20004
                 http_status_code: int = HTTPStatus.FORBIDDEN,  # 状态码 403
                 error_tag: str | None = None):
        super().__init__(message, error_code=error_code, http_status_code=http_status_code,
                         error_tag=error_tag)
        # 日志记录已在 AuthError 中处理


class ValidationError(APIException):
    """数据验证失败的异常。"""

    def __init__(self, message: str = "数据验证失败",
                 error_code: int | None = ErrorCode.PARAM_INVALID.value,  # 默认使用参数无效码
                 http_status_code: int = HTTPStatus.BAD_REQUEST,  # 状态码 400
                 error_tag: str | None = None):
        super().__init__(message, http_status_code=http_status_code, error_code=error_code,
                         error_tag=error_tag)
        logger.warning(f"[{type(self).__name__} Raised] Code {error_code}: {message}")


class BadRequestError(ValidationError):
    """请求参数错误（通常用于缺失或无效的客户端输入）。"""
    def __init__(self, message: str = "请求参数错误",
                 error_code: int | None = ErrorCode.PARAM_INVALID.value,
                 http_status_code: int = HTTPStatus.BAD_REQUEST,
                 error_tag: str | None = None):
        super().__init__(message, error_code=error_code, http_status_code=http_status_code,
                         error_tag=error_tag)
        logger.warning(f"[{type(self).__name__} Raised] Code {error_code}: {message}")


class ParamMissing(ValidationError):  # 继承自 ValidationError
    """缺少必需参数的异常。"""

    def __init__(self, message: str = "缺少必需参数",
                 error_code: int | None = ErrorCode.PARAM_MISSING.value,  # 使用 10001
                 http_status_code: int = HTTPStatus.BAD_REQUEST,
                 error_tag: str | None = None):
        super().__init__(message, error_code=error_code, http_status_code=http_status_code,
                         error_tag=error_tag)
        # 日志记录已在 ValidationError 中处理


class ParamInvalid(ValidationError):  # 继承自 ValidationError
    """参数值或类型无效的异常。"""

    def __init__(self, message: str = "参数无效",
                 error_code: int | None = ErrorCode.PARAM_INVALID.value,  # 使用 10002
                 http_status_code: int = HTTPStatus.BAD_REQUEST,
                 error_tag: str | None = None):
        super().__init__(message, error_code=error_code, http_status_code=http_status_code,
                         error_tag=error_tag)
        # 日志记录已在 ValidationError 中处理


class NotFoundError(APIException):
    """请求的资源未找到的异常。"""

    def __init__(self, message: str = "资源未找到",
                 error_code: int | None = ErrorCode.HTTP_NOT_FOUND.value,  # 使用 404000
                 http_status_code: int = HTTPStatus.NOT_FOUND,  # 状态码 404
                 error_tag: str | None = None):
        super().__init__(message, http_status_code=http_status_code, error_code=error_code,
                         error_tag=error_tag)
        # Not Found 通常不是错误，而是正常流程，日志级别可以是 INFO 或 WARNING
        logger.info(f"[{type(self).__name__} Raised] Code {error_code}: {message}")


class DatabaseError(APIException):
    """数据库操作相关错误的异常。"""

    def __init__(self, message: str = "数据库操作错误",
                 error_code: int | None = ErrorCode.DATABASE_ERROR.value,  # 可以定义一个专门的数据库错误码
                 http_status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,  # 通常是 500
                 error_tag: str | None = None):
        super().__init__(message, http_status_code=http_status_code, error_code=error_code,
                         error_tag=error_tag)
        logger.error(f"[{type(self).__name__} Raised] Code {error_code}: {message}")


class BusinessError(APIException):
    """与特定业务逻辑规则相关的错误的异常。"""

    def __init__(self, message: str = "业务逻辑错误",
                 # 通常业务错误返回 400 Bad Request 或 409 Conflict
                 http_status_code: int = HTTPStatus.BAD_REQUEST,
                 error_code: int | None = ErrorCode.OPERATION_FAILED.value,  # 使用通用的操作失败码或更具体的业务码
                 error_tag: str | None = None):
        super().__init__(message, http_status_code=http_status_code, error_code=error_code,
                         error_tag=error_tag)
        logger.warning(f"[{type(self).__name__} Raised] Code {error_code}: {message}")


# ======================
# Exportable Components
# ======================

__all__ = [
    "APIException",
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "BadRequestError",
    "ParamMissing",
    "ParamInvalid",
    "NotFoundError",
    "DatabaseError",
    "BusinessError",
]
