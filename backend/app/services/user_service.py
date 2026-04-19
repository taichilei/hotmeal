"""
@File       : user_service.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 用户服务层，处理用户数据的创建、查询、更新和删除逻辑，采用 "失败抛异常，成功返数据"模式
"""

import logging
from typing import Any

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.utils.db import db
from app.utils.error_codes import ErrorCode
from app.utils.exceptions import (
    APIException,
    AuthorizationError,
    BadRequestError,
    BusinessError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# --- 创建用户 ---
def create_user(account: str, password: str, role_name: str = "USER") -> dict[str, Any]:
    """
    创建新用户并存储加密密码。

    Args:
        account: 用户账号。
        password: 用户输入的明文密码。
        role_name: 用户角色名称 (字符串, e.g., "USER", "ADMIN")。

    Returns:
        成功时返回包含新用户信息（不含密码）的字典。

    Raises:
        BusinessError: 如果Account already exists或角色名称无效。
        APIException: 如果发生其他数据库错误。
    """
    if User.query.filter_by(account=account).first():
        logger.warning(f"尝试创建已存在的账号: {account}")
        raise BusinessError("Account already exists", error_code=ErrorCode.ACCOUNT_EXISTS.value)

    try:
        role_enum = UserRole[role_name.upper()]
    except KeyError:
        logger.warning(f"注册时提供了无效的角色: {role_name}")
        raise BusinessError("Invalid role", error_code=ErrorCode.PARAM_INVALID.value)

    user = User(account=account, role=role_enum)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        logger.info(f"用户 {account} 创建成功, role={role_enum.name}")
        return user.to_dict()
    except IntegrityError:
        db.session.rollback()
        logger.warning(f"创建用户时发生数据库层面的账号冲突: {account}")
        raise BusinessError("Account already exists (DB)",
                            error_code=ErrorCode.ACCOUNT_EXISTS.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"创建用户时发生数据库错误: {e}", exc_info=True)
        raise APIException("创建用户失败，发生数据库错误", error_code=ErrorCode.DATABASE_ERROR.value)
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建用户时发生未知错误: {e}", exc_info=True)
        raise APIException("创建用户时发生未知错误",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value)


# --- 查询用户 ---
def get_user_by_id(user_id: int) -> dict[str, Any]:
    """
    根据用户 ID 检索用户。

    Args:
        user_id: 用户 ID。

    Returns:
        包含用户信息的字典。

    Raises:
        NotFoundError: 如果User not found。
    """
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"尝试获取不存在的用户: user_id={user_id}")
        raise NotFoundError("User not found", error_code=ErrorCode.USER_NOT_FOUND.value)
    logger.debug(f"成功获取用户: user_id={user_id}")
    return user.to_dict()


def get_all_users() -> list[dict[str, Any]]:
    """
    检索所有状态为 ACTIVE 的用户。

    Returns:
        包含所有活跃用户信息的字典列表。

    Raises:
        APIException: 如果发生数据库错误。
    """
    try:
        users = User.query.filter(User.status == UserStatus.ACTIVE).all()
        user_list = [u.to_dict() for u in users]
        logger.info(f"成功检索到 {len(user_list)} 个活跃用户。")
        return user_list
    except SQLAlchemyError as e:
        logger.error(f"检索活跃用户列表时发生数据库错误: {e}", exc_info=True)
        raise APIException("获取用户列表失败", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 按角色查询活跃用户 ---
def get_users_by_role(role_name: str) -> list[dict[str, Any]]:
    """
    根据角色查询所有活跃用户。

    Args:
        role_name: 角色名称，例如 "STAFF"、"USER"、"ADMIN"

    Returns:
        匹配角色的活跃用户列表。
    """
    try:
        role_enum = UserRole[role_name.upper()]
    except KeyError:
        logger.warning(f"尝试查询非法角色: {role_name}")
        raise ValidationError("Invalid role name", error_code=ErrorCode.PARAM_INVALID.value)

    try:
        users = User.query.filter(
            User.role == role_enum,
            User.status == UserStatus.ACTIVE
        ).all()
        user_list = [u.to_dict() for u in users]
        logger.info(f"成功获取角色为 {role_enum.name} 的 {len(user_list)} 个活跃用户。")
        return user_list
    except SQLAlchemyError as e:
        logger.error(f"获取指定角色用户时数据库异常: {e}", exc_info=True)
        raise APIException("获取用户失败", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 分页获取指定角色的用户列表 ---
def list_users_by_role(role_name: str, page: int = 1, per_page: int = 10) -> dict[str, Any]:
    """
    分页获取指定角色的用户列表。

    Args:
        role_name: 角色名称，例如 "STAFF"
        page: 当前页码
        per_page: 每页数量

    Returns:
        包含分页信息和用户数据的字典
    """
    try:
        role_enum = UserRole[role_name.upper()]
    except KeyError:
        logger.warning(f"分页查询非法角色: {role_name}")
        raise ValidationError("Invalid role name", error_code=ErrorCode.PARAM_INVALID.value)

    try:
        pagination: Pagination = User.query.filter(
            User.role == role_enum,
            User.status == UserStatus.ACTIVE
        ).paginate(page=page, per_page=per_page, error_out=False)

        user_list = [user.to_dict() for user in pagination.items]
        return {
            "total": pagination.total,
            "pages": pagination.pages,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
            "items": user_list
        }
    except SQLAlchemyError as e:
        logger.error(f"分页获取角色为 {role_name} 的用户时发生数据库异常: {e}", exc_info=True)
        raise APIException("分页获取用户失败", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 更新用户 (内部辅助函数) ---
def _update_user_fields(user: User, data: dict[str, Any], allowed_fields: list[str]) -> bool:
    """
    内部函数，用于更新 User 对象的指定字段。
    不处理权限检查、用户查找和数据库提交。

    Args:
        user: 要更新的 User ORM 对象。
        data: 包含更新数据的字典。
        allowed_fields: 允许更新的字段名称列表。

    Returns:
        True 如果有字段被实际更新，否则 False。

    Raises:
        ValidationError: 如果 email/phone 格式无效，或 role/status 值无效。
                         (依赖 User 模型的 validate_* 方法抛出 ValueError)
                         (依赖枚举转换抛出 KeyError)
    """
    updated = False
    processed_data = {k: v for k, v in data.items() if v is not None}  # 忽略值为 None 的字段

    for key, value in processed_data.items():
        if key not in allowed_fields:
            logger.warning(f"尝试更新不允许的字段 '{key}' for user {user.user_id}")
            continue  # 跳过不允许更新的字段

        # --- 特殊字段处理 ---
        if key == 'password':
            # 密码应由外部调用 set_password 处理，这里只标记需要更新
            # 或者如果允许在此更新，确保 value 是明文密码
            logger.debug(f"字段 '{key}' 将由外部处理 (set_password)")
            continue  # 跳过密码字段，由外部函数处理
        elif key == 'role':
            try:
                role_enum = UserRole[str(value).upper()]
                if user.role != role_enum:
                    user.role = role_enum
                    updated = True
                    logger.debug(f"User {user.user_id} field 'role' set to {role_enum.name}")
            except KeyError:
                raise ValidationError(f"无效的角色: {value}",
                                      error_code=ErrorCode.PARAM_INVALID.value)
        elif key == 'status':
            try:
                status_enum = UserStatus[str(value).upper()]
                if user.status != status_enum:
                    user.status = status_enum
                    updated = True
                    logger.debug(f"User {user.user_id} field 'status' set to {status_enum.name}")
            except KeyError:
                raise ValidationError(f"无效的状态: {value}",
                                      error_code=ErrorCode.PARAM_INVALID.value)
        elif key == 'email':
            if getattr(user, key) != value:
                try:
                    user.email = value
                except ValueError as ve:
                    raise ValidationError(f"Invalid email format: {ve}",
                                          error_code=ErrorCode.PARAM_INVALID.value)
                updated = True
                logger.debug(f"User {user.user_id} field 'email' set to {value}")
        elif key == 'phone_number':
            if getattr(user, key) != value:
                user.phone_number = value
                updated = True
                logger.debug(f"User {user.user_id} field 'phone_number' set to {value}")
        # --- 处理 favorite_cuisine ---
        elif key == 'favorite_cuisine':
            clean_cuisine = value.strip() if isinstance(value, str) else None
            if getattr(user, key) != clean_cuisine:
                try:
                    # @validates 会处理长度等基础验证
                    user.favorite_cuisine = clean_cuisine
                    updated = True
                    logger.debug(
                        f"User {user.user_id} field 'favorite_cuisine' set to {clean_cuisine}")
                except ValueError as ve:
                    raise ValidationError(f"设置偏好菜系时出错: {ve}",
                                          error_code=ErrorCode.PARAM_INVALID.value)
        # --- 通用字段处理 (account, username) ---
        elif hasattr(user, key):
            if getattr(user, key) != value:
                # TODO: 在外部函数 commit 前检查 account, username 的唯一性
                setattr(user, key, value)
                updated = True
                logger.debug(f"User {user.user_id} field '{key}' set to {value}")
        else:
            # 这个分支理论上不应进入，因为有 allowed_fields 检查
            logger.error(f"尝试设置 User 对象不存在的属性: {key}")

    return updated


# --- 更新用户 (外部接口) ---
def update_user_profile(user_id: int, update_data: dict[str, Any]) -> dict[str, Any]:
    """
    允许用户更新自己的部分个人资料 (username, email, phone_number, password)。

    Args:
        user_id: 当前用户的 ID。
        update_data: 包含更新数据的字典。

    Returns:
        成功时返回更新后的用户信息字典。

    Raises:
        NotFoundError: 如果User not found。
        ValidationError: 如果输入数据无效 (格式错误)。
        BusinessError: 如果邮箱/手机号/用户名唯一性冲突。
        APIException: 如果发生其他数据库错误。
    """
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"尝试更新不存在的用户个人资料: user_id={user_id}")
        raise NotFoundError("User not found", error_code=ErrorCode.USER_NOT_FOUND.value)

    # 定义普通用户允许更新的字段
    allowed_fields = ['username', 'email', 'phone_number', 'password', 'favorite_cuisine']  # 包含密码

    # 调用内部函数处理允许的字段 (除密码外)
    data_without_password = {k: v for k, v in update_data.items() if k != 'password'}
    updated = _update_user_fields(user, data_without_password, allowed_fields)

    # 单独处理密码更新
    new_password = update_data.get('password')
    if new_password and 'password' in allowed_fields:
        user.set_password(new_password)
        logger.info(f"用户 {user_id} 更新了自己的密码。")
        updated = True  # 标记有更新发生

    if not updated:
        logger.info(f"用户 {user_id} 没有提供需要更新的个人资料信息。")
        return user.to_dict()

    # 提交数据库
    try:
        db.session.commit()
        logger.info(f"用户 {user_id} 个人资料更新成功。")
        return user.to_dict()
    except IntegrityError as e:  # 捕获唯一性约束冲突
        db.session.rollback()
        logger.error(f"更新用户 {user_id} 个人资料时发生唯一性冲突: {e}", exc_info=True)
        # 更具体的错误判断可能需要解析错误详情 e.orig
        raise BusinessError("更新失败，用户名、邮箱或手机号可能已被占用。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"更新用户 {user_id} 个人资料时发生数据库错误: {e}", exc_info=True)
        raise APIException("更新个人资料失败", error_code=ErrorCode.DATABASE_ERROR.value)


def admin_update_user(operator_id: int,
                      user_id: int,
                      update_data: dict[str, Any]) -> dict[str, Any]:
    """
    允许管理员更新指定用户的信息。

    Args:
        operator_id: 执行操作的管理员的用户 ID。
        user_id: 被更新用户的 ID。
        update_data: 包含待更新字段和值的字典。

    Returns:
        成功时返回更新后的用户信息字典。

    Raises:
        NotFoundError: 如果操作员或被更新User not found。
        AuthorizationError: 如果操作员不是管理员。
        ValidationError: 如果输入数据无效 (格式、角色、状态)。
        BusinessError: 如果账号、邮箱、手机号唯一性冲突。
        APIException: 如果发生其他数据库错误。
    """
    operator = User.query.get(operator_id)
    if not operator:
        logger.error(f"执行更新操作的管理员未找到: operator_id={operator_id}")
        raise NotFoundError("操作员信息无效", error_code=ErrorCode.USER_NOT_FOUND.value)

    user_to_update = User.query.get(user_id)
    if not user_to_update:
        logger.warning(f"管理员 {operator_id} 尝试更新不存在的用户: user_id={user_id}")
        raise NotFoundError("要更新的User not found", error_code=ErrorCode.USER_NOT_FOUND.value)

    if not operator.is_admin():
        logger.warning(f"用户 {operator_id} (非管理员) 尝试更新用户 {user_id} 的信息。")
        raise AuthorizationError("无权执行此操作", error_code=ErrorCode.FORBIDDEN.value)

    # 定义管理员允许更新的字段
    allowed_fields = ['account', 'username', 'email', 'phone_number', 'role', 'status', 'password',
                      'favorite_cuisine']

    # 调用内部函数处理允许的字段 (除密码外)
    data_without_password = {k: v for k, v in update_data.items() if k != 'password'}
    updated = _update_user_fields(user_to_update, data_without_password, allowed_fields)

    # 单独处理密码更新 (如果管理员允许设置)
    new_password = update_data.get('password')
    if new_password and 'password' in allowed_fields:
        user_to_update.set_password(new_password)
        logger.info(f"管理员 {operator_id} 更新了用户 {user_id} 的密码。")
        updated = True

    if not updated:
        logger.info(f"管理员 {operator_id} 没有为用户 {user_id} 提供需要更新的信息。")
        return user_to_update.to_dict()

    # 提交数据库
    try:
        db.session.commit()
        logger.info(f"管理员 {operator_id} 成功更新了用户 {user_id} 的信息。")
        return user_to_update.to_dict()
    except IntegrityError as e:  # 捕获唯一性约束冲突
        db.session.rollback()
        logger.error(f"管理员 {operator_id} 更新用户 {user_id} 时发生唯一性冲突: {e}",
                     exc_info=True)
        raise BusinessError("更新失败，账号、邮箱或手机号可能已被占用。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"管理员 {operator_id} 更新用户 {user_id} 时发生数据库错误: {e}",
                     exc_info=True)
        raise APIException("更新用户信息失败", error_code=ErrorCode.DATABASE_ERROR.value)


def update_user_avatar(user_id: int, avatar_url: str) -> str:
    """
    update user's avatar url
    """
    if not avatar_url or not avatar_url.startswith("http"):
        raise BadRequestError("invalid avatar url")

    user = User.query.get(user_id)
    if not user or not user.is_active():
        raise NotFoundError("User not found")

    user.avatar_url = avatar_url
    db.session.commit()
    return avatar_url


# --- 删除用户 ---
def deactivate_user(user_id: int) -> bool:
    """
    软删除用户 (更新状态为 DELETED)。

    Args:
        user_id: 用户 ID。

    Returns:
        True 表示成功。

    Raises:
        NotFoundError: 如果User not found。
        APIException: 如果发生数据库错误。
    """
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"尝试停用不存在的用户: user_id={user_id}")
        raise NotFoundError("User not found", error_code=ErrorCode.USER_NOT_FOUND.value)

    if user.status == UserStatus.DELETED:
        logger.info(f"用户 {user_id} 已处于 DELETED 状态，无需操作。")
        return True

    try:
        user.status = UserStatus.DELETED
        db.session.commit()
        logger.info(f"用户 {user.account} (ID: {user_id}) 已被停用 (软删除)。")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"停用用户 {user_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("停用用户失败", error_code=ErrorCode.DATABASE_ERROR.value)


def delete_user(user_id: int) -> bool:
    """
    硬删除用户 (从数据库中永久删除)。

    Args:
        user_id: 用户 ID。

    Returns:
        True 表示成功。

    Raises:
        NotFoundError: 如果User not found。
        BusinessError: 如果存在外键约束导致无法删除。
        APIException: 如果发生其他数据库错误。
    """
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"尝试删除不存在的用户: user_id={user_id}")
        raise NotFoundError("User not found", error_code=ErrorCode.USER_NOT_FOUND.value)

    try:
        account_copy = user.account
        db.session.delete(user)
        db.session.commit()
        logger.info(f"用户 {account_copy} (ID: {user_id}) 已被永久删除。")
        return True
    except IntegrityError as e:  # 捕获外键约束等错误
        db.session.rollback()
        logger.error(f"删除用户 {user_id} 失败，可能存在关联数据。错误: {e}", exc_info=True)
        raise BusinessError("无法删除用户，可能存在关联的订单或其他数据。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"删除用户 {user_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("删除用户失败", error_code=ErrorCode.DATABASE_ERROR.value)
