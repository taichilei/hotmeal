"""
@File       : category_service.py
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Desc       : 分类服务层，处理分类的增删改查及软删除/恢复逻辑。
              采用 "失败抛异常，成功返数据" 模式，并优化存在性检查。
"""

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.category import Category
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


def _serialize_category(category: Category) -> dict[str, Any]:
    """内部辅助函数，用于序列化 Category 对象。"""
    if not isinstance(category, Category):
        logger.error(f"尝试序列化非 Category 对象: {type(category)}")
        return {}
    # 调用模型自身的 to_dict 方法
    return category.to_dict(include_subcategories_count=True)  # 包含子分类数量


# --- 创建分类 ---
def create_category(name: str, description: str | None = None,
                    img_url: str | None = None,
                    parent_category_id: int | None = None) -> dict[str, Any]:
    """
    创建新分类。
    """
    # 参数清洗：将空字符串转换为 None，避免模型验证失败
    img_url = img_url.strip() if isinstance(img_url, str) else img_url
    if img_url == "":
        img_url = None
    if parent_category_id == "" or parent_category_id is None:
        parent_category_id = None
    clean_name = name.strip() if name else ""
    # 检查名称唯一性 (忽略大小写)
    name_exists = db.session.query(
        Category.query.filter(Category.name.ilike(clean_name)).exists()
    ).scalar()
    if name_exists:
        raise BusinessError(f"分类名称 '{clean_name}' 已存在。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)

    # 检查父分类是否存在 (使用 exists() 查询)
    if parent_category_id is not None:
        if not isinstance(parent_category_id, int):
            raise ValidationError("父分类 ID 必须是整数。", error_code=ErrorCode.PARAM_INVALID.value)
        parent_exists = db.session.query(
            Category.query.filter(Category.category_id == parent_category_id).exists()
        ).scalar()
        if not parent_exists:
            raise BusinessError(f"ID 为 {parent_category_id} 的父分类不存在。",
                                error_code=ErrorCode.PARAM_INVALID.value)
        # 注意：无法在此处可靠地检查循环引用（A->A），因为新 ID 还未生成。

    # 2. 创建 Category 实例 (依赖模型验证)
    try:
        category = Category(
            name=name,  # name 的验证在模型 @validates
            description=description,
            img_url=img_url,  # img_url 的验证在模型 @validates
            parent_category_id=parent_category_id
        )
    except ValueError as ve:  # 捕获模型验证错误
        raise ValidationError(f"创建分类时数据验证失败: {ve}",
                              error_code=ErrorCode.PARAM_INVALID.value)

    # 3. 添加到数据库
    try:
        db.session.add(category)
        db.session.commit()
        logger.info(f"分类 '{category.name}' (ID: {category.category_id}) 创建成功。")
        return _serialize_category(category)  # 返回序列化后的字典
    except IntegrityError as e:  # 捕获数据库层面的唯一性错误
        db.session.rollback()
        logger.error(f"创建分类 '{name}' 时发生数据库约束错误: {e}", exc_info=True)
        raise BusinessError("创建分类失败，名称已存在。", error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"创建分类 '{name}' 时发生数据库错误: {e}", exc_info=True)
        raise APIException("创建分类失败，数据库错误。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 查询分类 ---
def get_category_by_id(category_id: int, include_deleted: bool = False) -> dict[str, Any]:
    """
    根据 ID 获取单个分类。
    """
    query = Category.query.options(
        db.joinedload(Category.parent_category),
    )
    category = query.get(category_id)

    if not category:
        raise NotFoundError("Category not found",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    if not include_deleted and category.deleted_at is not None:
        raise NotFoundError("Category not found",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    logger.info(f"成功检索到分类: ID={category_id}, Name='{category.name}'")
    return _serialize_category(category)


def get_all_categories(include_deleted: bool = False,
                       parent_id: int | None = None) -> list[dict[str, Any]]:
    """
    获取所有分类，可选是否包含软删除的，或按父分类 ID 过滤。
    """
    try:
        query = Category.query.options(db.joinedload(Category.parent_category))

        if not include_deleted:
            query = query.filter(Category.deleted_at.is_(None))

        query = query.filter(Category.parent_category_id == parent_id)

        categories = query.order_by(Category.name).all()
        category_list = [_serialize_category(cat) for cat in categories]
        logger.info(f"成功检索到 {len(category_list)} 个分类。"
                    f"{' (包含已删除)' if include_deleted else ''}"
                    f"{' 父分类 ID: ' + str(parent_id) if parent_id is not None else ' (顶级分类)'}")
        return category_list
    except SQLAlchemyError as e:
        logger.error(f"检索分类列表时发生数据库错误: {e}", exc_info=True)
        raise APIException("获取分类列表失败。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 更新分类 ---
def update_category(category_id: int, update_data: dict[str, Any]) -> dict[str, Any]:
    """
    更新现有分类的信息。
    """
    category = Category.query.get(category_id)
    if not category:
        logger.warning(f"尝试更新不存在的分类: category_id={category_id}")
        raise NotFoundError(f"ID 为 {category_id} 的分类未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    if category.deleted_at is not None:
        raise BusinessError(f"分类 '{category.name}' 已被删除，无法更新。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)

    updated = False
    processed_data = {k: v for k, v in update_data.items() if v is not None}

    # 检查父分类 ID (如果提供了) - 使用 exists()
    new_parent_id = processed_data.get('parent_category_id')
    if new_parent_id is not None:
        if not isinstance(new_parent_id, int):
            raise ValidationError("父分类 ID 必须是整数。", error_code=ErrorCode.PARAM_INVALID.value)
        if new_parent_id == category.category_id:
            raise BusinessError("不能将分类自身设置为其父分类。",
                                error_code=ErrorCode.PARAM_INVALID.value)
        # 使用 exists() 检查父分类是否存在
        parent_exists = db.session.query(
            Category.query.filter(Category.category_id == new_parent_id).exists()
        ).scalar()
        if not parent_exists:
            raise BusinessError(f"ID 为 {new_parent_id} 的父分类不存在。",
                                error_code=ErrorCode.PARAM_INVALID.value)
        # TODO: 更复杂的循环引用检查

    # 检查名称唯一性 (如果提供了 name 且与当前不同)
    new_name = processed_data.get('name')
    if new_name and new_name.strip() != category.name:
        clean_new_name = new_name.strip()
        name_exists = db.session.query(
            Category.query.filter(Category.name.ilike(clean_new_name),
                                  Category.category_id != category_id).exists()
        ).scalar()
        if name_exists:
            raise BusinessError(f"分类名称 '{clean_new_name}' 已被其他分类使用。",
                                error_code=ErrorCode.HTTP_CONFLICT.value)

    # 尝试批量设置属性，依赖模型的 @validates
    allowed_fields = ['name', 'description', 'img_url', 'parent_category_id']
    try:
        for key, value in processed_data.items():
            if key in allowed_fields:
                current_value = getattr(category, key)
                if key == 'parent_category_id':
                    # 处理 None 和数字的比较
                    if current_value != (value if value is not None else None):
                        setattr(category, key, value)
                        updated = True
                elif current_value != value:
                    setattr(category, key, value)
                    updated = True

                if updated:
                    logger.debug(f"Category {category_id} field '{key}' will be updated to {value}")

    except ValueError as ve:  # 捕获模型验证错误
        db.session.rollback()  # 回滚以防部分属性已设置
        raise ValidationError(f"更新分类时数据验证失败: {ve}",
                              error_code=ErrorCode.PARAM_INVALID.value)

    if not updated:
        logger.info(f"没有为分类 {category_id} 提供需要更新的信息。")
        return _serialize_category(category)

    try:
        # updated_at 由模型 onupdate 自动处理
        db.session.commit()
        logger.info(f"分类 {category_id} ('{category.name}') 信息更新成功。")
        return _serialize_category(category)
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"更新分类 {category_id} 时发生数据库约束错误: {e}", exc_info=True)
        raise BusinessError("更新失败，可能分类名称已被占用。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"更新分类 {category_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("更新分类信息失败。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 删除/恢复分类 ---
def soft_delete_category(category_id: int) -> bool:
    """
    软删除分类 (设置 deleted_at 标记)。
    """
    category = Category.query.get(category_id)
    if not category:
        raise NotFoundError(f"ID 为 {category_id} 的分类未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    if category.deleted_at is not None:
        logger.info(f"分类 {category_id} 已处于软删除状态，无需操作。")
        return True

    # 可选：检查子分类或关联菜品
    # ...

    try:
        category.mark_as_deleted()  # 调用模型方法标记
        db.session.commit()
        logger.info(f"分类 {category_id} ('{category.name}') 已被软删除。")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"软删除分类 {category_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("软删除分类失败。", error_code=ErrorCode.DATABASE_ERROR.value)


def restore_category(category_id: int) -> dict[str, Any]:
    """
    恢复软删除的分类 (清除 deleted_at 标记)。
    """
    category = Category.query.get(category_id)
    if not category:
        raise NotFoundError(f"ID 为 {category_id} 的分类未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    if category.deleted_at is None:
        logger.info(f"分类 {category_id} ('{category.name}') 未被软删除，无需恢复。")
        return _serialize_category(category)

    # 可选：检查父分类状态
    # ...

    try:
        category.restore()  # 调用模型方法标记
        db.session.commit()
        logger.info(f"分类 {category_id} ('{category.name}') 已成功恢复。")
        return _serialize_category(category)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"恢复分类 {category_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("恢复分类失败。", error_code=ErrorCode.DATABASE_ERROR.value)


def delete_category_permanently(category_id: int) -> bool:
    """
    永久删除分类 (硬删除)。
    """
    category = Category.query.get(category_id)
    if not category:
        raise NotFoundError(f"ID 为 {category_id} 的分类未找到。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)

    # 检查子分类
    # 使用 exists() 检查更高效
    has_subcategories = db.session.query(category.subcategories.exists()).scalar()
    if has_subcategories:
        logger.warning(f"尝试永久删除有子分类的分类: category_id={category_id}")
        raise BusinessError(f"无法删除分类 '{category.name}'，请先删除其所有子分类。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)

    # 可选：检查关联菜品
    # ...

    try:
        category_name_copy = category.name
        db.session.delete(category)
        db.session.commit()
        logger.info(f"分类 {category_id} ('{category_name_copy}') 已被永久删除。")
        return True
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"永久删除分类 {category_id} 时发生数据库约束错误: {e}", exc_info=True)
        raise BusinessError(f"无法删除分类 '{category.name}'，可能仍被菜品等数据关联。",
                            error_code=ErrorCode.HTTP_CONFLICT.value)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"永久删除分类 {category_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("永久删除分类失败。", error_code=ErrorCode.DATABASE_ERROR.value)
