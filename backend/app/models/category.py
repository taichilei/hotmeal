"""
File Name:     /app/models/category.py
Project:       hotmeal
Author:        taichilei
Created:       2025-04-23
Description:   category model
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

# 导入 SQLAlchemy 相关
from sqlalchemy import (  # 添加 Text, Boolean
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship, validates

from app.utils.db import db

logger = logging.getLogger(__name__)


class Category(db.Model):
    """
    分类模型，对应数据库的 'category' 表。
    属性名与列名保持一致。
    """
    __tablename__ = 'category'
    __table_args__ = (
        Index('ix_category_name', 'name'),
        Index('ix_category_parent_id', 'parent_category_id'),  # 建议为外键添加索引
    )

    # --- 使用 Mapped 和 mapped_column ---
    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="分类主键 ID")
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment='分类名称')
    # --- 统一属性名和列名为 description ---
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment='分类描述')
    # --- 统一属性名和列名为 img_url ---
    img_url: Mapped[str | None] = mapped_column(String(255), nullable=True,
                                                   comment='分类图片 URL')
    # --- 时间戳字段 ---
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True,
                                                           comment="删除时间（软删除）")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), onupdate=func.now(),
                                                 comment="最后更新时间")
    # --- 父分类外键 ---
    parent_category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey('category.category_id', name='fk_category_parent_id'),
        nullable=True,
        comment="父分类 ID（构建分类树）"
    )

    # --- 关系定义 ---
    parent_category: Mapped[Optional["Category"]] = relationship(
        'Category',
        remote_side=[category_id],
        backref=backref('subcategories', lazy='dynamic', cascade='all, delete-orphan'),
        # 添加 cascade?
        foreign_keys=[parent_category_id]
    )

    # 与 Dish 的关系 (Dish 模型中使用 backref='category')
    # dishes: Mapped[List["Dish"]] = relationship(back_populates="category", lazy="dynamic") # 如果 Dish 中用 back_populates

    # --- @validates 验证 ---
    @validates('name')
    def validate_name(self, _key, name_value):
        """验证分类名称。"""
        if not name_value or not name_value.strip():
            raise ValueError("分类名称不能为空")
        clean_name = name_value.strip()
        if len(clean_name) > 50:
            raise ValueError("分类名称不能超过50个字符")
        return clean_name

    @validates('img_url')
    def validate_img_url(self, _key, url):
        """验证图片 URL，允许空字符串并自动转换为 None。"""
        if url is None or (isinstance(url, str) and url.strip() == ''):
            return None
        if not isinstance(url, str):
            raise ValueError("图片 URL 必须为字符串")
        if not re.match(r"^https?://\S+$", url):
            raise ValueError("无效的图片 URL 格式")
        if len(url) > 255:
            raise ValueError("图片 URL 不能超过255个字符")
        return url

    # parent_category_id 的存在性检查在服务层进行更可靠

    # --- 实例方法 ---
    def __repr__(self):
        return f"<Category(id={self.category_id}, name='{self.name}')>"

    def to_dict(self, include_subcategories_count: bool = False) -> dict[str, Any]:
        """将分类实例转换为字典。"""
        data = {
            "category_id": self.category_id,
            "name": self.name,
            "description": self.description,
            "img_url": self.img_url,
            "parent_category_id": self.parent_category_id,
            "created_at": self.created_at.astimezone(
                timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.astimezone(
                timezone.utc).isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.astimezone(
                timezone.utc).isoformat() if self.deleted_at else None,
        }
        if include_subcategories_count:
            try:
                # lazy='dynamic' 需要调用 .count()
                data["subcategories_count"] = self.subcategories.filter(
                    Category.deleted_at.is_(None)).count()  # 只计算未删除的子分类
            except Exception as e:
                logger.error(f"计算分类 {self.category_id} 的子分类数量时出错: {e}", exc_info=True)
                data["subcategories_count"] = 0  # 出错时返回 0
        return data

    def mark_as_deleted(self):
        """标记分类为软删除状态 (不 commit)。"""
        if self.deleted_at is None:
            self.deleted_at = datetime.now(timezone.utc)
            logger.info(f"分类 {self.category_id} ('{self.name}') 已标记为软删除。")

    def restore(self):
        """恢复软删除的分类 (不 commit)。"""
        if self.deleted_at is not None:
            self.deleted_at = None
            logger.info(f"分类 {self.category_id} ('{self.name}') 已恢复。")
