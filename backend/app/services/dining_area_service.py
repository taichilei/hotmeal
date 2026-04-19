"""
@File       : dining_area_service.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Description: 用餐区域服务层，处理用餐区域的创建、查询、分配、释放、更新和删除逻辑，采用 "失败抛异常，成功返数据"模式
"""

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.dining_area import DiningArea
from app.models.enums import AreaType, DiningAreaState
from app.models.user import User  # 需要导入 User 来检查用户是否存在
from app.utils.db import db

# 导入需要的错误码枚举
from app.utils.error_codes import ErrorCode

# 导入需要的异常类型
from app.utils.exceptions import (
    APIException,
    BusinessError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# --- 辅助函数 ---
# 确认 _serialize_dining_area 函数名，或者直接使用模型的 to_dict
def _serialize_dining_area(area: DiningArea) -> dict[str, Any]:
    """内部辅助函数，用于序列化 DiningArea 对象。"""
    if not isinstance(area, DiningArea):
        logger.error(f"尝试序列化非 DiningArea 对象: {type(area)}")
        return {}
    # 调用模型自身的 to_dict 方法
    return area.to_dict()  # 假设 to_dict 存在且符合要求


# --- 创建区域 ---
def create_dining_area(area_name: str, max_capacity: int | None, area_type: AreaType,
                       # max_capacity 改为可选
                       state: DiningAreaState = DiningAreaState.FREE) -> dict[str, Any]:
    """
    创建新的用餐区域。
    """
    try:
        # 输入验证 (模型层 @validates 也会验证，这里做初步检查)
        clean_name = area_name.strip() if area_name else ""
        if not clean_name:
            raise ValidationError("区域名称不能为空。", error_code=ErrorCode.PARAM_MISSING.value)

        if max_capacity is not None:  # 验证可选的 max_capacity
            if not isinstance(max_capacity, int) or max_capacity <= 0:
                logger.warning(f"尝试创建用餐区域时提供了无效的最大容量: {max_capacity}")
                raise ValidationError("最大容量必须是一个正整数。",
                                      error_code=ErrorCode.PARAM_INVALID.value)
        # else: # 如果 max_capacity 可以为 None，则无需验证

        if not isinstance(area_type, AreaType):
            logger.warning(f"尝试创建用餐区域时提供了无效的区域类型: {area_type}")
            raise ValidationError("无效的区域类型。", error_code=ErrorCode.PARAM_INVALID.value)
        if not isinstance(state, DiningAreaState):
            logger.warning(f"尝试创建用餐区域时提供了无效的状态: {state}")
            raise ValidationError("无效的区域状态。", error_code=ErrorCode.PARAM_INVALID.value)

        # 检查名称唯一性 (使用 exists() 更佳)
        name_exists = db.session.query(
            DiningArea.query.filter(DiningArea.area_name.ilike(clean_name)).exists()
        ).scalar()
        if name_exists:
            logger.warning(f"尝试创建已存在的用餐区域名称: {clean_name}")

            raise BusinessError("Dining area name already exists.",
                                error_code=ErrorCode.HTTP_CONFLICT.value)

        # 创建新区域实例 (依赖模型验证)
        try:
            # 注意：模型 __init__ 已移除，直接通过关键字参数创建
            new_area = DiningArea(
                area_name=clean_name,  # 使用处理过的名称
                max_capacity=max_capacity,
                area_type=area_type,
                state=state
            )
            # 模型的 @validates 会在赋值时触发
        except ValueError as ve:  # 捕获模型验证错误
            raise ValidationError(f"创建区域时数据验证失败: {ve}",
                                  error_code=ErrorCode.PARAM_INVALID.value) from ve

        logger.info(f"准备创建新用餐区域: {clean_name}, 容量: {max_capacity}, 类型: {area_type.name}")

        try:
            db.session.add(new_area)
            db.session.commit()
            logger.info(f"用餐区域 '{new_area.area_name}' (ID: {new_area.area_id}) 创建成功。")
            # 刷新不是必须的，因为 commit 后对象状态会自动更新，但有时为了确保关系等加载可以使用
            # db.session.refresh(new_area)
            return _serialize_dining_area(new_area)  # 返回序列化字典
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"创建用餐区域 '{clean_name}' 时发生唯一性冲突: {e}", exc_info=True)
            raise BusinessError(f"Dining area name '{clean_name}' already exists.",
                                error_code=ErrorCode.HTTP_CONFLICT.value) from e
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"创建用餐区域 '{clean_name}' 时发生数据库错误: {e}", exc_info=True)
            raise APIException("创建用餐区域失败，数据库错误。",
                               error_code=ErrorCode.DATABASE_ERROR.value) from e
    except Exception:
        logger.exception("创建用餐区域时发生未知错误", exc_info=True)
        raise APIException("创建用餐区域失败，发生未知服务器错误。", error_code=ErrorCode.INTERNAL_SERVER_ERROR.value)


# --- 查询区域 ---
def get_dining_area(area_id: int) -> dict[str, Any]:
    """
    根据 ID 检索用餐区域记录。
    """
    # 可以在查询时预加载关联数据（如果 to_dict 需要）
    # area = DiningArea.query.options(db.joinedload(DiningArea.assigned_user)).get(area_id)
    area = DiningArea.query.get(area_id)
    if not area:
        logger.warning(f"尝试获取不存在的用餐区域: area_id={area_id}")
        raise NotFoundError(f"ID 为 {area_id} 的用餐区域未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    logger.info(f"成功检索到用餐区域: area_id={area_id}, name='{area.area_name}'")
    return _serialize_dining_area(area)  # 使用序列化函数


def fetch_dining_areas(area_type: AreaType | None = None,
                       state: DiningAreaState | None = None) -> list[dict[str, Any]]:
    """
    检索所有用餐区域记录，可选按类型和状态过滤。
    """
    query = DiningArea.query

    if area_type is not None:
        # 类型检查可以省略，如果路由层已经保证了类型
        # if not isinstance(area_type, AreaType):
        #      raise ValidationError(...)
        query = query.filter(DiningArea.area_type == area_type)

    if state is not None:
        # if not isinstance(state, DiningAreaState):
        #     raise ValidationError(...)
        query = query.filter(DiningArea.state == state)

    try:
        areas = query.order_by(DiningArea.area_name).all()
        data = [_serialize_dining_area(area) for area in areas]  # 使用序列化函数
        logger.info(f"成功检索到 {len(data)} 个用餐区域记录。"
                    f"{' 类型: ' + area_type.name if area_type else ''}"
                    f"{' 状态: ' + state.name if state else ''}")
        return data
    except SQLAlchemyError as e:
        logger.error(f"检索用餐区域列表时发生数据库错误: {e}", exc_info=True)
        raise APIException("获取用餐区域列表失败。", error_code=ErrorCode.DATABASE_ERROR.value) from e


# --- 分配/占用区域 ---
def assign_dining_area(area_id: int, user_id: int) -> dict[str, Any]:
    """
    将一个空闲的用餐区域分配给指定用户。
    """
    area = DiningArea.query.get(area_id)
    if not area:
        raise NotFoundError(f"ID 为 {area_id} 的用餐区域未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(f"ID 为 {user_id} 的User not found。",
                            error_code=ErrorCode.USER_NOT_FOUND.value)

    if area.state != DiningAreaState.FREE:
        raise BusinessError("Area is already occupied",
                            error_code=ErrorCode.HTTP_CONFLICT.value)

    try:
        # 调用模型方法标记状态，但不 commit
        success_mark = area.mark_as_occupied(user_id)
        if not success_mark:  # 虽然当前模型实现总是返回 True，但以防万一
            # 这个分支理论上不会进入，因为前面检查了状态
            logger.error(f"标记区域 {area_id} 为占用时内部逻辑失败。")
            raise APIException("分配区域时发生内部错误。",
                               error_code=ErrorCode.INTERNAL_SERVER_ERROR.value)

        db.session.commit()  # 服务层提交
        logger.info(
            f"用餐区域 {area_id} ('{area.area_name}') 已成功分配给用户 {user_id} ('{user.account}')。")
        return _serialize_dining_area(area)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"将区域 {area_id} 分配给用户 {user_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("分配用餐区域失败。", error_code=ErrorCode.DATABASE_ERROR.value) from e


# --- 释放区域 ---
def release_dining_area(area_id: int) -> dict[str, Any]:
    """
    释放一个已被占用的用餐区域。
    """
    area = DiningArea.query.get(area_id)
    if not area:
        raise NotFoundError(f"ID 为 {area_id} 的用餐区域未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    if area.state == DiningAreaState.FREE:
        logger.info(f"用餐区域 {area_id} ('{area.area_name}') 已是空闲状态，无需释放。")
        return _serialize_dining_area(area)  # 幂等性：返回当前状态

    try:
        # 调用模型方法标记状态，但不 commit
        success_mark = area.mark_as_free()
        if not success_mark:  # 理论上如果状态是 OCCUPIED 应该能成功标记
            logger.error(f"标记区域 {area_id} 为空闲时内部逻辑失败。")
            raise APIException("释放区域时发生内部错误。",
                               error_code=ErrorCode.INTERNAL_SERVER_ERROR.value)

        db.session.commit()  # 服务层提交
        logger.info(f"用餐区域 {area_id} ('{area.area_name}') 已成功释放。")
        return _serialize_dining_area(area)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"释放区域 {area_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("释放用餐区域失败。", error_code=ErrorCode.DATABASE_ERROR.value) from e


# --- 更新区域信息 ---
def update_dining_area(area_id: int, update_data: dict[str, Any]) -> dict[str, Any]:
    """
    更新用餐区域的信息 (通常由管理员操作)。
    """
    area = DiningArea.query.get(area_id)
    if not area:
        raise NotFoundError(f"ID 为 {area_id} 的用餐区域未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    updated = False
    processed_data = {k: v for k, v in update_data.items() if v is not None}

    # 检查名称唯一性 (如果提供了 name 且与当前不同)
    new_name = processed_data.get('area_name')
    if new_name and new_name.strip() != area.area_name:
        clean_new_name = new_name.strip()
        name_exists = db.session.query(
            DiningArea.query.filter(DiningArea.area_name.ilike(clean_new_name),
                                    DiningArea.area_id != area_id).exists()
        ).scalar()
        if name_exists:
            raise BusinessError("Dining area name already exists.",
                                error_code=ErrorCode.HTTP_CONFLICT.value)

    # 尝试批量设置属性，依赖模型的 @validates
    allowed_fields = ['area_name', 'max_capacity', 'state', 'area_type']  # 定义允许更新的字段
    try:
        for key, value in processed_data.items():
            if key in allowed_fields:
                current_value = getattr(area, key)
                # 对枚举类型进行特殊比较
                if isinstance(current_value, (DiningAreaState, AreaType)):
                    try:
                        if key == 'state':
                            enum_value = DiningAreaState[str(value).upper()]
                        else:  # key == 'area_type'
                            enum_value = AreaType[str(value).upper()]

                        # 处理不允许的状态转换（如果直接更新状态）
                        if key == 'state':
                            if enum_value == DiningAreaState.FREE and area.assigned_user_id is not None:
                                logger.warning(
                                    f"将区域 {area_id} 状态改为 FREE，将清除关联的用户 ID {area.assigned_user_id}")
                                area.assigned_user_id = None  # 清除关联用户
                            elif enum_value == DiningAreaState.OCCUPIED and area.assigned_user_id is None:
                                raise ValidationError("不能直接将状态更新为占用，请使用分配接口。",
                                                      error_code=ErrorCode.PARAM_INVALID.value)

                        if current_value != enum_value:
                            setattr(area, key, enum_value)
                            updated = True
                    except KeyError:
                        raise ValidationError(f"无效的 {key} 值: {value}",
                                              error_code=ErrorCode.PARAM_INVALID.value) from None
                elif current_value != value:
                    # 对于 max_capacity, @validates 会处理类型和范围
                    setattr(area, key, value)  # 触发模型的 @validates
                    updated = True

                if updated and current_value != getattr(area, key):  # 确认值真的改变了再记录日志
                    logger.debug(
                        f"Area {area_id} field '{key}' will be updated to {getattr(area, key)}")

            else:
                logger.warning(f"尝试更新用餐区域 {area_id} 不支持的字段: {key}")

    except ValueError as ve:  # 捕获模型验证错误
        db.session.rollback()
        raise ValidationError(f"更新区域时数据验证失败: {ve}",
                              error_code=ErrorCode.PARAM_INVALID.value) from ve

    if not updated:
        logger.info(f"没有为用餐区域 {area_id} 提供需要更新的信息。")
        return _serialize_dining_area(area)

    try:
        # updated_at 由模型 onupdate 自动处理
        db.session.commit()
        logger.info(f"用餐区域 {area_id} ('{area.area_name}') 信息更新成功。")
        return _serialize_dining_area(area)
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"更新用餐区域 {area_id} 时发生唯一性冲突: {e}", exc_info=True)
        raise BusinessError(
            f"更新失败，用餐区域名称 '{processed_data.get('area_name')}' 可能已被占用。",
            error_code=ErrorCode.HTTP_CONFLICT.value) from e
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"更新用餐区域 {area_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("更新用餐区域信息失败。", error_code=ErrorCode.DATABASE_ERROR.value) from e


# --- 删除区域 ---
def delete_dining_area(area_id: int) -> bool:
    """
    删除一个用餐区域 (硬删除)。
    """
    area = DiningArea.query.get(area_id)
    if not area:
        raise NotFoundError(f"ID 为 {area_id} 的用餐区域未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    if area.state == DiningAreaState.OCCUPIED:
        raise BusinessError(
            "Dining area is currently occupied and cannot be deleted.",
            error_code=ErrorCode.HTTP_CONFLICT.value)

    # 可选：检查是否有订单关联 (特别是未完成的)
    # has_orders = db.session.query(area.orders.exists()).scalar()
    # if has_orders:
    #     raise BusinessError(...)

    try:
        area_name_copy = area.area_name
        db.session.delete(area)
        db.session.commit()
        logger.info(f"用餐区域 {area_id} ('{area_name_copy}') 已被成功删除。")
        return True
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"删除用餐区域 {area_id} 时发生外键约束错误: {e}", exc_info=True)
        raise BusinessError(f"无法删除用餐区域 '{area.area_name}'，可能仍被订单等数据关联。",
                            error_code=ErrorCode.HTTP_CONFLICT.value) from e
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"删除用餐区域 {area_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("删除用餐区域失败。", error_code=ErrorCode.DATABASE_ERROR.value) from e
