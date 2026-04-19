"""
@File       : response.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Description: 定义统一的 API 响应结构、辅助函数和全局异常处理器
@Version    : 1.1.0
@Copyright  : Copyright © 2025. All rights reserved.
"""

import logging
from http import HTTPStatus
from typing import Any

from flask import Response, jsonify, make_response
from werkzeug.exceptions import (
    HTTPException,  # 导入 HTTPException 用于更通用的 HTTP 异常处理
)

# 导入错误码枚举
from .error_codes import ErrorCode

# 导入自定义异常类
from .exceptions import (
    APIException,
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)

# configure logging
logger = logging.getLogger(__name__)


class ApiResponse:
    """
    API 的统一响应格式。
    """

    def __init__(self, status: str, error_code: int, message: str, data: Any | None = None,
                 error_tag: str | None = None):
        self.status = status
        self.error_code = error_code
        self.message = message
        self.data = data
        self.error_tag = error_tag

    def to_dict(self):
        """
         将响应对象转换为字典。
         :return: 响应的字典表示。
         """
        response = {
            "status": self.status,
            "error_code": self.error_code,
            "message": self.message,
        }
        # 仅在 data 不为 None 时包含 data 字段 (值为 null 或实际数据)
        # 或者如果希望 data 字段总是存在: response["data"] = self.data
        if self.data is not None:
            response["data"] = self.data

        # 仅在提供了 error_tag 时包含它
        if self.error_tag:
            response["error_tag"] = self.error_tag
        return response


# ======================
# Response Format Functions
# ======================

def success(message: str = "Operation succeeded",
            error_code: int = ErrorCode.SUCCESS.value,  # 默认错误码为 0
            data: Any | None = None,
            http_status_code: int = HTTPStatus.OK) -> Response:
    """
    成功响应格式封装函数。

    :param message: 响应消息 (默认: "Operation succeeded")。
    :param error_code: 错误码 (默认: ErrorCode.SUCCESS)。
    :param data: 响应数据 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 200 OK)。
    :return: Flask Response 对象。
    """
    response = ApiResponse("success", error_code, message, data)
    response_object = jsonify(response.to_dict())
    response_object.status_code = http_status_code
    return response_object


def fail(message: str = "操作失败",
         error_code: int = ErrorCode.OPERATION_FAILED.value,  # 默认操作失败码
         data: Any | None = None,
         error_tag: str | None = None,
         http_status_code: int = HTTPStatus.BAD_REQUEST) -> Response:  # 默认 400
    """
    失败响应格式封装函数。

    :param message: 错误消息 (默认: "操作失败")。
    :param error_code: 具体错误码 (默认: ErrorCode.OPERATION_FAILED)。
    :param data: 额外的错误数据/详情 (默认: None)。
    :param error_tag: 可选的错误标签，用于分组/识别错误 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 400 Bad Request)。
    :return: Flask Response 对象。
    """
    # 确保 error_code 有值，如果传入 None 则使用默认值
    final_error_code = error_code if error_code is not None else ErrorCode.OPERATION_FAILED.value
    response = ApiResponse(status="fail", error_code=final_error_code, message=message, data=data,
                           error_tag=error_tag)
    response_object = jsonify(response.to_dict())
    response_object.status_code = http_status_code
    return response_object


# ======================
# Common Response Shortcut Functions
# ======================

def created(data: Any | None = None,
            message: str = "资源创建成功",  # 默认消息更新
            error_code: int = ErrorCode.SUCCESS.value,
            http_status_code: int = HTTPStatus.CREATED,
            headers: dict[str, str] | None = None) -> Response:
    """
    返回 201 Created 响应。

    :param data: 创建的资源的数据 (例如，其 ID 或表示)。
    :param message: 成功消息 (默认: "资源创建成功")。
    :param error_code: 错误码 (默认: ErrorCode.SUCCESS)。
    :param http_status_code: HTTP 状态码 (默认: 201 Created)。
    :param headers: 要添加的可选头字典 (例如，{'Location': '/resource/id'})。
    :return: Flask Response 对象。
    """
    response = ApiResponse(status="success", error_code=error_code, message=message, data=data)
    response_object = jsonify(response.to_dict())
    response_object.status_code = http_status_code
    if headers:
        for key, value in headers.items():
            response_object.headers[key] = value
    return response_object


def no_content(message: str = "Operation succeeded，无内容返回",  # 默认消息更新
               http_status_code: int = HTTPStatus.NO_CONTENT) -> Response:
    """
    返回 204 No Content 响应 (例如，用于成功删除)。
    注意: 根据 RFC 7231，204 响应不应有主体。
          返回一个状态码正确且没有主体的空响应。

    :param message: 日志消息或内部注释 (不在响应主体中发送)。
    :param http_status_code: HTTP 状态码 (默认: 204 No Content)。
    :return: 状态码为 204 且无主体的 Flask Response 对象。
    """
    logger.info(f"响应 204 No Content: {message}")  # 如果需要，记录消息
    # 创建一个状态码正确的空响应
    response_object = make_response('', http_status_code)
    # 移除 Content-Type 头，因为没有内容
    response_object.headers.pop('Content-Type', None)
    return response_object


def bad_request(message: str = "错误的请求",  # 默认消息更新
                error_code: int = ErrorCode.PARAM_INVALID.value,
                error: Any | None = None,  # 参数名改为 error 以匹配 fail
                error_tag: str | None = None,
                http_status_code: int = HTTPStatus.BAD_REQUEST) -> Response:
    """
    返回 400 Bad Request 响应。

    :param message: 错误消息 (默认: "错误的请求")。
    :param error_code: 具体错误码 (默认: ErrorCode.PARAM_INVALID)。
    :param error: 额外的错误详情 (默认: None)。
    :param error_tag: 可选的错误标签 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 400 Bad Request)。
    :return: Flask Response 对象。
    """
    # 直接调用 fail 函数
    return fail(message=message, error_code=error_code, data=error,
                error_tag=error_tag, http_status_code=http_status_code)


def unauthorized(message: str = "未授权或认证失败",  # 默认消息更新
                 error_code: int = ErrorCode.UNAUTHORIZED.value,  # 使用 20003
                 error: Any | None = None,
                 error_tag: str | None = None,
                 http_status_code: int = HTTPStatus.UNAUTHORIZED) -> Response:
    """
    返回 401 Unauthorized 响应 (需要认证)。

    :param message: 错误消息 (默认: "未授权或认证失败")。
    :param error_code: 具体错误码 (默认: ErrorCode.UNAUTHORIZED)。
    :param error: 额外的错误详情 (默认: None)。
    :param error_tag: 可选的错误标签 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 401 Unauthorized)。
    :return: Flask Response 对象。
    """
    return fail(message=message, error_code=error_code, data=error,
                error_tag=error_tag, http_status_code=http_status_code)


def forbidden(message: str = "禁止访问",  # 默认消息更新
              error_code: int = ErrorCode.FORBIDDEN.value,  # 使用 20004
              error: Any | None = None,
              error_tag: str | None = None,
              http_status_code: int = HTTPStatus.FORBIDDEN) -> Response:
    """
     返回 403 Forbidden 响应 (授权失败/权限不足)。

     :param message: 错误消息 (默认: "禁止访问")。
     :param error_code: 具体错误码 (默认: ErrorCode.FORBIDDEN)。
     :param error: 额外的错误详情 (默认: None)。
     :param error_tag: 可选的错误标签 (默认: None)。
     :param http_status_code: HTTP 状态码 (默认: 403 Forbidden)。
     :return: Flask Response 对象。
     """
    return fail(message=message, error_code=error_code, data=error,
                error_tag=error_tag, http_status_code=http_status_code)


def not_found(message: str = "资源未找到",
              error_code: int = ErrorCode.HTTP_NOT_FOUND.value,
              error: Any | None = None,
              error_tag: str | None = None,
              http_status_code: int = HTTPStatus.NOT_FOUND) -> Response:
    """
    返回 404 Not Found 响应。

    :param message: 错误消息 (默认: "资源未找到")。
    :param error_code: 具体错误码 (默认: ErrorCode.HTTP_NOT_FOUND)。
    :param error: 额外的错误详情 (默认: None)。
    :param error_tag: 可选的错误标签 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 404 Not Found)。
    :return: Flask Response 对象。
    """
    return fail(message=message, error_code=error_code, data=error,
                error_tag=error_tag, http_status_code=http_status_code)


def method_not_allowed(message: str = "方法不允许",  # 默认消息更新
                       error_code: int = ErrorCode.HTTP_METHOD_NOT_ALLOWED.value,
                       error: Any | None = None,
                       error_tag: str | None = None,
                       http_status_code: int = HTTPStatus.METHOD_NOT_ALLOWED) -> Response:
    """
    返回 405 Method Not Allowed 响应。

    :param message: 错误消息 (默认: "方法不允许")。
    :param error_code: 具体错误码 (默认: ErrorCode.HTTP_METHOD_NOT_ALLOWED)。
    :param error: 额外的错误详情 (默认: None)。
    :param error_tag: 可选的错误标签 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 405 Method Not Allowed)。
    :return: Flask Response 对象。
    """
    return fail(message=message, error_code=error_code, data=error,
                error_tag=error_tag, http_status_code=http_status_code)


def conflict(message: str = "资源冲突",  # 默认消息更新
             error_code: int = ErrorCode.HTTP_CONFLICT.value,
             error: Any | None = None,
             error_tag: str | None = None,
             http_status_code: int = HTTPStatus.CONFLICT) -> Response:
    """
    返回 409 Conflict 响应。

    :param message: 错误消息 (默认: "资源冲突")。
    :param error_code: 具体错误码 (默认: ErrorCode.HTTP_CONFLICT)。
    :param error: 额外的错误详情 (默认: None)。
    :param error_tag: 可选的错误标签 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 409 Conflict)。
    :return: Flask Response 对象。
    """
    return fail(message=message, error_code=error_code, data=error,
                error_tag=error_tag, http_status_code=http_status_code)


def unsupported_media_type(message: str = "不支持的媒体类型",
                           error_code: int = ErrorCode.HTTP_UNSUPPORTED_MEDIA_TYPE.value,
                           error: Any | None = None,
                           error_tag: str | None = None,
                           http_status_code: int = HTTPStatus.UNSUPPORTED_MEDIA_TYPE) -> Response:
    """
    返回 415 Unsupported Media Type 响应。

    :param message: 错误消息 (默认: "不支持的媒体类型")。
    :param error_code: 具体错误码 (默认: ErrorCode.HTTP_UNSUPPORTED_MEDIA_TYPE)。
    :param error: 额外的错误详情 (默认: None)。
    :param error_tag: 可选的错误标签 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 415 Unsupported Media Type)。
    :return: Flask Response 对象。
    """
    return fail(message=message, error_code=error_code, data=error,
                error_tag=error_tag, http_status_code=http_status_code)


def too_many_requests(message: str = "请求过多",  # 默认消息更新
                      error_code: int = ErrorCode.HTTP_TOO_MANY_REQUESTS.value,
                      error: Any | None = None,
                      error_tag: str | None = None,
                      http_status_code: int = HTTPStatus.TOO_MANY_REQUESTS) -> Response:
    """
    返回 429 Too Many Requests 响应。

    :param message: 错误消息 (默认: "请求过多")。
    :param error_code: 具体错误码 (默认: ErrorCode.HTTP_TOO_MANY_REQUESTS)。
    :param error: 额外的错误详情 (默认: None)。
    :param error_tag: 可选的错误标签 (默认: None)。
    :param http_status_code: HTTP 状态码 (默认: 429 Too Many Requests)。
    :return: Flask Response 对象。
    """
    return fail(message=message, error_code=error_code, data=error,
                error_tag=error_tag, http_status_code=http_status_code)


def server_error(message: str = "服务器内部错误",  # 默认消息更新
                 error_code: int = ErrorCode.INTERNAL_SERVER_ERROR.value,
                 error: Any | None = None,
                 error_tag: str | None = None,
                 http_status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR) -> Response:
    """
     返回 500 Internal Server Error 响应。

     :param message: 错误消息 (默认: "服务器内部错误")。
     :param error_code: 具体错误码 (默认: ErrorCode.INTERNAL_SERVER_ERROR)。
     :param error: 额外的错误详情 (记录日志，可能不发送给客户端)。
     :param error_tag: 可选的错误标签 (默认: None)。
     :param http_status_code: HTTP 状态码 (默认: 500 Internal Server Error)。
     :return: Flask Response 对象。
     """
    # 记录详细错误（如果提供），但可能不在响应中暴露
    if error:
        logger.error(f"服务器内部错误详情: {error}", exc_info=True)  # 添加 exc_info=True 获取堆栈
    return fail(message=message, error_code=error_code, data=None,  # 通常不向客户端暴露内部错误细节 data=None
                error_tag=error_tag, http_status_code=http_status_code)


# ======================
# Error Handlers Registration
# ======================

def register_error_handlers(app):
    """
    为 Flask 应用注册错误处理器。

    处理自定义 API 异常、标准的 Werkzeug 异常 (如 BadRequest)、
    以及捕获通用异常。

    :param app: Flask 应用实例。
    """
    # 已统一使用项目定义的响应函数:
    # handle_authentication_error -> unauthorized(...)
    # handle_authorization_error  -> forbidden(...)
    # handle_not_found_error       -> not_found(...)
    # handle_validation_error      -> bad_request(...)
    # handle_business_error        -> fail(...)
    # handle_database_error        -> server_error(...)
    # handle_api_exception         -> fail(...)
    # handle_http_exception        -> fail(...)
    # handle_generic_exception     -> server_error(...)

    # 优先处理最具体的自定义异常
    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(e: AuthenticationError):
        """处理特定的认证失败异常"""
        logger.warning(f"认证失败: {e.message}")
        return unauthorized(message=e.message, error_code=e.error_code, error_tag=e.error_tag)

    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(e: AuthorizationError):
        """处理特定的授权失败异常"""
        logger.warning(f"权限不足: {e.message}")
        return forbidden(message=e.message, error_code=e.error_code, error_tag=e.error_tag)

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(e: NotFoundError):
        """处理资源未找到异常"""
        logger.info(f"资源未找到: {e.message}")  # Not Found 通常不是严重错误
        return not_found(message=e.message, error_code=e.error_code, error_tag=e.error_tag)

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        """处理验证错误 (包括 ParamMissing, ParamInvalid)"""
        logger.warning(f"验证错误: {e.message}")
        # 优先使用异常自带的 error_code
        error_code_to_use = e.error_code if e.error_code is not None else ErrorCode.PARAM_INVALID.value
        return bad_request(message=e.message, error_code=error_code_to_use, error_tag=e.error_tag)

    @app.errorhandler(BusinessError)
    def handle_business_error(e: BusinessError):
        """处理业务逻辑错误"""
        logger.warning(f"业务逻辑错误: {e.message}")
        # 错误码到 HTTP 状态码的映射表
        ERROR_CODE_HTTP_MAPPING = {
            20002: HTTPStatus.CONFLICT,     # Account already exists
            20003: HTTPStatus.NOT_FOUND,    # 用户不存在
            20004: HTTPStatus.FORBIDDEN,    # 权限不足
            20005: HTTPStatus.UNAUTHORIZED, # 未登录/登录失效
            20006: HTTPStatus.BAD_REQUEST,  # 参数非法
            # 可根据实际 error_code 扩展
        }

        status_code = ERROR_CODE_HTTP_MAPPING.get(e.error_code, e.http_status_code)

        return fail(message=e.message,
                    error_code=e.error_code,
                    http_status_code=status_code,
                    error_tag=e.error_tag)

    @app.errorhandler(DatabaseError)
    def handle_database_error(e: DatabaseError):
        """处理数据库错误"""
        logger.error(f"数据库错误: {e.message}", exc_info=True)
        # 数据库错误通常返回 500
        return server_error(message="数据库操作失败",  # 给用户的通用消息
                            error_code=e.error_code,
                            error_tag=e.error_tag)

    # 处理通用的自定义异常基类 (如果上面的具体异常没有捕获)
    @app.errorhandler(APIException)
    def handle_api_exception(e: APIException):
        """处理通用的 APIException"""
        logger.error(f"API 异常: Code {e.error_code} - {e.message}")
        return fail(message=e.message,
                    error_code=e.error_code,
                    http_status_code=e.http_status_code,
                    error_tag=e.error_tag)

    # 处理 Werkzeug HTTP 异常 (例如路由未匹配产生的 404, 方法不允许产生的 405)
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        """处理 Werkzeug 的 HTTPException"""
        logger.warning(f"HTTP 异常: {e.code} - {e.name}. Description: {e.description}")
        # 使用 fail 函数，并从异常中获取 HTTP 状态码和消息
        # 尝试映射 HTTP 状态码到业务错误码（可选，可以都用通用错误码）
        error_code = ErrorCode.OPERATION_FAILED.value  # 默认通用码
        if e.code == 400:
            error_code = ErrorCode.PARAM_INVALID.value
        elif e.code == 404:
            error_code = ErrorCode.HTTP_NOT_FOUND.value
        elif e.code == 405:
            error_code = ErrorCode.HTTP_METHOD_NOT_ALLOWED.value
        # ... 可以添加更多映射
        return fail(message=e.description or e.name,  # 使用 description 或 name 作为消息
                    error_code=error_code,
                    http_status_code=e.code)

    # 处理所有未被捕获的 Python 通用异常
    @app.errorhandler(Exception)
    def handle_generic_exception(e: Exception):
        """处理未捕获的通用异常"""
        logger.error(f"发生未捕获的异常: {str(e)}", exc_info=True)  # 记录完整堆栈
        # 返回标准的 500 JSON 错误响应
        return server_error(message="服务器发生内部错误，请稍后重试。")  # 更友好的用户消息


# ======================
# Exportable Components
# ======================

__all__ = [
    # HTTP Status Codes (re-exported for convenience)
    "HTTPStatus",

    # Response Structure & Functions
    "ApiResponse",
    "success", "fail",
    "created", "no_content",
    "bad_request", "unauthorized", "forbidden", "not_found",
    "method_not_allowed", "conflict", "unsupported_media_type",
    "too_many_requests", "server_error",

    # Error Handling Registration
    "register_error_handlers",

    # Error Codes Enum (Exported for use elsewhere, e.g., in services)
    "ErrorCode",

    # Custom Exceptions are now in exceptions.py, so removed from here
]
