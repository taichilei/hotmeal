"""
@File       : decorators.py
@Date       : 2025-03-01
@Desc       : General purpose decorators for Flask route handlers.


"""

import functools
import logging
import time
from collections.abc import Callable  # 导入 TypeVar, cast 用于泛型
from typing import Any, TypeVar, cast

from flask import request
from flask_jwt_extended import (  # 移除 get_jwt_identity 如果确实不用
    get_jwt,
    jwt_required,
)

from app.utils.error_codes import ErrorCode
from app.utils.exceptions import AuthorizationError  # 导入需要的异常

logger = logging.getLogger(__name__)

# 定义一个类型变量，用于装饰器的类型提示
F = TypeVar('F', bound=Callable[..., Any])


def log_request(f: F) -> F:
    """
    Decorator to log request details for debugging purposes.

    Logs method, path, headers, and body (for relevant methods).

    Args:
        f: The function to decorate.

    Returns:
        The decorated function.
    """

    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function for logging request."""
        log_prefix = f"[请求 {request.method} {request.path}]"
        try:
            req_headers = dict(request.headers)
            if 'Authorization' in req_headers:
                req_headers['Authorization'] = 'Bearer [REDACTED]'  # 脱敏

            logger.info(f"{log_prefix} 开始处理")
            logger.debug(f"{log_prefix} Headers: {req_headers}")

            if request.method in ['POST', 'PUT', 'PATCH']:
                req_body = None
                content_type = request.content_type or ''  # 处理 content_type 为 None 的情况
                if 'application/json' in content_type:
                    req_body = request.get_json(silent=True)
                    if req_body is None and request.data:
                        logger.warning(f"{log_prefix} Body: 收到无效 JSON: {request.data[:200]}...")
                elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
                    # 注意：对于 multipart/form-data，request.form 只包含表单字段，不含文件
                    req_body = request.form.to_dict()
                # 可以添加其他 Content-Type 的日志记录逻辑

                if req_body is not None:
                    logger.info(f"{log_prefix} Body/Form: {req_body}")
                # else: # 减少不必要的日志
                #      logger.debug(f"{log_prefix} 无 Body/Form 数据或 Content-Type 不支持记录。")

        except Exception as log_ex:
            logger.error(f"{log_prefix} 处理请求日志时出错: {log_ex}", exc_info=True)

        # 执行被装饰的函数
        result = f(*args, **kwargs)

        # 可以在这里记录响应状态码等信息（如果需要）
        # status_code = getattr(result, 'status_code', None)
        # logger.info(f"{log_prefix} 处理完成 (状态码: {status_code})")

        return result

    # 使用 cast 帮助类型检查器理解 wrapper 的类型与 f 一致
    return cast(F, wrapper)


def timing(f: F) -> F:
    """
    Decorator to measure and log the execution time of a function in milliseconds.

    Args:
        f: The function to decorate.

    Returns:
        The decorated function.
    """

    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function for timing."""
        start_time = time.perf_counter()
        try:
            result = f(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            duration = (end_time - start_time) * 1000
            func_name = f.__name__
            req_path = getattr(request, 'path', 'N/A')  # 在请求上下文之外调用时 request 可能不存在
            logger.info(f"[执行耗时] {func_name} @ {req_path} - {duration:.2f} ms")

    return cast(F, wrapper)


def require_roles(allowed_roles: list[str]) -> Callable[[F], F]:
    """
    Decorator factory to ensure the current user has one of the specified roles.

    Reads the 'role' claim from the JWT access token. Assumes `@jwt_required()`
    is applied before this decorator.

    Args:
        allowed_roles: A list of role name strings (case-insensitive) that are permitted.
                       Example: ["admin", "staff"]

    Returns:
        A decorator function.

    Raises:
        AuthorizationError: If the token/claims are missing, the role claim is missing,
                           or the user's role is not in the allowed list.
    """
    # 预处理允许的角色，转为大写集合以便高效查找
    allowed_set = {role.upper() for role in allowed_roles}

    def decorator(f: F) -> F:
        """The actual decorator."""

        @jwt_required()
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper that performs the role check."""
            claims = get_jwt()  # 获取 JWT payload
            if not claims:
                # Should ideally be caught by @jwt_required, but acts as a safeguard.
                logger.warning("require_roles: Missing JWT claims unexpectedly.")
                raise AuthorizationError("缺少认证令牌。", error_code=ErrorCode.UNAUTHORIZED.value)

            user_role = claims.get("role")  # 从 payload 中获取 'role'
            if not user_role or not isinstance(user_role, str):  # 检查是否存在且为字符串
                # sub (subject) 通常是 user_id
                identity = claims.get('sub', 'unknown')
                logger.error(
                    f"require_roles: JWT claim 'role' is missing or not a string for identity {identity}.")
                # 角色问题是权限问题
                raise AuthorizationError("令牌中缺少有效的角色信息。",
                                         error_code=ErrorCode.FORBIDDEN.value)

            # 统一转为大写进行比较
            if user_role.upper() not in allowed_set:
                identity = claims.get('sub', 'unknown')
                path = getattr(request, 'path', 'N/A')
                logger.warning(
                    f"require_roles: User {identity} with role '{user_role}' is not in allowed roles {allowed_set} for path '{path}'.")
                raise AuthorizationError("Permission denied",
                                         error_code=ErrorCode.FORBIDDEN.value)

            # Role check passed, execute the original function
            return f(*args, **kwargs)

        return cast(F, wrapper)  # 帮助类型检查器

    return decorator
