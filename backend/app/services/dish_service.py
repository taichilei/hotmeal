"""
@File       : dish_service.py
@Date       : 2025-03-01 (Refactored & Adapted: 2025-03-01)
@Desc       : 菜品服务模块，适配重构后的 Dish 模型。
              采用 "失败抛异常，成功返数据"模式。

@Version    : 1.2.1 # 版本更新
@Copyright  : Copyright © 2025. All rights reserved.
"""

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.category import Category
from app.models.dish import Dish  # 导入重构后的 Dish 模型
from app.models.tag import Tag
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


def serialize_dish(dish: Dish) -> dict[str, Any]:
    """
    序列化菜品 ORM 对象为字典 (使用模型的 to_dict 方法)。
    """
    if not isinstance(dish, Dish):
        logger.error(f"尝试序列化非 Dish 对象: {type(dish)}")
        return {}
    # 直接调用模型提供的 to_dict 方法
    # 确保 to_dict 返回的 price 是字符串或浮点数，时间戳是 ISO 格式
    return dish.to_dict(include_category_name=True)  # 假设 to_dict 支持此参数


# --- 创建菜品 ---
def create_dish(name: str, price: Decimal | float | str, stock: int,
                category_id: int, image_url: str | None = None,
                sales: int = 0, rating: float | str | None = None,
                description: str | None = None,
                is_available: bool = True,
                tag_names: list[str] | None = None) -> dict[str, Any]:
    """
    创建新菜品。
    """
    # 1. 业务逻辑验证：检查分类是否存在
    category = Category.query.get(category_id)
    if not category:
        # 分类不存在是参数问题，但更接近业务规则（不能创建属于不存在分类的菜品）
        raise BusinessError(f"ID 为 {category_id} 的分类不存在。",
                            error_code=ErrorCode.PARAM_INVALID.value)  # 或者定义一个 CATEGORY_NOT_FOUND 错误码

    # 检查名称唯一性（不区分大小写，忽略空格，排除软删除）
    existing = Dish.query.filter(
        Dish.name.ilike(name.strip()),
        Dish.deleted_at.is_(None)
    ).first()
    if existing:
        raise BusinessError(f"菜品名称 '{name}' 已存在", error_code=409)

    # 2. 创建 Dish 实例
    # 基础验证 (格式、范围) 由模型的 @validates 处理
    try:
        dish = Dish(
            name=name,  # name 的 strip 和长度验证在 @validates('name')
            price=price,  # price 的类型转换和非负验证在 @validates('price')
            stock=stock,  # stock 的整数和非负验证在 @validates('stock')
            category_id=category_id,
            image_url=image_url,
            sales=sales,  # sales 的整数和非负验证在 @validates('sales')
            rating=rating,  # rating 的类型转换和范围验证在 @validates('rating')
            description=description,
            is_available=is_available
        )
    except ValueError as ve:  # 捕获模型 @validates 抛出的 ValueError
        # 将模型的 ValueError 转换为服务的 ValidationError
        raise ValidationError(f"创建菜品时数据验证失败: {ve}",
                              error_code=ErrorCode.PARAM_INVALID.value)

    # 处理标签
    if tag_names:
        tag_objs = []
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            tag_objs.append(tag)
        dish.tags = tag_objs

    # 3. 添加到数据库
    try:
        db.session.add(dish)
        db.session.commit()
        logger.info(f"菜品 '{dish.name}' (ID: {dish.dish_id}) 创建成功。")
        return serialize_dish(dish)  # 返回序列化后的字典
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"创建菜品 '{name}' 时发生数据库约束错误: {e}", exc_info=True)
        raise BusinessError("创建菜品失败，可能名称已存在。", error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"创建菜品 '{name}' 时发生数据库错误: {e}", exc_info=True)
        raise APIException("创建菜品失败，数据库错误。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 查询菜品 ---
def get_dish_by_id(dish_id: int) -> dict[str, Any]:
    """
    根据 ID 获取单个菜品。
    """
    dish = Dish.query.options(db.joinedload(Dish.category)).get(dish_id)
    if not dish:
        logger.warning(f"尝试获取不存在的菜品: dish_id={dish_id}")
        raise NotFoundError('Dish not found',
                            error_code=ErrorCode.DISH_NOT_FOUND.value)

    logger.info(f"成功检索到菜品: dish_id={dish_id}, name='{dish.name}'")
    return serialize_dish(dish)  # 使用序列化函数


def get_available_dishes(category_id: int | None = None) -> list[dict[str, Any]]:
    """
    获取所有可用的菜品（is_available = True），可选按分类过滤。
    """
    try:
        query = Dish.query.options(db.joinedload(Dish.category)).filter(Dish.is_available)

        if category_id is not None:
            # 可选：提前检查分类是否存在
            # if not Category.query.get(category_id):
            #    raise BusinessError(f"分类 ID {category_id} 不存在", ...)
            query = query.filter(Dish.category_id == category_id)

        dishes = query.order_by(Dish.name).all()
        dish_list = [serialize_dish(dish) for dish in dishes]  # 使用序列化函数
        logger.info(f"成功检索到 {len(dish_list)} 个可用菜品。"
                    f"{' 分类 ID: ' + str(category_id) if category_id else ''}")
        return dish_list
    except SQLAlchemyError as e:
        logger.error(f"检索可用菜品列表时发生数据库错误: {e}", exc_info=True)
        raise APIException("获取可用菜品列表失败。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 更新菜品 ---
def update_dish(dish_id: int, update_data: dict[str, Any]) -> dict[str, Any]:
    """
    更新现有菜品的信息。
    """
    dish = Dish.query.get(dish_id)
    if not dish:
        logger.warning(f"尝试更新不存在的菜品: dish_id={dish_id}")
        raise NotFoundError('Dish not found',
                            error_code=ErrorCode.DISH_NOT_FOUND.value)

    updated = False
    processed_data = {k: v for k, v in update_data.items() if v is not None}

    # 处理标签更新
    if 'tag_names' in update_data:
        tag_names = update_data['tag_names']
        if tag_names is None:
            dish.tags = []
        else:
            tag_objs = []
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if not tag_name:
                    continue
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                tag_objs.append(tag)
            dish.tags = tag_objs
        updated = True
        logger.debug(f"Dish {dish_id} tags updated to: {tag_names}")

    # 检查分类 ID 是否有效 (如果提供了 category_id)
    new_category_id = processed_data.get('category_id')
    if new_category_id is not None:
        try:
            cat_id = int(new_category_id)
            if not Category.query.get(cat_id):
                raise BusinessError(f"ID 为 {cat_id} 的分类不存在。",
                                    error_code=ErrorCode.PARAM_INVALID.value)
        except (TypeError, ValueError):
            raise ValidationError("分类 ID 必须是整数。", error_code=ErrorCode.PARAM_INVALID.value)

    # 可选字段更新
    # 若更新名称，检查唯一性（忽略大小写、空格）
    if 'name' in processed_data:
        new_name = processed_data['name'].strip()
        if new_name.lower() != dish.name.lower():
            conflict = Dish.query.filter(
                Dish.name.ilike(new_name),
                Dish.dish_id != dish_id,
                Dish.deleted_at.is_(None)
            ).first()
            if conflict:
                raise BusinessError(f"菜品名称 '{new_name}' 已存在", error_code=409)
            dish.name = new_name
            updated = True
            logger.debug(f"Dish {dish_id} field 'name' set to {new_name}")
        # 跳过后续批量赋值对 name 的处理
        processed_data = {k: v for k, v in processed_data.items() if k != 'name'}

    # 尝试批量设置属性，依赖模型的 @validates 进行验证
    try:
        for key, value in processed_data.items():
            if key == "dish_id":  # 跳过主键
                continue
            # 只有当值与当前值不同时才尝试设置
            if hasattr(dish, key) and getattr(dish, key) != value:
                setattr(dish, key, value)  # 触发模型的 @validates
                updated = True
                logger.debug(f"Dish {dish_id} field '{key}' set to {value}")

    except ValueError as ve:  # 捕获模型 @validates 抛出的 ValueError
        # 回滚可能已部分设置的属性（虽然 SQLAlchemy 通常在 commit 前不写入）
        db.session.rollback()
        raise ValidationError(f"更新菜品时数据验证失败: {ve}",
                              error_code=ErrorCode.PARAM_INVALID.value)

    if not updated:
        logger.info(f"没有为菜品 {dish_id} 提供需要更新的信息。")
        return serialize_dish(dish)

    try:
        # updated_at 由模型 onupdate 自动处理
        db.session.commit()
        logger.info(f"菜品 {dish_id} ('{dish.name}') 信息更新成功。")
        return serialize_dish(dish)  # 返回更新后的数据
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"更新菜品 {dish_id} 时发生数据库约束错误: {e}", exc_info=True)
        raise BusinessError("更新失败，可能菜品名称已被占用。", error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"更新菜品 {dish_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("更新菜品信息失败。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 删除/下架菜品 ---
def set_dish_availability(dish_id: int, is_available: bool) -> bool:
    """
    设置菜品的上架/下架状态。
    """
    dish = Dish.query.get(dish_id)
    if not dish:
        logger.warning(f"尝试设置可用性时未找到菜品: dish_id={dish_id}")
        raise NotFoundError('Dish not found',
                            error_code=ErrorCode.DISH_NOT_FOUND.value)

    if dish.is_available is is_available:
        logger.info(f"菜品 {dish_id} 的可用性已是 {is_available}，无需更改。")
        return True

    try:
        # 调用模型的方法来标记状态，但不 commit
        dish.mark_as_available(is_available)
        db.session.commit()  # 服务层负责 commit
        action = "上架" if is_available else "下架"
        logger.info(f"菜品 {dish_id} ('{dish.name}') 已成功 {action}。")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"设置菜品 {dish_id} 可用性为 {is_available} 时发生数据库错误: {e}",
                     exc_info=True)
        raise APIException("设置菜品可用性失败。", error_code=ErrorCode.DATABASE_ERROR.value)


def delete_dish_permanently(dish_id: int) -> bool:
    """
    永久删除菜品 (硬删除)。
    """
    dish = Dish.query.get(dish_id)
    if not dish:
        logger.warning(f"尝试永久删除不存在的菜品: dish_id={dish_id}")
        raise NotFoundError('Dish not found',
                            error_code=ErrorCode.DISH_NOT_FOUND.value)

    try:
        dish_name_copy = dish.name
        db.session.delete(dish)
        db.session.commit()
        logger.info(f"菜品 {dish_id} ('{dish_name_copy}') 已被永久删除。")
        return True
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"永久删除菜品 {dish_id} 时发生数据库约束错误: {e}", exc_info=True)
        raise BusinessError(f"无法删除菜品 '{dish.name}'，可能仍被订单等数据关联。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"永久删除菜品 {dish_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("永久删除菜品失败。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- (可选) 软删除接口 ---
def soft_delete_dish(dish_id: int) -> bool:
    """
    软删除菜品 (设置 deleted_at 标记并下架)。
    """
    dish = Dish.query.get(dish_id)
    if not dish:
        logger.warning(f"尝试软删除不存在的菜品: dish_id={dish_id}")
        raise NotFoundError('Dish not found',
                            error_code=ErrorCode.DISH_NOT_FOUND.value)

    if dish.deleted_at is not None:
        logger.info(f"菜品 {dish_id} 已被软删除，无需操作。")
        return True  # 幂等性

    try:
        # 调用模型的方法标记，但不 commit
        dish.mark_as_deleted()
        db.session.commit()  # 服务层负责 commit
        logger.info(f"菜品 {dish_id} ('{dish.name}') 已被软删除。")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"软删除菜品 {dish_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("软删除菜品失败。", error_code=ErrorCode.DATABASE_ERROR.value)
